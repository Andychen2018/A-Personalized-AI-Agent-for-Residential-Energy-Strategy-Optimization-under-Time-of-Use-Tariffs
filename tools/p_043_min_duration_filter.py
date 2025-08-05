#!/usr/bin/env python3
"""
Agent V2 - Minimum Duration Event Filter
========================================

This module implements the second step of the event filtering pipeline:
1. Load appliance constraints from output/04_user_constraints/{house_id}/appliance_constraints_revise_by_llm.json
2. Load event segments from output/02_event_segments/{house_id}/02_appliance_event_segments_id_{house_id}.csv
3. Extract reschedulable events (is_reschedulable=True)
4. Apply minimum duration filtering by modifying is_reschedulable attribute
5. Save filtered results to output/04_min_duration_filter/{house_id}/min_duration_filtered_{house_id}.csv

Features:
- Single household and batch processing support
- Preserves all events while updating reschedulable status
- Detailed filtering statistics and reporting
- Support for different duration column name variations
"""

import os
import sys
import json
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory and parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)


class MinDurationEventFilter:
    """Filter events based on minimum duration constraints"""
    
    def __init__(self):
        self.duration_column_names = ['duration(min)', 'duration_minutes', 'duration', 'Duration']
    
    def load_appliance_constraints(self, house_id: str, constraints_dir: str = None) -> Optional[Dict]:
        """Load appliance constraints for a specific house"""

        # Auto-detect constraints directory if not provided
        if constraints_dir is None:
            possible_paths = [
                "./output/04_user_constraints",
                "../Agent_V2/output/04_user_constraints",
                "./Agent_V2/output/04_user_constraints",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "04_user_constraints")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    constraints_dir = path
                    break
            if constraints_dir is None:
                constraints_dir = "./output/04_user_constraints"

        constraints_file = os.path.join(constraints_dir, house_id, "appliance_constraints_revise_by_llm.json")
        
        if not os.path.exists(constraints_file):
            print(f"❌ Constraints file not found: {constraints_file}")
            return None
        
        try:
            with open(constraints_file, 'r', encoding='utf-8') as f:
                constraint_data = json.load(f)
            
            # Extract appliance constraints
            appliance_constraints = constraint_data.get('appliance_constraints', {})
            print(f"✅ Loaded constraints for {len(appliance_constraints)} appliances from {house_id}")
            return appliance_constraints
            
        except Exception as e:
            print(f"❌ Error loading constraints from {constraints_file}: {e}")
            return None
    
    def load_event_segments(self, house_id: str, events_dir: str = None) -> Optional[pd.DataFrame]:
        """Load event segments for a specific house"""

        # Auto-detect events directory if not provided
        if events_dir is None:
            possible_paths = [
                "./output/02_event_segments",
                "../Agent_V2/output/02_event_segments",
                "./Agent_V2/output/02_event_segments",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "02_event_segments")
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    events_dir = path
                    break
            if events_dir is None:
                events_dir = "./output/02_event_segments"

        events_file = os.path.join(events_dir, house_id, f"02_appliance_event_segments_id_{house_id}.csv")
        
        if not os.path.exists(events_file):
            print(f"❌ Events file not found: {events_file}")
            return None
        
        try:
            events_df = pd.read_csv(events_file)
            
            # Standardize column names
            if 'appliance_ID' in events_df.columns:
                events_df = events_df.rename(columns={'appliance_ID': 'appliance_id'})
            
            print(f"✅ Loaded {len(events_df)} events from {house_id}")
            return events_df
            
        except Exception as e:
            print(f"❌ Error loading events from {events_file}: {e}")
            return None
    
    def find_duration_column(self, events_df: pd.DataFrame) -> Optional[str]:
        """Find the duration column in the events dataframe"""
        
        for col_name in self.duration_column_names:
            if col_name in events_df.columns:
                print(f"📊 Found duration column: {col_name}")
                return col_name

        print(f"❌ No duration column found. Available columns: {list(events_df.columns)}")
        return None
    
    def apply_min_duration_filter(self, events_df: pd.DataFrame, appliance_constraints: Dict) -> Tuple[pd.DataFrame, Dict]:
        """Apply minimum duration filtering to events"""
        
        # Find duration column
        duration_col = self.find_duration_column(events_df)
        if duration_col is None:
            return events_df, {}
        
        # Create a copy to avoid modifying the original
        filtered_df = events_df.copy()
        
        # Statistics tracking
        stats = {
            'total_events': len(filtered_df),
            'initial_reschedulable': len(filtered_df[filtered_df['is_reschedulable'] == True]),
            'updated_to_non_reschedulable': 0,
            'appliance_stats': {}
        }
        
        # Apply filtering for each event
        for idx, event in filtered_df.iterrows():
            # Only process events that are currently reschedulable
            if event['is_reschedulable'] == True:
                appliance_name = event['appliance_name']
                duration_minutes = event[duration_col]
                
                # Find minimum duration constraint for this appliance
                min_duration = self._get_min_duration_for_appliance(appliance_name, appliance_constraints)
                
                # Track appliance statistics
                if appliance_name not in stats['appliance_stats']:
                    stats['appliance_stats'][appliance_name] = {
                        'total_reschedulable': 0,
                        'filtered_out': 0,
                        'min_duration_constraint': min_duration
                    }
                
                stats['appliance_stats'][appliance_name]['total_reschedulable'] += 1
                
                # Check if event meets minimum duration requirement
                if duration_minutes < min_duration:
                    # Update is_reschedulable to False
                    filtered_df.at[idx, 'is_reschedulable'] = False
                    stats['updated_to_non_reschedulable'] += 1
                    stats['appliance_stats'][appliance_name]['filtered_out'] += 1
        
        # Calculate final statistics
        stats['final_reschedulable'] = len(filtered_df[filtered_df['is_reschedulable'] == True])
        stats['filtering_efficiency'] = (stats['updated_to_non_reschedulable'] / stats['initial_reschedulable'] * 100) if stats['initial_reschedulable'] > 0 else 0
        
        print(f"📊 Min duration filtering completed:")
        print(f"  • Total events: {stats['total_events']:,}")
        print(f"  • Initial reschedulable: {stats['initial_reschedulable']:,}")
        print(f"  • Updated to non-reschedulable: {stats['updated_to_non_reschedulable']:,}")
        print(f"  • Final reschedulable: {stats['final_reschedulable']:,}")
        print(f"  • Filtering efficiency: {stats['filtering_efficiency']:.1f}%")
        
        return filtered_df, stats
    
    def _get_min_duration_for_appliance(self, appliance_name: str, appliance_constraints: Dict) -> int:
        """Get minimum duration constraint for a specific appliance"""
        
        # Direct match
        if appliance_name in appliance_constraints:
            return appliance_constraints[appliance_name].get('min_duration', 5)
        
        # Fuzzy match for appliance names
        for constraint_name, constraint_data in appliance_constraints.items():
            if constraint_name.lower() in appliance_name.lower() or appliance_name.lower() in constraint_name.lower():
                return constraint_data.get('min_duration', 5)
        
        # Default minimum duration
        return 5
    
    def save_filtered_events(self, filtered_df: pd.DataFrame, house_id: str, 
                           output_dir: str = "./output/04_min_duration_filter") -> str:
        """Save filtered events to file"""
        
        # Create output directory
        house_output_dir = os.path.join(output_dir, house_id)
        os.makedirs(house_output_dir, exist_ok=True)
        
        # Save filtered events
        output_file = os.path.join(house_output_dir, f"min_duration_filtered_{house_id}.csv")
        filtered_df.to_csv(output_file, index=False)
        
        print(f"✅ Filtered events saved to: {output_file}")
        return output_file
    
    def process_single_household(self, house_id: str,
                               constraints_dir: str = None,
                               events_dir: str = None,
                               output_dir: str = None) -> Optional[Dict]:
        """Process minimum duration filtering for a single household"""
        
        print(f"🏠 Processing minimum duration filtering for {house_id.upper()}...")
        
        # Step 1: Load appliance constraints
        appliance_constraints = self.load_appliance_constraints(house_id, constraints_dir)
        if not appliance_constraints:
            print(f"❌ Failed to load constraints for {house_id}")
            return None
        
        # Step 2: Load event segments
        events_df = self.load_event_segments(house_id, events_dir)
        if events_df is None:
            print(f"❌ Failed to load events for {house_id}")
            return None
        
        # Step 3: Apply minimum duration filtering
        filtered_df, stats = self.apply_min_duration_filter(events_df, appliance_constraints)
        
        # Step 4: Save filtered events
        output_file = self.save_filtered_events(filtered_df, house_id, output_dir)
        
        # Step 5: Display results
        print(f"📊 Filtering results for {house_id}:")
        print(f"  • Total events: {stats['total_events']:,}")
        print(f"  • Initial reschedulable events: {stats['initial_reschedulable']:,}")
        print(f"  • Events updated to non-reschedulable: {stats['updated_to_non_reschedulable']:,}")
        print(f"  • Final reschedulable events: {stats['final_reschedulable']:,}")
        print(f"  • Filtering efficiency: {stats['filtering_efficiency']:.1f}%")
        
        # Display appliance-specific statistics
        print(f"\n📋 Appliance-specific filtering:")
        for appliance_name, appliance_stat in stats['appliance_stats'].items():
            if appliance_stat['total_reschedulable'] > 0:
                efficiency = (appliance_stat['filtered_out'] / appliance_stat['total_reschedulable'] * 100)
                print(f"  • {appliance_name}: {appliance_stat['filtered_out']}/{appliance_stat['total_reschedulable']} filtered ({efficiency:.1f}%), min_duration={appliance_stat['min_duration_constraint']}min")
        
        return {
            "house_id": house_id,
            "output_file": output_file,
            "statistics": stats,
            "appliance_constraints_count": len(appliance_constraints)
        }
    
    def process_batch_households(self, house_list: List[str],
                               constraints_dir: str = "./output/04_user_constraints",
                               events_dir: str = "./output/02_event_segments", 
                               output_dir: str = "./output/04_min_duration_filter") -> Dict:
        """Process minimum duration filtering for multiple households"""
        
        print(f"🚀 Starting batch minimum duration filtering...")
        print(f"🏠 Target households: {len(house_list)}")
        print("=" * 80)
        
        results = {}
        failed_houses = []
        
        for i, house_id in enumerate(house_list, 1):
            try:
                print(f"\n[{i}/{len(house_list)}] Processing {house_id}...")
                
                result = self.process_single_household(
                    house_id=house_id,
                    constraints_dir=constraints_dir,
                    events_dir=events_dir,
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
        
        # Generate batch summary
        print(f"\n🎉 Batch minimum duration filtering completed!")
        print(f"✅ Successfully processed: {len(results)} households")
        if failed_houses:
            print(f"❌ Failed to process: {len(failed_houses)} households")
            for house in failed_houses:
                print(f"  - {house}")
        
        # Calculate overall statistics
        if results:
            total_events = sum(r['statistics']['total_events'] for r in results.values())
            total_initial_reschedulable = sum(r['statistics']['initial_reschedulable'] for r in results.values())
            total_updated = sum(r['statistics']['updated_to_non_reschedulable'] for r in results.values())
            total_final_reschedulable = sum(r['statistics']['final_reschedulable'] for r in results.values())
            
            print(f"\n📊 Overall Statistics:")
            print(f"  • Total events processed: {total_events:,}")
            print(f"  • Initial reschedulable events: {total_initial_reschedulable:,}")
            print(f"  • Events updated to non-reschedulable: {total_updated:,}")
            print(f"  • Final reschedulable events: {total_final_reschedulable:,}")
            print(f"  • Overall filtering efficiency: {(total_updated/total_initial_reschedulable*100):.1f}%")
        
        print("=" * 80)

        # Generate detailed results table
        if results:
            self._generate_batch_results_table(results)

        return results

    def _generate_batch_results_table(self, results: Dict):
        """Generate detailed batch processing results table"""

        print(f"\n📊 Batch Minimum Duration Filtering Results Summary")
        print("=" * 100)

        # Collect table data
        table_data = []
        for house_id, result in results.items():
            if result and 'statistics' in result:
                stats = result['statistics']
                table_data.append({
                    'House_ID': house_id,
                    'Total_Events': stats['total_events'],
                    'Input_Reschedulable': stats['initial_reschedulable'],
                    'Final_Reschedulable': stats['final_reschedulable'],
                    'Events_Filtered_Out': stats['updated_to_non_reschedulable'],
                    'Filter_Efficiency_%': round(stats['filtering_efficiency'], 1)
                })

        if table_data:
            # Print table header
            print(f"{'House_ID':<10} {'Total_Events':<13} {'Input_Reschedulable':<18} {'Final_Reschedulable':<17} {'Events_Filtered_Out':<19} {'Filter_Efficiency_%':<18}")
            print("-" * 100)

            # Print table rows
            for row in table_data:
                print(f"{row['House_ID']:<10} {row['Total_Events']:>13,} {row['Input_Reschedulable']:>18,} {row['Final_Reschedulable']:>17,} {row['Events_Filtered_Out']:>19,} {row['Filter_Efficiency_%']:>18}")

            print("-" * 100)

            # Calculate and print summary
            total_houses = len(table_data)
            total_events = sum(row['Total_Events'] for row in table_data)
            total_before = sum(row['Input_Reschedulable'] for row in table_data)
            total_after = sum(row['Final_Reschedulable'] for row in table_data)
            total_filtered = sum(row['Events_Filtered_Out'] for row in table_data)
            avg_efficiency = sum(row['Filter_Efficiency_%'] for row in table_data) / total_houses

            print(f"{'TOTAL':<10} {total_events:>13,} {total_before:>18,} {total_after:>17,} {total_filtered:>19,} {avg_efficiency:>18.1f}")
            print("=" * 100)

            print(f"\n✅ Successfully processed: {total_houses} households")
        else:
            print("No data available for table generation.")


# Convenience functions for direct usage
def process_single_household_min_duration(house_id: str) -> Optional[Dict]:
    """Convenience function to process a single household's minimum duration filtering"""
    filter_processor = MinDurationEventFilter()
    return filter_processor.process_single_household(house_id)


def process_batch_household_min_duration(house_list: List[str]) -> Dict:
    """Convenience function to process multiple households' minimum duration filtering"""
    filter_processor = MinDurationEventFilter()
    return filter_processor.process_batch_households(house_list)


def get_available_houses(event_segments_dir: str = None) -> list:
    """Get available houses from event segments output directory"""
    available_houses = []

    # Auto-detect the correct path
    if event_segments_dir is None:
        # Try different possible paths
        possible_paths = [
            "./output/02_event_segments",  # Current directory
            "../Agent_V2/output/02_event_segments",  # If running from TimeSeries
            "./Agent_V2/output/02_event_segments",  # If running from TimeSeries
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "02_event_segments")  # Relative to script
        ]

        event_segments_dir = None
        for path in possible_paths:
            if os.path.exists(path):
                event_segments_dir = path
                break

        if event_segments_dir is None:
            print(f"❌ Could not find event_segments directory in any of these locations:")
            for path in possible_paths:
                print(f"  - {os.path.abspath(path)}")
            # Fallback to a default list
            return [f"house{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]]

    try:
        if os.path.exists(event_segments_dir):
            print(f"📁 Scanning for houses in: {os.path.abspath(event_segments_dir)}")
            # Get all subdirectories that start with 'house'
            for item in os.listdir(event_segments_dir):
                item_path = os.path.join(event_segments_dir, item)
                if os.path.isdir(item_path) and item.startswith('house'):
                    # Check if the required event segments file exists
                    expected_file = os.path.join(item_path, f"event_segments_{item}.csv")
                    if os.path.exists(expected_file):
                        available_houses.append(item)

            available_houses.sort()  # Sort for consistent ordering
            print(f"✅ Found {len(available_houses)} houses with event segments files")

        if not available_houses:
            print(f"⚠️ No houses found in {event_segments_dir}")
            # Fallback to a default list if no houses found
            available_houses = [f"house{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]]

    except Exception as e:
        print(f"❌ Error scanning for available houses: {str(e)}")
        # Fallback to a default list
        available_houses = [f"house{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 21]]

    return available_houses


def main():
    """Main function for direct execution of minimum duration filter"""
    print("🚀 Agent V2 - Minimum Duration Event Filter")
    print("=" * 70)

    print("Please select processing mode:")
    print("1. Single household processing (Default)")
    print("2. Batch processing")

    try:
        choice = input("Enter your choice (1-2) [Default: 1]: ").strip()
        if not choice:
            choice = "1"

        # Get available houses from event segments output
        available_houses = get_available_houses()

        if choice == "1":
            # Single household mode
            print(f"\n📋 Available households: {available_houses}")
            house_input = input("Enter house ID (e.g., house1) [Default: house1]: ").strip()
            if not house_input:
                house_input = "house1"

            if house_input not in available_houses:
                print(f"❌ House {house_input} not found in configuration")
                return

            # Process single household
            result = process_single_household_min_duration(house_input)

            if result:
                print(f"\n✅ Processing completed successfully!")
                print(f"📁 Output file: {result['output_file']}")
            else:
                print(f"❌ Processing failed")

        elif choice == "2":
            # Batch processing mode
            print(f"\n📋 Available households: {len(available_houses)} houses")
            print("Select batch processing mode:")
            print("1. Process first 3 households")
            print("2. Process all households")
            print("3. Custom selection")

            batch_choice = input("Enter your choice (1-3) [Default: 1]: ").strip()
            if not batch_choice:
                batch_choice = "1"

            if batch_choice == "1":
                selected_houses = available_houses[:3]
            elif batch_choice == "2":
                selected_houses = available_houses
            elif batch_choice == "3":
                print(f"Available houses: {available_houses}")
                house_input = input("Enter house IDs separated by commas: ").strip()
                selected_houses = [h.strip() for h in house_input.split(',') if h.strip() in available_houses]
                if not selected_houses:
                    print("❌ No valid houses selected")
                    return
            else:
                print("❌ Invalid choice")
                return

            print(f"🎯 Selected houses: {selected_houses}")

            # Process batch
            results = process_batch_household_min_duration(selected_houses)

            if results:
                print(f"\n✅ Batch processing completed!")
                print(f"📊 Summary:")
                print(f"  • Total processed: {len(results)} households")

                print(f"\n📋 Individual results:")
                for house_id, result in results.items():
                    stats = result['statistics']
                    efficiency = stats['filtering_efficiency']
                    print(f"  ✅ {house_id}: {stats['updated_to_non_reschedulable']:,} events filtered ({efficiency:.1f}%)")
            else:
                print(f"❌ Batch processing failed")

        else:
            print("❌ Invalid choice")
            return

    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
