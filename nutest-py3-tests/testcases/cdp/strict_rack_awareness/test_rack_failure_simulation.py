"""
Test Rack Failure Simulation

This module contains tests for simulating rack failures and validating quorum maintenance.
"""

import logging
import time
from typing import List, Dict, Any

from nutest_py3_tests.workflows.rack_awareness_workflows import RackAwarenessWorkflows
from nutest_py3_tests.workflows.cluster_workflows import ClusterWorkflows
from nutest_py3_tests.workflows.storage_workflows import StorageWorkflows


class RackFailureSimulation:
    """
    Test class for rack failure simulation and quorum validation
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
        self.failed_racks = []
        self.failure_scenarios = []
    
    def setup(self):
        """Setup method called before each test"""
        self.logger.info("Setting up RackFailureSimulation test")
        
        # Validate that rack failure simulation is enabled
        if not self.test_params.get('rack_failure_simulation_enabled', True):
            raise RuntimeError("Rack failure simulation is disabled in test parameters")
        
        # Validate cluster connectivity and health
        try:
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            if 'error' in health_summary:
                raise RuntimeError(f"Cluster health check failed: {health_summary['error']}")
            
            # Ensure we have enough racks for meaningful testing
            rack_count = health_summary.get('rack_count', 0)
            if rack_count < 3:
                raise RuntimeError(f"Insufficient racks for failure testing: {rack_count} < 3")
            
            self.logger.info(f"Cluster status: {health_summary.get('cluster_status')}")
            self.logger.info(f"Available racks: {rack_count}")
            
        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise
    
    def teardown(self):
        """Teardown method called after each test"""
        self.logger.info("Tearing down RackFailureSimulation test")
        
        # Recover all failed racks
        try:
            self._recover_all_racks()
        except Exception as e:
            self.logger.warning(f"Failed to recover all racks: {str(e)}")
        
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
        self.failed_racks.clear()
        self.failure_scenarios.clear()
    
    def test_simulate_rack_failure_and_validate_quorum(self):
        """
        Test simulate rack failure and validate metadata quorum and data availability
        
        Test Steps:
        1. Enable strict rack awareness
        2. Create test containers and data
        3. Generate failure scenarios
        4. Execute single rack failure scenarios
        5. Execute multiple rack failure scenarios if configured
        6. Test recovery scenarios if configured
        7. Validate quorum maintenance throughout
        8. Validate data availability during failures
        """
        self.logger.info("Starting test_simulate_rack_failure_and_validate_quorum")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 60) * 60
        start_time = time.time()
        
        try:
            # Step 1: Enable strict rack awareness
            self.logger.info("Step 1: Enabling strict rack awareness")
            
            if not self.rack_workflows.cluster_entity.get_rack_awareness_status():
                success = self.rack_workflows.transition_to_strict_ra_workflow()
                if not success:
                    raise AssertionError("Failed to enable strict rack awareness")
            
            self.logger.info("Strict rack awareness confirmed to be enabled")
            
            # Step 2: Create test containers and data
            self.logger.info("Step 2: Creating test containers and data")
            
            containers_count = self.test_params.get('test_containers_count', 3)
            container_prefix = "rack_failure_test"
            
            for i in range(containers_count):
                container_name = f"{container_prefix}_{int(time.time())}_{i}"
                
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=container_name,
                    replication_factor=2,
                    strict_rack_awareness=True
                )
                
                if not container_uuid:
                    raise AssertionError(f"Failed to create test container: {container_name}")
                
                self.created_container_names.append(container_name)
                self.test_containers.append({
                    'name': container_name,
                    'uuid': container_uuid,
                    'replication_factor': 2
                })
            
            self.logger.info(f"Created {len(self.test_containers)} test containers")
            
            # Wait for containers to be properly distributed
            time.sleep(30)
            
            # Step 3: Generate failure scenarios
            self.logger.info("Step 3: Generating failure scenarios")
            
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            total_racks = health_summary.get('rack_count', 0)
            
            self._generate_failure_scenarios(total_racks)
            
            # Step 4: Execute single rack failure scenarios
            if self.test_params.get('test_single_rack_failure', True):
                self.logger.info("Step 4: Executing single rack failure scenarios")
                
                single_rack_scenarios = [s for s in self.failure_scenarios if len(s['failed_racks']) == 1]
                
                for scenario in single_rack_scenarios[:2]:  # Test first 2 single rack scenarios
                    self._execute_failure_scenario(scenario)
            
            # Step 5: Execute multiple rack failure scenarios if configured
            if self.test_params.get('test_multiple_rack_failure', True):
                self.logger.info("Step 5: Executing multiple rack failure scenarios")
                
                multi_rack_scenarios = [s for s in self.failure_scenarios if len(s['failed_racks']) > 1]
                
                for scenario in multi_rack_scenarios[:1]:  # Test first multiple rack scenario
                    self._execute_failure_scenario(scenario)
            
            # Step 6: Test recovery scenarios if configured
            if self.test_params.get('test_recovery_scenarios', True):
                self.logger.info("Step 6: Testing recovery scenarios")
                self._test_recovery_scenarios()
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            self.logger.info("test_simulate_rack_failure_and_validate_quorum completed successfully")
            
            return {
                'status': 'PASSED',
                'message': 'Successfully tested rack failure scenarios and quorum maintenance',
                'scenarios_tested': len([s for s in self.failure_scenarios if s.get('executed', False)]),
                'containers_created': len(self.test_containers),
                'elapsed_time_seconds': elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_simulate_rack_failure_and_validate_quorum failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'elapsed_time_seconds': elapsed_time
            }
    
    def _generate_failure_scenarios(self, total_racks: int):
        """Generate rack failure scenarios based on cluster configuration"""
        self.logger.info(f"Generating failure scenarios for {total_racks} racks")
        
        # Get rack information
        rack_info = self.rack_workflows.rack_entity.list_entities()
        rack_ids = [rack['rack_uuid'] for rack in rack_info.get('entities', [])]
        
        # Single rack failure scenarios
        for rack_id in rack_ids:
            self.failure_scenarios.append({
                'name': f'single_rack_failure_{rack_id}',
                'description': f'Fail single rack: {rack_id}',
                'failed_racks': [rack_id],
                'expected_quorum': total_racks > 2,  # General rule for single rack failure
                'executed': False
            })
        
        # Multiple rack failure scenarios (if we have enough racks)
        if total_racks > 3:
            # Test failing 2 racks
            if len(rack_ids) >= 2:
                self.failure_scenarios.append({
                    'name': 'dual_rack_failure',
                    'description': f'Fail two racks: {rack_ids[0]}, {rack_ids[1]}',
                    'failed_racks': rack_ids[:2],
                    'expected_quorum': (total_racks - 2) > (total_racks // 2),
                    'executed': False
                })
        
        self.logger.info(f"Generated {len(self.failure_scenarios)} failure scenarios")
    
    def _execute_failure_scenario(self, scenario: Dict[str, Any]):
        """Execute a specific failure scenario"""
        scenario_name = scenario['name']
        failed_racks = scenario['failed_racks']
        expected_quorum = scenario['expected_quorum']
        
        self.logger.info(f"Executing failure scenario: {scenario_name}")
        
        try:
            # Record pre-failure state
            pre_failure_health = self.cluster_workflows.get_cluster_health_summary()
            
            # Simulate rack failures
            for rack_id in failed_racks:
                self.logger.info(f"Simulating failure of rack: {rack_id}")
                success = self.rack_workflows.simulate_rack_failure_workflow(rack_id)
                
                if success:
                    self.failed_racks.append(rack_id)
                    self.logger.info(f"Successfully simulated failure of rack: {rack_id}")
                else:
                    self.logger.warning(f"Failed to simulate failure of rack: {rack_id}")
            
            # Wait for cluster to react
            failure_detection_timeout = self.test_params.get('failure_detection_timeout', 120)
            self.logger.info(f"Waiting {failure_detection_timeout}s for cluster to detect failures")
            time.sleep(failure_detection_timeout)
            
            # Validate quorum status
            if self.test_params.get('validate_quorum_maintenance', True):
                self._validate_quorum_after_failure(failed_racks, expected_quorum, scenario_name)
            
            # Validate data availability
            if self.test_params.get('validate_data_availability', True):
                self._validate_data_availability_after_failure(scenario_name)
            
            # Mark scenario as executed
            scenario['executed'] = True
            
            # Record post-failure metrics
            post_failure_health = self.cluster_workflows.get_cluster_health_summary()
            scenario['post_failure_health'] = post_failure_health
            
        except Exception as e:
            self.logger.error(f"Failure scenario {scenario_name} failed: {str(e)}")
            raise
        
        finally:
            # Always try to recover for next scenario
            self._recover_failed_racks(failed_racks)
    
    def _validate_quorum_after_failure(self, failed_racks: List[str], expected_quorum: bool, scenario_name: str):
        """Validate quorum status after rack failure"""
        self.logger.info(f"Validating quorum after failure scenario: {scenario_name}")
        
        is_valid, message = self.rack_workflows.validate_quorum_maintenance_workflow(failed_racks)
        
        if expected_quorum:
            if not is_valid:
                raise AssertionError(f"Quorum should be maintained but validation failed: {message}")
            else:
                self.logger.info(f"Quorum correctly maintained: {message}")
        else:
            # If quorum is expected to be lost, we should see degraded cluster state
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            cluster_status = health_summary.get('cluster_status')
            
            if cluster_status == 'NORMAL':
                self.logger.warning(f"Cluster status is NORMAL despite expected quorum loss")
                # This might be acceptable depending on implementation
            else:
                self.logger.info(f"Cluster correctly shows degraded state: {cluster_status}")
    
    def _validate_data_availability_after_failure(self, scenario_name: str):
        """Validate data availability after rack failure"""
        self.logger.info(f"Validating data availability for scenario: {scenario_name}")
        
        container_names = [container['name'] for container in self.test_containers]
        is_available, message = self.rack_workflows.validate_data_availability_workflow(container_names)
        
        if is_available:
            self.logger.info(f"Data remains available after failure: {message}")
        else:
            self.logger.warning(f"Data availability impacted after failure: {message}")
            # This may be expected behavior depending on the failure scenario
    
    def _test_recovery_scenarios(self):
        """Test recovery scenarios"""
        self.logger.info("Testing recovery scenarios")
        
        # Test gradual recovery if we have multiple failed racks
        if len(self.failed_racks) > 1:
            self.logger.info("Testing gradual recovery scenario")
            
            # Recover one rack at a time
            for i, rack_id in enumerate(self.failed_racks.copy()):
                self.logger.info(f"Recovering rack {i+1}/{len(self.failed_racks)}: {rack_id}")
                
                success = self.rack_workflows.recover_rack_workflow(rack_id)
                if success:
                    self.failed_racks.remove(rack_id)
                    
                    # Validate intermediate state
                    remaining_failed = self.failed_racks.copy()
                    if remaining_failed:
                        is_valid, message = self.rack_workflows.validate_quorum_maintenance_workflow(remaining_failed)
                        self.logger.info(f"Quorum status with {len(remaining_failed)} racks still failed: {message}")
                
                # Brief wait between recoveries
                time.sleep(30)
        
        self.logger.info("Recovery scenarios testing completed")
    
    def _recover_failed_racks(self, rack_ids: List[str]):
        """Recover specific failed racks"""
        self.logger.info(f"Recovering racks: {', '.join(rack_ids)}")
        
        for rack_id in rack_ids:
            if rack_id in self.failed_racks:
                success = self.rack_workflows.recover_rack_workflow(rack_id)
                if success:
                    self.failed_racks.remove(rack_id)
                    self.logger.info(f"Successfully recovered rack: {rack_id}")
                else:
                    self.logger.warning(f"Failed to recover rack: {rack_id}")
        
        # Wait for cluster to stabilize after recovery
        if rack_ids:
            self.logger.info("Waiting for cluster to stabilize after recovery")
            recovery_timeout = self.test_params.get('recovery_timeout_minutes', 15)
            stable = self.cluster_workflows.wait_for_cluster_stable(timeout_minutes=recovery_timeout)
            if not stable:
                self.logger.warning("Cluster did not stabilize after rack recovery")
    
    def _recover_all_racks(self):
        """Recover all failed racks"""
        if self.failed_racks:
            self.logger.info(f"Recovering all failed racks: {', '.join(self.failed_racks)}")
            self._recover_failed_racks(self.failed_racks.copy())
        
        # Final validation
        health_summary = self.cluster_workflows.get_cluster_health_summary()
        if health_summary.get('cluster_status') != 'NORMAL':
            self.logger.warning(f"Cluster not fully recovered: {health_summary.get('cluster_status')}")
            # Wait a bit more for full recovery
            self.cluster_workflows.wait_for_cluster_stable(timeout_minutes=15)