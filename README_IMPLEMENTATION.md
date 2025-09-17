# Nutanix CDP Strict Rack Awareness Test Implementation

## Overview

This implementation provides comprehensive automated tests for Nutanix CDP strict rack awareness functionality, following the existing nutest-py3 and nutest-py3-tests framework patterns.

## Implementation Structure

### Framework Architecture (nutest-py3/)

The framework follows a layered architecture:

1. **Entities Layer** (`nutest-py3/framework/entities/`)
   - `BaseEntity` - Abstract base for all entities
   - `ClusterEntity` - Cluster-level operations
   - `StorageEntity` - Storage container operations
   - `HostEntity` - Host management operations
   - `RackEntity` - Rack-aware operations

2. **Session Layer** (`nutest-py3/framework/session.py`)
   - HTTP session wrapper for API calls
   - Authentication and error handling
   - Request/response logging

### Workflows Layer (nutest-py3-tests/workflows/)

High-level workflows built on top of entities:

1. **ClusterWorkflows** - Cluster health, stability, FT upgrades
2. **StorageWorkflows** - Container lifecycle, placement validation
3. **RackAwarenessWorkflows** - Strict RA transitions, failure simulation

### Test Cases (nutest-py3-tests/testcases/cdp/strict_rack_awareness/)

Following the pattern you described, tests are organized as:

```
cdp.strict_rack_awareness.test_module.ClassName.test_method_name
```

## Implemented Test Cases

### 1. CreateClusterStrictRackAwareness
**File**: `test_create_cluster_strict_rack_awareness.py`
**Test Method**: `test_create_enable_disable_strict_ra_cluster`

Tests basic strict RA enable/disable functionality:
- Prerequisites validation (3+ racks, healthy cluster)
- Enable strict RA and validate RPP updates
- Create containers with strict placement
- Disable strict RA and validate transition
- Test container creation in best-effort mode

### 2. TransitionWorkflows
**File**: `test_transition_workflows.py`
**Test Methods**:
- `test_transition_best_effort_to_strict_ra`
- `test_transition_strict_ra_to_best_effort`

Tests smooth transitions between modes:
- Best-effort → Strict RA with prerequisites validation
- Strict RA → Best-effort with RPP reversion
- Container accessibility during transitions
- New container creation after transitions

### 3. FTUpgradeWorkflows
**File**: `test_ft_upgrade_workflows.py`
**Test Method**: `test_ft1_to_ft2_with_strict_ra`

Tests fault tolerance upgrades with strict RA:
- FT1 → FT2 upgrade process
- RPP updates to kRF3_Strict
- Metadata ensemble validation
- Data rebalance verification
- Quorum maintenance throughout upgrade

### 4. APIValidation
**File**: `test_api_validation.py`
**Test Method**: `test_validate_cluster_config_apis`

Tests cluster configuration APIs:
- GET API for `rack_awareness_strict` field presence
- PUT API with valid/invalid values
- Field validation and type checking
- Backward compatibility verification
- Edge case handling

### 5. RackFailureSimulation
**File**: `test_rack_failure_simulation.py`
**Test Method**: `test_simulate_rack_failure_and_validate_quorum`

Tests rack failure scenarios:
- Single and multiple rack failures
- Quorum maintenance validation
- Data availability during failures
- Recovery scenario testing
- Failure impact assessment

### 6. SkewedClusterBehavior
**File**: `test_skewed_cluster_behavior.py`
**Test Method**: `test_validate_skewed_cluster_behavior`

Tests behavior in uneven clusters:
- Skewed resource distribution analysis
- Container creation in constrained environments
- Placement behavior validation
- Resource utilization patterns
- Alert generation verification

### 7. StoragePolicyEnforcement
**File**: `test_storage_policy_enforcement.py`
**Test Method**: `test_validate_storage_policy_enforcement`

Tests policy enforcement:
- Valid container creation with strict RA
- Invalid policy override blocking
- Replication factor enforcement
- vDisk policy inheritance
- Policy enforcement during failures

## Configuration Structure

The `config.json` follows your described pattern:

```json
{
  "cdp.strict_rack_awareness.test_module.ClassName": {
    "cluster_ip": "10.1.1.100",
    "cluster_username": "admin",
    "cluster_password": "admin123",
    // ... class-level parameters
  },
  "cdp.strict_rack_awareness.test_module.ClassName.test_method_name": {
    "test_description": "Test description",
    "test_timeout_minutes": 45,
    "expected_result": "Expected outcome",
    // ... test-level parameters
  }
}
```

## Test Execution

### Running All Tests
```bash
cd /workspace/nutest-py3-tests
python test_runner.py --config testcases/cdp/strict_rack_awareness/config.json
```

### Running Specific Test
```bash
python test_runner.py --config testcases/cdp/strict_rack_awareness/config.json \
  --test "cdp.strict_rack_awareness.test_create_cluster_strict_rack_awareness.CreateClusterStrictRackAwareness.test_create_enable_disable_strict_ra_cluster"
```

### Debug Mode
```bash
python test_runner.py --config testcases/cdp/strict_rack_awareness/config.json --log-level DEBUG
```

## Key Features

### 1. Comprehensive Workflow Integration
- Tests use workflows that build on framework entities
- Workflows provide high-level operations (enable strict RA, simulate failures, etc.)
- Entities provide low-level API interactions

### 2. Robust Error Handling
- Comprehensive exception handling in all layers
- Graceful cleanup in teardown methods
- Session-level retry logic with authentication

### 3. Configurable Test Parameters
- Class-level and test-level parameter inheritance
- Flexible timeout and retry configurations
- Environment-specific cluster settings

### 4. Realistic Test Scenarios
- Based on actual CDP operational patterns
- Covers positive and negative test cases
- Includes edge cases and failure scenarios

### 5. Detailed Reporting
- Comprehensive test result tracking
- Performance metrics collection
- Structured logging with multiple levels

## Integration with Existing Framework

### Following nutest-py3 Patterns
- Entity-based architecture for API interactions
- Workflow layer for business logic
- Session management for HTTP communications
- Configuration-driven test execution

### Following nutest-py3-tests Patterns
- Package structure: `testcases/cdp/strict_rack_awareness/`
- Test naming: `package.module.ClassName.test_method`
- Parameter inheritance: class-level → test-level
- Workflow composition in test methods

### API Integration
- RESTful API calls to Nutanix cluster
- Authentication and session management
- Error handling and retry logic
- Response validation and parsing

## Extensibility

### Adding New Tests
1. Create new test module in `testcases/cdp/strict_rack_awareness/`
2. Define test class with `__init__(session, test_params)`
3. Implement `setup()`, `teardown()`, and test methods
4. Add configuration entries to `config.json`

### Adding New Workflows
1. Create workflow class in `workflows/`
2. Initialize with session and use entities
3. Implement high-level business operations
4. Use in test classes for complex operations

### Adding New Entities
1. Create entity class inheriting from `BaseEntity`
2. Implement required abstract methods
3. Add entity-specific API operations
4. Use in workflows for low-level operations

## Testing Best Practices

### 1. Test Isolation
- Each test has independent setup/teardown
- Resource cleanup prevents test interference
- Configuration isolation per test

### 2. Realistic Scenarios
- Tests simulate real-world conditions
- Failure scenarios test system resilience
- Edge cases validate robustness

### 3. Comprehensive Validation
- Multi-level validation (prerequisites, intermediate, final)
- Both positive and negative test cases
- Performance and functional testing

### 4. Maintainability
- Modular architecture with clear separation
- Reusable workflows and utilities
- Comprehensive documentation and logging

## Deployment Requirements

### Cluster Prerequisites
- **Minimum 3 racks** with proper configuration
- **Healthy cluster state** (all nodes operational)
- **Admin API access** with full permissions
- **Sufficient capacity** for test operations

### Configuration
1. Update cluster credentials in `config.json`
2. Adjust timeouts based on cluster performance
3. Enable/disable rack failure simulation as needed
4. Configure logging levels and paths

### Execution Environment
- Python 3.7+
- Required packages: `requests`, `urllib3`
- Network access to cluster management interface
- Sufficient permissions for cluster operations

This implementation provides a production-ready test suite that follows your existing framework patterns while delivering comprehensive validation of strict rack awareness functionality.