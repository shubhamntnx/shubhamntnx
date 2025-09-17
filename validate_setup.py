#!/usr/bin/env python3
"""
Validation script to test the RBAC automation setup
"""

import sys
import os
import json
from pathlib import Path

def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        "testcases/cdp/stargate/storage_policy/rbac/test_storage_policy_rbac.py",
        "testcases/cdp/stargate/storage_policy/rbac/config.py",
        "testcases/cdp/stargate/storage_policy/rbac/__init__.py",
        "workflows/cdp/test_orchestrator/storage_policy_utils/storage_policy_grbac_helper.py",
        "workflows/cdp/test_orchestrator/storage_policy_utils/__init__.py",
        "requirements.txt",
        "pytest.ini",
        "run_rbac_tests.py",
        "README.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_user_entities_data():
    """Test user entities data structure without importing selenium."""
    # Read the helper file and extract user entities manually
    helper_file = "workflows/cdp/test_orchestrator/storage_policy_utils/storage_policy_grbac_helper.py"
    
    try:
        with open(helper_file, 'r') as f:
            content = f.read()
        
        # Check if user entities are defined
        if 'self.user_entities = {' in content:
            print("✅ User entities data structure found")
            
            # Count users by looking for email patterns
            user_count = content.count('@qa.nutanix.com')
            print(f"✅ Found {user_count} test users configured")
            
            # Check for required fields
            if "'category':" in content and "'sps':" in content:
                print("✅ Required fields (category, sps) found in user data")
            else:
                print("❌ Missing required fields in user data")
                return False
                
            return True
        else:
            print("❌ User entities data structure not found")
            return False
            
    except Exception as e:
        print(f"❌ Error reading helper file: {e}")
        return False

def test_configuration():
    """Test configuration file."""
    try:
        sys.path.append('testcases/cdp/stargate/storage_policy/rbac')
        
        # Import without selenium dependencies
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "config", 
            "testcases/cdp/stargate/storage_policy/rbac/config.py"
        )
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        config_class = config_module.RBACTestConfig
        config_dict = config_class.get_config()
        
        print("✅ Configuration file loads successfully")
        print(f"✅ Prism Central URL: {config_dict['prism_central_url']}")
        print(f"✅ User credentials configured: {len(config_dict['user_credentials'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False

def test_requirements():
    """Test requirements file."""
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        required_packages = ['selenium', 'pytest', 'webdriver-manager']
        missing_packages = []
        
        for package in required_packages:
            if package not in requirements:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing required packages: {missing_packages}")
            return False
        else:
            print("✅ All required packages listed in requirements.txt")
            return True
            
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False

def main():
    """Main validation function."""
    print("🔍 Validating Storage Policy RBAC automation setup...\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("User Entities Data", test_user_entities_data),
        ("Configuration", test_configuration),
        ("Requirements", test_requirements)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
    
    print(f"\n📊 Validation Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Setup validation completed successfully!")
        print("🚀 You can now run the RBAC tests with: python3 run_rbac_tests.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validation tests failed")
        print("🔧 Please fix the issues before running the RBAC tests")
        return 1

if __name__ == "__main__":
    sys.exit(main())