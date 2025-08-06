#!/usr/bin/env python3
"""
Test script for test_func_5_int.py integration tool
"""

from test_func_5_int import (
    process_single_household_energy_optimization,
    process_batch_household_energy_optimization,
    print_result_summary
)

def test_single_household():
    """Test single household processing"""
    print("🧪 Testing Single Household Processing")
    print("=" * 50)
    
    # Test with default settings
    result = process_single_household_energy_optimization(
        house_id="house1",
        user_instruction="For Washing Machine: avoid operation between 5 PM and 8 PM, ignore events shorter than 10 minutes"
    )
    
    print_result_summary(result)
    return result

def test_batch_households():
    """Test batch household processing"""
    print("\n🧪 Testing Batch Household Processing")
    print("=" * 50)
    
    # Test with a small batch
    house_list = ["house1", "house2"]
    user_instructions = {
        "house1": "Washing Machine: no operation between 11 PM and 6 AM",
        "house2": "Dishwasher: must finish by 2 PM next day"
    }
    
    result = process_batch_household_energy_optimization(
        house_list=house_list,
        user_instructions=user_instructions,
        tariff_config="tariff_config",  # Use default UK tariffs
        interactive_mode=False  # Non-interactive for testing
    )
    
    print_result_summary(result)
    return result

def main():
    """Main test function"""
    print("🚀 Testing Energy Optimization Integration Tool")
    print("=" * 60)
    
    try:
        # Test single household
        single_result = test_single_household()
        
        # Test batch households
        batch_result = test_batch_households()
        
        # Summary
        print("\n📊 Test Summary:")
        print("=" * 30)
        print(f"Single household test: {'✅ PASS' if single_result['status'] == 'success' else '❌ FAIL'}")
        print(f"Batch household test: {'✅ PASS' if batch_result['status'] == 'success' else '❌ FAIL'}")
        
        if single_result['status'] == 'success' and batch_result['status'] == 'success':
            print("\n🎉 All tests passed! Integration tool is working correctly.")
        else:
            print("\n⚠️ Some tests failed. Check the output above for details.")
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
