#!/usr/bin/env python3
"""
Agent V2 Test - Appliance Information Standardization Module
===========================================================

This module provides appliance information standardization functionality:
- Extract appliance lists from event segments
- Handle duplicate appliance names with automatic numbering
- Support multiple tariff types (UK, Germany, California)
- Single household or batch processing
- Generate structured appliance summaries for scheduling modules
"""

import os
import sys
import json
from typing import Dict, List, Optional

# Add current directory to path for imports
sys.path.append('.')

from tools.p_041_get_appliance_list import (
    get_appliance_list_from_csv,
    batch_get_appliance_lists,
    single_house_appliance_analysis,
    handle_duplicate_appliance_names
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


def display_appliance_summary(summary: Dict):
    """Display a formatted appliance summary"""
    print(f"\n📊 Appliance Summary for {summary.get('house_id', 'Unknown').upper()}:")
    print("=" * 60)
    
    print(f"🏠 House ID: {summary.get('house_id', 'N/A')}")
    print(f"💰 Tariff Type: {summary.get('tariff_type', 'N/A')}")
    print(f"🔧 Total Appliances: {summary.get('total_appliances', 0)}")
    print(f"📅 Total Events: {summary.get('total_events', 0):,}")
    
    reschedulable_count = len(summary.get('reschedulable_ids', []))
    non_reschedulable_count = len(summary.get('non_reschedulable_ids', []))
    
    print(f"✅ Reschedulable: {reschedulable_count}")
    print(f"❌ Non-reschedulable: {non_reschedulable_count}")
    
    if summary.get('appliance_details'):
        print(f"\n📋 Detailed Appliance List:")
        print("-" * 60)
        
        for detail in summary['appliance_details']:
            appliance_id = detail.get('appliance_id', 'N/A')
            appliance_name = detail.get('appliance_name', 'N/A')
            original_name = detail.get('original_name', appliance_name)
            is_reschedulable = detail.get('is_reschedulable', False)
            
            status = "✅ Reschedulable" if is_reschedulable else "❌ Non-reschedulable"
            original_note = f" (originally: {original_name})" if appliance_name != original_name else ""
            
            print(f"  • {appliance_id}: {appliance_name}{original_note} - {status}")


def main():
    """Main function for interactive appliance information standardization"""
    print("🚀 Starting Agent V2 Test - Appliance Information Standardization Module")
    print("=" * 80)
    
    # Display available tariff types
    available_types = get_available_tariff_types()
    print("📊 Available tariff types:")
    for i, tariff_type in enumerate(available_types, 1):
        print(f"  {i}. {tariff_type}")
    
    print("\n" + "=" * 80)
    print("Please select processing mode:")
    print("1. Single household analysis (Default)")
    print("2. Batch analysis - All households")
    print("3. Test duplicate name handling")
    
    try:
        choice = input("Please enter your choice (1/2/3) [Default: 1]: ").strip()
        if not choice:
            choice = "1"
        
        if choice == "3":
            # Test duplicate name handling
            print("\n🧪 Testing duplicate name handling...")
            test_data = [
                {'appliance_id': 'Appliance1', 'appliance_name': 'Fridge', 'is_reschedulable': False},
                {'appliance_id': 'Appliance2', 'appliance_name': 'Fridge', 'is_reschedulable': False},
                {'appliance_id': 'Appliance3', 'appliance_name': 'Washing Machine', 'is_reschedulable': True},
                {'appliance_id': 'Appliance4', 'appliance_name': 'Fridge', 'is_reschedulable': False},
                {'appliance_id': 'Appliance5', 'appliance_name': 'Television', 'is_reschedulable': False},
            ]
            
            result = handle_duplicate_appliance_names(test_data)
            
            print("Original data:")
            for item in test_data:
                print(f"  {item['appliance_id']}: {item['appliance_name']}")
            
            print("\nAfter duplicate handling:")
            for item in result:
                print(f"  {item['appliance_id']}: {item['appliance_name']} (original: {item['original_name']})")
            
            return
        
        # Select tariff type
        print("\nSelect tariff type:")
        for i, tariff_type in enumerate(available_types, 1):
            print(f"  {i}. {tariff_type}")
        
        tariff_choice = input(f"Please enter your choice (1-{len(available_types)}) [Default: 1]: ").strip()
        if not tariff_choice:
            tariff_choice = "1"
        
        try:
            tariff_index = int(tariff_choice) - 1
            if 0 <= tariff_index < len(available_types):
                selected_tariff = available_types[tariff_index]
            else:
                print("Invalid choice, using UK as default")
                selected_tariff = "UK"
        except ValueError:
            print("Invalid input, using UK as default")
            selected_tariff = "UK"
        
        print(f"\n✅ Selected tariff type: {selected_tariff}")
        
        # Load house configuration
        house_appliances = load_house_appliances_config()
        
        if choice == "1":
            # Single household mode
            print(f"\n📋 Available households: {list(house_appliances.keys())}")
            house_input = input("Enter house ID (e.g., house1) [Default: house1]: ").strip()
            if not house_input:
                house_input = "house1"
            
            if house_input not in house_appliances:
                print(f"❌ House {house_input} not found in configuration")
                return
            
            summary = single_house_appliance_analysis(
                house_id=house_input,
                tariff_type=selected_tariff
            )
            
            if summary:
                display_appliance_summary(summary)
                print(f"\n🎉 Single household analysis completed!")
            else:
                print(f"\n❌ Analysis failed")
        
        elif choice == "2":
            # Batch mode
            results = batch_get_appliance_lists(
                house_data_dict=house_appliances,
                tariff_type=selected_tariff
            )

            print(f"\n�� Batch analysis completed!")
            print(f"📊 Results summary:")
            print(f"  • Tariff type: {selected_tariff}")
            print(f"  • Total processed: {len(results)}")

            # Show detailed results for all households
            if results:
                print(f"\n" + "=" * 100)
                print(f"📋 DETAILED RESULTS FOR ALL {len(results)} HOUSEHOLDS")
                print("=" * 100)

                # Sort houses by house number for better display
                sorted_houses = sorted(results.keys(), key=lambda x: int(x.replace('house', '')))

                for i, house_id in enumerate(sorted_houses, 1):
                    print(f"\n[{i}/{len(results)}] " + "=" * 80)
                    display_appliance_summary(results[house_id])

                    # Add separator between houses (except for the last one)
                    if i < len(results):
                        print("\n" + "-" * 100)

                print(f"\n" + "=" * 100)
                print(f"🎯 ALL {len(results)} HOUSEHOLD SUMMARIES COMPLETED!")
                print("=" * 100)
        
        else:
            print("❌ Invalid choice")
            return
        
    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()