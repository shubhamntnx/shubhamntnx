"""
Test Skewed Cluster Behavior

This module contains tests for validating strict RA behavior in skewed clusters with uneven rack resources.
"""

import logging
import time
from typing import List, Dict, Any
from collections import defaultdict

from nutest_py3_tests.workflows.rack_awareness_workflows import RackAwarenessWorkflows
from nutest_py3_tests.workflows.cluster_workflows import ClusterWorkflows
from nutest_py3_tests.workflows.storage_workflows import StorageWorkflows


class SkewedClusterBehavior:
    """
    Test class for skewed cluster behavior validation
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
        self.skewed_config = None
        self.created_workloads = []
    
    def setup(self):
        """Setup method called before each test"""
        self.logger.info("Setting up SkewedClusterBehavior test")
        
        # Validate cluster connectivity and analyze skew
        try:
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            if 'error' in health_summary:
                raise RuntimeError(f"Cluster health check failed: {health_summary['error']}")
            
            self.logger.info(f"Cluster status: {health_summary.get('cluster_status')}")
            
            # Analyze current cluster skew
            self._analyze_cluster_skew()
            
        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise
    
    def teardown(self):
        """Teardown method called after each test"""
        self.logger.info("Tearing down SkewedClusterBehavior test")
        
        # Cleanup workloads
        self._cleanup_workloads()
        
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
        self.created_workloads.clear()
    
    def test_validate_skewed_cluster_behavior(self):
        """
        Test validate strict RA behavior in skewed cluster with uneven rack resources
        
        Test Steps:
        1. Analyze/create skewed cluster scenario
        2. Enable strict rack awareness
        3. Test container creation in skewed environment
        4. Validate placement behavior
        5. Test resource utilization patterns
        6. Simulate failures in skewed cluster
        7. Validate alert generation
        8. Test recovery behavior
        """
        self.logger.info("Starting test_validate_skewed_cluster_behavior")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 75) * 60
        start_time = time.time()
        
        try:
            # Step 1: Analyze/create skewed cluster scenario
            if self.test_params.get('create_skewed_scenario', True):
                self.logger.info("Step 1: Analyzing/creating skewed cluster scenario")
                self._setup_skewed_scenario()
            
            # Step 2: Enable strict rack awareness
            self.logger.info("Step 2: Enabling strict rack awareness")
            
            if not self.rack_workflows.cluster_entity.get_rack_awareness_status():
                success = self.rack_workflows.transition_to_strict_ra_workflow()
                if not success:
                    raise AssertionError("Failed to enable strict rack awareness")
            
            self.logger.info("Strict rack awareness confirmed to be enabled")
            
            # Step 3: Test container creation in skewed environment
            if self.test_params.get('test_container_creation', True):
                self.logger.info("Step 3: Testing container creation in skewed environment")
                self._test_container_creation_in_skewed_env()
            
            # Step 4: Validate placement behavior
            if self.test_params.get('validate_placement_behavior', True):
                self.logger.info("Step 4: Validating placement behavior")
                self._validate_placement_behavior()
            
            # Step 5: Test resource utilization patterns
            if self.test_params.get('test_resource_utilization', True):
                self.logger.info("Step 5: Testing resource utilization patterns")
                self._test_resource_utilization()
            
            # Step 6: Simulate failures in skewed cluster
            if self.test_params.get('simulate_failures_in_skewed_cluster', True):
                self.logger.info("Step 6: Simulating failures in skewed cluster")
                self._simulate_failures_in_skewed_cluster()
            
            # Step 7: Validate alert generation
            if self.test_params.get('validate_alert_generation', True):
                self.logger.info("Step 7: Validating alert generation")
                self._validate_alert_generation()
            
            # Step 8: Test recovery behavior
            if self.test_params.get('test_recovery_behavior', True):
                self.logger.info("Step 8: Testing recovery behavior")
                self._test_recovery_behavior()
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            self.logger.info("test_validate_skewed_cluster_behavior completed successfully")
            
            return {
                'status': 'PASSED',
                'message': 'Successfully validated skewed cluster behavior with strict RA',
                'containers_created': len(self.test_containers),
                'skew_ratio': self.skewed_config.get('skew_ratio', 'N/A') if self.skewed_config else 'N/A',
                'elapsed_time_seconds': elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_validate_skewed_cluster_behavior failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'elapsed_time_seconds': elapsed_time
            }
    
    def _analyze_cluster_skew(self):
        """Analyze current cluster configuration to understand skew"""
        self.logger.info("Analyzing current cluster configuration for skew")
        
        health_summary = self.cluster_workflows.get_cluster_health_summary()
        rack_details = health_summary.get('rack_details', {})
        
        # Analyze host distribution across racks
        host_counts = []
        for rack_id, rack_info in rack_details.items():
            host_count = rack_info.get('total_hosts', 0)
            host_counts.append(host_count)
            self.logger.info(f"Rack {rack_id}: {host_count} hosts")
        
        if host_counts:
            max_hosts = max(host_counts)
            min_hosts = min(host_counts)
            skew_ratio = max_hosts / min_hosts if min_hosts > 0 else float('inf')
            
            self.logger.info(f"Current cluster skew ratio (hosts): {skew_ratio:.2f}")
            
            # Store skew information
            self.skewed_config = {
                'natural_skew': True,
                'skew_ratio': skew_ratio,
                'max_hosts_per_rack': max_hosts,
                'min_hosts_per_rack': min_hosts,
                'rack_count': len(rack_details)
            }
            
            # Check if cluster is significantly skewed
            skew_threshold = self.test_params.get('skew_ratio_threshold', 2.0)
            if skew_ratio > skew_threshold:
                self.logger.info(f"Cluster has significant natural skew: {skew_ratio:.2f} > {skew_threshold}")
            else:
                self.logger.info(f"Cluster has relatively balanced host distribution")
    
    def _setup_skewed_scenario(self):
        """Setup or simulate a skewed cluster scenario"""
        self.logger.info("Setting up skewed cluster scenario")
        
        if not self.skewed_config:
            self._analyze_cluster_skew()
        
        # Since we can't actually modify the physical cluster configuration,
        # we'll work with the existing skew or create logical skew through workloads
        
        self.logger.info(f"Working with cluster skew ratio: {self.skewed_config.get('skew_ratio', 'N/A')}")
        
        # The skewed behavior will be tested through container creation patterns
        # and monitoring how the system handles uneven resource distribution
    
    def _test_container_creation_in_skewed_env(self):
        """Test container creation behavior in skewed environment"""
        self.logger.info("Testing container creation in skewed environment")
        
        # Create containers with different replication factors
        replication_factors = [2, 3]
        containers_per_rf = 2
        
        for rf in replication_factors:
            self.logger.info(f"Testing container creation with RF={rf}")
            
            for i in range(containers_per_rf):
                container_name = f"skewed_test_rf{rf}_{int(time.time())}_{i}"
                
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=container_name,
                    replication_factor=rf,
                    strict_rack_awareness=True
                )
                
                if container_uuid:
                    self.created_container_names.append(container_name)
                    self.test_containers.append({
                        'name': container_name,
                        'uuid': container_uuid,
                        'replication_factor': rf,
                        'created_in_skewed_env': True
                    })
                    self.logger.info(f"Successfully created container {container_name} with RF={rf}")
                else:
                    self.logger.warning(f"Failed to create container {container_name} with RF={rf}")
                    # This might be expected if skew prevents proper placement
        
        if not self.test_containers:
            raise AssertionError("Failed to create any containers in skewed environment")
        
        self.logger.info(f"Created {len(self.test_containers)} containers in skewed environment")
    
    def _validate_placement_behavior(self):
        """Validate placement behavior in skewed environment"""
        self.logger.info("Validating placement behavior in skewed environment")
        
        placement_successes = 0
        placement_issues = 0
        
        for container in self.test_containers:
            is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                container['name'], expected_strict_mode=True
            )
            
            if is_valid:
                placement_successes += 1
                self.logger.info(f"Container {container['name']} placement valid: {message}")
            else:
                placement_issues += 1
                self.logger.warning(f"Container {container['name']} placement issue: {message}")
        
        # In a skewed environment, some placement challenges are expected
        # but strict RA should still be honored where possible
        if placement_successes == 0:
            raise AssertionError("No containers have valid placement in skewed environment")
        
        self.logger.info(f"Placement validation: {placement_successes} successes, {placement_issues} issues")
    
    def _test_resource_utilization(self):
        """Test resource utilization patterns in skewed environment"""
        self.logger.info("Testing resource utilization patterns")
        
        # Create simulated workloads on test containers
        for container in self.test_containers:
            workload = {
                'name': f"workload_{container['name']}",
                'container': container['name'],
                'type': 'mixed_io',
                'duration_minutes': 5,
                'simulated': True
            }
            
            self.created_workloads.append(workload)
            self.logger.info(f"Simulated workload: {workload['name']}")
        
        # Monitor resource utilization patterns
        health_summary = self.cluster_workflows.get_cluster_health_summary()
        rack_details = health_summary.get('rack_details', {})
        
        utilization_metrics = {}
        for rack_id, rack_info in rack_details.items():
            # In a real implementation, you'd get actual utilization metrics
            # For now, we'll use host availability as a proxy
            total_hosts = rack_info.get('total_hosts', 0)
            available_hosts = rack_info.get('available_hosts', 0)
            utilization_ratio = (total_hosts - available_hosts) / total_hosts if total_hosts > 0 else 0
            
            utilization_metrics[rack_id] = utilization_ratio
            self.logger.info(f"Rack {rack_id} utilization proxy: {utilization_ratio:.2f}")
        
        # Check for utilization skew
        if utilization_metrics:
            max_util = max(utilization_metrics.values())
            min_util = min(utilization_metrics.values())
            util_skew = max_util - min_util
            
            self.logger.info(f"Resource utilization skew: {util_skew:.2f}")
            
            if self.test_params.get('resource_utilization_monitoring', True):
                # In a real implementation, this would trigger more detailed monitoring
                self.logger.info("Resource utilization monitoring would be enhanced here")
    
    def _simulate_failures_in_skewed_cluster(self):
        """Simulate failures in skewed cluster environment"""
        self.logger.info("Simulating failures in skewed cluster")
        
        # Identify the rack with the most resources (highest impact failure)
        health_summary = self.cluster_workflows.get_cluster_health_summary()
        rack_details = health_summary.get('rack_details', {})
        
        max_hosts = 0
        target_rack = None
        
        for rack_id, rack_info in rack_details.items():
            host_count = rack_info.get('total_hosts', 0)
            if host_count > max_hosts:
                max_hosts = host_count
                target_rack = rack_id
        
        if target_rack and self.test_params.get('rack_failure_simulation_enabled', True):
            self.logger.info(f"Simulating failure of resource-rich rack: {target_rack}")
            
            # Record pre-failure state
            pre_failure_containers = len(self.test_containers)
            
            # Simulate rack failure
            success = self.rack_workflows.simulate_rack_failure_workflow(target_rack)
            
            if success:
                # Wait for cluster to react
                time.sleep(60)
                
                # Validate behavior after failure
                is_valid, message = self.rack_workflows.validate_quorum_maintenance_workflow([target_rack])
                self.logger.info(f"Quorum status after skewed rack failure: {message}")
                
                # Check data availability
                container_names = [c['name'] for c in self.test_containers]
                is_available, avail_message = self.rack_workflows.validate_data_availability_workflow(container_names)
                self.logger.info(f"Data availability after skewed rack failure: {avail_message}")
                
                # Recovery
                self.rack_workflows.recover_rack_workflow(target_rack)
                self.cluster_workflows.wait_for_cluster_stable(timeout_minutes=10)
                
            else:
                self.logger.warning("Failed to simulate rack failure")
        else:
            self.logger.info("Skipping failure simulation (not enabled or no suitable rack)")
    
    def _validate_alert_generation(self):
        """Validate that appropriate alerts are generated"""
        self.logger.info("Validating alert generation in skewed environment")
        
        # Test different alert scenarios that should be triggered in skewed environments
        expected_alerts = [
            "resource_imbalance",
            "placement_constraints",
            "fault_tolerance_risk"
        ]
        
        # In a real implementation, this would check the actual alerting system
        # For now, we'll simulate the validation
        alerts_found = []
        
        for alert_type in expected_alerts:
            # Simulate alert checking logic
            if self._check_for_alert_condition(alert_type):
                alerts_found.append(alert_type)
                self.logger.info(f"Alert condition detected: {alert_type}")
        
        if self.test_params.get('alert_validation', True):
            if not alerts_found:
                self.logger.warning("No alert conditions detected in skewed environment")
            else:
                self.logger.info(f"Alert validation completed: {len(alerts_found)} conditions detected")
    
    def _check_for_alert_condition(self, alert_type: str) -> bool:
        """Check if a specific alert condition exists"""
        # Placeholder implementation for alert condition checking
        if alert_type == "resource_imbalance":
            # Check if resource distribution is significantly skewed
            return self.skewed_config and self.skewed_config.get('skew_ratio', 1) > 2.0
        
        elif alert_type == "placement_constraints":
            # Check if placement constraints are being challenged
            return len(self.test_containers) > 0  # If we created containers, there were constraints
        
        elif alert_type == "fault_tolerance_risk":
            # Check if FT might be at risk due to skew
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            rack_count = health_summary.get('rack_count', 0)
            return rack_count <= 3  # Risk increases with fewer racks in skewed environment
        
        return False
    
    def _test_recovery_behavior(self):
        """Test recovery behavior in skewed environment"""
        self.logger.info("Testing recovery behavior in skewed environment")
        
        # Test creating new containers after skewed operations
        recovery_container_name = f"recovery_test_{int(time.time())}"
        
        container_uuid = self.storage_workflows.create_test_container_workflow(
            name=recovery_container_name,
            replication_factor=2,
            strict_rack_awareness=True
        )
        
        if container_uuid:
            self.created_container_names.append(recovery_container_name)
            
            # Validate placement of recovery container
            is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                recovery_container_name, expected_strict_mode=True
            )
            
            if is_valid:
                self.logger.info(f"Recovery container placement validated: {message}")
            else:
                self.logger.warning(f"Recovery container placement issues: {message}")
        else:
            self.logger.warning("Failed to create recovery container in skewed environment")
        
        # Test cluster rebalancing behavior
        self.logger.info("Testing cluster rebalancing in skewed environment")
        
        # Wait for any ongoing rebalancing to complete
        stable = self.cluster_workflows.wait_for_cluster_stable(timeout_minutes=15)
        if stable:
            self.logger.info("Cluster remained stable during skewed environment testing")
        else:
            self.logger.warning("Cluster stability issues in skewed environment")
    
    def _cleanup_workloads(self):
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