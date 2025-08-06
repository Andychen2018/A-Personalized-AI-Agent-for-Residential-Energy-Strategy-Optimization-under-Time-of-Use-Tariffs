#!/usr/bin/env python3
"""
test_func_5_int.py - Integrated Tool for Energy Optimization

This tool integrates p042, p043, and p044 functionalities:
- p042: User constraints processing with LLM
- p043: Minimum duration filtering  
- p044: TOU optimization and filtering

Default behavior: Uses config/tariff_config.json for single user processing
Batch mode: Processes multiple users with tariff_config.json by default, with user choice options

Author: Andychen2018
"""

import os
import json
import pandas as pd
from typing import Dict, List, Optional, Union

# Import individual tool classes
from tools.p_042_user_constraints import UserConstraintsParser
from tools.p_043_min_duration_filter import MinDurationEventFilter
from tools.p_044_tou_optimization_filter import process_and_mask_events

class EnergyOptimizationIntegrator:
    """Integrated energy optimization tool combining p042, p043, p044"""

    def __init__(self):
        self.default_tariff_config = "config/tariff_config.json"
        self.available_tariffs = {
            "tariff_config": {
                "path": "config/tariff_config.json",
                "tariffs": ["Economy_7", "Economy_10"],
                "description": "UK Economy tariffs"
            },
            "TOU_D": {
                "path": "config/TOU_D.json",
                "tariffs": ["TOU_D"],
                "description": "California TOU-D seasonal tariff"
            },
            "Germany_Variable": {
                "path": "config/Germany_Variable.json",
                "tariffs": ["Germany_Variable"],
                "description": "Germany variable pricing"
            }
        }

    def get_all_available_houses(self) -> List[str]:
        """Get all available house IDs from the output directories"""
        house_dirs = []

        # Check multiple directories to find available houses
        check_dirs = [
            "output/02_event_segments",
            "output/04_appliance_summary/UK",
            "output/04_min_duration_filter"
        ]

        for check_dir in check_dirs:
            if os.path.exists(check_dir):
                for item in os.listdir(check_dir):
                    if item.startswith("house") and os.path.isdir(os.path.join(check_dir, item)):
                        if item not in house_dirs:
                            house_dirs.append(item)
                break  # Use first available directory

        # Sort house IDs naturally (house1, house2, ..., house10, house11, ...)
        def natural_sort_key(house_id):
            import re
            return int(re.search(r'\d+', house_id).group())

        house_dirs.sort(key=natural_sort_key)
        return house_dirs
    
    def process_single_user(self, house_id: str = "house1", 
                           user_instruction: str = None,
                           tariff_config: str = None) -> Dict:
        """
        Process energy optimization for a single user
        
        Args:
            house_id: House identifier
            user_instruction: Natural language constraints instruction
            tariff_config: Tariff configuration to use (default: tariff_config.json)
        
        Returns:
            Processing result dictionary
        """
        print(f"🏠 Processing single user: {house_id}")
        print("=" * 60)
        
        # Use default tariff config if not specified
        if tariff_config is None:
            tariff_config = "tariff_config"
        
        # Set default user instruction if not provided
        if user_instruction is None:
            user_instruction = (
                "For Washing Machine, Tumble Dryer, and Dishwasher:\n"
                "- Replace the default forbidden operating time with 23:30 to 06:00 (next day);\n"
                "- Set latest_finish to 14:00 of the next day (i.e., 38:00);\n"
                "- Ignore all events shorter than 5 minutes.\n"
                "Keep all other appliances with default scheduling rules."
            )
        
        try:
            # Step 1: Process user constraints (p042)
            print("🔧 Step 1: Processing user constraints...")
            constraints_parser = UserConstraintsParser()
            constraint_result = constraints_parser.process_single_household(
                house_id=house_id,
                user_input=user_instruction
            )

            if not constraint_result:
                return {"status": "failed", "error": "Failed to process user constraints"}
            
            constraint_file = constraint_result.get('revised_file')
            llm_success = constraint_result.get('llm_success', False)
            
            # Step 2: Apply minimum duration filtering (p043)
            print("⏱️ Step 2: Applying minimum duration filtering...")
            duration_filter = MinDurationEventFilter()
            duration_result = duration_filter.process_single_household(
                house_id=house_id,
                output_dir="./output/04_min_duration_filter"
            )
            
            if not duration_result:
                return {"status": "failed", "error": "Failed to apply duration filtering"}

            duration_filtered_file = duration_result.get('output_file')
            duration_statistics = duration_result.get('statistics', {})
            
            # Step 3: Apply TOU optimization (p044)
            print("💰 Step 3: Applying TOU optimization...")
            tariff_info = self.available_tariffs[tariff_config]
            output_files = []
            
            for tariff_name in tariff_info["tariffs"]:
                print(f"🔄 Processing {tariff_name}...")
                
                # Create output directory
                output_dir = f"output/04_TOU_filter/{tariff_name}/{house_id}"
                os.makedirs(output_dir, exist_ok=True)
                
                try:
                    tou_result_file = process_and_mask_events(
                        event_csv_path=duration_filtered_file,
                        constraint_json_path=constraint_file,
                        tariff_config_path=tariff_info["path"],
                        tariff_name=tariff_name,
                        output_dir=output_dir
                    )
                    
                    if tou_result_file and os.path.exists(tou_result_file):
                        output_files.append(tou_result_file)
                        print(f"✅ {tariff_name} optimization completed")
                    else:
                        print(f"❌ {tariff_name} optimization failed")
                        
                except Exception as e:
                    print(f"❌ Error processing {tariff_name}: {e}")
            
            # Generate statistics
            statistics = self._generate_statistics(output_files)
            
            return {
                "status": "success",
                "house_id": house_id,
                "tariff_config": tariff_config,
                "processed_tariffs": tariff_info["tariffs"],
                "output_files": output_files,
                "llm_parsing_success": llm_success,
                "user_instruction": user_instruction,
                "statistics": statistics,
                "duration_statistics": duration_statistics,
                "file_paths": {
                    "constraints": constraint_file,
                    "duration_filtered": duration_filtered_file,
                    "tou_optimized": output_files
                }
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": f"Processing failed: {str(e)}"
            }
    
    def process_batch_users(self, house_list: List[str],
                           user_instructions: Dict[str, str] = None,
                           tariff_config: str = None,
                           interactive_mode: bool = True) -> Dict:
        """
        Process energy optimization for multiple users
        
        Args:
            house_list: List of house identifiers
            user_instructions: Dict mapping house_id to user instruction
            tariff_config: Tariff configuration to use (default: tariff_config.json)
            interactive_mode: Whether to allow user to choose tariff options
        
        Returns:
            Batch processing result dictionary
        """
        print(f"🚀 Processing batch users: {len(house_list)} houses")
        print("=" * 60)
        
        # Interactive tariff selection
        if interactive_mode:
            tariff_config = self._interactive_tariff_selection()
        elif tariff_config is None:
            tariff_config = "tariff_config"  # Default
        
        if user_instructions is None:
            user_instructions = {}
        
        results = {}
        failed_houses = []
        
        for i, house_id in enumerate(house_list, 1):
            print(f"\n[{i}/{len(house_list)}] Processing {house_id}...")
            
            user_instruction = user_instructions.get(house_id, None)
            
            try:
                result = self.process_single_user(
                    house_id=house_id,
                    user_instruction=user_instruction,
                    tariff_config=tariff_config
                )
                
                if result["status"] == "success":
                    results[house_id] = result
                    print(f"✅ {house_id} completed successfully!")
                else:
                    failed_houses.append(house_id)
                    print(f"❌ {house_id} failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed_houses.append(house_id)
                print(f"❌ {house_id} crashed: {str(e)}")
            
            print("-" * 40)
        
        # Generate batch summary
        batch_statistics = self._generate_batch_statistics(results)
        
        return {
            "status": "success" if results else "failed",
            "processed_houses": len(results),
            "failed_houses": len(failed_houses),
            "failed_house_list": failed_houses,
            "tariff_config": tariff_config,
            "results": results,
            "batch_statistics": batch_statistics
        }
    
    def _interactive_tariff_selection(self) -> str:
        """Interactive tariff selection for batch processing"""
        print("\n📋 Available tariff configurations:")
        print("-" * 40)
        
        options = list(self.available_tariffs.keys())
        for i, (key, info) in enumerate(self.available_tariffs.items(), 1):
            print(f"{i}. {key}: {info['description']}")
            print(f"   Tariffs: {', '.join(info['tariffs'])}")
            print(f"   Config: {info['path']}")
            print()
        
        while True:
            try:
                choice = input(f"Select tariff configuration (1-{len(options)}) [default: 1]: ").strip()
                
                if not choice:
                    choice = "1"
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(options):
                    selected = options[choice_idx]
                    print(f"✅ Selected: {selected}")
                    return selected
                else:
                    print(f"❌ Invalid choice. Please enter 1-{len(options)}")
                    
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print("\n👋 Using default tariff_config")
                return "tariff_config"
    
    def _generate_statistics(self, output_files: List[str]) -> Dict:
        """Generate statistics from output files"""
        stats = {"files": len(output_files), "tariff_results": {}}
        
        for file_path in output_files:
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    filename = os.path.basename(file_path)
                    
                    # Extract tariff name
                    if "Economy_7" in filename:
                        tariff_name = "Economy_7"
                    elif "Economy_10" in filename:
                        tariff_name = "Economy_10"
                    elif "TOU_D" in filename:
                        tariff_name = "TOU_D"
                    elif "Germany_Variable" in filename:
                        tariff_name = "Germany_Variable"
                    else:
                        tariff_name = "Unknown"
                    
                    total_events = len(df)
                    reschedulable_events = len(df[df['is_reschedulable'] == True])
                    filter_efficiency = (total_events - reschedulable_events) / total_events * 100 if total_events > 0 else 0
                    
                    stats["tariff_results"][tariff_name] = {
                        "total_events": total_events,
                        "reschedulable_events": reschedulable_events,
                        "filter_efficiency": round(filter_efficiency, 1)
                    }
                except Exception as e:
                    print(f"⚠️ Error processing statistics for {file_path}: {e}")
        
        return stats
    
    def _generate_batch_statistics(self, results: Dict) -> Dict:
        """Generate batch processing statistics with detailed tables"""
        if not results:
            return {}

        total_files = sum(len(r["output_files"]) for r in results.values())
        total_llm_success = sum(1 for r in results.values() if r["llm_parsing_success"])

        # Collect detailed statistics for each house and tariff
        detailed_stats = {}

        for house_id, result in results.items():
            detailed_stats[house_id] = {}

            # Get duration filtering statistics from the result
            duration_stats = result.get("duration_statistics", {})

            for tariff, tou_stats in result["statistics"]["tariff_results"].items():
                detailed_stats[house_id][tariff] = {
                    "total_events": duration_stats.get("total_events", 0),
                    "input_reschedulable": duration_stats.get("initial_reschedulable", 0),
                    "final_reschedulable": tou_stats["reschedulable_events"],
                    "events_filtered_out": tou_stats["total_events"] - tou_stats["reschedulable_events"],
                    "filter_efficiency": tou_stats["filter_efficiency"]
                }

        # Aggregate tariff statistics
        aggregated_tariff_stats = {}
        for result in results.values():
            for tariff, stats in result["statistics"]["tariff_results"].items():
                if tariff not in aggregated_tariff_stats:
                    aggregated_tariff_stats[tariff] = {
                        "total_events": 0,
                        "reschedulable_events": 0,
                        "houses": 0
                    }

                aggregated_tariff_stats[tariff]["total_events"] += stats["total_events"]
                aggregated_tariff_stats[tariff]["reschedulable_events"] += stats["reschedulable_events"]
                aggregated_tariff_stats[tariff]["houses"] += 1

        # Calculate overall efficiency for each tariff
        for tariff, stats in aggregated_tariff_stats.items():
            if stats["total_events"] > 0:
                efficiency = (stats["total_events"] - stats["reschedulable_events"]) / stats["total_events"] * 100
                stats["filter_efficiency"] = round(efficiency, 1)

        return {
            "total_output_files": total_files,
            "llm_success_rate": f"{total_llm_success}/{len(results)}",
            "tariff_statistics": aggregated_tariff_stats,
            "detailed_statistics": detailed_stats
        }


# Main execution functions
def process_single_household_energy_optimization(house_id: str = "house1", 
                                               user_instruction: str = None,
                                               tariff_config: str = None) -> Dict:
    """
    Convenience function for single household processing
    
    Args:
        house_id: House identifier (default: "house1")
        user_instruction: Natural language constraints instruction
        tariff_config: Tariff configuration ("tariff_config", "TOU_D", "Germany_Variable")
    
    Returns:
        Processing result dictionary
    """
    integrator = EnergyOptimizationIntegrator()
    return integrator.process_single_user(house_id, user_instruction, tariff_config)


def process_batch_household_energy_optimization(house_list: List[str],
                                              user_instructions: Dict[str, str] = None,
                                              tariff_config: str = None,
                                              interactive_mode: bool = True) -> Dict:
    """
    Convenience function for batch household processing
    
    Args:
        house_list: List of house identifiers
        user_instructions: Dict mapping house_id to user instruction
        tariff_config: Tariff configuration to use
        interactive_mode: Whether to allow interactive tariff selection
    
    Returns:
        Batch processing result dictionary
    """
    integrator = EnergyOptimizationIntegrator()
    return integrator.process_batch_users(house_list, user_instructions, tariff_config, interactive_mode)


def print_detailed_table(detailed_stats: Dict, tariff_name: str):
    """Print detailed statistics table for a specific tariff"""

    print(f"\n📊 {tariff_name} Results:")
    print("-" * 100)

    # Table header
    header = f"{'House_ID':<10} {'Total_Events':<13} {'Input_Reschedulable':<18} {'Final_Reschedulable':<17} {'Events_Filtered_Out':<19} {'Filter_Efficiency_%':<18}"
    print(header)

    # Calculate totals
    total_events = 0
    total_input_reschedulable = 0
    total_final_reschedulable = 0
    total_filtered_out = 0
    house_count = 0

    # Sort houses naturally
    def natural_sort_key(house_id):
        import re
        return int(re.search(r'\d+', house_id).group())

    sorted_houses = sorted(detailed_stats.keys(), key=natural_sort_key)

    # Print table rows
    for house_id in sorted_houses:
        if tariff_name in detailed_stats[house_id]:
            stats = detailed_stats[house_id][tariff_name]

            total_events += stats['total_events']
            total_input_reschedulable += stats['input_reschedulable']
            total_final_reschedulable += stats['final_reschedulable']
            total_filtered_out += stats['events_filtered_out']
            house_count += 1

            row = f"{house_id:<10} {stats['total_events']:>13,} {stats['input_reschedulable']:>18,} {stats['final_reschedulable']:>17,} {stats['events_filtered_out']:>19,} {stats['filter_efficiency']:>18.1f}"
            print(row)

    print("-" * 100)

    # Print totals
    avg_efficiency = total_filtered_out / total_input_reschedulable * 100 if total_input_reschedulable > 0 else 0
    total_row = f"{'TOTAL':<10} {total_events:>13,} {total_input_reschedulable:>18,} {total_final_reschedulable:>17,} {total_filtered_out:>19,} {avg_efficiency:>18.1f}"
    print(total_row)
    print("=" * 100)

    # Summary
    print(f"\n📋 {tariff_name} Summary:")
    print(f"• Successfully processed: {house_count} households")
    print(f"• Total events: {total_events:,}")
    print(f"• Input reschedulable events: {total_input_reschedulable:,}")
    print(f"• Final reschedulable events: {total_final_reschedulable:,}")
    print(f"• Events filtered out by TOU: {total_filtered_out:,}")
    print(f"• Average TOU filtering efficiency: {avg_efficiency:.1f}%")


def print_result_summary(result: Dict):
    """Print a formatted summary of processing results"""

    if result["status"] != "success":
        print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
        return

    if "batch_statistics" in result:
        # Batch processing summary with detailed tables
        print("\n📊 Batch Processing Summary:")
        print("=" * 50)
        print(f"✅ Successfully processed: {result['processed_houses']} houses")
        if result['failed_houses'] > 0:
            print(f"❌ Failed to process: {result['failed_houses']} houses")

        batch_stats = result["batch_statistics"]
        print(f"📁 Total output files: {batch_stats['total_output_files']}")
        print(f"🧠 LLM success rate: {batch_stats['llm_success_rate']}")

        # Print detailed tables for each tariff
        if "detailed_statistics" in batch_stats:
            detailed_stats = batch_stats["detailed_statistics"]

            # Get all tariffs
            all_tariffs = set()
            for house_stats in detailed_stats.values():
                all_tariffs.update(house_stats.keys())

            # Print table for each tariff
            for tariff in sorted(all_tariffs):
                print_detailed_table(detailed_stats, tariff)

    else:
        # Single processing summary with single-row table
        print("\n📊 Processing Summary:")
        print("=" * 50)
        print(f"🏠 House: {result['house_id']}")
        print(f"📋 Tariff config: {result['tariff_config']}")
        print(f"🧠 LLM parsing: {'✅ Success' if result['llm_parsing_success'] else '⚠️ Failed'}")
        print(f"📁 Output files: {len(result['output_files'])}")

        # Print single-house table for each tariff
        if result["statistics"]["tariff_results"]:
            duration_stats = result.get("duration_statistics", {})

            for tariff, tou_stats in result["statistics"]["tariff_results"].items():
                print(f"\n📊 {tariff} Results:")
                print("-" * 100)

                # Table header
                header = f"{'House_ID':<10} {'Total_Events':<13} {'Input_Reschedulable':<18} {'Final_Reschedulable':<17} {'Events_Filtered_Out':<19} {'Filter_Efficiency_%':<18}"
                print(header)

                # Single row
                total_events = duration_stats.get('total_events', 0)
                input_reschedulable = duration_stats.get('initial_reschedulable', 0)
                final_reschedulable = tou_stats['reschedulable_events']
                events_filtered_out = tou_stats['total_events'] - tou_stats['reschedulable_events']
                filter_efficiency = tou_stats['filter_efficiency']

                row = f"{result['house_id']:<10} {total_events:>13,} {input_reschedulable:>18,} {final_reschedulable:>17,} {events_filtered_out:>19,} {filter_efficiency:>18.1f}"
                print(row)
                print("=" * 100)


def main():
    """Main function for interactive execution"""
    print("🚀 Energy Optimization Integration Tool")
    print("=" * 60)
    print("This tool integrates p042 (constraints), p043 (duration), p044 (TOU optimization)")
    print()

    try:
        # Choose processing mode
        print("📋 Processing modes:")
        print("1. Single household processing")
        print("2. Batch household processing")
        print()

        try:
            mode_choice = input("Select mode (1-2) [default: 1]: ").strip()
            if not mode_choice:
                mode_choice = "1"
        except (EOFError, KeyboardInterrupt):
            print("Using default mode: 1")
            mode_choice = "1"

        if mode_choice == "1":
            # Single household processing
            print("\n🏠 Single Household Processing")
            print("-" * 40)

            house_id = input("Enter house ID [default: house1]: ").strip()
            if not house_id:
                house_id = "house1"

            print("\n📝 User instruction (press Enter for default):")
            user_instruction = input().strip()
            if not user_instruction:
                user_instruction = None

            print(f"\n🔄 Processing {house_id}...")
            result = process_single_household_energy_optimization(
                house_id=house_id,
                user_instruction=user_instruction
            )

            print_result_summary(result)

        elif mode_choice == "2":
            # Batch household processing
            print("\n🏠 Batch Household Processing")
            print("-" * 40)

            # Get house list
            integrator = EnergyOptimizationIntegrator()
            all_houses = integrator.get_all_available_houses()

            print(f"Available houses: {len(all_houses)} houses ({', '.join(all_houses)})")
            house_input = input(f"Enter house IDs (comma-separated) [default: all {len(all_houses)} houses]: ").strip()
            if not house_input:
                house_list = all_houses
            else:
                house_list = [h.strip() for h in house_input.split(",")]

            print(f"\n🔄 Processing {len(house_list)} houses...")
            result = process_batch_household_energy_optimization(
                house_list=house_list,
                interactive_mode=True
            )

            print_result_summary(result)

        else:
            print("❌ Invalid mode selection")
            return

    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
