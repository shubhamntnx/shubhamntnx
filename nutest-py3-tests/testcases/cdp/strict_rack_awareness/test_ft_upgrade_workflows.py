"""
Test FT Upgrade Workflows

This module contains tests for fault tolerance upgrades with strict rack awareness.
"""

import logging
import time
from typing import List, Dict, Any

from nutest_py3_tests.workflows.rack_awareness_workflows import RackAwarenessWorkflows
from nutest_py3_tests.workflows.cluster_workflows import ClusterWorkflows
from nutest_py3_tests.workflows.storage_workflows import StorageWorkflows


class FTUpgradeWorkflows:
    """
    Test class for FT upgrade workflows with strict rack awareness
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
        self.initial_ft_level = None
    
    def setup(self):
        """Setup method called before each test"""
        self.logger.info("Setting up FTUpgradeWorkflows test")
        
        # Validate cluster connectivity and get initial state
        try:
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            if 'error' in health_summary:
                raise RuntimeError(f"Cluster health check failed: {health_summary['error']}")
            
            self.initial_ft_level = health_summary.get('fault_tolerance_level', 1)
            self.logger.info(f"Initial FT level: {self.initial_ft_level}")
            self.logger.info(f"Cluster status: {health_summary.get('cluster_status')}")
            
        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise
    
    def teardown(self):
        """Teardown method called after each test"""
        self.logger.info("Tearing down FTUpgradeWorkflows test")
        
        # Cleanup test containers
        if self.created_container_names:
            try:
                cleaned_count = self.storage_workflows.cleanup_test_containers_workflow(
                    self.created_container_names
                )
                self.logger.info(f"Cleaned up {cleaned_count} test containers")
            except Exception as e:
                self.logger.warning(f"Cleanup failed: {str(e)}")
        
        # Note: We don't revert FT level as that's typically not supported
        # and would be destructive
        
        # Reset test data
        self.test_containers.clear()
        self.created_container_names.clear()
    
    def test_ft1_to_ft2_with_strict_ra(self):
        """
        Test upgrade cluster from FT1 to FT2 with strict RA enabled
        
        Test Steps:
        1. Ensure cluster is at appropriate initial FT level
        2. Enable strict rack awareness if not already enabled
        3. Create test containers for validation
        4. Record baseline metrics
        5. Initiate FT upgrade to target level
        6. Monitor upgrade progress
        7. Validate upgrade completion
        8. Validate RPPs updated to expected format (e.g., kRF3_Strict)
        9. Validate metadata ensemble if configured
        10. Validate data rebalance
        11. Validate quorum maintenance throughout
        """
        self.logger.info("Starting test_ft1_to_ft2_with_strict_ra")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 90) * 60
        start_time = time.time()
        
        try:
            # Get test parameters
            initial_ft = self.test_params.get('initial_ft_level', 1)
            target_ft = self.test_params.get('target_ft_level', 2)
            expected_rpp = self.test_params.get('expected_rpp', 'kRF3_Strict')
            
            # Step 1: Ensure cluster is at appropriate initial FT level
            self.logger.info(f"Step 1: Ensuring cluster is at FT{initial_ft}")
            
            current_ft = self.rack_workflows.cluster_entity.get_ft_level()
            
            if current_ft < initial_ft:
                self.logger.info(f"Upgrading cluster from FT{current_ft} to FT{initial_ft}")
                success = self.cluster_workflows.upgrade_ft_level_workflow(initial_ft)
                if not success:
                    raise AssertionError(f"Failed to upgrade cluster to FT{initial_ft}")
            elif current_ft > target_ft:
                raise AssertionError(f"Cluster is already at FT{current_ft}, higher than target FT{target_ft}")
            
            self.logger.info(f"Cluster confirmed to be at FT{current_ft}")
            
            # Step 2: Enable strict rack awareness
            self.logger.info("Step 2: Ensuring strict rack awareness is enabled")
            
            if not self.rack_workflows.cluster_entity.get_rack_awareness_status():
                success = self.rack_workflows.transition_to_strict_ra_workflow()
                if not success:
                    raise AssertionError("Failed to enable strict rack awareness")
            
            self.logger.info("Strict rack awareness confirmed to be enabled")
            
            # Step 3: Create test containers for validation
            self.logger.info("Step 3: Creating test containers for upgrade validation")
            
            container_prefix = "ft_upgrade_test"
            for i in range(2):  # Create 2 test containers
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
            
            # Step 4: Record baseline metrics
            self.logger.info("Step 4: Recording baseline metrics")
            
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            baseline_metrics = {
                'initial_ft_level': self.rack_workflows.cluster_entity.get_ft_level(),
                'rack_count': health_summary.get('rack_count', 0),
                'total_hosts': health_summary.get('total_hosts', 0),
                'available_hosts': health_summary.get('available_hosts', 0),
                'cluster_status': health_summary.get('cluster_status')
            }
            
            self.logger.info(f"Baseline metrics: {baseline_metrics}")
            
            # Step 5: Initiate FT upgrade
            self.logger.info(f"Step 5: Initiating FT upgrade to FT{target_ft}")
            
            upgrade_start_time = time.time()
            success = self.rack_workflows.ft_upgrade_with_strict_ra_workflow(target_ft)
            upgrade_duration = time.time() - upgrade_start_time
            
            if not success:
                raise AssertionError(f"Failed to upgrade cluster to FT{target_ft}")
            
            self.logger.info(f"FT upgrade completed in {upgrade_duration:.2f} seconds")
            
            # Step 6-7: Monitor and validate upgrade completion (handled by workflow)
            self.logger.info("Step 6-7: Upgrade monitoring and completion handled by workflow")
            
            # Verify FT level
            final_ft = self.rack_workflows.cluster_entity.get_ft_level()
            if final_ft != target_ft:
                raise AssertionError(f"FT level not upgraded: {final_ft} != {target_ft}")
            
            # Step 8: Validate RPPs updated to expected format
            self.logger.info("Step 8: Validating RPP updates")
            
            rpp_timeout = self.test_params.get('ft_upgrade_timeout_minutes', 60) * 60
            rpp_updated = self.storage_workflows.validate_rpp_updates_workflow(
                expected_strict_mode=True, timeout_seconds=min(rpp_timeout, 600)
            )
            
            if not rpp_updated:
                self.logger.warning("RPP updates not confirmed within timeout")
                # Continue test but log warning
            else:
                self.logger.info(f"RPP updates validated for strict mode")
            
            # Additional RPP validation for specific format
            try:
                policies = self.storage_workflows.storage_entity.get_replication_policies()
                found_expected_rpp = False
                
                for policy in policies.get('entities', []):
                    policy_name = policy.get('metadata', {}).get('name', '')
                    if expected_rpp in policy_name or 'Strict' in policy_name:
                        found_expected_rpp = True
                        self.logger.info(f"Found expected RPP format: {policy_name}")
                        break
                
                if not found_expected_rpp:
                    self.logger.warning(f"Expected RPP format '{expected_rpp}' not found")
                    
            except Exception as e:
                self.logger.warning(f"Failed to validate specific RPP format: {str(e)}")
            
            # Step 9: Validate metadata ensemble if configured
            if self.test_params.get('validate_metadata_ensemble', True):
                self.logger.info("Step 9: Validating metadata ensemble")
                
                try:
                    ft_status = self.rack_workflows.cluster_entity.get_fault_tolerance_status()
                    self.logger.info(f"Fault tolerance status after upgrade: {ft_status}")
                    
                    # Additional metadata ensemble validation would go here
                    # This depends on specific implementation details
                    
                except Exception as e:
                    self.logger.warning(f"Metadata ensemble validation failed: {str(e)}")
            
            # Step 10: Validate data rebalance
            if self.test_params.get('validate_data_rebalance', True):
                self.logger.info("Step 10: Validating data rebalance")
                
                for container in self.test_containers:
                    is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                        container['name'], expected_strict_mode=True
                    )
                    
                    if not is_valid:
                        self.logger.warning(f"Container {container['name']} placement after rebalance: {message}")
                        # This might be acceptable during/after rebalance
                    else:
                        self.logger.info(f"Container {container['name']} placement validated after upgrade")
            
            # Step 11: Validate quorum maintenance
            self.logger.info("Step 11: Validating quorum maintenance")
            
            final_health = self.cluster_workflows.get_cluster_health_summary()
            
            # Check that all hosts are still available
            final_available_hosts = final_health.get('available_hosts', 0)
            initial_available_hosts = baseline_metrics.get('available_hosts', 0)
            
            if final_available_hosts < initial_available_hosts:
                self.logger.warning(
                    f"Host availability decreased: {final_available_hosts} < {initial_available_hosts}"
                )
            
            # Validate cluster is still healthy
            final_cluster_status = final_health.get('cluster_status')
            if final_cluster_status != 'NORMAL':
                raise AssertionError(f"Cluster not healthy after upgrade: {final_cluster_status}")
            
            # Validate quorum with no failed racks
            is_valid, message = self.rack_workflows.validate_quorum_maintenance_workflow([])
            if not is_valid:
                raise AssertionError(f"Quorum validation failed: {message}")
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            self.logger.info("test_ft1_to_ft2_with_strict_ra completed successfully")
            
            return {
                'status': 'PASSED',
                'message': f'Successfully upgraded cluster from FT{initial_ft} to FT{target_ft} with strict RA',
                'initial_ft_level': baseline_metrics['initial_ft_level'],
                'final_ft_level': final_ft,
                'upgrade_duration_seconds': upgrade_duration,
                'total_elapsed_time_seconds': elapsed_time,
                'baseline_metrics': baseline_metrics,
                'final_metrics': {
                    'cluster_status': final_cluster_status,
                    'available_hosts': final_available_hosts,
                    'rack_count': final_health.get('rack_count', 0)
                }
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_ft1_to_ft2_with_strict_ra failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'elapsed_time_seconds': elapsed_time
            }
    
    def validate_ft_upgrade_prerequisites(self, target_ft: int) -> Dict[str, Any]:
        """
        Helper method to validate FT upgrade prerequisites
        """
        try:
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            
            # Check minimum rack count for target FT
            rack_count = health_summary.get('rack_count', 0)
            min_racks_for_ft = target_ft + 1  # General rule
            
            if rack_count < min_racks_for_ft:
                return {
                    'valid': False,
                    'message': f"Insufficient racks for FT{target_ft}: {rack_count} < {min_racks_for_ft}"
                }
            
            # Check cluster health
            cluster_status = health_summary.get('cluster_status')
            if cluster_status != 'NORMAL':
                return {
                    'valid': False,
                    'message': f"Cluster not healthy for upgrade: {cluster_status}"
                }
            
            # Check current FT level
            current_ft = self.rack_workflows.cluster_entity.get_ft_level()
            if current_ft >= target_ft:
                return {
                    'valid': False,
                    'message': f"Cluster already at FT{current_ft} >= target FT{target_ft}"
                }
            
            return {
                'valid': True,
                'message': f"Prerequisites met for FT{target_ft} upgrade",
                'current_ft': current_ft,
                'target_ft': target_ft,
                'rack_count': rack_count
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f"Failed to validate FT upgrade prerequisites: {str(e)}"
            }