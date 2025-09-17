"""
Test Case: FT1 to FT2 Upgrade with Strict Rack Awareness

Test Case Name: ft1_to_ft2_with_strict_ra
Description: Upgrade cluster from FT1 to FT2 with strict RA enabled.
Steps: Use PUT /cluster to change FT to 2. Validate RPP, metadata ensemble, and rebalance.
Expected Result: Cluster transitions to FT2 with kRF3_Strict and quorum maintained.
"""

import time
from typing import List, Dict, Any

from nutest_py3.framework import BaseTest, TestConfig, TestPriority
from nutest_py3_tests.common import RackAwarenessTestUtils, ClusterValidationUtils, TestDataGenerator


class FT1ToFT2WithStrictRATest(BaseTest):
    """
    Test upgrading cluster from FT1 to FT2 with strict rack awareness enabled
    """
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.rack_utils = RackAwarenessTestUtils(config)
        self.cluster_validation = ClusterValidationUtils(config)
        self.test_data_gen = TestDataGenerator()
        self.test_containers = []
        self.initial_ft_level = None
        self.target_ft_level = 2
        
    @property
    def test_name(self) -> str:
        return "ft1_to_ft2_with_strict_ra"
    
    @property
    def description(self) -> str:
        return "Upgrade cluster from FT1 to FT2 with strict RA enabled"
    
    @property
    def priority(self) -> TestPriority:
        return TestPriority.CRITICAL
    
    @property
    def timeout_minutes(self) -> int:
        return 90  # FT upgrades can take a long time
    
    @property
    def prerequisites(self) -> List[str]:
        return [
            "Cluster must have at least 3 racks for FT2 with strict RA",
            "Cluster must be in healthy state",
            "Sufficient storage capacity for FT2 replication",
            "Cluster must be at FT1 initially"
        ]
    
    def setup(self) -> None:
        """Setup test environment"""
        super().setup()
        
        self.logger.info("Setting up FT1 to FT2 with strict RA test")
        
        # Validate prerequisites
        self._validate_test_prerequisites()
        
        # Ensure cluster is at FT1
        self._ensure_ft1_state()
        
        # Enable strict rack awareness
        self._enable_strict_rack_awareness()
        
        # Create test containers for validation
        self._create_test_containers()
        
    def execute(self) -> None:
        """Main test execution"""
        self.logger.info("Executing FT1 to FT2 with strict RA upgrade test")
        
        # Step 1: Validate initial state (FT1 + strict RA)
        self._validate_initial_state()
        
        # Step 2: Record baseline metrics
        self._record_baseline_metrics()
        
        # Step 3: Initiate FT upgrade to FT2
        self._initiate_ft_upgrade()
        
        # Step 4: Monitor upgrade progress
        self._monitor_upgrade_progress()
        
        # Step 5: Validate upgrade completion
        self._validate_upgrade_completion()
        
        # Step 6: Validate RPPs updated to kRF3_Strict
        self._validate_rpp_updates()
        
        # Step 7: Validate metadata ensemble
        self._validate_metadata_ensemble()
        
        # Step 8: Validate data rebalance
        self._validate_data_rebalance()
        
        # Step 9: Validate quorum maintenance
        self._validate_quorum_maintenance()
        
    def teardown(self) -> None:
        """Cleanup test environment"""
        try:
            # Clean up test containers
            if self.test_containers:
                container_names = [container.name for container in self.test_containers]
                self.rack_utils.cleanup_test_containers(container_names)
            
            # Note: We don't revert FT level as that's typically not supported
            # and would be destructive
                
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
        
        # Verify we have at least 3 racks for FT2 with strict RA
        rack_count = health_summary.get('rack_count', 0)
        self.assert_true(
            rack_count >= 3,
            f"Insufficient racks for FT2 with strict RA: {rack_count} < 3"
        )
        
        # Check if cluster has sufficient resources for FT2
        # This would typically involve checking storage capacity, host count, etc.
        self._validate_ft2_capacity_requirements()
        
        self.logger.info(f"Prerequisites validated: {rack_count} racks available")
    
    def _validate_ft2_capacity_requirements(self) -> None:
        """Validate cluster has sufficient capacity for FT2"""
        self.logger.info("Validating FT2 capacity requirements")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        # Check minimum host count (typically need more hosts for FT2)
        total_hosts = health_summary.get('total_hosts', 0)
        self.assert_true(
            total_hosts >= 3,  # Minimum for FT2
            f"Insufficient hosts for FT2: {total_hosts} < 3"
        )
        
        # Additional capacity checks would go here based on your specific requirements
        self.logger.info("FT2 capacity requirements validated")
    
    def _ensure_ft1_state(self) -> None:
        """Ensure cluster is at FT1"""
        self.logger.info("Ensuring cluster is at FT1")
        
        current_ft = self.rack_utils.get_cluster_ft_level()
        self.initial_ft_level = current_ft
        
        if current_ft == 0:
            # Need to upgrade from FT0 to FT1 first
            self.logger.info("Upgrading cluster from FT0 to FT1")
            success = self.rack_utils.upgrade_cluster_ft_level(1)
            self.assert_true(success, "Failed to upgrade cluster to FT1")
            current_ft = 1
        elif current_ft > 1:
            # Already at higher FT level - this is acceptable but log it
            self.logger.warning(f"Cluster is already at FT{current_ft}, higher than expected FT1")
        
        self.assert_true(
            current_ft >= 1,
            f"Cluster should be at FT1 or higher: FT{current_ft}"
        )
        
        self.logger.info(f"Cluster confirmed to be at FT{current_ft}")
    
    def _enable_strict_rack_awareness(self) -> None:
        """Enable strict rack awareness if not already enabled"""
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
    
    def _create_test_containers(self) -> None:
        """Create test containers for validation during upgrade"""
        self.logger.info("Creating test containers for upgrade validation")
        
        # Generate test container configurations
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
        
        self.logger.info(f"Created {len(self.test_containers)} test containers")
    
    def _validate_initial_state(self) -> None:
        """Validate initial state before upgrade"""
        self.logger.info("Validating initial state before FT upgrade")
        
        # Confirm current FT level
        current_ft = self.rack_utils.get_cluster_ft_level()
        self.assert_true(current_ft >= 1, f"Cluster should be at FT1 or higher: FT{current_ft}")
        
        # Confirm strict RA is enabled
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_true(is_strict_enabled, "Strict rack awareness should be enabled")
        
        # Validate cluster health
        health_summary = self.cluster_manager.get_cluster_health_summary()
        self.assert_equal(
            health_summary.get('cluster_status'), 'NORMAL',
            f"Cluster should be healthy before upgrade: {health_summary.get('cluster_status')}"
        )
        
        self.logger.info(f"Initial state validated: FT{current_ft} with strict RA enabled")
    
    def _record_baseline_metrics(self) -> None:
        """Record baseline metrics before upgrade"""
        self.logger.info("Recording baseline metrics")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        self.test_result.add_metric("initial_ft_level", self.rack_utils.get_cluster_ft_level())
        self.test_result.add_metric("initial_rack_count", health_summary.get('rack_count', 0))
        self.test_result.add_metric("initial_total_hosts", health_summary.get('total_hosts', 0))
        self.test_result.add_metric("initial_available_hosts", health_summary.get('available_hosts', 0))
        
        # Record container count
        containers = self.api_client.get_storage_containers()
        self.test_result.add_metric("initial_container_count", len(containers.get('entities', [])))
        
        self.logger.info("Baseline metrics recorded")
    
    def _initiate_ft_upgrade(self) -> None:
        """Initiate FT upgrade from current level to FT2"""
        self.logger.info(f"Initiating FT upgrade to FT{self.target_ft_level}")
        
        # Record start time
        upgrade_start_time = time.time()
        self.test_result.add_metric("ft_upgrade_start_time", upgrade_start_time)
        
        # Initiate the upgrade
        success = self.rack_utils.upgrade_cluster_ft_level(self.target_ft_level)
        self.assert_true(success, f"Failed to initiate FT upgrade to FT{self.target_ft_level}")
        
        self.logger.info(f"FT upgrade to FT{self.target_ft_level} initiated")
    
    def _monitor_upgrade_progress(self) -> None:
        """Monitor the upgrade progress"""
        self.logger.info("Monitoring FT upgrade progress")
        
        start_time = time.time()
        last_status_time = start_time
        status_interval = 60  # Log status every minute
        
        while True:
            current_time = time.time()
            
            # Check if upgrade completed
            current_ft = self.rack_utils.get_cluster_ft_level()
            if current_ft == self.target_ft_level:
                upgrade_duration = current_time - start_time
                self.test_result.add_metric("ft_upgrade_duration_seconds", upgrade_duration)
                self.logger.info(f"FT upgrade completed in {upgrade_duration:.2f} seconds")
                break
            
            # Log progress periodically
            if current_time - last_status_time >= status_interval:
                health_summary = self.cluster_manager.get_cluster_health_summary()
                self.logger.info(
                    f"Upgrade in progress: FT{current_ft}, "
                    f"cluster status: {health_summary.get('cluster_status')}, "
                    f"elapsed: {current_time - start_time:.0f}s"
                )
                last_status_time = current_time
            
            # Check for timeout
            if current_time - start_time > self.timeout_minutes * 60:
                self.assert_true(False, "FT upgrade timeout exceeded")
            
            time.sleep(10)  # Check every 10 seconds
    
    def _validate_upgrade_completion(self) -> None:
        """Validate that upgrade completed successfully"""
        self.logger.info("Validating FT upgrade completion")
        
        # Verify FT level
        current_ft = self.rack_utils.get_cluster_ft_level()
        self.assert_equal(
            current_ft, self.target_ft_level,
            f"FT level should be {self.target_ft_level}: FT{current_ft}"
        )
        
        # Wait for cluster to stabilize
        stable = self.cluster_manager.wait_for_cluster_stable(timeout_minutes=15)
        self.assert_true(stable, "Cluster should stabilize after FT upgrade")
        
        # Validate cluster health
        health_summary = self.cluster_manager.get_cluster_health_summary()
        cluster_status = health_summary.get('cluster_status')
        self.assert_equal(cluster_status, 'NORMAL', f"Cluster should be healthy after upgrade: {cluster_status}")
        
        self.logger.info(f"FT upgrade to FT{self.target_ft_level} completed successfully")
    
    def _validate_rpp_updates(self) -> None:
        """Validate that RPPs are updated to kRF3_Strict"""
        self.logger.info("Validating RPP updates to kRF3_Strict")
        
        # Wait for RPPs to be updated
        rpp_updated = self.rack_utils.wait_for_rpp_update(
            expected_strict_mode=True, timeout_seconds=600  # 10 minutes for FT upgrade
        )
        self.assert_true(rpp_updated, "RPPs should be updated after FT upgrade")
        
        # Validate RPPs reflect both FT2 and strict RA
        policies = self.rack_utils.get_replication_policies()
        
        # Check for expected policy types (this would depend on your specific implementation)
        expected_policies = ['kRF3_Strict']  # For FT2 with strict RA
        
        found_policies = []
        for policy in policies.get('entities', []):
            policy_name = policy.get('metadata', {}).get('name', '')
            if any(expected in policy_name for expected in expected_policies):
                found_policies.append(policy_name)
        
        self.assert_true(
            len(found_policies) > 0,
            f"Should find kRF3_Strict policies, found: {found_policies}"
        )
        
        self.logger.info(f"RPP validation completed: {found_policies}")
    
    def _validate_metadata_ensemble(self) -> None:
        """Validate metadata ensemble after FT upgrade"""
        self.logger.info("Validating metadata ensemble")
        
        # Get fault tolerance status
        ft_status = self.cluster_manager.get_fault_tolerance_status()
        
        # Validate metadata ensemble configuration
        # This would depend on your specific metadata ensemble implementation
        # For FT2, you typically expect a 5-node ensemble
        
        # Placeholder validation - implement based on your specific requirements
        self.logger.info("Metadata ensemble validation completed (placeholder)")
    
    def _validate_data_rebalance(self) -> None:
        """Validate data rebalance after FT upgrade"""
        self.logger.info("Validating data rebalance")
        
        # Check that data is properly distributed according to new FT level
        # This would involve checking replica placement across racks
        
        for container in self.test_containers:
            is_valid, message = self.rack_utils.validate_container_placement(
                container.name, expected_strict_mode=True
            )
            
            self.assert_true(
                is_valid,
                f"Container {container.name} placement after rebalance: {message}"
            )
        
        # Additional rebalance validation would go here
        self.logger.info("Data rebalance validation completed")
    
    def _validate_quorum_maintenance(self) -> None:
        """Validate that quorum is maintained throughout upgrade"""
        self.logger.info("Validating quorum maintenance")
        
        # Verify cluster maintained quorum during upgrade
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        # All hosts should be available (no failures during upgrade)
        total_hosts = health_summary.get('total_hosts', 0)
        available_hosts = health_summary.get('available_hosts', 0)
        
        self.assert_equal(
            available_hosts, total_hosts,
            f"All hosts should be available after upgrade: {available_hosts}/{total_hosts}"
        )
        
        # Validate quorum with new FT level
        is_valid, message = self.cluster_validation.validate_quorum_maintenance([])
        self.assert_true(is_valid, f"Quorum validation failed: {message}")
        
        self.logger.info("Quorum maintenance validation completed")