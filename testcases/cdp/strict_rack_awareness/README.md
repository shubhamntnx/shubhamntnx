# Strict Rack Awareness Test Suite

This test suite provides comprehensive automated testing for Nutanix CDP strict rack awareness functionality.

## Overview

The test suite includes 7 main test cases that validate different aspects of strict rack awareness:

1. **transition_best_effort_to_strict_ra** - Tests enabling strict rack awareness
2. **transition_strict_ra_to_best_effort** - Tests disabling strict rack awareness  
3. **ft1_to_ft2_with_strict_ra** - Tests FT upgrades with strict RA enabled
4. **validate_cluster_config_apis** - Tests API handling of strict RA field
5. **simulate_rack_failure_and_validate_quorum** - Tests rack failure scenarios
6. **validate_skewed_cluster_behavior** - Tests behavior in uneven clusters
7. **validate_storage_policy_enforcement** - Tests policy enforcement

## Architecture

### Framework Components

- **nutest-py3/framework/** - Core testing framework
  - `BaseTest` - Base class for all tests
  - `TestConfig` - Configuration management
  - `APIClient` - Cluster API interactions
  - `ClusterManager` - High-level cluster operations
  - `TestResult` - Test result tracking

- **nutest-py3-tests/common/** - Common utilities
  - `RackAwarenessTestUtils` - Rack awareness specific operations
  - `ClusterValidationUtils` - Cluster validation utilities
  - `TestDataGenerator` - Test data generation

### Test Structure

Each test follows a standard pattern:
1. **Setup** - Validate prerequisites and prepare environment
2. **Execute** - Run test steps with validations
3. **Teardown** - Clean up resources and restore state

## Configuration

### Configuration File

Edit `config.json` to match your cluster environment:

```json
{
  "cluster": {
    "ip": "your-cluster-ip",
    "username": "admin", 
    "password": "your-password",
    "port": 9440,
    "use_https": true
  },
  "min_racks_required": 3,
  "rack_failure_simulation": true,
  "parallel_execution": false,
  "max_parallel_tests": 3
}
```

### Environment Variables

Alternatively, use environment variables:
- `CLUSTER_IP` - Cluster IP address
- `CLUSTER_USERNAME` - Username
- `CLUSTER_PASSWORD` - Password
- `MIN_RACKS` - Minimum racks required (default: 3)
- `LOG_LEVEL` - Logging level (default: INFO)

## Usage

### Running All Tests

```bash
# Sequential execution (recommended)
python test_runner.py --config config.json

# Parallel execution (faster but may cause conflicts)
python test_runner.py --config config.json --parallel

# With custom logging
python test_runner.py --config config.json --log-level DEBUG --log-file /tmp/tests.log
```

### Running Specific Tests

```bash
# Run a specific test
python test_runner.py --test TransitionBestEffortToStrictRATest

# Run with different log level
python test_runner.py --test ValidateClusterConfigAPIsTest --log-level DEBUG
```

### Direct Test Execution

```python
from nutest_py3.framework import TestConfig
from testcases.cdp.strict_rack_awareness.tests.test_transition_best_effort_to_strict_ra import TransitionBestEffortToStrictRATest

# Load config and run test
config = TestConfig.from_file('config.json')
test = TransitionBestEffortToStrictRATest(config)
result = test.run()

print(f"Test result: {result.status}")
```

## Prerequisites

### Cluster Requirements

1. **Minimum 3 racks** - Required for strict rack awareness testing
2. **Healthy cluster state** - All nodes operational
3. **Sufficient capacity** - For creating test containers and handling failures
4. **API access** - Admin credentials with full cluster access

### Rack Configuration

- Racks must be properly configured in cluster
- Each rack should have multiple hosts for meaningful testing
- Network connectivity between all racks

### Permissions

The test user must have permissions for:
- Cluster configuration changes
- Storage container management
- Host power operations (for failure simulation)
- Protection domain operations

## Test Details

### Test Case 1: transition_best_effort_to_strict_ra

**Purpose**: Validate enabling strict rack awareness

**Steps**:
1. Ensure cluster is in best-effort mode
2. Validate prerequisites (3+ racks, healthy cluster)
3. Enable strict rack awareness
4. Validate RPPs are updated
5. Verify new containers follow strict placement

**Expected Results**:
- Strict RA successfully enabled
- RPPs updated to strict versions
- Container placement honors rack boundaries

### Test Case 2: transition_strict_ra_to_best_effort

**Purpose**: Validate disabling strict rack awareness

**Steps**:
1. Ensure cluster has strict RA enabled
2. Disable strict rack awareness
3. Validate RPPs revert to best-effort
4. Test new container creation

**Expected Results**:
- Strict RA successfully disabled
- RPPs revert to best-effort versions
- Containers can be created without strict constraints

### Test Case 3: ft1_to_ft2_with_strict_ra

**Purpose**: Validate FT upgrades with strict RA

**Steps**:
1. Ensure cluster is at FT1 with strict RA
2. Initiate upgrade to FT2
3. Monitor upgrade progress
4. Validate RPPs updated to kRF3_Strict
5. Verify metadata ensemble and rebalancing

**Expected Results**:
- Successful upgrade to FT2
- RPPs updated to kRF3_Strict
- Quorum maintained throughout upgrade

### Test Case 4: validate_cluster_config_apis

**Purpose**: Validate API handling of rack_awareness_strict field

**Steps**:
1. Test GET /cluster API
2. Test PUT /cluster API with field changes
3. Validate field acceptance and backward compatibility
4. Test edge cases and invalid values

**Expected Results**:
- Field present in GET responses
- PUT accepts boolean values
- Invalid values rejected or converted
- Backward compatibility maintained

### Test Case 5: simulate_rack_failure_and_validate_quorum

**Purpose**: Test rack failure scenarios and quorum maintenance

**Steps**:
1. Create test data across racks
2. Simulate single rack failure
3. Validate quorum maintenance
4. Test multiple rack failures
5. Validate data availability
6. Test recovery scenarios

**Expected Results**:
- Quorum maintained within FT limits
- Data remains available when possible
- Cluster recovers properly after rack restoration

### Test Case 6: validate_skewed_cluster_behavior

**Purpose**: Test behavior in clusters with uneven rack resources

**Steps**:
1. Analyze/create skewed cluster scenario
2. Enable strict RA in skewed environment
3. Test container creation and placement
4. Simulate failures in skewed cluster
5. Validate alert generation

**Expected Results**:
- Strict RA works despite resource imbalance
- Placement honors rack boundaries where possible
- Appropriate alerts raised for FT risks

### Test Case 7: validate_storage_policy_enforcement

**Purpose**: Test storage policy enforcement for strict RA

**Steps**:
1. Create containers with strict RA policies
2. Test invalid policy overrides
3. Validate replication factor enforcement
4. Test vDisk policy inheritance
5. Test enforcement during failures

**Expected Results**:
- Invalid overrides blocked or warned
- Policies properly inherited
- Enforcement maintained during failures

## Troubleshooting

### Common Issues

1. **Insufficient Racks**
   - Error: "Insufficient racks for strict RA: X < 3"
   - Solution: Ensure cluster has at least 3 properly configured racks

2. **API Authentication**
   - Error: "Authentication failed"
   - Solution: Verify credentials in config.json

3. **Cluster Not Healthy**
   - Error: "Cluster not in healthy state"
   - Solution: Resolve any cluster health issues before testing

4. **Timeout Issues**
   - Error: "Test timeout exceeded"
   - Solution: Increase timeout values in configuration

### Debug Mode

Enable debug logging for detailed information:

```bash
python test_runner.py --log-level DEBUG --log-file debug.log
```

### Test Isolation

If tests interfere with each other:
1. Run tests sequentially (default)
2. Increase inter-test delays
3. Ensure proper cleanup in teardown methods

## Extending the Test Suite

### Adding New Tests

1. Create new test class inheriting from `BaseTest`
2. Implement required properties and methods
3. Add to `test_runner.py` test_classes list
4. Update this README

### Custom Validation

Add custom validation methods to utility classes:
- `RackAwarenessTestUtils` for RA-specific validations
- `ClusterValidationUtils` for general cluster validations
- `TestDataGenerator` for test data creation

### Configuration Extensions

Add new configuration options to:
1. `TestConfig` class in framework
2. Default config.json
3. Environment variable handling

## Metrics and Reporting

Tests collect detailed metrics including:
- Execution times
- Resource utilization
- Failure scenarios tested
- API response times
- Placement validation results

Metrics are available in TestResult objects and can be exported for analysis.

## Support

For issues or questions:
1. Check logs for detailed error information
2. Verify cluster meets all prerequisites  
3. Review configuration settings
4. Test individual components in isolation