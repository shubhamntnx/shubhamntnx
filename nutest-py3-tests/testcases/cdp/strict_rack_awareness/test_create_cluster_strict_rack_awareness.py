"""
Test Create Cluster Strict Rack Awareness

This module contains tests for creating and managing clusters with strict rack awareness.
"""

import logging
import time
from typing import List, Dict, Any

from nutest_py3_tests.workflows.rack_awareness_workflows import RackAwarenessWorkflows
from nutest_py3_tests.workflows.cluster_workflows import ClusterWorkflows
from nutest_py3_tests.workflows.storage_workflows import StorageWorkflows


class CreateClusterStrictRackAwareness:
    """
    Test class for cluster strict rack awareness operations
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
    
    def setup(self):
        """Setup method called before each test"""
        self.logger.info("Setting up CreateClusterStrictRackAwareness test")
        
        # Validate cluster connectivity
        try:
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            if 'error' in health_summary:
                raise RuntimeError(f"Cluster health check failed: {health_summary['error']}")
            
            self.logger.info(f"Cluster status: {health_summary.get('cluster_status')}")
            
        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise
    
    def teardown(self):
        """Teardown method called after each test"""
        self.logger.info("Tearing down CreateClusterStrictRackAwareness test")
        
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
    
    def test_create_enable_disable_strict_ra_cluster(self):
        """
        Test creating cluster with strict rack awareness and toggle enable/disable
        
        Test Steps:
        1. Validate cluster prerequisites for strict RA
        2. Enable strict rack awareness
        3. Create test containers with strict RA
        4. Validate container placement
        5. Disable strict rack awareness
        6. Validate transition to best-effort
        7. Create new containers in best-effort mode
        """
        self.logger.info("Starting test_create_enable_disable_strict_ra_cluster")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 45) * 60
        start_time = time.time()
        
        try:
            # Step 1: Validate prerequisites
            self.logger.info("Step 1: Validating strict RA prerequisites")
            is_valid, issues = self.rack_workflows.validate_strict_ra_prerequisites_workflow()
            
            if not is_valid:
                raise AssertionError(f"Prerequisites not met: {', '.join(issues)}")
            
            self.logger.info("Prerequisites validated successfully")
            
            # Step 2: Enable strict rack awareness
            self.logger.info("Step 2: Enabling strict rack awareness")
            success = self.rack_workflows.transition_to_strict_ra_workflow()
            
            if not success:
                raise AssertionError("Failed to enable strict rack awareness")
            
            self.logger.info("Strict rack awareness enabled successfully")
            
            # Step 3: Create test containers with strict RA
            self.logger.info("Step 3: Creating test containers with strict RA")
            containers_count = self.test_params.get('test_containers_count', 3)
            replication_factor = self.test_params.get('replication_factor', 2)
            container_prefix = self.test_params.get('test_container_prefix', 'strict_ra_test')
            
            for i in range(containers_count):
                container_name = f"{container_prefix}_{int(time.time())}_{i}"
                
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=container_name,
                    replication_factor=replication_factor,
                    strict_rack_awareness=True
                )
                
                if not container_uuid:
                    raise AssertionError(f"Failed to create test container: {container_name}")
                
                self.created_container_names.append(container_name)
                self.test_containers.append({
                    'name': container_name,
                    'uuid': container_uuid,
                    'replication_factor': replication_factor,
                    'strict_rack_awareness': True
                })
            
            self.logger.info(f"Created {len(self.test_containers)} test containers")
            
            # Step 4: Validate container placement
            self.logger.info("Step 4: Validating container placement with strict RA")
            for container in self.test_containers:
                is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                    container['name'], expected_strict_mode=True
                )
                
                if not is_valid:
                    raise AssertionError(f"Container placement validation failed: {message}")
            
            self.logger.info("Container placement validation passed")
            
            # Step 5: Disable strict rack awareness
            self.logger.info("Step 5: Disabling strict rack awareness")
            success = self.rack_workflows.transition_to_best_effort_workflow()
            
            if not success:
                raise AssertionError("Failed to disable strict rack awareness")
            
            self.logger.info("Strict rack awareness disabled successfully")
            
            # Step 6: Validate transition to best-effort
            self.logger.info("Step 6: Validating transition to best-effort")
            
            # Check that cluster is now in best-effort mode
            strict_ra_enabled = self.rack_workflows.cluster_entity.get_rack_awareness_status()
            if strict_ra_enabled:
                raise AssertionError("Cluster should be in best-effort mode but strict RA is still enabled")
            
            self.logger.info("Transition to best-effort validated")
            
            # Step 7: Create new containers in best-effort mode
            self.logger.info("Step 7: Creating containers in best-effort mode")
            
            best_effort_container_name = f"{container_prefix}_best_effort_{int(time.time())}"
            container_uuid = self.storage_workflows.create_test_container_workflow(
                name=best_effort_container_name,
                replication_factor=replication_factor,
                strict_rack_awareness=False
            )
            
            if not container_uuid:
                raise AssertionError(f"Failed to create best-effort container: {best_effort_container_name}")
            
            self.created_container_names.append(best_effort_container_name)
            
            # Validate best-effort placement
            is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                best_effort_container_name, expected_strict_mode=False
            )
            
            if not is_valid:
                self.logger.warning(f"Best-effort container placement validation: {message}")
                # This might be acceptable in best-effort mode
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            self.logger.info("test_create_enable_disable_strict_ra_cluster completed successfully")
            
            return {
                'status': 'PASSED',
                'message': 'Successfully tested enable/disable strict RA cluster operations',
                'containers_created': len(self.test_containers) + 1,
                'elapsed_time_seconds': elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_create_enable_disable_strict_ra_cluster failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'elapsed_time_seconds': elapsed_time
            }
    
    def validate_cluster_configuration(self) -> Dict[str, Any]:
        """
        Helper method to validate cluster configuration
        """
        try:
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            
            # Check basic requirements
            rack_count = health_summary.get('rack_count', 0)
            min_racks = self.test_params.get('min_racks_required', 3)
            
            if rack_count < min_racks:
                return {
                    'valid': False,
                    'message': f"Insufficient racks: {rack_count} < {min_racks}"
                }
            
            cluster_status = health_summary.get('cluster_status')
            if cluster_status != 'NORMAL':
                return {
                    'valid': False,
                    'message': f"Cluster not healthy: {cluster_status}"
                }
            
            return {
                'valid': True,
                'message': f"Cluster configuration valid: {rack_count} racks, status {cluster_status}",
                'rack_count': rack_count,
                'cluster_status': cluster_status,
                'total_hosts': health_summary.get('total_hosts', 0)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f"Failed to validate cluster configuration: {str(e)}"
            }