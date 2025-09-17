# Storage Policy RBAC UI Automation

This project automates the verification of Role-Based Access Control (RBAC) for storage policies in Nutanix Prism Central UI.

## Overview

The automation verifies that users can only see and access storage policies according to their assigned permissions. It tests the UI behavior for multiple users with different permission levels.

## Project Structure

```
/workspace/
├── testcases/cdp/stargate/storage_policy/rbac/
│   ├── __init__.py
│   ├── test_storage_policy_rbac.py      # Main test cases
│   └── config.py                        # Configuration settings
├── workflows/cdp/test_orchestrator/storage_policy_utils/
│   ├── __init__.py
│   └── storage_policy_grbac_helper.py   # RBAC helper utilities
├── run_rbac_tests.py                    # Test runner script
├── requirements.txt                     # Python dependencies
├── pytest.ini                          # Pytest configuration
└── README.md                           # This file
```

## Features

- **Automated UI Testing**: Uses Selenium WebDriver to interact with Prism Central UI
- **Multi-User RBAC Verification**: Tests permissions for 24 different users
- **Comprehensive Reporting**: Generates detailed HTML and text reports
- **Flexible Test Execution**: Supports different test types (unit, integration, slow)
- **Screenshot Capture**: Captures screenshots on failures for debugging
- **Configurable Environment**: Supports environment variables for configuration

## User Entities Tested

The automation tests the following user types based on their category and storage policy access:

### Users with 'ALL' Category Access
- `ca_user12@qa.nutanix.com` - Full access to all storage policies
- `ca_user14@qa.nutanix.com` - Full access to all storage policies
- `ca_user17@qa.nutanix.com` - Full access to all storage policies
- And more...

### Users with Limited Category Access
- `vo_user4@qa.nutanix.com` - Limited to specific categories
- `cdp_user1@qa.nutanix.com` - Restricted access
- `ca_user20@qa.nutanix.com` - Specific category permissions
- And more...

## Prerequisites

1. **Python 3.8+** installed
2. **Google Chrome browser** installed
3. **Access to Prism Central** at `https://10.46.100.3:9440/`
4. **Valid user credentials** for the test users

## Installation

1. Clone or download the project files
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables

Set the following environment variables for configuration:

```bash
# Prism Central URL (default: https://10.46.100.3:9440/)
export PRISM_CENTRAL_URL="https://your-prism-central:9440/"

# Browser settings
export BROWSER_HEADLESS="true"  # or "false" for visible browser
export BROWSER_TIMEOUT="30"

# User passwords (use secure credential store in production)
export VO_USER2_PASSWORD="actual_password"
export CA_USER21_PASSWORD="actual_password"
# ... set passwords for all test users
```

### User Credentials

**Important**: The current configuration uses placeholder passwords. In a production environment:

1. Use a secure credential management system
2. Set actual passwords via environment variables
3. Never commit real passwords to version control

## Usage

### Quick Start

Run all tests with default settings:
```bash
python run_rbac_tests.py
```

### Advanced Usage

```bash
# Run only unit tests
python run_rbac_tests.py --test-type unit

# Run integration tests with visible browser
python run_rbac_tests.py --test-type integration --no-headless

# Run slow/comprehensive tests
python run_rbac_tests.py --test-type slow

# Skip dependency installation
python run_rbac_tests.py --no-install

# Run with minimal output
python run_rbac_tests.py --quiet
```

### Direct Pytest Usage

You can also run tests directly with pytest:

```bash
# Run all tests
pytest testcases/cdp/stargate/storage_policy/rbac/test_storage_policy_rbac.py -v

# Run specific test
pytest testcases/cdp/stargate/storage_policy/rbac/test_storage_policy_rbac.py::TestStoragePolicyRBAC::test_individual_user_rbac -v

# Run with specific markers
pytest -m "not slow" -v  # Skip slow tests
pytest -m "integration" -v  # Run only integration tests
```

## Test Types

### Unit Tests
- Test helper class initialization
- Validate user entities data structure
- Test error handling
- Pattern analysis

### Integration Tests
- Test Prism Central accessibility
- Verify UI elements presence
- End-to-end user login and navigation

### Individual User Tests
- Login verification for specific users
- Storage policy visibility verification
- RBAC permission validation

### Comprehensive Tests (Slow)
- Test all users in batch mode
- Generate detailed reports
- Full RBAC verification matrix

## Reports

The automation generates multiple types of reports:

### HTML Report
- Location: `reports/rbac_test_report.html`
- Interactive HTML report with test results
- Screenshots of failures
- Execution timeline

### Text Report
- Location: `rbac_verification_report.txt`
- Detailed RBAC verification results
- User-by-user permission analysis
- Summary statistics

### Log Files
- Location: `storage_policy_rbac_tests.log`
- Detailed execution logs
- Debug information
- Error traces

## Key Classes and Methods

### StoragePolicyRBACHelper
Main helper class for RBAC verification:

- `setup_driver()` - Initialize Selenium WebDriver
- `login_to_prism_central()` - Login with user credentials
- `navigate_to_storage_policies()` - Navigate to storage policies page
- `get_visible_storage_policies()` - Get list of visible policies
- `verify_user_rbac_permissions()` - Verify user permissions
- `verify_all_users_rbac()` - Batch verification for all users
- `generate_report()` - Generate detailed reports

### TestStoragePolicyRBAC
Main test class with various test methods:

- `test_individual_user_rbac()` - Test specific users
- `test_users_with_all_category_access()` - Test users with full access
- `test_users_with_limited_category_access()` - Test restricted users
- `test_all_users_rbac_batch()` - Comprehensive batch testing

## Troubleshooting

### Common Issues

1. **Chrome driver not found**
   - The automation uses webdriver-manager to auto-download Chrome driver
   - Ensure Chrome browser is installed

2. **Login failures**
   - Verify Prism Central URL is accessible
   - Check user credentials are correct
   - Ensure users exist in the system

3. **UI element not found**
   - Prism Central UI may have changed
   - Update selectors in the helper class
   - Enable screenshots to debug UI issues

4. **Test timeouts**
   - Increase BROWSER_TIMEOUT environment variable
   - Check network connectivity to Prism Central
   - Verify system performance

### Debug Mode

Enable debug mode for troubleshooting:
```bash
# Run with visible browser and verbose logging
python run_rbac_tests.py --no-headless --test-type unit

# Enable screenshot capture
export ENABLE_SCREENSHOTS="true"
```

## Customization

### Adding New Users
1. Update `user_entities` dictionary in `storage_policy_grbac_helper.py`
2. Add credentials to `config.py` or environment variables
3. Update test parameters as needed

### Modifying UI Selectors
1. Update selectors in helper methods if UI changes
2. Test with visible browser mode first
3. Add fallback selectors for robustness

### Custom Reports
1. Extend `generate_report()` method for custom formats
2. Add new report types (JSON, XML, etc.)
3. Integrate with CI/CD reporting systems

## CI/CD Integration

The automation is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run RBAC Tests
  run: |
    python run_rbac_tests.py --test-type unit
    python run_rbac_tests.py --test-type integration
  env:
    BROWSER_HEADLESS: "true"
    PRISM_CENTRAL_URL: ${{ secrets.PRISM_CENTRAL_URL }}
    # Add user credentials as secrets
```

## Security Considerations

1. **Never commit real passwords** to version control
2. **Use secure credential stores** in production
3. **Limit test user permissions** to minimum required
4. **Rotate test credentials** regularly
5. **Monitor test execution logs** for security events

## Contributing

1. Follow existing code style and patterns
2. Add tests for new functionality
3. Update documentation for changes
4. Ensure all tests pass before submitting

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review log files for errors
3. Enable debug mode for investigation
4. Contact the development team

---

**Note**: This automation is designed for QA environments. Ensure proper security measures when running in production environments.