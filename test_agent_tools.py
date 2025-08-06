#!/usr/bin/env python3
"""
Test script for Agent Tools integration
"""

import sys
import os

# Add current directory to path for imports
sys.path.append('.')

def test_import():
    """Test if all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from agent_tools import process_energy_constraints, validate_user_instruction
        print("✅ agent_tools imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_validation():
    """Test instruction validation"""
    print("\n🔍 Testing instruction validation...")
    
    try:
        from agent_tools import validate_user_instruction
        
        test_instruction = (
            "For Washing Machine and Dishwasher:\n"
            "- Do not operate between 5 PM and 8 PM\n"
            "- Ignore events shorter than 10 minutes"
        )
        
        validation = validate_user_instruction(test_instruction)
        print(f"✅ Validation result: {validation}")
        return True
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def test_file_structure():
    """Test if required files exist"""
    print("\n🔍 Testing file structure...")
    
    required_files = [
        "tools/p_042_user_constraints.py",
        "tools/p_043_min_duration_filter.py", 
        "tools/p_044_tou_optimization_filter.py",
        "config/TOU_D.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def main():
    """Main test function"""
    print("🧪 Testing Agent Energy Optimization Tools")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_import),
        ("File Structure Test", test_file_structure),
        ("Validation Test", test_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔧 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Agent tools are ready for use.")
        
        # Show usage example
        print("\n📋 Usage Example:")
        print("""
from agent_tools import process_energy_constraints

result = process_energy_constraints(
    user_instruction="Washing machine cannot run between 11 PM and 6 AM",
    region="California"
)

print(f"Status: {result['status']}")
print(f"Output files: {result['output_files']}")
        """)
    else:
        print("⚠️ Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main()
