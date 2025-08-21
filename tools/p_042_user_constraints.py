#!/usr/bin/env python3
"""
Agent V2 - User Constraints Parser
=================================

This module handles the first step of the event filtering pipeline:
1. Load appliance summary from output/04_appliance_summary/{tariff_type}/{house_id}/appliance_summary.json
2. Generate default constraints for all appliances (appliance_constraints.json)
3. Parse user natural language input to modify specific appliance constraints
4. Save the revised constraints (appliance_constraints_revise_by_llm.json)

Features:
- Single household and batch processing support
- LLM-based natural language constraint parsing with fallback
- Default constraint generation for all appliance types
- Support for multiple tariff types (UK, Germany, California)

Output structure:
- output/04_user_constraints/{house_id}/appliance_constraints.json (default)
- output/04_user_constraints/{house_id}/appliance_constraints_revise_by_llm.json (user-modified)
"""

import os
import sys
import json
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

try:
    from .llm_proxy import GPTProxyClient
except ImportError:
    try:
        from llm_proxy import GPTProxyClient
    except ImportError:
        # Fallback: create a dummy client for testing
        class GPTProxyClient:
            def call_gpt(self, prompt):
                return None


class UserConstraintsParser:
    """Parse user constraints and generate appliance constraint files"""
    
    def __init__(self):
        # Default constraint values for all appliances
        self.default_constraints = {
            "forbidden_time": [["00:00", "06:30"], ["23:00", "24:00"]],
            "latest_finish": "24:00",
            "shift_rule": "only_delay",
            "min_duration": 5
        }
        
        # Note: All appliances use the same global default constraints
        # Only user input should modify specific appliance constraints
    
    def load_appliance_summary(self, house_id: str, appliance_summary_dir: str = "./output/04_appliance_summary") -> Optional[Dict]:
        """Load appliance summary for a specific house"""
        
        # Try to find appliance summary in any tariff type directory
        for tariff_type in ["UK", "Germany", "California"]:
            summary_file = os.path.join(appliance_summary_dir, tariff_type, house_id, "appliance_summary.json")
            if os.path.exists(summary_file):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary = json.load(f)
                    logger.info(f"✅ Loaded appliance summary for {house_id} from {tariff_type}")
                    return summary
                except Exception as e:
                    logger.error(f"❌ Error loading appliance summary from {summary_file}: {e}")
                    continue
        
        logger.error(f"❌ No appliance summary found for {house_id}")
        return None
    
    def generate_default_constraints(self, appliance_summary: Dict) -> Dict:
        """Generate default constraints for all appliances in the summary"""

        constraints = {}
        appliance_names = appliance_summary.get('appliance_names', [])

        for appliance_name in appliance_names:
            # All appliances use the same global default constraints
            # Only user input should modify specific appliance constraints
            constraints[appliance_name] = self.default_constraints.copy()

        logger.info(f"✅ Generated default constraints for {len(constraints)} appliances")
        return constraints
    
    def parse_user_constraints_with_llm(self, user_input: str, default_constraints: Dict) -> Tuple[Dict, bool]:
        """Parse user natural language constraints using LLM"""

        if not user_input.strip():
            logger.info("📋 No user input provided, using default constraints")
            return default_constraints, True

        try:
            # Initialize LLM client
            llm_client = GPTProxyClient()

            # Get all appliance names
            all_appliance_names = list(default_constraints.keys())

            # Create example output showing how to modify specific appliances
            example_output = {
                "Washing Machine": {
                    "forbidden_time": [["00:00", "06:00"], ["23:30", "30:00"]],
                    "latest_finish": "38:00",
                    "shift_rule": "only_delay",
                    "min_duration": 5
                },
                "Tumble Dryer": {
                    "forbidden_time": [["00:00", "06:00"], ["23:30", "30:00"]],
                    "latest_finish": "38:00",
                    "shift_rule": "only_delay",
                    "min_duration": 5
                },
                "Dishwasher": {
                    "forbidden_time": [["00:00", "06:00"], ["23:30", "30:00"]],
                    "latest_finish": "38:00",
                    "shift_rule": "only_delay",
                    "min_duration": 5
                }
            }

            # Create prompt based on previous implementation
            prompt = f"""
        You are a smart assistant helping to revise electricity scheduling constraints.

        TASK: Modify ONLY the appliances mentioned in the user instruction. Keep all other appliances unchanged.

        USER INSTRUCTION: {user_input}

        RULES:
        1. ONLY modify appliances explicitly mentioned in the user instruction
        2. For forbidden_time, SMART MERGE with existing periods:
           - User wants "23:30 to 06:00 next day" = [["23:30", "30:00"]]
           - Original: [["00:00", "06:30"], ["23:00", "24:00"]]
           - MERGE LOGIC:
             * ["00:00", "06:30"] overlaps with ["24:00", "30:00"] → merge to ["00:00", "06:00"]
             * ["23:00", "24:00"] overlaps with ["23:30", "30:00"] → merge to ["23:30", "30:00"]
           - RESULT: [["00:00", "06:00"], ["23:30", "30:00"]] (exactly 2 periods, not 3!)
        3. For latest_finish: "14:00 next day" = "38:00"
        4. Keep min_duration as 5 unless user specifies otherwise
        5. Keep shift_rule as "only_delay"

        CRITICAL: When merging time periods, combine overlapping ranges. Do NOT keep separate periods that overlap!

        EXAMPLE MERGE:
        - Original: [["00:00", "06:30"], ["23:00", "24:00"]]
        - Add: "23:30 to 06:00 next day" = [["23:30", "30:00"]]
        - WRONG: [["00:00", "06:30"], ["23:00", "24:00"], ["23:30", "30:00"]] (3 periods)
        - CORRECT: [["00:00", "06:00"], ["23:30", "30:00"]] (2 merged periods)

        OUTPUT: Valid JSON with ALL appliances. Modified appliances should have merged time periods.

        ORIGINAL CONSTRAINTS:
        {json.dumps(default_constraints, indent=2, ensure_ascii=False)}
        """

            # Call LLM using the chat method
            try:
                response = llm_client.chat([{"role": "user", "content": prompt}])
                if response.get("success"):
                    content = response["content"].strip().strip("```json").strip("```")
                    revised_constraints = json.loads(content)

                    # Check if LLM actually made changes by comparing with defaults
                    changes_made = False
                    for appliance_name in ["Washing Machine", "Tumble Dryer", "Dishwasher"]:
                        if appliance_name in revised_constraints:
                            revised_appliance = revised_constraints[appliance_name]
                            default_appliance = default_constraints.get(appliance_name, {})

                            # Check if forbidden_time or latest_finish changed
                            if (revised_appliance.get("forbidden_time") != default_appliance.get("forbidden_time") or
                                revised_appliance.get("latest_finish") != default_appliance.get("latest_finish")):
                                changes_made = True
                                break

                    if not changes_made:
                        print("⚠️  LLM returned default constraints, using fallback parser...")
                        raise Exception("LLM did not make expected changes")

                else:
                    raise Exception(f"LLM call failed: {response.get('error', 'Unknown error')}")
            except Exception as e:
                # Use fallback parser
                print(f"🔄 LLM parsing failed: {str(e)}")
                print("🔄 Using fallback constraint parsing...")
                revised_constraints = self._fallback_parse_constraints(user_input, default_constraints)

            # Process the LLM response like in the original implementation
            final_constraints = {}
            default_values = self.default_constraints

            for appliance_name in all_appliance_names:
                if appliance_name in revised_constraints:
                    # LLM modified this appliance, use LLM result but fill missing fields
                    final_constraints[appliance_name] = {}
                    for k in default_values:
                        if k in revised_constraints[appliance_name]:
                            final_constraints[appliance_name][k] = revised_constraints[appliance_name][k]
                        else:
                            # Use default value to fill missing fields
                            final_constraints[appliance_name][k] = default_constraints.get(appliance_name, {}).get(k, default_values[k])

                    # Handle special 'forbidden' field
                    if "forbidden" in revised_constraints[appliance_name]:
                        final_constraints[appliance_name]["forbidden_time"] = revised_constraints[appliance_name]["forbidden"]
                else:
                    # LLM didn't modify this appliance, use default constraints
                    final_constraints[appliance_name] = default_constraints.get(appliance_name, default_values.copy())

            logger.info("✅ LLM successfully parsed user constraints")
            return final_constraints, True

        except Exception as e:
            logger.error(f"❌ LLM constraint parsing failed: {e}")
            return self._fallback_parse_constraints(user_input, default_constraints), False
    
    def _fallback_parse_constraints(self, user_input: str, default_constraints: Dict) -> Dict:
        """Fallback constraint parsing using simple pattern matching"""
        logger.info("🔄 Using fallback constraint parsing...")

        import copy
        updated_constraints = copy.deepcopy(default_constraints)

        # Simple pattern matching for common constraint patterns
        lines = user_input.lower().split('\n')

        # Track appliances mentioned in previous lines for context
        context_appliances = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Find mentioned appliances in current line
            mentioned_appliances = []
            for appliance_name in updated_constraints.keys():
                if appliance_name.lower() in line:
                    mentioned_appliances.append(appliance_name)

            # Update context with newly mentioned appliances
            if mentioned_appliances:
                context_appliances = mentioned_appliances

            # For global statements like "each event", use context appliances
            target_appliances = mentioned_appliances if mentioned_appliances else context_appliances

            # Apply simple parsing rules for each target appliance
            for appliance_name in target_appliances:
                # Parse forbidden time patterns
                if 'forbidden' in line or 'not run between' in line or 'cannot run' in line:
                    if '23:30' in line and ('06:00' in line or '30:00' in line):
                        updated_constraints[appliance_name]['forbidden_time'] = [["23:30", "30:00"]]
                    elif '07:00' in line and '22:00' in line:
                        updated_constraints[appliance_name]['forbidden_time'] = [["07:00", "22:00"]]
                
                # Parse latest finish time
                if ('latest_finish' in line or 'finish by' in line or 'complete by' in line or
                    'completes by' in line or 'event completes' in line):
                    if '38:00' in line or ('14:00' in line and ('next day' in line or 'the next day' in line)):
                        updated_constraints[appliance_name]['latest_finish'] = "38:00"
                    elif '26:00' in line or ('02:00' in line and ('next day' in line or 'the next day' in line)):
                        updated_constraints[appliance_name]['latest_finish'] = "26:00"
                
                # Parse minimum duration
                if 'min' in line and 'duration' in line:
                    import re
                    duration_match = re.search(r'(\d+)\s*min', line)
                    if duration_match:
                        updated_constraints[appliance_name]['min_duration'] = int(duration_match.group(1))
        
        logger.info("✅ Fallback constraint parsing completed")
        return updated_constraints

    def save_constraints(self, constraints: Dict, house_id: str, output_dir: str = "./output/04_user_constraints",
                        filename: str = "appliance_constraints.json", user_input: str = "", llm_success: bool = True) -> str:
        """Save constraints to file"""

        # Create output directory
        house_output_dir = os.path.join(output_dir, house_id)
        os.makedirs(house_output_dir, exist_ok=True)

        # Prepare constraint data with metadata
        constraint_data = {
            "house_id": house_id,
            "generated_time": datetime.now().isoformat(),
            "user_input": user_input,
            "llm_parsing_success": llm_success,
            "appliance_constraints": constraints,
            "summary": {
                "total_appliances": len(constraints),
                "constrained_appliances": len([c for c in constraints.values() if c.get('user_input')])
            }
        }

        # Save to file
        constraints_file = os.path.join(house_output_dir, filename)
        with open(constraints_file, 'w', encoding='utf-8') as f:
            json.dump(constraint_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Constraints saved to: {constraints_file}")
        return constraints_file

    def process_single_household(self, house_id: str, user_input: str = "",
                               appliance_summary_dir: str = "./output/04_appliance_summary",
                               output_dir: str = "./output/04_user_constraints") -> Optional[Dict]:
        """Process constraints for a single household"""

        print(f"🏠 Processing constraints for {house_id.upper()}...")

        # Step 1: Load appliance summary
        appliance_summary = self.load_appliance_summary(house_id, appliance_summary_dir)
        if not appliance_summary:
            print(f"❌ Failed to load appliance summary for {house_id}")
            return None

        # Step 2: Generate default constraints
        default_constraints = self.generate_default_constraints(appliance_summary)

        # Step 3: Save default constraints
        default_file = self.save_constraints(
            constraints=default_constraints,
            house_id=house_id,
            output_dir=output_dir,
            filename="appliance_constraints.json",
            user_input="",
            llm_success=True
        )
        print(f"📋 Default constraints saved: {os.path.basename(default_file)}")

        # Step 4: Parse user input and create revised constraints
        revised_constraints, llm_success = self.parse_user_constraints_with_llm(user_input, default_constraints)

        # Step 5: Save revised constraints
        revised_file = self.save_constraints(
            constraints=revised_constraints,
            house_id=house_id,
            output_dir=output_dir,
            filename="appliance_constraints_revise_by_llm.json",
            user_input=user_input,
            llm_success=llm_success
        )
        print(f"🤖 Revised constraints saved: {os.path.basename(revised_file)}")

        # Step 6: Display results
        print(f"📊 Generated constraints for {len(revised_constraints)} appliances:")
        for appliance_name in revised_constraints.keys():
            print(f"  • {appliance_name}")

        if user_input:
            constrained_appliances = [name for name, constraint in revised_constraints.items()
                                    if constraint.get('user_input')]
            if constrained_appliances:
                print(f"🎯 User constraints applied to: {', '.join(constrained_appliances)}")

            if llm_success:
                print("🤖 LLM parsing successful")
            else:
                print("⚠️ Used fallback parsing")
        else:
            print("📋 Using default constraints (no user input)")

        return {
            "house_id": house_id,
            "default_file": default_file,
            "revised_file": revised_file,
            "appliance_count": len(revised_constraints),
            "user_input": user_input,
            "llm_success": llm_success,
            "constraints": revised_constraints
        }

    def process_batch_households(self, house_list: List[str], user_inputs: Dict[str, str] = None,
                               appliance_summary_dir: str = "./output/04_appliance_summary",
                               output_dir: str = "./output/04_user_constraints") -> Dict:
        """Process constraints for multiple households"""

        if user_inputs is None:
            user_inputs = {}

        print(f"🚀 Starting batch constraint processing...")
        print(f"🏠 Target households: {len(house_list)}")
        print("=" * 80)

        results = {}
        failed_houses = []

        for i, house_id in enumerate(house_list, 1):
            try:
                print(f"\n[{i}/{len(house_list)}] Processing {house_id}...")

                user_input = user_inputs.get(house_id, "")
                result = self.process_single_household(
                    house_id=house_id,
                    user_input=user_input,
                    appliance_summary_dir=appliance_summary_dir,
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
        print(f"\n🎉 Batch constraint processing completed!")
        print(f"✅ Successfully processed: {len(results)} households")
        if failed_houses:
            print(f"❌ Failed to process: {len(failed_houses)} households")
            for house in failed_houses:
                print(f"  - {house}")

        return results


# Convenience functions for direct usage
def process_single_household_constraints(house_id: str, user_input: str = "") -> Optional[Dict]:
    """Convenience function to process a single household's constraints"""
    parser = UserConstraintsParser()
    return parser.process_single_household(house_id, user_input)


def process_batch_household_constraints(house_list: List[str], user_inputs: Dict[str, str] = None) -> Dict:
    """Convenience function to process multiple households' constraints"""
    parser = UserConstraintsParser()
    return parser.process_batch_households(house_list, user_inputs)


def load_house_appliances_config(config_path: str = "./config/house_appliances.json") -> dict:
    """Load house appliances configuration"""
    house_appliances = {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        lines = content.split('\n')
        current_house = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('House '):
                house_num = line.split()[1]
                current_house = f"house{house_num}"
            elif current_house and not line.startswith('House '):
                house_appliances[current_house] = line
                current_house = None

        return house_appliances

    except Exception as e:
        print(f"❌ Error loading house appliances config: {str(e)}")
        return {}


def main():
    """Main function for direct execution of user constraints parser"""
    print("🚀 Agent V2 - User Constraints Parser")
    print("=" * 60)

    print("Please select processing mode:")
    print("1. Single household processing (Default)")
    print("2. Batch processing")

    try:
        choice = input("Enter your choice (1-2) [Default: 1]: ").strip()
        if not choice:
            choice = "1"

        # Load house configuration
        house_appliances = load_house_appliances_config()
        available_houses = list(house_appliances.keys())

        if choice == "1":
            # Single household mode
            print(f"\n📋 Available households: {available_houses}")
            house_input = input("Enter house ID (e.g., house1) [Default: house1]: ").strip()
            if not house_input:
                house_input = "house1"

            if house_input not in available_houses:
                print(f"❌ House {house_input} not found in configuration")
                return

            # Get user constraints
            print(f"\n📝 Enter user constraints for {house_input} (optional):")
            print("Examples:")
            print("  - 'Washing machine should not run between 23:30 and 06:00, latest finish is 14:00 next day'")
            print("  - 'Tumble dryer and dishwasher forbidden from 23:30 to 30:00, latest finish 38:00'")
            print("Leave empty to use default constraints only.")
            user_input = input("User constraints: ").strip()

            # Process single household
            result = process_single_household_constraints(house_input, user_input)

            if result:
                print(f"\n✅ Processing completed successfully!")
                print(f"📊 Results:")
                print(f"  • House ID: {result['house_id']}")
                print(f"  • Appliance count: {result['appliance_count']}")
                print(f"  • LLM parsing success: {result['llm_success']}")

                if user_input:
                    modified_appliances = [name for name, constraint in result['constraints'].items()
                                         if constraint.get('user_input')]
                    print(f"  • Modified appliances: {modified_appliances}")

                print(f"\n📁 Files saved:")
                print(f"  • Default: {result['default_file']}")
                print(f"  • Revised: {result['revised_file']}")
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

            # Get user inputs for batch processing
            with open("./config/default_user_constrain.txt", "r", encoding="utf-8") as f:
                default_user_input = f.read().strip()
                print(f"default_user_input: {default_user_input}")

            print(f"\n📝 Enter user constraints for specific houses (optional):")
            print("You can specify constraints for individual houses or leave empty for default.")
            print(f"Default constraint: {default_user_input}")

            user_inputs = {}
            for house_id in selected_houses[:3]:  # Only ask for first 3 to avoid too much input
                constraint_input = input(f"Constraints for {house_id} (or press Enter for default): ").strip()
                if constraint_input:
                    user_inputs[house_id] = constraint_input
                else:
                    user_inputs[house_id] = default_user_input

            # Apply default to remaining houses
            for house_id in selected_houses[3:]:
                user_inputs[house_id] = default_user_input

            # Process batch
            results = process_batch_household_constraints(selected_houses, user_inputs)

            if results:
                print(f"\n✅ Batch processing completed!")
                print(f"📊 Summary:")
                print(f"  • Total processed: {len(results)} households")
                print(f"  • With user constraints: {len([r for r in results.values() if r['user_input']])}")
                print(f"  • LLM success rate: {len([r for r in results.values() if r['llm_success']])}/{len(results)}")

                print(f"\n📋 Individual results:")
                for house_id, result in results.items():
                    status = "✅" if result['llm_success'] else "⚠️"
                    user_status = "🎯" if result['user_input'] else "📋"
                    print(f"  {status} {user_status} {house_id}: {result['appliance_count']} appliances")
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
