#!/usr/bin/env python3
"""
Debug script for p_042_user_constraints
"""

import os
from tools.p_042_user_constraints import UserConstraintsParser

def test_load_appliance_summary():
    """Test loading appliance summary"""
    print("🔍 Testing appliance summary loading...")
    
    parser = UserConstraintsParser()
    
    # Test direct file existence
    summary_file = "output/04_appliance_summary/UK/house1/appliance_summary.json"
    print(f"File exists: {os.path.exists(summary_file)}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Test load_appliance_summary method
    summary = parser.load_appliance_summary("house1")
    print(f"Loaded summary: {summary is not None}")
    
    if summary:
        print(f"Summary keys: {list(summary.keys())}")
        if 'appliances' in summary:
            print(f"Number of appliances: {len(summary['appliances'])}")
    
    return summary

def test_process_single_household():
    """Test process_single_household method"""
    print("\n🔍 Testing process_single_household...")
    
    parser = UserConstraintsParser()
    result = parser.process_single_household(
        house_id="house1",
        user_input="Test instruction"
    )
    
    print(f"Process result: {result}")
    return result

def main():
    """Main debug function"""
    print("🧪 Debugging p_042_user_constraints")
    print("=" * 50)
    
    try:
        # Test 1: Load appliance summary
        summary = test_load_appliance_summary()
        
        if summary:
            # Test 2: Process single household
            result = test_process_single_household()
        else:
            print("❌ Cannot proceed without appliance summary")
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
