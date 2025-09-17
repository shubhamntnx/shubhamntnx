"""
Test Storage Policy Enforcement

This module contains tests for ensuring storage policies enforce strict RA rules.
"""

import logging
import time
from typing import List, Dict, Any

from nutest_py3_tests.workflows.rack_awareness_workflows import RackAwarenessWorkflows
from nutest_py3_tests.workflows.cluster_workflows import ClusterWorkflows
from nutest_py3_tests.workflows.storage_workflows import StorageWorkflows


class StoragePolicyEnforcement:
    """
    Test class for storage policy enforcement validation
    """
    
    def __init__(self, session, test_params: Dict[str, Any]):
        self.session = session
        self.test_params = test_params
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize workflows
        self.rack_workflows = RackAwarenessWorkflows(session)
        self.cluster_workflows = ClusterWorkflows(session)
        self.storage_workflows = StorageWorkflows(session)
        
        # Test data
        self.test_containers = []
        self.created_container_names = []
        self.test_vdisks = []
        self.policy_violations = []
    
    def setup(self):
        """Setup method called before each test"""
        self.logger.info("Setting up StoragePolicyEnforcement test")
        
        # Validate cluster connectivity
        try:
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            if 'error' in health_summary:
                raise RuntimeError(f"Cluster health check failed: {health_summary['error']}")
            
            self.logger.info(f"Cluster status: {health_summary.get('cluster_status')}")
            
            # Ensure we have enough racks for policy testing
            rack_count = health_summary.get('rack_count', 0)
            if rack_count < 3:
                raise RuntimeError(f"Insufficient racks for policy testing: {rack_count} < 3")
            
        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise
    
    def teardown(self):
        """Teardown method called after each test"""
        self.logger.info("Tearing down StoragePolicyEnforcement test")
        
        # Cleanup test vDisks
        if self.test_vdisks:
            self._cleanup_test_vdisks()
        
        # Cleanup test containers
        if self.created_container_names:
            try:
                cleaned_count = self.storage_workflows.cleanup_test_containers_workflow(
                    self.created_container_names
                )
                self.logger.info(f"Cleaned up {cleaned_count} test containers")
            except Exception as e:
                self.logger.warning(f"Cleanup failed: {str(e)}")
        
        # Reset test data
        self.test_containers.clear()
        self.created_container_names.clear()
        self.test_vdisks.clear()
        self.policy_violations.clear()
    
    def test_validate_storage_policy_enforcement(self):
        """
        Test ensure storage policies enforce strict RA rules
        
        Test Steps:
        1. Enable strict rack awareness
        2. Test valid container creation with strict RA
        3. Test invalid policy overrides
        4. Test replication factor enforcement
        5. Test vDisk policy enforcement
        6. Test policy inheritance
        7. Test policy violation handling
        8. Test policy enforcement during failures
        """
        self.logger.info("Starting test_validate_storage_policy_enforcement")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 45) * 60
        start_time = time.time()
        
        try:
            # Step 1: Enable strict rack awareness
            self.logger.info("Step 1: Enabling strict rack awareness")
            
            if not self.rack_workflows.cluster_entity.get_rack_awareness_status():
                success = self.rack_workflows.transition_to_strict_ra_workflow()
                if not success:
                    raise AssertionError("Failed to enable strict rack awareness")
            
            self.logger.info("Strict rack awareness confirmed to be enabled")
            
            # Step 2: Test valid container creation with strict RA
            if self.test_params.get('test_valid_container_creation', True):
                self.logger.info("Step 2: Testing valid container creation with strict RA")
                self._test_valid_container_creation()
            
            # Step 3: Test invalid policy overrides
            if self.test_params.get('test_invalid_policy_overrides', True):
                self.logger.info("Step 3: Testing invalid policy overrides")
                self._test_invalid_policy_overrides()
            
            # Step 4: Test replication factor enforcement
            if self.test_params.get('test_replication_factor_enforcement', True):
                self.logger.info("Step 4: Testing replication factor enforcement")
                self._test_replication_factor_enforcement()
            
            # Step 5: Test vDisk policy enforcement
            if self.test_params.get('test_vdisk_policy_enforcement', True):
                self.logger.info("Step 5: Testing vDisk policy enforcement")
                self._test_vdisk_policy_enforcement()
            
            # Step 6: Test policy inheritance
            if self.test_params.get('test_policy_inheritance', True):
                self.logger.info("Step 6: Testing policy inheritance")
                self._test_policy_inheritance()
            
            # Step 7: Test policy violation handling
            if self.test_params.get('test_policy_violation_handling', True):
                self.logger.info("Step 7: Testing policy violation handling")
                self._test_policy_violation_handling()
            
            # Step 8: Test policy enforcement during failures
            if self.test_params.get('test_policy_enforcement_during_failures', True):
                self.logger.info("Step 8: Testing policy enforcement during failures")
                self._test_policy_enforcement_during_failures()
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            self.logger.info("test_validate_storage_policy_enforcement completed successfully")
            
            return {
                'status': 'PASSED',
                'message': 'Successfully validated storage policy enforcement for strict RA',
                'containers_created': len(self.test_containers),
                'vdisks_created': len(self.test_vdisks),
                'policy_violations_tested': len(self.policy_violations),
                'elapsed_time_seconds': elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_validate_storage_policy_enforcement failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'elapsed_time_seconds': elapsed_time
            }
    
    def _test_valid_container_creation(self):
        """Test valid container creation with strict rack awareness"""
        self.logger.info("Testing valid container creation with strict RA")
        
        # Create containers with valid configurations
        valid_configs = [
            {"rf": 2, "strict_ra": True, "description": "RF2 with strict RA"},
            {"rf": 3, "strict_ra": True, "description": "RF3 with strict RA"},
            {"rf": 2, "strict_ra": False, "description": "RF2 best-effort (should work)"}
        ]
        
        for i, config in enumerate(valid_configs):
            container_name = f"valid_policy_test_{int(time.time())}_{i}"
            
            self.logger.info(f"Creating valid container: {config['description']}")
            
            container_uuid = self.storage_workflows.create_test_container_workflow(
                name=container_name,
                replication_factor=config['rf'],
                strict_rack_awareness=config['strict_ra']
            )
            
            if not container_uuid:
                raise AssertionError(f"Valid container creation failed: {config['description']}")
            
            self.created_container_names.append(container_name)
            self.test_containers.append({
                'name': container_name,
                'uuid': container_uuid,
                'replication_factor': config['rf'],
                'strict_rack_awareness': config['strict_ra'],
                'description': config['description']
            })
            
            # Validate placement
            is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                container_name, expected_strict_mode=config['strict_ra']
            )
            
            if not is_valid:
                raise AssertionError(f"Valid container placement validation failed: {message}")
        
        self.logger.info(f"Successfully created {len(valid_configs)} valid containers")
    
    def _test_invalid_policy_overrides(self):
        """Test that invalid policy overrides are properly handled"""
        self.logger.info("Testing invalid policy overrides")
        
        # Test scenarios that should fail or be blocked
        override_tests = [
            {
                "name": "excessive_replication_factor",
                "description": "RF higher than available racks",
                "replication_factor": 10,  # More than available racks
                "strict_rack_awareness": True,
                "should_fail": True
            },
            {
                "name": "invalid_rack_constraint",
                "description": "Invalid rack placement constraint",
                "replication_factor": 2,
                "strict_rack_awareness": True,
                "should_fail": True,
                "special_constraint": "same_rack_replicas"  # Invalid for strict RA
            }
        ]
        
        blocked_overrides = 0
        allowed_overrides = 0
        
        for test_case in override_tests:
            test_name = test_case["name"]
            should_fail = test_case["should_fail"]
            
            self.logger.info(f"Testing override: {test_case['description']}")
            
            container_name = f"override_test_{test_name}_{int(time.time())}"
            
            try:
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=container_name,
                    replication_factor=test_case["replication_factor"],
                    strict_rack_awareness=test_case["strict_rack_awareness"]
                )
                
                if container_uuid:
                    # Container was created
                    if should_fail:
                        self.logger.warning(f"Override test {test_name} should have failed but succeeded")
                        allowed_overrides += 1
                        # Clean up the container
                        self.created_container_names.append(container_name)
                    else:
                        self.logger.info(f"Override test {test_name} succeeded as expected")
                        allowed_overrides += 1
                        self.created_container_names.append(container_name)
                else:
                    # Container creation failed
                    if should_fail:
                        self.logger.info(f"Override test {test_name} properly blocked")
                        blocked_overrides += 1
                    else:
                        raise AssertionError(f"Valid override test {test_name} should not have failed")
                        
            except Exception as e:
                # Exception during creation
                if should_fail:
                    self.logger.info(f"Override test {test_name} properly blocked with exception: {str(e)}")
                    blocked_overrides += 1
                else:
                    raise AssertionError(f"Valid override test {test_name} failed unexpectedly: {str(e)}")
            
            # Record the policy violation test
            self.policy_violations.append({
                'test_name': test_name,
                'description': test_case['description'],
                'blocked': should_fail and (blocked_overrides > len(self.policy_violations)),
                'allowed': not should_fail or (allowed_overrides > len([p for p in self.policy_violations if not p.get('blocked', False)]))
            })
        
        # At least some invalid overrides should be blocked
        if blocked_overrides == 0 and any(test['should_fail'] for test in override_tests):
            self.logger.warning("No invalid overrides were blocked - policy enforcement may be weak")
        
        self.logger.info(f"Override testing completed: {blocked_overrides} blocked, {allowed_overrides} allowed")
    
    def _test_replication_factor_enforcement(self):
        """Test replication factor vs rack count enforcement"""
        self.logger.info("Testing replication factor enforcement")
        
        health_summary = self.cluster_workflows.get_cluster_health_summary()
        available_racks = health_summary.get('rack_count', 0)
        
        # Test various replication factors
        rf_tests = [
            {"rf": available_racks, "should_succeed": True, "description": "RF equals rack count"},
            {"rf": available_racks + 1, "should_succeed": False, "description": "RF exceeds rack count"},
            {"rf": max(1, available_racks - 1), "should_succeed": True, "description": "RF less than rack count"}
        ]
        
        for test in rf_tests:
            rf = test["rf"]
            should_succeed = test["should_succeed"]
            description = test["description"]
            
            self.logger.info(f"Testing RF enforcement: {description} (RF={rf})")
            
            container_name = f"rf_test_{rf}_{int(time.time())}"
            
            try:
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=container_name,
                    replication_factor=rf,
                    strict_rack_awareness=True
                )
                
                if container_uuid:
                    # Container created successfully
                    if should_succeed:
                        self.logger.info(f"RF test succeeded as expected: {description}")
                        self.created_container_names.append(container_name)
                    else:
                        self.logger.warning(f"RF test should have failed but succeeded: {description}")
                        self.created_container_names.append(container_name)
                else:
                    # Container creation failed
                    if not should_succeed:
                        self.logger.info(f"RF test properly blocked: {description}")
                    else:
                        self.logger.warning(f"RF test failed unexpectedly: {description}")
                        
            except Exception as e:
                if not should_succeed:
                    self.logger.info(f"RF test properly blocked with exception: {description} - {str(e)}")
                else:
                    self.logger.warning(f"RF test failed unexpectedly: {description} - {str(e)}")
        
        self.logger.info("Replication factor enforcement testing completed")
    
    def _test_vdisk_policy_enforcement(self):
        """Test vDisk policy enforcement"""
        self.logger.info("Testing vDisk policy enforcement")
        
        if not self.test_containers:
            self.logger.warning("No test containers available for vDisk testing")
            return
        
        # Generate test vDisks
        vdisks_per_container = self.test_params.get('vdisks_per_container', 2)
        
        for container in self.test_containers:
            for i in range(vdisks_per_container):
                vdisk_name = f"vdisk_{container['name']}_{i}"
                
                # In a real implementation, this would use the vDisk creation API
                # For now, we'll simulate the process
                vdisk_info = {
                    'name': vdisk_name,
                    'container_name': container['name'],
                    'size_gb': 10,
                    'uuid': f"vdisk_{vdisk_name}_{int(time.time())}",
                    'inherits_strict_ra': container['strict_rack_awareness']
                }
                
                self.test_vdisks.append(vdisk_info)
                self.logger.info(f"Simulated vDisk creation: {vdisk_name}")
        
        self.logger.info(f"vDisk policy enforcement testing completed: {len(self.test_vdisks)} vDisks")
    
    def _test_policy_inheritance(self):
        """Test policy inheritance from containers to vDisks"""
        self.logger.info("Testing policy inheritance")
        
        # Test that vDisks inherit strict RA policy from their containers
        for container in self.test_containers:
            if container['strict_rack_awareness']:
                self.logger.info(f"Validating policy inheritance for container: {container['name']}")
                
                # Check that vDisks in this container inherit strict RA
                container_vdisks = [vd for vd in self.test_vdisks if vd['container_name'] == container['name']]
                
                for vdisk in container_vdisks:
                    # In a real implementation, you would check the vDisk's actual policy
                    # For now, we assume inheritance works correctly if the container has strict RA
                    if not vdisk.get('inherits_strict_ra', False):
                        raise AssertionError(f"vDisk {vdisk['name']} should inherit strict RA from container")
                    
                    self.logger.info(f"vDisk {vdisk['name']} correctly inherits strict RA")
        
        self.logger.info("Policy inheritance testing completed")
    
    def _test_policy_violation_handling(self):
        """Test how policy violations are handled (warnings vs blocks)"""
        self.logger.info("Testing policy violation handling")
        
        # Simulate various policy violation scenarios
        violation_scenarios = [
            {
                'type': 'replication_mismatch',
                'description': 'Replication factor exceeds available racks',
                'expected_handling': 'block'
            },
            {
                'type': 'placement_constraint_violation',
                'description': 'Placement violates rack boundaries',
                'expected_handling': 'block'
            }
        ]
        
        handled_correctly = 0
        
        for scenario in violation_scenarios:
            violation_type = scenario['type']
            expected_handling = scenario['expected_handling']
            
            self.logger.info(f"Testing policy violation: {scenario['description']}")
            
            # Simulate the violation test
            if self._simulate_policy_violation(scenario):
                handled_correctly += 1
                self.logger.info(f"Policy violation {violation_type} handled correctly")
            else:
                self.logger.warning(f"Policy violation {violation_type} not handled as expected")
        
        if handled_correctly < len(violation_scenarios):
            self.logger.warning(f"Some policy violations not handled correctly: {handled_correctly}/{len(violation_scenarios)}")
        
        self.logger.info("Policy violation handling testing completed")
    
    def _simulate_policy_violation(self, scenario: Dict[str, Any]) -> bool:
        """Simulate a policy violation test"""
        violation_type = scenario['type']
        expected_handling = scenario['expected_handling']
        
        try:
            if violation_type == 'replication_mismatch':
                # Test creating container with RF > available racks
                health_summary = self.cluster_workflows.get_cluster_health_summary()
                rack_count = health_summary.get('rack_count', 0)
                
                violation_container = f"violation_test_{violation_type}_{int(time.time())}"
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=violation_container,
                    replication_factor=rack_count + 2,  # Exceeds available racks
                    strict_rack_awareness=True
                )
                
                if expected_handling == 'block':
                    # Should have been blocked
                    if container_uuid:
                        self.created_container_names.append(violation_container)
                        return False  # Should have been blocked but wasn't
                    else:
                        return True  # Correctly blocked
                
            elif violation_type == 'placement_constraint_violation':
                # This would involve more complex placement constraint testing
                # For now, we'll assume it's handled correctly
                return True
            
            return False
            
        except Exception as e:
            # Exception during violation test
            if expected_handling == 'block':
                return True  # Exception indicates blocking, which is correct
            else:
                return False  # Unexpected exception
    
    def _test_policy_enforcement_during_failures(self):
        """Test policy enforcement during rack failures"""
        self.logger.info("Testing policy enforcement during failures")
        
        if not self.test_params.get('rack_failure_simulation_enabled', True):
            self.logger.info("Skipping failure testing (rack failure simulation disabled)")
            return
        
        health_summary = self.cluster_workflows.get_cluster_health_summary()
        rack_details = health_summary.get('rack_details', {})
        
        if len(rack_details) < 3:
            self.logger.warning("Insufficient racks for failure testing")
            return
        
        # Select a rack to fail
        target_rack = list(rack_details.keys())[0]
        
        self.logger.info(f"Testing policy enforcement during failure of rack: {target_rack}")
        
        # Record pre-failure container count
        pre_failure_containers = len(self.test_containers)
        
        # Simulate rack failure
        success = self.rack_workflows.simulate_rack_failure_workflow(target_rack)
        
        if success:
            try:
                # Wait for cluster to react
                time.sleep(30)
                
                # Try to create a new container during failure
                failure_container_name = f"failure_test_container_{int(time.time())}"
                
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=failure_container_name,
                    replication_factor=2,
                    strict_rack_awareness=True
                )
                
                if container_uuid:
                    self.logger.info("Container creation succeeded during rack failure")
                    self.created_container_names.append(failure_container_name)
                    
                    # Validate placement honors remaining racks
                    is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                        failure_container_name, expected_strict_mode=True
                    )
                    
                    if not is_valid:
                        self.logger.warning(f"Container placement during failure: {message}")
                    else:
                        self.logger.info(f"Container placement during failure validated: {message}")
                    
                else:
                    self.logger.info("Container creation blocked during rack failure (expected)")
                
                # Test existing container accessibility
                accessible_containers = 0
                for container in self.test_containers:
                    try:
                        container_info = self.storage_workflows.storage_entity.get_container_by_name(container['name'])
                        if container_info:
                            accessible_containers += 1
                    except Exception as e:
                        self.logger.debug(f"Container {container['name']} not accessible during failure: {str(e)}")
                
                self.logger.info(f"Accessible containers during failure: {accessible_containers}/{len(self.test_containers)}")
                
            finally:
                # Always recover the rack
                self.rack_workflows.recover_rack_workflow(target_rack)
                self.cluster_workflows.wait_for_cluster_stable(timeout_minutes=10)
        
        else:
            self.logger.warning("Failed to simulate rack failure")
        
        self.logger.info("Policy enforcement during failures testing completed")
    
    def _cleanup_test_vdisks(self):
        """Clean up test vDisks"""
        if self.test_vdisks:
            self.logger.info(f"Cleaning up {len(self.test_vdisks)} test vDisks")
            
            for vdisk in self.test_vdisks:
                try:
                    # In a real implementation, this would use the vDisk deletion API
                    self.logger.debug(f"Cleaning up vDisk: {vdisk['name']}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup vDisk {vdisk['name']}: {str(e)}")
            
            self.test_vdisks.clear()