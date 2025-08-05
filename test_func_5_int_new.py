#!/usr/bin/env python3
"""
Agent V2 Test - Integrated Event Filtering and Constraint Management
===================================================================

This module provides integrated testing for:
- User constraint parsing and appliance constraint generation
- Reschedulable event extraction (is_reschedulable=True)
- Minimum duration filtering
- Time-of-Use (TOU) tariff-based filtering
- Single household and batch processing support

Updated for new path structure:
- output/05_constraints/{house_id}/appliance_constraints_revise_by_llm.json
- output/04_min_duration_filter/{house_id}/min_duration_filtered_{house_id}.csv
- output/04_TOU_filter/{tariff_type}/{house_id}/tou_filtered_{house_id}.csv
"""

import os
import sys
import json
from typing import Dict, List, Optional

# Add current directory to path for imports
sys.path.append('.')

from tools.p_05_processing_functions import (
    process_single_household_constraints,
    process_single_household_filtering,
    batch_process_constraints,
    batch_process_filtering
)


def load_house_appliances_config(config_path: str = "./config/house_appliances.json") -> dict:
    """Load house appliances configuration from text file"""
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


def get_available_tariff_types() -> List[str]:
    """Get list of available tariff types"""
    return ["UK", "Germany", "California"]


def main():
    """Main function for integrated event filtering and constraint management"""
    print("🚀 Starting Agent V2 Test - Integrated Event Filtering and Constraint Management")
    print("=" * 90)
    
    # Display available tariff types
    available_types = get_available_tariff_types()
    print("📊 Available tariff types:")
    for i, tariff_type in enumerate(available_types, 1):
        print(f"  {i}. {tariff_type}")
    
    print("\n" + "=" * 90)
    print("Please select processing step:")
    print("1. Step 1: Generate appliance constraints (Default)")
    print("2. Step 2: Filter reschedulable events by minimum duration")
    print("3. Step 3: Filter events by TOU optimization potential")
    print("4. Complete pipeline: All steps (1→2→3)")
    print("5. Batch mode: Process all households")
    
    try:
        choice = input("Please enter your choice (1-5) [Default: 1]: ").strip()
        if not choice:
            choice = "1"

        # Load house configuration
        house_appliances = load_house_appliances_config()

        # Determine processing mode (single vs batch)
        if choice == "5":
            # Batch mode
            processing_mode = "batch"
            print(f"\n🚀 Batch processing mode selected...")
            print(f"🏠 Will process {len(house_appliances)} households")
        else:
            # Single household mode
            processing_mode = "single"
            print(f"\n📋 Available households: {list(house_appliances.keys())}")
            house_input = input("Enter house ID (e.g., house1) [Default: house1]: ").strip()
            if not house_input:
                house_input = "house1"

            if house_input not in house_appliances:
                print(f"❌ House {house_input} not found in configuration")
                return

        # Step 1: Generate appliance constraints
        if choice in ["1", "4", "5"]:
            print(f"\n" + "=" * 80)
            print("🔄 STEP 1: Generating appliance constraints...")
            print("=" * 80)

            if processing_mode == "single":
                # Get user constraints
                print(f"\n📝 Enter user constraints for {house_input} (optional):")
                print("Example: 'Washing machine should not run between 07:00 and 22:00, latest finish is 14:00 next day'")
                user_input = input("User constraints: ").strip()

                constraint_result = process_single_household_constraints(
                    house_id=house_input,
                    user_input=user_input
                )

                if constraint_result:
                    print(f"✅ Step 1 completed for {house_input}!")
                else:
                    print(f"❌ Step 1 failed for {house_input}")
                    return
            else:
                # Batch constraints processing
                constraint_results = batch_process_constraints(
                    house_data_dict=house_appliances
                )
                print(f"✅ Step 1 completed for {len(constraint_results)} households!")

        # Step 2: Filter by minimum duration
        if choice in ["2", "4", "5"]:
            print(f"\n" + "=" * 80)
            print("🔄 STEP 2: Filtering events by minimum duration...")
            print("=" * 80)

            # This step doesn't need tariff selection as it's tariff-independent
            if processing_mode == "single":
                filtering_result = process_single_household_filtering(
                    house_id=house_input,
                    tariff_types=[]  # Empty list means only do min duration filtering
                )

                if filtering_result:
                    print(f"✅ Step 2 completed for {house_input}!")
                    print(f"📊 Results:")
                    print(f"  • Total events: {filtering_result['total_events']:,}")
                    print(f"  • Initial reschedulable events: {filtering_result['initial_reschedulable_events']:,}")
                    print(f"  • Min duration filtered events (remaining): {filtering_result['min_duration_filtered_events']:,}")
                    print(f"  • Events filtered out (too short): {filtering_result['events_filtered_out']:,}")
                else:
                    print(f"❌ Step 2 failed for {house_input}")
                    return
            else:
                # Batch min duration filtering
                filtering_results = batch_process_filtering(
                    house_data_dict=house_appliances,
                    tariff_types=[]  # Empty list means only do min duration filtering
                )
                print(f"✅ Step 2 completed for {len(filtering_results)} households!")

        # Step 3: Filter by TOU optimization
        if choice in ["3", "4", "5"]:
            print(f"\n" + "=" * 80)
            print("🔄 STEP 3: Filtering events by TOU optimization potential...")
            print("=" * 80)

            # Select tariff types for TOU filtering
            print("\nSelect tariff types for TOU optimization:")
            for i, tariff_type in enumerate(available_types, 1):
                print(f"  {i}. {tariff_type}")
            print("  4. All tariff types")

            tariff_choice = input(f"Please enter your choice (1-4) [Default: 1]: ").strip()
            if not tariff_choice:
                tariff_choice = "1"

            if tariff_choice == "4":
                selected_tariffs = available_types
            else:
                try:
                    tariff_index = int(tariff_choice) - 1
                    if 0 <= tariff_index < len(available_types):
                        selected_tariffs = [available_types[tariff_index]]
                    else:
                        print("Invalid choice, using UK as default")
                        selected_tariffs = ["UK"]
                except ValueError:
                    print("Invalid input, using UK as default")
                    selected_tariffs = ["UK"]

            print(f"\n✅ Selected tariff types: {selected_tariffs}")

            if processing_mode == "single":
                tou_filtering_result = process_single_household_filtering(
                    house_id=house_input,
                    tariff_types=selected_tariffs
                )

                if tou_filtering_result:
                    print(f"✅ Step 3 completed for {house_input}!")
                    print(f"📊 TOU Optimization Results:")
                    for tariff_type in selected_tariffs:
                        tou_count = tou_filtering_result['tou_results'].get(tariff_type, {}).get('event_count', 0)
                        print(f"  • {tariff_type} optimizable events: {tou_count:,}")
                else:
                    print(f"❌ Step 3 failed for {house_input}")
                    return
            else:
                # Batch TOU filtering
                tou_filtering_results = batch_process_filtering(
                    house_data_dict=house_appliances,
                    tariff_types=selected_tariffs
                )
                print(f"✅ Step 3 completed for {len(tou_filtering_results)} households!")

        print(f"\n🎉 Processing completed successfully!")
        print(f"📁 Output files saved to:")
        print(f"  • Constraints: ./output/04_user_constraints/")
        print(f"  • Min duration filtered: ./output/04_min_duration_filter/")
        print(f"  • TOU filtered: ./output/04_TOU_filter/")
        
    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
