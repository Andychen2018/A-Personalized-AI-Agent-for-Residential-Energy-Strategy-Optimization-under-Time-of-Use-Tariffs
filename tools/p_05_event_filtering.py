#!/usr/bin/env python3
"""
Agent V2 - Event Filtering and Constraint Management System
==========================================================

This module provides comprehensive event filtering functionality:
- User constraint parsing and appliance constraint generation
- Reschedulable event extraction (is_reschedulable=True)
- Minimum duration filtering
- Time-of-Use (TOU) tariff-based filtering
- Support for single household and batch processing

Features:
- Natural language constraint parsing with LLM
- Default appliance constraint generation
- Multi-stage event filtering pipeline
- Support for multiple tariff types (UK, Germany, California)
- Comprehensive output file organization

Updated for new path structure:
- output/05_constraints/{house_id}/appliance_constraints_revise_by_llm.json
- output/04_min_duration_filter/{house_id}/min_duration_filtered_{house_id}.csv
- output/04_TOU_filter/{tariff_type}/{house_id}/tou_filtered_{house_id}.csv
"""

import os
import pandas as pd
import json
import re
import sys
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    from .llm_proxy import GPTProxyClient
except ImportError:
    from llm_proxy import GPTProxyClient


class ApplianceConstraintManager:
    """Manage appliance constraints and user input parsing"""

    def __init__(self):
        # Updated default constraints based on previous implementation
        self.default_constraints = {
            "forbidden_time": [["00:00", "06:30"], ["23:00", "24:00"]],
            "latest_finish": "24:00",
            "shift_rule": "only_delay",
            "min_duration": 5
        }

        # Appliance-specific constraints
        self.appliance_specific_constraints = {
            "Washing Machine": {
                "forbidden_time": [["07:00", "22:00"]],
                "latest_finish": "38:00",  # Next day 14:00
                "shift_rule": "only_delay",
                "min_duration": 60
            },
            "Tumble Dryer": {
                "forbidden_time": [["07:00", "22:00"]],
                "latest_finish": "38:00",  # Next day 14:00
                "shift_rule": "only_delay",
                "min_duration": 120
            },
            "Dishwasher": {
                "forbidden_time": [["06:00", "22:00"]],
                "latest_finish": "38:00",  # Next day 14:00
                "shift_rule": "only_delay",
                "min_duration": 90
            },
            "Fridge": {
                "forbidden_time": [],
                "latest_finish": "26:00",  # Next day 02:00
                "shift_rule": "only_delay",
                "min_duration": 30
            },
            "Electric Heater": {
                "forbidden_time": [["08:00", "22:00"]],
                "latest_finish": "25:00",  # Next day 01:00
                "shift_rule": "only_delay",
                "min_duration": 15
            }
        }
    
    def generate_default_constraints(self, appliance_summary: Dict) -> Dict:
        """Generate default constraints based on appliance summary"""
        constraints = {}

        for appliance_name in appliance_summary.get('appliance_names', []):
            # Clean appliance name (remove numbering like "(1)", "(2)")
            clean_name = re.sub(r'\s*\(\d+\)$', '', appliance_name)

            # Find matching appliance-specific constraint
            matched_constraint = None
            for specific_name, specific_constraint in self.appliance_specific_constraints.items():
                if specific_name.lower() in clean_name.lower() or clean_name.lower() in specific_name.lower():
                    matched_constraint = specific_constraint.copy()
                    break

            # Use default constraint if no specific match found
            if matched_constraint is None:
                matched_constraint = self.default_constraints.copy()

            constraints[appliance_name] = matched_constraint

        return constraints
    
    def parse_user_constraints_with_llm(self, user_input: str, current_constraints: Dict) -> Tuple[Dict, bool]:
        """Parse natural language user constraints using LLM and update appliance constraints"""
        if not user_input.strip():
            return current_constraints, True

        try:
            # Initialize LLM client
            llm_client = GPTProxyClient()

            # Create prompt for LLM
            appliance_list = list(current_constraints.keys())

            prompt = f"""
You are an expert in home appliance scheduling constraints. Please analyze the user's natural language instruction and convert it into structured JSON constraints.

Available appliances: {appliance_list}

Current constraint format for each appliance:
{{
    "forbidden_time": [["start_time", "end_time"], ...],  // Time ranges when appliance cannot run
    "latest_finish": "HH:MM",  // Latest time the appliance can finish (use 24+ for next day)
    "shift_rule": "only_delay",  // How the appliance can be rescheduled
    "min_duration": minutes  // Minimum duration in minutes
}}

User instruction: "{user_input}"

Please return ONLY a JSON object with the updated constraints for the mentioned appliances. Keep existing constraints for appliances not mentioned. Use 24-hour format (e.g., "14:00" for 2 PM, "26:00" for 2 AM next day).

Example response:
{{
    "Washing Machine": {{
        "forbidden_time": [["07:00", "22:00"]],
        "latest_finish": "38:00",
        "shift_rule": "only_delay",
        "min_duration": 60
    }}
}}
"""

            # Call LLM
            response = llm_client.call_gpt(prompt)

            if response and response.strip():
                try:
                    # Parse LLM response
                    llm_constraints = json.loads(response.strip())

                    # Update constraints with LLM results
                    updated_constraints = current_constraints.copy()
                    for appliance_name, new_constraint in llm_constraints.items():
                        if appliance_name in updated_constraints:
                            updated_constraints[appliance_name].update(new_constraint)
                            # Store original user input
                            updated_constraints[appliance_name]['user_input'] = user_input

                    logger.info("✅ LLM successfully parsed user constraints")
                    return updated_constraints, True

                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse LLM response as JSON: {e}")
                    return self._fallback_parse_constraints(user_input, current_constraints), False
            else:
                logger.error("❌ Empty response from LLM")
                return self._fallback_parse_constraints(user_input, current_constraints), False

        except Exception as e:
            logger.error(f"❌ LLM constraint parsing failed: {e}")
            return self._fallback_parse_constraints(user_input, current_constraints), False

    def _fallback_parse_constraints(self, user_input: str, current_constraints: Dict) -> Dict:
        """Fallback constraint parsing using simple pattern matching"""
        logger.info("🔄 Using fallback constraint parsing...")

        updated_constraints = current_constraints.copy()
        lines = user_input.lower().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Find mentioned appliances
            mentioned_appliances = []
            for appliance_name in updated_constraints.keys():
                if appliance_name.lower() in line:
                    mentioned_appliances.append(appliance_name)

            # Apply simple parsing rules
            for appliance_name in mentioned_appliances:
                # Parse forbidden time patterns
                if 'forbidden' in line or 'not run between' in line:
                    # Extract time ranges - simplified pattern
                    if '23:30' in line and '06:00' in line:
                        updated_constraints[appliance_name]['forbidden_time'] = [["23:30", "06:00"]]
                    elif '07:00' in line and '22:00' in line:
                        updated_constraints[appliance_name]['forbidden_time'] = [["07:00", "22:00"]]

                # Parse latest finish time
                if 'latest_finish' in line or 'finish' in line:
                    if '14:00' in line and 'next day' in line:
                        updated_constraints[appliance_name]['latest_finish'] = "38:00"
                    elif '38:00' in line:
                        updated_constraints[appliance_name]['latest_finish'] = "38:00"

                # Parse minimum duration
                if 'min' in line and 'duration' in line:
                    duration_match = re.search(r'(\d+)\s*min', line)
                    if duration_match:
                        updated_constraints[appliance_name]['min_duration'] = int(duration_match.group(1))

                # Store user input
                updated_constraints[appliance_name]['user_input'] = user_input

        return updated_constraints


class EventFilter:
    """Handle multi-stage event filtering"""
    
    def __init__(self):
        self.tariff_configs = {
            "UK": {
                "Standard": {"all_day": 0.15},
                "Economy_7": {
                    "peak": {"hours": list(range(7, 24)), "rate": 0.18},
                    "off_peak": {"hours": list(range(0, 7)), "rate": 0.09}
                },
                "Economy_10": {
                    "peak": {"hours": list(range(7, 14)) + list(range(20, 24)), "rate": 0.18},
                    "off_peak": {"hours": list(range(0, 7)) + list(range(14, 20)), "rate": 0.09}
                }
            },
            "Germany": {
                "Germany_Variable_Base": {"all_day": 0.25},
                "Germany_Variable": {
                    "peak": {"hours": list(range(6, 22)), "rate": 0.30},
                    "off_peak": {"hours": list(range(22, 24)) + list(range(0, 6)), "rate": 0.20}
                }
            },
            "California": {
                "TOU_D_Base": {"all_day": 0.22},
                "TOU_D": {
                    "summer_peak": {"hours": list(range(16, 21)), "rate": 0.45, "months": [6, 7, 8, 9]},
                    "summer_off_peak": {"hours": list(range(0, 16)) + list(range(21, 24)), "rate": 0.25, "months": [6, 7, 8, 9]},
                    "winter_peak": {"hours": list(range(17, 20)), "rate": 0.35, "months": [1, 2, 3, 4, 5, 10, 11, 12]},
                    "winter_off_peak": {"hours": list(range(0, 17)) + list(range(20, 24)), "rate": 0.20, "months": [1, 2, 3, 4, 5, 10, 11, 12]}
                }
            }
        }
    
    def extract_reschedulable_events(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """Extract events where is_reschedulable=True"""
        reschedulable_events = events_df[events_df['is_reschedulable'] == True].copy()
        logger.info(f"Extracted {len(reschedulable_events)} reschedulable events from {len(events_df)} total events")
        return reschedulable_events
    
    def filter_by_min_duration(self, events_df: pd.DataFrame, constraints: Dict) -> pd.DataFrame:
        """Filter events based on minimum duration constraints"""
        filtered_events = []
        
        for _, event in events_df.iterrows():
            appliance_name = event['appliance_name']
            duration_minutes = event['duration_minutes']
            
            # Find constraint for this appliance
            constraint = None
            for constraint_name, constraint_data in constraints.items():
                if constraint_name in appliance_name or appliance_name in constraint_name:
                    constraint = constraint_data
                    break
            
            # Use default if no specific constraint found
            if constraint is None:
                min_duration = 30  # Default 30 minutes
            else:
                min_duration = constraint.get('min_duration_minutes', 30)
            
            # Keep event if it meets minimum duration
            if duration_minutes >= min_duration:
                filtered_events.append(event)
        
        filtered_df = pd.DataFrame(filtered_events)
        logger.info(f"Duration filtering: {len(filtered_df)} events remain from {len(events_df)} events")
        return filtered_df
    
    def get_event_tariff_rate(self, event_time: datetime, tariff_type: str, tariff_name: str) -> float:
        """Get tariff rate for a specific event time"""
        if tariff_type not in self.tariff_configs:
            return 0.20  # Default rate
        
        tariff_config = self.tariff_configs[tariff_type].get(tariff_name, {})
        
        # Handle flat rate tariffs
        if 'all_day' in tariff_config:
            return tariff_config['all_day']
        
        # Handle time-of-use tariffs
        hour = event_time.hour
        month = event_time.month
        
        for period_name, period_config in tariff_config.items():
            period_hours = period_config.get('hours', [])
            period_months = period_config.get('months', list(range(1, 13)))
            
            if hour in period_hours and month in period_months:
                return period_config.get('rate', 0.20)
        
        return 0.20  # Default rate
    
    def filter_by_tou_optimization(self, events_df: pd.DataFrame, tariff_type: str) -> pd.DataFrame:
        """Filter events based on TOU optimization potential"""
        if tariff_type not in self.tariff_configs:
            logger.warning(f"Unknown tariff type: {tariff_type}")
            return events_df
        
        optimizable_events = []
        
        for _, event in events_df.iterrows():
            event_time = pd.to_datetime(event['start_time'])
            
            # Get rates for all available tariffs in this type
            tariff_rates = {}
            for tariff_name in self.tariff_configs[tariff_type].keys():
                tariff_rates[tariff_name] = self.get_event_tariff_rate(event_time, tariff_type, tariff_name)
            
            # Find the minimum rate
            min_rate = min(tariff_rates.values())
            current_rate = max(tariff_rates.values())  # Assume worst case as current
            
            # Keep event if there's potential for savings (at least 10% difference)
            if (current_rate - min_rate) / current_rate >= 0.1:
                event_copy = event.copy()
                event_copy['current_rate'] = current_rate
                event_copy['optimal_rate'] = min_rate
                event_copy['potential_savings'] = current_rate - min_rate
                optimizable_events.append(event_copy)
        
        filtered_df = pd.DataFrame(optimizable_events)
        logger.info(f"TOU filtering: {len(filtered_df)} optimizable events from {len(events_df)} events")
        return filtered_df


def process_single_household_constraints(
    house_id: str,
    user_input: str = "",
    input_dir: str = "./output/04_appliance_summary",
    output_dir: str = "./output/05_constraints"
) -> Optional[Dict]:
    """Process appliance constraints for a single household"""

    print(f"🏠 Processing constraints for {house_id.upper()}...")

    # Load appliance summary
    summary_file = os.path.join(input_dir, "UK", house_id, "appliance_summary.json")
    if not os.path.exists(summary_file):
        print(f"❌ Appliance summary not found: {summary_file}")
        return None

    with open(summary_file, 'r') as f:
        appliance_summary = json.load(f)

    # Generate constraints
    constraint_manager = ApplianceConstraintManager()
    default_constraints = constraint_manager.generate_default_constraints(appliance_summary)

    # Parse user input and update constraints
    final_constraints = constraint_manager.parse_user_constraints(user_input, default_constraints)

    # Create output directory
    house_output_dir = os.path.join(output_dir, house_id)
    os.makedirs(house_output_dir, exist_ok=True)

    # Save constraints
    constraints_file = os.path.join(house_output_dir, "appliance_constraints_revise_by_llm.json")
    constraint_data = {
        "house_id": house_id,
        "generated_time": datetime.now().isoformat(),
        "user_input": user_input,
        "appliance_constraints": final_constraints,
        "summary": {
            "total_appliances": len(final_constraints),
            "constrained_appliances": len([c for c in final_constraints.values() if c['user_constraints']])
        }
    }

    with open(constraints_file, 'w') as f:
        json.dump(constraint_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Constraints saved to: {constraints_file}")
    print(f"📊 Generated constraints for {len(final_constraints)} appliances")

    return constraint_data


def process_single_household_filtering(
    house_id: str,
    tariff_types: List[str] = ["UK", "Germany", "California"],
    input_dir: str = "./output/02_event_segments",
    constraints_dir: str = "./output/05_constraints",
    min_duration_output_dir: str = "./output/04_min_duration_filter",
    tou_output_dir: str = "./output/04_TOU_filter"
) -> Dict:
    """Process event filtering for a single household"""

    print(f"🔄 Processing event filtering for {house_id.upper()}...")

    # Load event segments
    events_file = os.path.join(input_dir, house_id, f"02_appliance_event_segments_id_{house_id}.csv")
    if not os.path.exists(events_file):
        print(f"❌ Events file not found: {events_file}")
        return {}

    # Load events
    events_df = pd.read_csv(events_file)

    # Standardize column names
    if 'appliance_ID' in events_df.columns:
        events_df = events_df.rename(columns={'appliance_ID': 'appliance_id'})

    print(f"📊 Loaded {len(events_df)} total events")

    # Load constraints
    constraints_file = os.path.join(constraints_dir, house_id, "appliance_constraints_revise_by_llm.json")
    constraints = {}
    if os.path.exists(constraints_file):
        with open(constraints_file, 'r') as f:
            constraint_data = json.load(f)
            constraints = constraint_data.get('appliance_constraints', {})

    # Initialize event filter
    event_filter = EventFilter()

    # Step 1: Extract reschedulable events
    reschedulable_events = event_filter.extract_reschedulable_events(events_df)

    # Step 2: Filter by minimum duration
    duration_filtered_events = event_filter.filter_by_min_duration(reschedulable_events, constraints)

    # Save minimum duration filtered events
    min_duration_dir = os.path.join(min_duration_output_dir, house_id)
    os.makedirs(min_duration_dir, exist_ok=True)

    min_duration_file = os.path.join(min_duration_dir, f"min_duration_filtered_{house_id}.csv")
    duration_filtered_events.to_csv(min_duration_file, index=False)
    print(f"✅ Min duration filtered events saved: {min_duration_file}")

    # Step 3: Filter by TOU optimization for each tariff type
    tou_results = {}

    for tariff_type in tariff_types:
        print(f"🔄 Processing TOU filtering for {tariff_type}...")

        tou_filtered_events = event_filter.filter_by_tou_optimization(duration_filtered_events, tariff_type)

        # Save TOU filtered events
        tou_tariff_dir = os.path.join(tou_output_dir, tariff_type, house_id)
        os.makedirs(tou_tariff_dir, exist_ok=True)

        tou_file = os.path.join(tou_tariff_dir, f"tou_filtered_{house_id}.csv")
        tou_filtered_events.to_csv(tou_file, index=False)

        tou_results[tariff_type] = {
            "file_path": tou_file,
            "event_count": len(tou_filtered_events),
            "potential_savings": tou_filtered_events['potential_savings'].sum() if len(tou_filtered_events) > 0 else 0
        }

        print(f"✅ {tariff_type} TOU filtered events saved: {tou_file}")
        print(f"📊 {len(tou_filtered_events)} optimizable events found")

    results = {
        "house_id": house_id,
        "total_events": len(events_df),
        "reschedulable_events": len(reschedulable_events),
        "min_duration_filtered": len(duration_filtered_events),
        "tou_results": tou_results
    }

    print(f"🎉 Event filtering completed for {house_id.upper()}!")
    return results


def batch_process_constraints(
    house_data_dict: Dict,
    user_inputs: Dict[str, str] = None,
    input_dir: str = "./output/04_appliance_summary",
    output_dir: str = "./output/05_constraints"
) -> Dict:
    """Batch process appliance constraints for multiple households"""

    if user_inputs is None:
        user_inputs = {}

    print(f"🚀 Starting batch constraint processing...")
    print(f"🏠 Target households: {len(house_data_dict)}")
    print("=" * 80)

    results = {}
    failed_houses = []

    for i, house_id in enumerate(house_data_dict.keys(), 1):
        try:
            print(f"\n[{i}/{len(house_data_dict)}] Processing {house_id}...")

            user_input = user_inputs.get(house_id, "")
            result = process_single_household_constraints(
                house_id=house_id,
                user_input=user_input,
                input_dir=input_dir,
                output_dir=output_dir
            )

            if result:
                results[house_id] = result
                print(f"✅ {house_id} completed successfully!")
            else:
                failed_houses.append(house_id)
                print(f"❌ Failed to process {house_id}")

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    print(f"\n🎉 Batch constraint processing completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for house in failed_houses:
            print(f"  - {house}")

    return results


def batch_process_filtering(
    house_data_dict: Dict,
    tariff_types: List[str] = ["UK", "Germany", "California"],
    input_dir: str = "./output/02_event_segments",
    constraints_dir: str = "./output/05_constraints",
    min_duration_output_dir: str = "./output/04_min_duration_filter",
    tou_output_dir: str = "./output/04_TOU_filter"
) -> Dict:
    """Batch process event filtering for multiple households"""

    print(f"🚀 Starting batch event filtering...")
    print(f"🏠 Target households: {len(house_data_dict)}")
    print(f"📊 Tariff types: {tariff_types}")
    print("=" * 80)

    results = {}
    failed_houses = []

    for i, house_id in enumerate(house_data_dict.keys(), 1):
        try:
            print(f"\n[{i}/{len(house_data_dict)}] Processing {house_id}...")

            result = process_single_household_filtering(
                house_id=house_id,
                tariff_types=tariff_types,
                input_dir=input_dir,
                constraints_dir=constraints_dir,
                min_duration_output_dir=min_duration_output_dir,
                tou_output_dir=tou_output_dir
            )

            if result:
                results[house_id] = result
                print(f"✅ {house_id} completed successfully!")
            else:
                failed_houses.append(house_id)
                print(f"❌ Failed to process {house_id}")

        except Exception as e:
            print(f"❌ Error processing {house_id}: {str(e)}")
            failed_houses.append(house_id)
            continue

        print("-" * 80)

    # Generate batch summary
    print(f"\n🎉 Batch event filtering completed!")
    print(f"✅ Successfully processed: {len(results)} households")
    if failed_houses:
        print(f"❌ Failed to process: {len(failed_houses)} households")
        for house in failed_houses:
            print(f"  - {house}")

    # Calculate overall statistics
    if results:
        total_events = sum(r['total_events'] for r in results.values())
        total_reschedulable = sum(r['reschedulable_events'] for r in results.values())
        total_min_duration_filtered = sum(r['min_duration_filtered'] for r in results.values())

        print(f"\n📊 Overall Statistics:")
        print(f"  • Total events processed: {total_events:,}")
        print(f"  • Reschedulable events: {total_reschedulable:,}")
        print(f"  • Min duration filtered: {total_min_duration_filtered:,}")

        for tariff_type in tariff_types:
            tariff_events = sum(r['tou_results'].get(tariff_type, {}).get('event_count', 0) for r in results.values())
            tariff_savings = sum(r['tou_results'].get(tariff_type, {}).get('potential_savings', 0) for r in results.values())
            print(f"  • {tariff_type} optimizable events: {tariff_events:,} (${tariff_savings:.2f} potential savings)")

    print("=" * 80)

    return results
