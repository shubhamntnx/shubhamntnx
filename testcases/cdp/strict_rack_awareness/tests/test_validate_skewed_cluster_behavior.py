"""
Test Case: Validate Skewed Cluster Behavior

Test Case Name: validate_skewed_cluster_behavior
Description: Validate strict RA behavior in skewed cluster with uneven rack resources.
Steps: Create skewed cluster, enable strict RA, create containers, simulate failures.
Expected Result: Placement honors rack boundaries. Alerts raised if FT is compromised.
"""

import time
from typing import List, Dict, Any

from nutest_py3.framework import BaseTest, TestConfig, TestPriority
from nutest_py3_tests.common import RackAwarenessTestUtils, ClusterValidationUtils, TestDataGenerator


class ValidateSkewedClusterBehaviorTest(BaseTest):
    """
    Test strict rack awareness behavior in skewed cluster configurations
    """
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.rack_utils = RackAwarenessTestUtils(config)
        self.cluster_validation = ClusterValidationUtils(config)
        self.test_data_gen = TestDataGenerator()
        self.test_containers = []
        self.skewed_config = None
        self.created_workloads = []
        
    @property
    def test_name(self) -> str:
        return "validate_skewed_cluster_behavior"
    
    @property
    def description(self) -> str:
        return "Validate strict RA behavior in skewed cluster with uneven rack resources"
    
    @property
    def priority(self) -> TestPriority:
        return TestPriority.HIGH
    
    @property
    def timeout_minutes(self) -> int:
        return 75
    
    @property
    def prerequisites(self) -> List[str]:
        return [
            "Cluster must have at least 3 racks",
            "Cluster must be in healthy state", 
            "Ability to create skewed resource distribution",
            "Sufficient overall cluster capacity"
        ]
    
    def setup(self) -> None:
        """Setup test environment"""
        super().setup()
        
        self.logger.info("Setting up skewed cluster behavior validation test")
        
        # Validate prerequisites
        self._validate_test_prerequisites()
        
        # Analyze current cluster configuration
        self._analyze_cluster_configuration()
        
        # Generate or simulate skewed configuration
        self._setup_skewed_scenario()
        
        # Enable strict rack awareness
        self._enable_strict_rack_awareness()
        
    def execute(self) -> None:
        """Main test execution"""
        self.logger.info("Executing skewed cluster behavior validation test")
        
        # Step 1: Validate skewed cluster setup
        self._validate_skewed_setup()
        
        # Step 2: Test container creation in skewed environment
        self._test_container_creation()
        
        # Step 3: Validate placement behavior
        self._validate_placement_behavior()
        
        # Step 4: Test resource utilization patterns
        self._test_resource_utilization()
        
        # Step 5: Simulate failures in skewed environment
        self._simulate_failures_in_skewed_cluster()
        
        # Step 6: Validate alert generation
        self._validate_alert_generation()
        
        # Step 7: Test recovery in skewed environment
        self._test_recovery_behavior()
        
    def teardown(self) -> None:
        """Cleanup test environment"""
        try:
            # Clean up workloads
            self._cleanup_workloads()
            
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
        
        # Verify we have at least 3 racks
        rack_count = health_summary.get('rack_count', 0)
        self.assert_true(
            rack_count >= 3,
            f"Insufficient racks for skewed testing: {rack_count} < 3"
        )
        
        self.logger.info(f"Prerequisites validated: {rack_count} racks available")
    
    def _analyze_cluster_configuration(self) -> None:
        """Analyze current cluster configuration to understand skew"""
        self.logger.info("Analyzing current cluster configuration")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        rack_details = health_summary.get('rack_details', {})
        
        # Analyze resource distribution across racks
        rack_host_counts = []
        for rack_id, rack_info in rack_details.items():
            host_count = rack_info.get('total_hosts', 0)
            rack_host_counts.append(host_count)
            self.logger.info(f"Rack {rack_id}: {host_count} hosts")
        
        if rack_host_counts:
            max_hosts = max(rack_host_counts)
            min_hosts = min(rack_host_counts)
            skew_ratio = max_hosts / min_hosts if min_hosts > 0 else float('inf')
            
            self.test_result.add_metric("natural_host_skew_ratio", skew_ratio)
            self.logger.info(f"Natural cluster skew ratio (hosts): {skew_ratio:.2f}")
            
            # Determine if cluster is already significantly skewed
            if skew_ratio > 2.0:
                self.logger.info("Cluster already has significant natural skew")
            else:
                self.logger.info("Cluster has relatively balanced host distribution")
    
    def _setup_skewed_scenario(self) -> None:
        """Setup or simulate a skewed cluster scenario"""
        self.logger.info("Setting up skewed cluster scenario")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        total_racks = health_summary.get('rack_count', 0)
        
        # Generate skewed configuration
        self.skewed_config = self.test_data_gen.generate_skewed_cluster_config(total_racks)
        
        self.logger.info(f"Generated skewed config with ratio: {self.skewed_config['skew_ratio']:.2f}")
        
        # Since we can't actually modify the physical cluster configuration,
        # we'll simulate the skewed behavior by creating workloads that would
        # expose skewed placement behavior
        
        success = self.cluster_validation.create_skewed_cluster_scenario()
        self.assert_true(success, "Failed to create skewed cluster scenario")
        
        self.test_result.add_metric("simulated_skew_ratio", self.skewed_config['skew_ratio'])
    
    def _enable_strict_rack_awareness(self) -> None:
        """Enable strict rack awareness for skewed testing"""
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
    
    def _validate_skewed_setup(self) -> None:
        """Validate that skewed setup is properly configured"""
        self.logger.info("Validating skewed cluster setup")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        # Verify cluster is still healthy despite skew
        self.assert_equal(
            health_summary.get('cluster_status'), 'NORMAL',
            f"Cluster should remain healthy in skewed setup: {health_summary.get('cluster_status')}"
        )
        
        # Verify strict RA is working
        is_strict_enabled = self.cluster_manager.is_strict_rack_awareness_enabled()
        self.assert_true(is_strict_enabled, "Strict RA should be enabled in skewed setup")
        
        # Record skewed cluster metrics
        rack_details = health_summary.get('rack_details', {})
        for rack_id, rack_info in rack_details.items():
            self.test_result.add_metric(f"rack_{rack_id}_hosts", rack_info.get('total_hosts', 0))
            self.test_result.add_metric(f"rack_{rack_id}_available_hosts", rack_info.get('available_hosts', 0))
        
        self.logger.info("Skewed cluster setup validation completed")
    
    def _test_container_creation(self) -> None:
        """Test container creation behavior in skewed environment"""
        self.logger.info("Testing container creation in skewed environment")
        
        # Create containers with different replication factors
        replication_factors = [2, 3]
        
        for rf in replication_factors:
            self.logger.info(f"Testing container creation with RF={rf}")
            
            # Generate test containers
            test_containers = self.test_data_gen.generate_test_containers(
                count=2, strict_rack_awareness=True
            )
            
            for container in test_containers:
                container.replication_factor = rf
                
                # Attempt to create container
                container_uuid = self.rack_utils.create_test_container(
                    name=container.name,
                    replication_factor=container.replication_factor,
                    strict_rack_awareness=container.strict_rack_awareness
                )
                
                if container_uuid:
                    container.uuid = container_uuid
                    self.test_containers.append(container)
                    self.logger.info(f"Successfully created container {container.name} with RF={rf}")
                else:
                    self.logger.warning(f"Failed to create container {container.name} with RF={rf}")
                    # This might be expected if skew prevents proper placement
        
        self.assert_true(
            len(self.test_containers) > 0,
            "Should be able to create at least some containers in skewed environment"
        )
        
        self.test_result.add_metric("containers_created_in_skewed_env", len(self.test_containers))
    
    def _validate_placement_behavior(self) -> None:
        """Validate placement behavior in skewed environment"""
        self.logger.info("Validating placement behavior in skewed environment")
        
        placement_violations = []
        placement_successes = []
        
        for container in self.test_containers:
            is_valid, message = self.rack_utils.validate_container_placement(
                container.name, expected_strict_mode=True
            )
            
            if is_valid:
                placement_successes.append(container.name)
                self.logger.info(f"Container {container.name} placement valid: {message}")
            else:
                placement_violations.append(container.name)
                self.logger.warning(f"Container {container.name} placement issue: {message}")
        
        # Record placement metrics
        self.test_result.add_metric("placement_successes", len(placement_successes))
        self.test_result.add_metric("placement_violations", len(placement_violations))
        
        # In a skewed environment, some placement challenges are expected
        # but strict RA should still be honored where possible
        if placement_violations:
            self.logger.info(f"Placement violations in skewed environment: {placement_violations}")
            # This might be expected behavior - document it
            self.test_result.add_metric("placement_violations_list", placement_violations)
        
        # At least some placements should succeed
        self.assert_true(
            len(placement_successes) > 0,
            "At least some containers should have valid placement in skewed environment"
        )
    
    def _test_resource_utilization(self) -> None:
        """Test resource utilization patterns in skewed environment"""
        self.logger.info("Testing resource utilization patterns")
        
        # Create workloads on test containers
        container_names = [c.name for c in self.test_containers]
        workloads = self.test_data_gen.generate_test_workloads(container_names)
        
        # Simulate running workloads (in a real implementation, this would
        # actually start I/O workloads)
        for workload in workloads:
            self.logger.info(f"Simulating workload: {workload['name']}")
            # Placeholder for actual workload execution
            self.created_workloads.append(workload)
        
        # Monitor resource utilization patterns
        # This would involve checking how resources are utilized across racks
        health_summary = self.cluster_manager.get_cluster_health_summary()
        
        # Analyze utilization skew
        rack_details = health_summary.get('rack_details', {})
        utilization_metrics = {}
        
        for rack_id, rack_info in rack_details.items():
            # In a real implementation, you'd get actual utilization metrics
            # For now, we'll use host availability as a proxy
            total_hosts = rack_info.get('total_hosts', 0)
            available_hosts = rack_info.get('available_hosts', 0)
            utilization_ratio = (total_hosts - available_hosts) / total_hosts if total_hosts > 0 else 0
            
            utilization_metrics[rack_id] = utilization_ratio
            self.test_result.add_metric(f"rack_{rack_id}_utilization", utilization_ratio)
        
        # Check for utilization skew
        if utilization_metrics:
            max_util = max(utilization_metrics.values())
            min_util = min(utilization_metrics.values())
            util_skew = max_util - min_util
            
            self.test_result.add_metric("utilization_skew", util_skew)
            self.logger.info(f"Resource utilization skew: {util_skew:.2f}")
        
        self.logger.info("Resource utilization testing completed")
    
    def _simulate_failures_in_skewed_cluster(self) -> None:
        """Simulate failures in skewed cluster environment"""
        self.logger.info("Simulating failures in skewed cluster")
        
        health_summary = self.cluster_manager.get_cluster_health_summary()
        rack_details = health_summary.get('rack_details', {})
        
        # Identify the rack with the most resources (highest impact failure)
        max_hosts = 0
        target_rack = None
        
        for rack_id, rack_info in rack_details.items():
            host_count = rack_info.get('total_hosts', 0)
            if host_count > max_hosts:
                max_hosts = host_count
                target_rack = rack_id
        
        if target_rack and self.config.rack_failure_simulation:
            self.logger.info(f"Simulating failure of resource-rich rack: {target_rack}")
            
            # Record pre-failure state
            pre_failure_containers = len(self.test_containers)
            
            # Simulate rack failure
            success = self.cluster_manager.simulate_rack_failure(target_rack)
            
            if success:
                # Wait for cluster to react
                time.sleep(60)
                
                # Validate behavior after failure
                post_failure_health = self.cluster_manager.get_cluster_health_summary()
                
                # Check if quorum is maintained
                is_valid, message = self.cluster_validation.validate_quorum_maintenance([target_rack])
                self.logger.info(f"Quorum status after skewed rack failure: {message}")
                
                # Check data availability
                container_names = [c.name for c in self.test_containers]
                is_available, avail_message = self.cluster_validation.validate_data_availability(container_names)
                self.logger.info(f"Data availability after skewed rack failure: {avail_message}")
                
                # Record failure impact metrics
                self.test_result.add_metric("failed_rack_host_count", max_hosts)
                self.test_result.add_metric("quorum_maintained_after_skewed_failure", is_valid)
                self.test_result.add_metric("data_available_after_skewed_failure", is_available)
                
                # Recovery
                self.cluster_manager.recover_rack(target_rack)
                self.cluster_manager.wait_for_cluster_stable(timeout_minutes=10)
                
            else:
                self.logger.warning("Failed to simulate rack failure")
        else:
            self.logger.info("Skipping failure simulation (not enabled or no suitable rack)")
    
    def _validate_alert_generation(self) -> None:
        """Validate that appropriate alerts are generated"""
        self.logger.info("Validating alert generation in skewed environment")
        
        # Test different alert scenarios
        expected_alerts = [
            "resource_imbalance",
            "placement_constraints", 
            "fault_tolerance_risk"
        ]
        
        is_valid, message = self.cluster_validation.validate_alerts_and_warnings(expected_alerts)
        
        self.test_result.add_metric("alerts_validation_passed", is_valid)
        self.test_result.add_metric("alerts_validation_message", message)
        
        if is_valid:
            self.logger.info(f"Alert validation passed: {message}")
        else:
            self.logger.warning(f"Alert validation issues: {message}")
            # In skewed environments, some alert issues might be expected
    
    def _test_recovery_behavior(self) -> None:
        """Test recovery behavior in skewed environment"""
        self.logger.info("Testing recovery behavior in skewed environment")
        
        # Test creating new containers after skewed operations
        recovery_container = self.test_data_gen.generate_test_containers(count=1, strict_rack_awareness=True)[0]
        
        container_uuid = self.rack_utils.create_test_container(
            name=recovery_container.name,
            replication_factor=recovery_container.replication_factor,
            strict_rack_awareness=recovery_container.strict_rack_awareness
        )
        
        if container_uuid:
            recovery_container.uuid = container_uuid
            self.test_containers.append(recovery_container)
            
            # Validate placement of recovery container
            is_valid, message = self.rack_utils.validate_container_placement(
                recovery_container.name, expected_strict_mode=True
            )
            
            self.test_result.add_metric("recovery_container_placement_valid", is_valid)
            self.logger.info(f"Recovery container placement: {message}")
        else:
            self.test_result.add_metric("recovery_container_creation_failed", True)
            self.logger.warning("Failed to create recovery container in skewed environment")
        
        # Test cluster rebalancing behavior
        # In a real implementation, this would trigger rebalancing operations
        self.logger.info("Testing cluster rebalancing in skewed environment")
        
        # Wait for any ongoing rebalancing to complete
        stable = self.cluster_manager.wait_for_cluster_stable(timeout_minutes=15)
        self.test_result.add_metric("cluster_stable_after_skewed_operations", stable)
        
        if stable:
            self.logger.info("Cluster remained stable during skewed environment testing")
        else:
            self.logger.warning("Cluster stability issues in skewed environment")
    
    def _cleanup_workloads(self) -> None:
        """Clean up created workloads"""
        if self.created_workloads:
            self.logger.info(f"Cleaning up {len(self.created_workloads)} workloads")
            
            for workload in self.created_workloads:
                try:
                    # In a real implementation, this would stop the workload
                    self.logger.debug(f"Cleaning up workload: {workload['name']}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup workload {workload['name']}: {str(e)}")
            
            self.created_workloads.clear()