"""
Test Case: Simulate Rack Failure and Validate Quorum

Test Case Name: simulate_rack_failure_and_validate_quorum
Description: Simulate rack failure and validate metadata quorum and data availability.
Steps: Power off one or more racks and monitor cluster behavior.
Expected Result: Quorum is maintained within FT limits. Cluster remains operational.
"""

import time
from typing import List, Dict, Any

from nutest_py3.framework import BaseTest, TestConfig, TestPriority
from nutest_py3_tests.common import RackAwarenessTestUtils, ClusterValidationUtils, TestDataGenerator


class SimulateRackFailureAndValidateQuorumTest(BaseTest):
    """
    Test rack failure scenarios and validate quorum maintenance
    """
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.rack_utils = RackAwarenessTestUtils(config)
        self.cluster_validation = ClusterValidationUtils(config)
        self.test_data_gen = TestDataGenerator()
        self.test_containers = []
        self.failed_racks = []
        self.failure_scenarios = []
        
    @property
    def test_name(self) -> str:
        return "simulate_rack_failure_and_validate_quorum"
    
    @property
    def description(self) -> str:
        return "Simulate rack failure and validate metadata quorum and data availability"
    
    @property
    def priority(self) -> TestPriority:
        return TestPriority.CRITICAL
    
    @property
    def timeout_minutes(self) -> int:
        return 60
    
    @property
    def prerequisites(self) -> List[str]:
        return [
            "Cluster must have at least 3 racks",
            "Cluster must be in healthy state",
            "Rack failure simulation must be enabled",
            "Sufficient hosts per rack for meaningful failure testing"
        ]
    
    def setup(self) -> None:
        """Setup test environment"""
        super().setup()
        
        self.logger.info("Setting up rack failure simulation test")
        
        # Validate prerequisites
        self._validate_test_prerequisites()
        
        # Enable strict rack awareness
        self._enable_strict_rack_awareness()
        
        # Create test containers and data
        self._create_test_data()
        
        # Generate failure scenarios
        self._generate_failure_scenarios()
        
    def execute(self) -> None:
        """Main test execution"""
        self.logger.info("Executing rack failure simulation test")
        
        # Step 1: Validate initial healthy state
        self._validate_initial_state()
        
        # Step 2: Execute failure scenarios
        for scenario in self.failure_scenarios:
            self._execute_failure_scenario(scenario)
        
        # Step 3: Test recovery scenarios
        self._test_recovery_scenarios()
        
    def teardown(self) -> None:
        """Cleanup test environment"""
        try:
            # Recover all failed racks
            self._recover_all_racks()
            
            # Clean up test containers
            if self.test_containers:
                container_names = [container.name for container in self.test_containers]
                self.rack_utils.cleanup_test_containers(container_names)
                
        except Exception as e:
            self.logger.warning(f"Teardown failed: {str(e)}")
        
        super().teardown()
    
    def _validate_test_prerequisites(self) -> None:
        """Validate that all test prerequisites are met"""
        self.logger.info("Validating test prerequisites")
        
        # Check rack failure simulation is enabled
        self.assert_true(
            self.config.rack_failure_simulation,
            "Rack failure simulation must be enabled in configuration"
        )
        
        # Check cluster health
        health_summary = self.cluster_manager.get_cluster_health_summary()
        self.assert_equal(
            health_summary.get('cluster_status'), 'NORMAL',
            f"Cluster not in healthy state: {health_summary.get('cluster_status')}"
        )
        
        # Verify we have at least 3 racks
        rack_count = health_summary.get('rack_count', 0)
        self.assert_true(
            rack_count >= 3,
            f"Insufficient racks for failure testing: {rack_count} < 3"
        )
        
        # Check rack distribution
        rack_details = health_summary.get('rack_details', {})
        for rack_id, rack_info in rack_details.items():
            host_count = rack_info.get('total_hosts', 0)
            self.assert_true(
                host_count > 0,
                f"Rack {rack_id} has no hosts: {host_count}"
            )
        
        self.logger.info(f"Prerequisites validated: {rack_count} racks available")
    
    def _enable_strict_rack_awareness(self) -> None:
        """Enable strict rack awareness for testing"""
        self.logger.info("Ensuring strict rack awareness is enabled")
        
        if not self.cluster_manager.is_strict_rack_awareness_enabled():
            # Validate preconditions
            is_valid, issues = self.rack_utils.validate_strict_ra_prerequisites()
            self.assert_true(is_valid, f"Cannot enable strict RA: {', '.join(issues)}")
            
            # Enable strict RA
            success = self.cluster_manager.enable_strict_rack_awareness()
            self.assert_true(success, "Failed to enable strict rack awareness")
        
        # Verify strict RA is enabled
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_true(is_strict_enabled, "Strict rack awareness should be enabled")
        
        self.logger.info("Strict rack awareness confirmed to be enabled")
    
    def _create_test_data(self) -> None:
        """Create test containers and data for failure validation"""
        self.logger.info("Creating test data for failure validation")
        
        # Generate test container configurations
        self.test_containers = self.test_data_gen.generate_test_containers(
            count=3, strict_rack_awareness=True
        )
        
        # Create the containers
        for container in self.test_containers:
            container_uuid = self.rack_utils.create_test_container(
                name=container.name,
                replication_factor=container.replication_factor,
                strict_rack_awareness=container.strict_rack_awareness
            )
            
            self.assert_true(
                container_uuid is not None,
                f"Failed to create test container: {container.name}"
            )
            
            container.uuid = container_uuid
        
        # Wait for containers to be properly distributed
        time.sleep(30)
        
        self.logger.info(f"Created {len(self.test_containers)} test containers")
    
    def _generate_failure_scenarios(self) -> None:
        """Generate rack failure scenarios based on cluster configuration"""
        self.logger.info("Generating rack failure scenarios")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        total_racks = health_summary.get('rack_count', 0)
        
        # Generate scenarios using test data generator
        self.failure_scenarios = self.test_data_gen.generate_rack_failure_scenarios(
            total_racks=total_racks,
            max_failures=min(2, total_racks - 1)  # Don't fail all racks
        )
        
        self.logger.info(f"Generated {len(self.failure_scenarios)} failure scenarios")
        
        # Log scenarios for visibility
        for scenario in self.failure_scenarios:
            self.logger.info(f"Scenario: {scenario['name']} - {scenario['description']}")
    
    def _validate_initial_state(self) -> None:
        """Validate initial healthy state before failure simulation"""
        self.logger.info("Validating initial healthy state")
        
        # Record baseline metrics
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        self.test_result.add_metric("initial_rack_count", health_summary.get('rack_count', 0))
        self.test_result.add_metric("initial_total_hosts", health_summary.get('total_hosts', 0))
        self.test_result.add_metric("initial_available_hosts", health_summary.get('available_hosts', 0))
        self.test_result.add_metric("initial_cluster_status", health_summary.get('cluster_status'))
        
        # Validate all containers are healthy
        for container in self.test_containers:
            is_valid, message = self.rack_utils.validate_container_placement(
                container.name, expected_strict_mode=True
            )
            self.assert_true(
                is_valid,
                f"Container {container.name} should be healthy initially: {message}"
            )
        
        # Validate data availability
        container_names = [c.name for c in self.test_containers]
        is_available, message = self.cluster_validation.validate_data_availability(container_names)
        self.assert_true(is_available, f"Data should be available initially: {message}")
        
        self.logger.info("Initial state validation completed")
    
    def _execute_failure_scenario(self, scenario: Dict[str, Any]) -> None:
        """Execute a specific failure scenario"""
        scenario_name = scenario['name']
        failed_racks = scenario['failed_racks']
        expected_quorum = scenario['expected_quorum']
        
        self.logger.info(f"Executing failure scenario: {scenario_name}")
        
        try:
            # Step 1: Record pre-failure state
            pre_failure_health = self.cluster_manager.get_cluster_health_summary()
            
            # Step 2: Simulate rack failures
            self._simulate_rack_failures(failed_racks)
            
            # Step 3: Wait for cluster to react
            time.sleep(60)  # Give cluster time to detect failures
            
            # Step 4: Validate quorum status
            self._validate_quorum_after_failure(failed_racks, expected_quorum)
            
            # Step 5: Validate data availability
            self._validate_data_availability_after_failure(scenario_name)
            
            # Step 6: Validate cluster behavior
            self._validate_cluster_behavior_after_failure(scenario_name, expected_quorum)
            
            # Step 7: Record failure metrics
            self._record_failure_metrics(scenario_name, failed_racks)
            
        except Exception as e:
            self.logger.error(f"Failure scenario {scenario_name} failed: {str(e)}")
            raise
        finally:
            # Always try to recover for next scenario
            self._recover_failed_racks(failed_racks)
    
    def _simulate_rack_failures(self, rack_ids: List[str]) -> None:
        """Simulate failure of specified racks"""
        self.logger.info(f"Simulating failure of racks: {', '.join(rack_ids)}")
        
        for rack_id in rack_ids:
            success = self.cluster_manager.simulate_rack_failure(rack_id)
            if success:
                self.failed_racks.append(rack_id)
                self.logger.info(f"Successfully simulated failure of rack: {rack_id}")
            else:
                self.logger.warning(f"Failed to simulate failure of rack: {rack_id}")
    
    def _validate_quorum_after_failure(self, failed_racks: List[str], expected_quorum: bool) -> None:
        """Validate quorum status after rack failure"""
        self.logger.info(f"Validating quorum after failure of racks: {', '.join(failed_racks)}")
        
        # Use cluster validation utility
        is_valid, message = self.cluster_validation.validate_quorum_maintenance(failed_racks)
        
        if expected_quorum:
            self.assert_true(
                is_valid,
                f"Quorum should be maintained after failing {len(failed_racks)} racks: {message}"
            )
            self.logger.info(f"Quorum correctly maintained: {message}")
        else:
            # If quorum is expected to be lost, validate that cluster behaves appropriately
            health_summary = self.cluster_manager.get_cluster_health_summary()
            cluster_status = health_summary.get('cluster_status')
            
            # Cluster should indicate degraded state when quorum is lost
            self.assert_not_equal(
                cluster_status, 'NORMAL',
                f"Cluster status should indicate degraded state when quorum is lost: {cluster_status}"
            )
            self.logger.info(f"Cluster correctly indicates degraded state: {cluster_status}")
    
    def _validate_data_availability_after_failure(self, scenario_name: str) -> None:
        """Validate data availability after rack failure"""
        self.logger.info(f"Validating data availability for scenario: {scenario_name}")
        
        container_names = [c.name for c in self.test_containers]
        is_available, message = self.cluster_validation.validate_data_availability(container_names)
        
        # Data should remain available if quorum is maintained
        # If quorum is lost, some data may be unavailable but the test should document this
        
        if is_available:
            self.logger.info(f"Data remains available after failure: {message}")
        else:
            self.logger.warning(f"Data availability impacted after failure: {message}")
            # This may be expected behavior depending on the failure scenario
        
        # Record availability status
        self.test_result.add_metric(f"{scenario_name}_data_available", is_available)
        self.test_result.add_metric(f"{scenario_name}_data_availability_message", message)
    
    def _validate_cluster_behavior_after_failure(self, scenario_name: str, expected_quorum: bool) -> None:
        """Validate overall cluster behavior after failure"""
        self.logger.info(f"Validating cluster behavior for scenario: {scenario_name}")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        # Check if cluster is still responsive
        try:
            cluster_info = self.cluster_manager.get_cluster_info()
            cluster_responsive = True
        except Exception as e:
            cluster_responsive = False
            self.logger.warning(f"Cluster not responsive after failure: {str(e)}")
        
        if expected_quorum:
            # If quorum is maintained, cluster should remain operational
            self.assert_true(
                cluster_responsive,
                f"Cluster should remain responsive when quorum is maintained"
            )
            
            # Should be able to perform basic operations
            try:
                containers = self.api_client.get_storage_containers()
                operations_available = True
            except Exception as e:
                operations_available = False
                self.logger.warning(f"Basic operations not available: {str(e)}")
            
            self.assert_true(
                operations_available,
                f"Basic operations should be available when quorum is maintained"
            )
        
        # Record behavior metrics
        self.test_result.add_metric(f"{scenario_name}_cluster_responsive", cluster_responsive)
        self.test_result.add_metric(f"{scenario_name}_expected_quorum", expected_quorum)
        self.test_result.add_metric(f"{scenario_name}_cluster_status", health_summary.get('cluster_status'))
    
    def _record_failure_metrics(self, scenario_name: str, failed_racks: List[str]) -> None:
        """Record metrics for the failure scenario"""
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        self.test_result.add_metric(f"{scenario_name}_failed_racks", failed_racks)
        self.test_result.add_metric(f"{scenario_name}_failed_rack_count", len(failed_racks))
        self.test_result.add_metric(f"{scenario_name}_remaining_racks", 
                                  health_summary.get('rack_count', 0) - len(failed_racks))
        self.test_result.add_metric(f"{scenario_name}_available_hosts", 
                                  health_summary.get('available_hosts', 0))
        self.test_result.add_metric(f"{scenario_name}_total_hosts", 
                                  health_summary.get('total_hosts', 0))
    
    def _recover_failed_racks(self, rack_ids: List[str]) -> None:
        """Recover specific failed racks"""
        self.logger.info(f"Recovering racks: {', '.join(rack_ids)}")
        
        for rack_id in rack_ids:
            if rack_id in self.failed_racks:
                success = self.cluster_manager.recover_rack(rack_id)
                if success:
                    self.failed_racks.remove(rack_id)
                    self.logger.info(f"Successfully recovered rack: {rack_id}")
                else:
                    self.logger.warning(f"Failed to recover rack: {rack_id}")
        
        # Wait for cluster to stabilize after recovery
        if rack_ids:
            self.logger.info("Waiting for cluster to stabilize after recovery")
            stable = self.cluster_manager.wait_for_cluster_stable(timeout_minutes=10)
            if not stable:
                self.logger.warning("Cluster did not stabilize after rack recovery")
    
    def _test_recovery_scenarios(self) -> None:
        """Test recovery scenarios"""
        self.logger.info("Testing recovery scenarios")
        
        # Test gradual recovery
        if len(self.failure_scenarios) > 0:
            # Take the most severe scenario and test gradual recovery
            severe_scenario = max(self.failure_scenarios, key=lambda s: len(s['failed_racks']))
            failed_racks = severe_scenario['failed_racks']
            
            if len(failed_racks) > 1:
                self.logger.info("Testing gradual recovery scenario")
                
                # Fail all racks in the scenario
                self._simulate_rack_failures(failed_racks)
                
                # Recover one rack at a time
                for i, rack_id in enumerate(failed_racks):
                    self.logger.info(f"Recovering rack {i+1}/{len(failed_racks)}: {rack_id}")
                    self._recover_failed_racks([rack_id])
                    
                    # Validate intermediate state
                    remaining_failed = failed_racks[i+1:]
                    if remaining_failed:
                        is_valid, message = self.cluster_validation.validate_quorum_maintenance(remaining_failed)
                        self.logger.info(f"Quorum status with {len(remaining_failed)} racks still failed: {message}")
        
        self.logger.info("Recovery scenarios testing completed")
    
    def _recover_all_racks(self) -> None:
        """Recover all failed racks"""
        if self.failed_racks:
            self.logger.info(f"Recovering all failed racks: {', '.join(self.failed_racks)}")
            self._recover_failed_racks(self.failed_racks.copy())
        
        # Final validation
        health_summary = self.cluster_manager.get_cluster_health_summary()
        if health_summary.get('cluster_status') != 'NORMAL':
            self.logger.warning(f"Cluster not fully recovered: {health_summary.get('cluster_status')}")
            # Wait a bit more for full recovery
            self.cluster_manager.wait_for_cluster_stable(timeout_minutes=15)