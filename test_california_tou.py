#!/usr/bin/env python3
"""
Test California TOU_D processing directly
"""

import sys
import os
sys.path.append('tools')

from p_044_tou_optimization_filter import process_and_mask_events

def test_california_tou():
    print("🧪 Testing California TOU_D Processing")
    print("=" * 50)
    
    # Test parameters
    house_id = "house1"
    tariff_type = "California"
    tariff_name = "TOU_D"

    # File paths
    input_file = f"output/04_min_duration_filter/{house_id}/min_duration_filtered_{house_id}.csv"
    constraint_file = f"output/04_user_constraints/{house_id}/appliance_constraints_revise_by_llm.json"
    tariff_config = f"config/TOU_D.json"
    output_dir = "output/04_TOU_filter"
    
    print(f"📋 Test Parameters:")
    print(f"  House ID: {house_id}")
    print(f"  Tariff Type: {tariff_type}")
    print(f"  Tariff Name: {tariff_name}")
    print(f"  Input File: {input_file}")
    print(f"  Constraint File: {constraint_file}")
    print(f"  Tariff Config: {tariff_config}")
    
    # Check if files exist
    for file_path in [input_file, constraint_file, tariff_config]:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        else:
            print(f"✅ File exists: {file_path}")
    
    print(f"\n🔄 Processing TOU filtering...")
    
    try:
        # Call the processing function directly
        result = process_and_mask_events(
            event_csv_path=input_file,
            constraint_json_path=constraint_file,
            tariff_config_path=tariff_config,
            tariff_name=tariff_name,
            output_dir=output_dir
        )
        
        print(f"✅ Processing completed successfully!")
        print(f"📊 Results:")
        print(f"  Output file: {result}")

        # Check if output file was created and has correct filtering
        if os.path.exists(result):
            import pandas as pd
            df = pd.read_csv(result)
            total_events = len(df)
            reschedulable_events = len(df[df['is_reschedulable'] == True])
            filtered_events = len(df[df['is_reschedulable'] == False])
            efficiency = (filtered_events / total_events * 100) if total_events > 0 else 0

            print(f"  📊 File Analysis:")
            print(f"    Total events: {total_events}")
            print(f"    Reschedulable events: {reschedulable_events}")
            print(f"    Filtered events: {filtered_events}")
            print(f"    Filter efficiency: {efficiency:.1f}%")
        
    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_california_tou()
