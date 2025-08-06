#!/usr/bin/env python3
"""
Test batch processing with a small subset of houses
"""

from test_func_5_int import (
    process_batch_household_energy_optimization,
    print_result_summary
)

def test_small_batch():
    """Test batch processing with 3 houses"""
    print("🧪 Testing Small Batch Processing (3 houses)")
    print("=" * 60)
    
    # Test with a small batch
    house_list = ["house1", "house2", "house3"]
    
    result = process_batch_household_energy_optimization(
        house_list=house_list,
        tariff_config="tariff_config",  # Use default UK tariffs
        interactive_mode=False  # Non-interactive for testing
    )
    
    print_result_summary(result)
    return result

def main():
    """Main test function"""
    try:
        result = test_small_batch()
        
        # Summary
        print("\n📊 Test Summary:")
        print("=" * 30)
        print(f"Batch test: {'✅ PASS' if result['status'] == 'success' else '❌ FAIL'}")
        
        if result['status'] == 'success':
            print(f"✅ Successfully processed {result['processed_houses']} houses")
            print("🎉 Small batch test completed successfully!")
        else:
            print("⚠️ Batch test failed. Check the output above for details.")
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
