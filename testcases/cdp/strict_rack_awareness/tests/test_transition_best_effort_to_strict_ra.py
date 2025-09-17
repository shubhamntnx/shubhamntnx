"""
Test Case: Transition from Best-Effort to Strict Rack Awareness

Test Case Name: transition_best_effort_to_strict_ra
Description: Transition from best-effort to strict RA with all preconditions met.
Steps: Ensure 3+ racks, rack config, rack-aware data, CFT OK. Enable strict RA via UI/API.
Expected Result: Strict RA is enabled and RPPs updated to strict versions.
"""

import time
from typing import List

from nutest_py3.framework import BaseTest, TestConfig, TestPriority
from nutest_py3_tests.common import RackAwarenessTestUtils, ClusterValidationUtils, TestDataGenerator


class TransitionBestEffortToStrictRATest(BaseTest):
    """
    Test transitioning from best-effort to strict rack awareness
    """
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.rack_utils = RackAwarenessTestUtils(config)
        self.cluster_validation = ClusterValidationUtils(config)
        self.test_data_gen = TestDataGenerator()
        self.test_containers = []
        
    @property
    def test_name(self) -> str:
        return "transition_best_effort_to_strict_ra"
    
    @property
    def description(self) -> str:
        return "Transition from best-effort to strict RA with all preconditions met"
    
    @property
    def priority(self) -> TestPriority:
        return TestPriority.HIGH
    
    @property
    def timeout_minutes(self) -> int:
        return 45
    
    @property
    def prerequisites(self) -> List[str]:
        return [
            "Cluster must have at least 3 racks",
            "Cluster must be in healthy state",
            "Rack configuration must be properly set up",
            "Sufficient storage capacity across racks"
        ]
    
    def setup(self) -> None:
        """Setup test environment"""
        super().setup()
        
        self.logger.info("Setting up transition best-effort to strict RA test")
        
        # Validate prerequisites
        self._validate_test_prerequisites()
        
        # Ensure we start in best-effort mode
        self._ensure_best_effort_mode()
        
        # Create test containers for validation
        self._create_test_containers()
        
    def execute(self) -> None:
        """Main test execution"""
        self.logger.info("Executing transition best-effort to strict RA test")
        
        # Step 1: Validate initial state (best-effort mode)
        self._validate_initial_state()
        
        # Step 2: Validate preconditions for strict RA
        self._validate_strict_ra_preconditions()
        
        # Step 3: Enable strict rack awareness
        self._enable_strict_rack_awareness()
        
        # Step 4: Validate transition completed successfully
        self._validate_transition_success()
        
        # Step 5: Validate RPPs are updated
        self._validate_rpp_updates()
        
        # Step 6: Validate container behavior with strict RA
        self._validate_container_behavior()
        
    def teardown(self) -> None:
        """Cleanup test environment"""
        try:
            # Clean up test containers
            if self.test_containers:
                container_names = [container.name for container in self.test_containers]
                self.rack_utils.cleanup_test_containers(container_names)
            
            # Optionally revert to best-effort mode for other tests
            if self.config.cleanup_on_failure:
                self.cluster_manager.disable_strict_rack_awareness()
                
        except Exception as e:
            self.logger.warning(f"Teardown failed: {str(e)}")
        
        super().teardown()
    
    def _validate_test_prerequisites(self) -> None:
        """Validate that all test prerequisites are met"""
        self.logger.info("Validating test prerequisites")
        
        # Check rack count
        is_valid, message = self.cluster_manager.validate_rack_requirements()
        self.assert_true(is_valid, f"Rack requirements not met: {message}")
        
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
            f"Insufficient racks for strict RA: {rack_count} < 3"
        )
        
        self.logger.info(f"Prerequisites validated: {rack_count} racks available")
    
    def _ensure_best_effort_mode(self) -> None:
        """Ensure cluster starts in best-effort mode"""
        self.logger.info("Ensuring cluster is in best-effort mode")
        
        if self.cluster_manager.is_strict_rack_awareness_enabled():
            self.logger.info("Disabling strict rack awareness to start in best-effort mode")
            success = self.cluster_manager.disable_strict_rack_awareness()
            self.assert_true(success, "Failed to disable strict rack awareness")
        
        # Verify best-effort mode
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_false(is_strict_enabled, "Cluster should be in best-effort mode")
        
        self.logger.info("Cluster confirmed to be in best-effort mode")
    
    def _create_test_containers(self) -> None:
        """Create test containers for validation"""
        self.logger.info("Creating test containers")
        
        # Generate test container configurations
        self.test_containers = self.test_data_gen.generate_test_containers(
            count=3, strict_rack_awareness=False
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
        
        self.logger.info(f"Created {len(self.test_containers)} test containers")
    
    def _validate_initial_state(self) -> None:
        """Validate initial state is best-effort mode"""
        self.logger.info("Validating initial state (best-effort mode)")
        
        # Confirm strict RA is disabled
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_false(is_strict_enabled, "Strict rack awareness should be disabled initially")
        
        # Validate RPPs are in best-effort mode
        rpp_valid = self.rack_utils.validate_rpp_updates(expected_strict_mode=False)
        self.assert_true(rpp_valid, "RPPs should be in best-effort mode initially")
        
        self.logger.info("Initial state validation completed")
    
    def _validate_strict_ra_preconditions(self) -> None:
        """Validate preconditions for enabling strict rack awareness"""
        self.logger.info("Validating strict rack awareness preconditions")
        
        is_valid, issues = self.rack_utils.validate_strict_ra_prerequisites()
        
        if not is_valid:
            self.logger.error(f"Strict RA preconditions not met: {', '.join(issues)}")
            self.assert_true(is_valid, f"Preconditions failed: {', '.join(issues)}")
        
        self.logger.info("Strict rack awareness preconditions validated")
    
    def _enable_strict_rack_awareness(self) -> None:
        """Enable strict rack awareness"""
        self.logger.info("Enabling strict rack awareness")
        
        # Record start time for performance measurement
        start_time = time.time()
        
        # Enable strict RA
        success = self.cluster_manager.enable_strict_rack_awareness()
        self.assert_true(success, "Failed to enable strict rack awareness")
        
        # Record transition time
        transition_time = time.time() - start_time
        self.test_result.add_metric("strict_ra_enable_time_seconds", transition_time)
        
        self.logger.info(f"Strict rack awareness enabled in {transition_time:.2f} seconds")
    
    def _validate_transition_success(self) -> None:
        """Validate that transition to strict RA was successful"""
        self.logger.info("Validating transition success")
        
        # Verify strict RA is now enabled
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_true(is_strict_enabled, "Strict rack awareness should be enabled after transition")
        
        # Wait for cluster to stabilize
        stable = self.cluster_manager.wait_for_cluster_stable(timeout_minutes=10)
        self.assert_true(stable, "Cluster should stabilize after enabling strict RA")
        
        # Validate cluster health after transition
        health_summary = self.cluster_manager.get_cluster_health_summary()
        cluster_status = health_summary.get('cluster_status')
        self.assert_equal(cluster_status, 'NORMAL', f"Cluster should remain healthy: {cluster_status}")
        
        self.logger.info("Transition success validation completed")
    
    def _validate_rpp_updates(self) -> None:
        """Validate that RPPs are updated to strict versions"""
        self.logger.info("Validating RPP updates")
        
        # Wait for RPPs to be updated
        rpp_updated = self.rack_utils.wait_for_rpp_update(
            expected_strict_mode=True, timeout_seconds=300
        )
        self.assert_true(rpp_updated, "RPPs should be updated to strict mode")
        
        # Validate RPPs are in strict mode
        rpp_valid = self.rack_utils.validate_rpp_updates(expected_strict_mode=True)
        self.assert_true(rpp_valid, "RPPs should be in strict mode after transition")
        
        self.logger.info("RPP updates validation completed")
    
    def _validate_container_behavior(self) -> None:
        """Validate container behavior with strict rack awareness"""
        self.logger.info("Validating container behavior with strict RA")
        
        for container in self.test_containers:
            # Validate container placement follows strict RA rules
            is_valid, message = self.rack_utils.validate_container_placement(
                container.name, expected_strict_mode=True
            )
            
            self.assert_true(
                is_valid,
                f"Container {container.name} placement validation failed: {message}"
            )
        
        # Create a new container to test strict RA enforcement
        new_container = self.test_data_gen.generate_test_containers(count=1, strict_rack_awareness=True)[0]
        
        container_uuid = self.rack_utils.create_test_container(
            name=new_container.name,
            replication_factor=new_container.replication_factor,
            strict_rack_awareness=True
        )
        
        self.assert_true(
            container_uuid is not None,
            f"Failed to create new container with strict RA: {new_container.name}"
        )
        
        # Add to cleanup list
        self.test_containers.append(new_container)
        new_container.uuid = container_uuid
        
        # Validate new container follows strict placement
        is_valid, message = self.rack_utils.validate_container_placement(
            new_container.name, expected_strict_mode=True
        )
        
        self.assert_true(
            is_valid,
            f"New container {new_container.name} should follow strict placement: {message}"
        )
        
        self.logger.info("Container behavior validation completed")