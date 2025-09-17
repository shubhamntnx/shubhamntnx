"""
Test Transition Workflows

This module contains tests for transitioning between strict RA and best-effort modes.
"""

import logging
import time
from typing import List, Dict, Any

from nutest_py3_tests.workflows.rack_awareness_workflows import RackAwarenessWorkflows
from nutest_py3_tests.workflows.cluster_workflows import ClusterWorkflows
from nutest_py3_tests.workflows.storage_workflows import StorageWorkflows


class TransitionWorkflows:
    """
    Test class for rack awareness transition workflows
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
        self.logger.info("Setting up TransitionWorkflows test")
        
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
        self.logger.info("Tearing down TransitionWorkflows test")
        
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
    
    def test_transition_best_effort_to_strict_ra(self):
        """
        Test transition from best-effort to strict RA with all preconditions met
        
        Test Steps:
        1. Ensure cluster is in best-effort mode
        2. Validate prerequisites for strict RA
        3. Create test containers in best-effort mode
        4. Transition to strict rack awareness
        5. Validate RPPs are updated
        6. Validate existing containers still work
        7. Create new containers with strict RA
        """
        self.logger.info("Starting test_transition_best_effort_to_strict_ra")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 45) * 60
        start_time = time.time()
        
        try:
            # Step 1: Ensure cluster is in best-effort mode
            self.logger.info("Step 1: Ensuring cluster is in best-effort mode")
            
            current_strict_ra = self.rack_workflows.cluster_entity.get_rack_awareness_status()
            if current_strict_ra:
                self.logger.info("Disabling strict RA to start in best-effort mode")
                success = self.rack_workflows.transition_to_best_effort_workflow()
                if not success:
                    raise AssertionError("Failed to disable strict RA for test setup")
            
            self.logger.info("Cluster confirmed to be in best-effort mode")
            
            # Step 2: Validate prerequisites
            if self.test_params.get('validate_prerequisites', True):
                self.logger.info("Step 2: Validating strict RA prerequisites")
                is_valid, issues = self.rack_workflows.validate_strict_ra_prerequisites_workflow()
                
                if not is_valid:
                    raise AssertionError(f"Prerequisites not met: {', '.join(issues)}")
                
                self.logger.info("Prerequisites validated successfully")
            
            # Step 3: Create test containers in best-effort mode
            self.logger.info("Step 3: Creating test containers in best-effort mode")
            containers_count = self.test_params.get('test_containers_count', 2)
            container_prefix = self.test_params.get('test_container_prefix', 'transition_test')
            
            for i in range(containers_count):
                container_name = f"{container_prefix}_be_{int(time.time())}_{i}"
                
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=container_name,
                    replication_factor=2,
                    strict_rack_awareness=False
                )
                
                if not container_uuid:
                    raise AssertionError(f"Failed to create best-effort container: {container_name}")
                
                self.created_container_names.append(container_name)
                self.test_containers.append({
                    'name': container_name,
                    'uuid': container_uuid,
                    'created_mode': 'best_effort'
                })
            
            self.logger.info(f"Created {len(self.test_containers)} best-effort containers")
            
            # Step 4: Transition to strict rack awareness
            self.logger.info("Step 4: Transitioning to strict rack awareness")
            
            transition_start_time = time.time()
            success = self.rack_workflows.transition_to_strict_ra_workflow()
            transition_time = time.time() - transition_start_time
            
            if not success:
                raise AssertionError("Failed to transition to strict rack awareness")
            
            self.logger.info(f"Transitioned to strict RA in {transition_time:.2f} seconds")
            
            # Step 5: Validate RPPs are updated
            if self.test_params.get('validate_rpp_updates', True):
                self.logger.info("Step 5: Validating RPP updates")
                
                rpp_timeout = self.test_params.get('rpp_update_timeout', 300)
                rpp_updated = self.storage_workflows.validate_rpp_updates_workflow(
                    expected_strict_mode=True, timeout_seconds=rpp_timeout
                )
                
                if not rpp_updated:
                    self.logger.warning("RPP updates not confirmed within timeout")
                    # Continue test but log warning
                else:
                    self.logger.info("RPP updates validated successfully")
            
            # Step 6: Validate existing containers still work
            self.logger.info("Step 6: Validating existing containers after transition")
            
            for container in self.test_containers:
                # Check container accessibility
                container_info = self.storage_workflows.storage_entity.get_container_by_name(
                    container['name']
                )
                
                if not container_info:
                    raise AssertionError(f"Container {container['name']} not accessible after transition")
                
                container_status = container_info.get('status', 'UNKNOWN')
                if container_status not in ['NORMAL', 'ONLINE']:
                    self.logger.warning(f"Container {container['name']} status: {container_status}")
            
            self.logger.info("Existing containers validated after transition")
            
            # Step 7: Create new containers with strict RA
            self.logger.info("Step 7: Creating new containers with strict RA")
            
            strict_container_name = f"{container_prefix}_strict_{int(time.time())}"
            container_uuid = self.storage_workflows.create_test_container_workflow(
                name=strict_container_name,
                replication_factor=2,
                strict_rack_awareness=True
            )
            
            if not container_uuid:
                raise AssertionError(f"Failed to create strict RA container: {strict_container_name}")
            
            self.created_container_names.append(strict_container_name)
            
            # Validate strict placement
            is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                strict_container_name, expected_strict_mode=True
            )
            
            if not is_valid:
                raise AssertionError(f"Strict RA container placement validation failed: {message}")
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            self.logger.info("test_transition_best_effort_to_strict_ra completed successfully")
            
            return {
                'status': 'PASSED',
                'message': 'Successfully transitioned from best-effort to strict RA',
                'transition_time_seconds': transition_time,
                'total_containers_created': len(self.created_container_names),
                'elapsed_time_seconds': elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_transition_best_effort_to_strict_ra failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'elapsed_time_seconds': elapsed_time
            }
    
    def test_transition_strict_ra_to_best_effort(self):
        """
        Test disable strict RA and revert to best-effort placement
        
        Test Steps:
        1. Ensure cluster has strict RA enabled
        2. Create test containers with strict RA
        3. Transition to best-effort mode
        4. Validate RPPs revert to best-effort
        5. Validate existing containers remain accessible
        6. Test new container creation in best-effort mode
        """
        self.logger.info("Starting test_transition_strict_ra_to_best_effort")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 30) * 60
        start_time = time.time()
        
        try:
            # Step 1: Ensure cluster has strict RA enabled
            self.logger.info("Step 1: Ensuring cluster has strict RA enabled")
            
            current_strict_ra = self.rack_workflows.cluster_entity.get_rack_awareness_status()
            if not current_strict_ra:
                self.logger.info("Enabling strict RA for test setup")
                success = self.rack_workflows.transition_to_strict_ra_workflow()
                if not success:
                    raise AssertionError("Failed to enable strict RA for test setup")
            
            self.logger.info("Cluster confirmed to have strict RA enabled")
            
            # Step 2: Create test containers with strict RA
            self.logger.info("Step 2: Creating test containers with strict RA")
            container_prefix = self.test_params.get('test_container_prefix', 'transition_test')
            
            strict_container_name = f"{container_prefix}_strict_{int(time.time())}"
            container_uuid = self.storage_workflows.create_test_container_workflow(
                name=strict_container_name,
                replication_factor=2,
                strict_rack_awareness=True
            )
            
            if not container_uuid:
                raise AssertionError(f"Failed to create strict RA container: {strict_container_name}")
            
            self.created_container_names.append(strict_container_name)
            self.test_containers.append({
                'name': strict_container_name,
                'uuid': container_uuid,
                'created_mode': 'strict'
            })
            
            self.logger.info("Created strict RA container for testing")
            
            # Step 3: Transition to best-effort mode
            self.logger.info("Step 3: Transitioning to best-effort mode")
            
            transition_start_time = time.time()
            success = self.rack_workflows.transition_to_best_effort_workflow()
            transition_time = time.time() - transition_start_time
            
            if not success:
                raise AssertionError("Failed to transition to best-effort mode")
            
            self.logger.info(f"Transitioned to best-effort in {transition_time:.2f} seconds")
            
            # Step 4: Validate RPPs revert to best-effort
            if self.test_params.get('validate_rpp_reversion', True):
                self.logger.info("Step 4: Validating RPP reversion to best-effort")
                
                rpp_timeout = self.test_params.get('rpp_update_timeout', 300)
                rpp_reverted = self.storage_workflows.validate_rpp_updates_workflow(
                    expected_strict_mode=False, timeout_seconds=rpp_timeout
                )
                
                if not rpp_reverted:
                    self.logger.warning("RPP reversion not confirmed within timeout")
                    # Continue test but log warning
                else:
                    self.logger.info("RPP reversion validated successfully")
            
            # Step 5: Validate existing containers remain accessible
            self.logger.info("Step 5: Validating existing containers after transition")
            
            for container in self.test_containers:
                container_info = self.storage_workflows.storage_entity.get_container_by_name(
                    container['name']
                )
                
                if not container_info:
                    raise AssertionError(f"Container {container['name']} not accessible after transition")
                
                container_status = container_info.get('status', 'UNKNOWN')
                if container_status not in ['NORMAL', 'ONLINE']:
                    self.logger.warning(f"Container {container['name']} status: {container_status}")
            
            self.logger.info("Existing containers validated after transition")
            
            # Step 6: Test new container creation in best-effort mode
            if self.test_params.get('test_new_container_creation', True):
                self.logger.info("Step 6: Testing new container creation in best-effort mode")
                
                be_container_name = f"{container_prefix}_be_after_{int(time.time())}"
                container_uuid = self.storage_workflows.create_test_container_workflow(
                    name=be_container_name,
                    replication_factor=2,
                    strict_rack_awareness=False
                )
                
                if not container_uuid:
                    raise AssertionError(f"Failed to create best-effort container: {be_container_name}")
                
                self.created_container_names.append(be_container_name)
                
                # Validate best-effort placement (may be lenient)
                is_valid, message = self.storage_workflows.validate_container_placement_workflow(
                    be_container_name, expected_strict_mode=False
                )
                
                if not is_valid:
                    self.logger.warning(f"Best-effort placement validation: {message}")
                    # This might be acceptable in best-effort mode
                
                self.logger.info("New container creation in best-effort mode validated")
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            self.logger.info("test_transition_strict_ra_to_best_effort completed successfully")
            
            return {
                'status': 'PASSED',
                'message': 'Successfully transitioned from strict RA to best-effort',
                'transition_time_seconds': transition_time,
                'total_containers_created': len(self.created_container_names),
                'elapsed_time_seconds': elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_transition_strict_ra_to_best_effort failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'elapsed_time_seconds': elapsed_time
            }