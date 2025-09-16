"""
Test Case: Transition from Strict Rack Awareness to Best-Effort

Test Case Name: transition_strict_ra_to_best_effort
Description: Disable strict RA and revert to best-effort placement.
Steps: Disable strict RA via UI/API.
Expected Result: RPPs revert to best-effort and containers reflect updated policy.
"""

import time
from typing import List

from nutest_py3.framework import BaseTest, TestConfig, TestPriority
from nutest_py3_tests.common import RackAwarenessTestUtils, ClusterValidationUtils, TestDataGenerator


class TransitionStrictRATobestEffortTest(BaseTest):
    """
    Test transitioning from strict rack awareness to best-effort mode
    """
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.rack_utils = RackAwarenessTestUtils(config)
        self.cluster_validation = ClusterValidationUtils(config)
        self.test_data_gen = TestDataGenerator()
        self.test_containers = []
        
    @property
    def test_name(self) -> str:
        return "transition_strict_ra_to_best_effort"
    
    @property
    def description(self) -> str:
        return "Disable strict RA and revert to best-effort placement"
    
    @property
    def priority(self) -> TestPriority:
        return TestPriority.HIGH
    
    @property
    def timeout_minutes(self) -> int:
        return 30
    
    @property
    def prerequisites(self) -> List[str]:
        return [
            "Cluster must be in healthy state",
            "Strict rack awareness must be enabled initially",
            "Existing containers with strict placement"
        ]
    
    def setup(self) -> None:
        """Setup test environment"""
        super().setup()
        
        self.logger.info("Setting up transition strict RA to best-effort test")
        
        # Validate prerequisites
        self._validate_test_prerequisites()
        
        # Ensure we start in strict mode
        self._ensure_strict_mode()
        
        # Create test containers for validation
        self._create_test_containers()
        
    def execute(self) -> None:
        """Main test execution"""
        self.logger.info("Executing transition strict RA to best-effort test")
        
        # Step 1: Validate initial state (strict mode)
        self._validate_initial_state()
        
        # Step 2: Disable strict rack awareness
        self._disable_strict_rack_awareness()
        
        # Step 3: Validate transition completed successfully
        self._validate_transition_success()
        
        # Step 4: Validate RPPs are reverted to best-effort
        self._validate_rpp_reversion()
        
        # Step 5: Validate container behavior with best-effort mode
        self._validate_container_behavior()
        
        # Step 6: Test new container creation in best-effort mode
        self._test_new_container_creation()
        
    def teardown(self) -> None:
        """Cleanup test environment"""
        try:
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
        
        # Check cluster health
        health_summary = self.cluster_manager.get_cluster_health_summary()
        self.assert_equal(
            health_summary.get('cluster_status'), 'NORMAL',
            f"Cluster not in healthy state: {health_summary.get('cluster_status')}"
        )
        
        self.logger.info("Prerequisites validated")
    
    def _ensure_strict_mode(self) -> None:
        """Ensure cluster starts in strict rack awareness mode"""
        self.logger.info("Ensuring cluster is in strict rack awareness mode")
        
        if not self.cluster_manager.is_strict_rack_awareness_enabled():
            self.logger.info("Enabling strict rack awareness to start in strict mode")
            
            # Validate we can enable strict RA
            is_valid, issues = self.rack_utils.validate_strict_ra_prerequisites()
            self.assert_true(is_valid, f"Cannot enable strict RA: {', '.join(issues)}")
            
            success = self.cluster_manager.enable_strict_rack_awareness()
            self.assert_true(success, "Failed to enable strict rack awareness")
        
        # Verify strict mode
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_true(is_strict_enabled, "Cluster should be in strict rack awareness mode")
        
        self.logger.info("Cluster confirmed to be in strict rack awareness mode")
    
    def _create_test_containers(self) -> None:
        """Create test containers with strict rack awareness"""
        self.logger.info("Creating test containers with strict RA")
        
        # Generate test container configurations with strict RA
        self.test_containers = self.test_data_gen.generate_test_containers(
            count=2, strict_rack_awareness=True
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
        
        self.logger.info(f"Created {len(self.test_containers)} test containers with strict RA")
    
    def _validate_initial_state(self) -> None:
        """Validate initial state is strict rack awareness mode"""
        self.logger.info("Validating initial state (strict RA mode)")
        
        # Confirm strict RA is enabled
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_true(is_strict_enabled, "Strict rack awareness should be enabled initially")
        
        # Validate RPPs are in strict mode
        rpp_valid = self.rack_utils.validate_rpp_updates(expected_strict_mode=True)
        self.assert_true(rpp_valid, "RPPs should be in strict mode initially")
        
        # Validate existing containers follow strict placement
        for container in self.test_containers:
            is_valid, message = self.rack_utils.validate_container_placement(
                container.name, expected_strict_mode=True
            )
            self.assert_true(
                is_valid,
                f"Container {container.name} should follow strict placement: {message}"
            )
        
        self.logger.info("Initial state validation completed")
    
    def _disable_strict_rack_awareness(self) -> None:
        """Disable strict rack awareness"""
        self.logger.info("Disabling strict rack awareness")
        
        # Record start time for performance measurement
        start_time = time.time()
        
        # Disable strict RA
        success = self.cluster_manager.disable_strict_rack_awareness()
        self.assert_true(success, "Failed to disable strict rack awareness")
        
        # Record transition time
        transition_time = time.time() - start_time
        self.test_result.add_metric("strict_ra_disable_time_seconds", transition_time)
        
        self.logger.info(f"Strict rack awareness disabled in {transition_time:.2f} seconds")
    
    def _validate_transition_success(self) -> None:
        """Validate that transition to best-effort was successful"""
        self.logger.info("Validating transition success")
        
        # Verify strict RA is now disabled
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_false(is_strict_enabled, "Strict rack awareness should be disabled after transition")
        
        # Wait for cluster to stabilize
        stable = self.cluster_manager.wait_for_cluster_stable(timeout_minutes=10)
        self.assert_true(stable, "Cluster should stabilize after disabling strict RA")
        
        # Validate cluster health after transition
        health_summary = self.cluster_manager.get_cluster_health_summary()
        cluster_status = health_summary.get('cluster_status')
        self.assert_equal(cluster_status, 'NORMAL', f"Cluster should remain healthy: {cluster_status}")
        
        self.logger.info("Transition success validation completed")
    
    def _validate_rpp_reversion(self) -> None:
        """Validate that RPPs are reverted to best-effort versions"""
        self.logger.info("Validating RPP reversion to best-effort")
        
        # Wait for RPPs to be updated
        rpp_updated = self.rack_utils.wait_for_rpp_update(
            expected_strict_mode=False, timeout_seconds=300
        )
        self.assert_true(rpp_updated, "RPPs should be reverted to best-effort mode")
        
        # Validate RPPs are in best-effort mode
        rpp_valid = self.rack_utils.validate_rpp_updates(expected_strict_mode=False)
        self.assert_true(rpp_valid, "RPPs should be in best-effort mode after transition")
        
        self.logger.info("RPP reversion validation completed")
    
    def _validate_container_behavior(self) -> None:
        """Validate existing container behavior after transition"""
        self.logger.info("Validating existing container behavior after transition")
        
        # Note: Existing containers may retain their strict placement until rebalanced
        # but they should be accessible and functional
        
        for container in self.test_containers:
            # Validate container is still accessible and healthy
            containers = self.api_client.get_storage_containers()
            container_found = False
            
            for api_container in containers.get('entities', []):
                if api_container.get('name') == container.name:
                    container_found = True
                    container_status = api_container.get('status', 'UNKNOWN')
                    
                    self.assert_in(
                        container_status, ['NORMAL', 'ONLINE'],
                        f"Container {container.name} should be healthy: {container_status}"
                    )
                    break
            
            self.assert_true(
                container_found,
                f"Container {container.name} should still exist after transition"
            )
        
        self.logger.info("Container behavior validation completed")
    
    def _test_new_container_creation(self) -> None:
        """Test creating new containers in best-effort mode"""
        self.logger.info("Testing new container creation in best-effort mode")
        
        # Create a new container without strict RA
        new_container = self.test_data_gen.generate_test_containers(count=1, strict_rack_awareness=False)[0]
        
        container_uuid = self.rack_utils.create_test_container(
            name=new_container.name,
            replication_factor=new_container.replication_factor,
            strict_rack_awareness=False
        )
        
        self.assert_true(
            container_uuid is not None,
            f"Failed to create new container in best-effort mode: {new_container.name}"
        )
        
        # Add to cleanup list
        self.test_containers.append(new_container)
        new_container.uuid = container_uuid
        
        # Validate new container follows best-effort placement
        is_valid, message = self.rack_utils.validate_container_placement(
            new_container.name, expected_strict_mode=False
        )
        
        self.assert_true(
            is_valid,
            f"New container {new_container.name} should follow best-effort placement: {message}"
        )
        
        # Test creating container with explicit strict RA request (should be allowed but may not be enforced)
        strict_container = self.test_data_gen.generate_test_containers(count=1, strict_rack_awareness=True)[0]
        
        container_uuid = self.rack_utils.create_test_container(
            name=strict_container.name,
            replication_factor=strict_container.replication_factor,
            strict_rack_awareness=True
        )
        
        # This should succeed (backward compatibility)
        self.assert_true(
            container_uuid is not None,
            f"Container creation with strict RA request should succeed: {strict_container.name}"
        )
        
        # Add to cleanup list
        self.test_containers.append(strict_container)
        strict_container.uuid = container_uuid
        
        self.logger.info("New container creation testing completed")