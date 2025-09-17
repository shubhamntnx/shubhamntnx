"""
Test API Validation

This module contains tests for validating cluster configuration APIs for strict rack awareness.
"""

import logging
import time
import json
from typing import List, Dict, Any

from nutest_py3_tests.workflows.rack_awareness_workflows import RackAwarenessWorkflows
from nutest_py3_tests.workflows.cluster_workflows import ClusterWorkflows


class APIValidation:
    """
    Test class for API validation of strict rack awareness functionality
    """
    
    def __init__(self, session, test_params: Dict[str, Any]):
        self.session = session
        self.test_params = test_params
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize workflows
        self.rack_workflows = RackAwarenessWorkflows(session)
        self.cluster_workflows = ClusterWorkflows(session)
        
        # Store original configuration for restoration
        self.original_config = None
    
    def setup(self):
        """Setup method called before each test"""
        self.logger.info("Setting up APIValidation test")
        
        # Store original configuration for restoration
        try:
            self.original_config = self.rack_workflows.cluster_entity.get_cluster_config()
            self.logger.info("Original cluster configuration backed up")
            
        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise
    
    def teardown(self):
        """Teardown method called after each test"""
        self.logger.info("Tearing down APIValidation test")
        
        # Restore original configuration
        if self.original_config:
            try:
                entities = self.original_config.get('entities', [])
                if entities:
                    restore_data = {
                        'spec': entities[0]['spec'],
                        'metadata': entities[0]['metadata']
                    }
                    self.rack_workflows.cluster_entity.update_cluster_config(restore_data)
                    self.logger.info("Original configuration restored")
                    
            except Exception as e:
                self.logger.warning(f"Failed to restore original configuration: {str(e)}")
    
    def test_validate_cluster_config_apis(self):
        """
        Test validate GET, POST, PUT cluster APIs for strict RA field
        
        Test Steps:
        1. Test GET API for rack_awareness_strict field presence
        2. Test PUT API with valid boolean values
        3. Test PUT API with invalid values (should be rejected/converted)
        4. Test field validation and type checking
        5. Test backward compatibility
        6. Test edge cases
        """
        self.logger.info("Starting test_validate_cluster_config_apis")
        
        test_timeout = self.test_params.get('test_timeout_minutes', 20) * 60
        start_time = time.time()
        
        api_results = {
            'get_api': {'success': False, 'error': None},
            'put_api': {'success': False, 'error': None},
            'field_validation': {'success': False, 'error': None},
            'backward_compatibility': {'success': False, 'error': None},
            'edge_cases': {'success': False, 'error': None}
        }
        
        try:
            # Step 1: Test GET API
            if self.test_params.get('test_get_api', True):
                self.logger.info("Step 1: Testing GET API")
                api_results['get_api'] = self._test_get_api()
            
            # Step 2: Test PUT API with valid values
            if self.test_params.get('test_put_api', True):
                self.logger.info("Step 2: Testing PUT API")
                api_results['put_api'] = self._test_put_api()
            
            # Step 3: Test field validation
            if self.test_params.get('test_field_validation', True):
                self.logger.info("Step 3: Testing field validation")
                api_results['field_validation'] = self._test_field_validation()
            
            # Step 4: Test backward compatibility
            if self.test_params.get('test_backward_compatibility', True):
                self.logger.info("Step 4: Testing backward compatibility")
                api_results['backward_compatibility'] = self._test_backward_compatibility()
            
            # Step 5: Test edge cases
            if self.test_params.get('test_edge_cases', True):
                self.logger.info("Step 5: Testing edge cases")
                api_results['edge_cases'] = self._test_edge_cases()
            
            # Check test timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > test_timeout:
                raise TimeoutError(f"Test exceeded timeout: {elapsed_time:.2f}s > {test_timeout}s")
            
            # Evaluate overall results
            failed_tests = [test_name for test_name, result in api_results.items() 
                          if not result.get('success', False)]
            
            if failed_tests:
                error_msg = f"API validation failed for: {', '.join(failed_tests)}"
                self.logger.error(error_msg)
                
                return {
                    'status': 'FAILED',
                    'message': error_msg,
                    'api_results': api_results,
                    'elapsed_time_seconds': elapsed_time
                }
            
            self.logger.info("test_validate_cluster_config_apis completed successfully")
            
            return {
                'status': 'PASSED',
                'message': 'All API validation tests passed successfully',
                'api_results': api_results,
                'elapsed_time_seconds': elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"test_validate_cluster_config_apis failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                'status': 'FAILED',
                'message': error_msg,
                'api_results': api_results,
                'elapsed_time_seconds': elapsed_time
            }
    
    def _test_get_api(self) -> Dict[str, Any]:
        """Test GET /cluster API"""
        try:
            cluster_config = self.rack_workflows.cluster_entity.get_cluster_config()
            
            # Validate response structure
            if 'entities' not in cluster_config:
                return {
                    'success': False,
                    'error': "GET response missing 'entities' field"
                }
            
            entities = cluster_config.get('entities', [])
            if not entities:
                return {
                    'success': False,
                    'error': "GET response contains no cluster entities"
                }
            
            # Check for rack_awareness_strict field
            entity = entities[0]
            spec = entity.get('spec', {})
            resources = spec.get('resources', {})
            config = resources.get('config', {})
            
            has_field = 'rack_awareness_strict' in config
            field_value = config.get('rack_awareness_strict')
            
            # Field may or may not be present initially
            if has_field:
                if not isinstance(field_value, bool):
                    return {
                        'success': False,
                        'error': f"rack_awareness_strict field has wrong type: {type(field_value)}"
                    }
                
                self.logger.info(f"rack_awareness_strict field found with value: {field_value}")
            else:
                self.logger.info("rack_awareness_strict field not present in current config")
            
            return {
                'success': True,
                'has_field': has_field,
                'field_value': field_value,
                'message': "GET API validation passed"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"GET API test failed: {str(e)}"
            }
    
    def _test_put_api(self) -> Dict[str, Any]:
        """Test PUT /cluster API with rack_awareness_strict field"""
        try:
            cluster_config = self.rack_workflows.cluster_entity.get_cluster_config()
            entities = cluster_config.get('entities', [])
            
            if not entities:
                return {
                    'success': False,
                    'error': "No cluster entities found for PUT test"
                }
            
            entity = entities[0]
            original_spec = entity['spec'].copy()
            
            # Test valid boolean values
            valid_values = [True, False]
            
            for value in valid_values:
                self.logger.info(f"Testing PUT with rack_awareness_strict = {value}")
                
                test_spec = original_spec.copy()
                
                # Ensure config structure exists
                if 'resources' not in test_spec:
                    test_spec['resources'] = {}
                if 'config' not in test_spec['resources']:
                    test_spec['resources']['config'] = {}
                
                test_spec['resources']['config']['rack_awareness_strict'] = value
                
                # Apply the update
                update_data = {
                    'spec': test_spec,
                    'metadata': entity['metadata']
                }
                
                self.rack_workflows.cluster_entity.update_cluster_config(update_data)
                
                # Verify the change took effect
                updated_config = self.rack_workflows.cluster_entity.get_cluster_config()
                updated_entity = updated_config['entities'][0]
                actual_value = updated_entity['spec']['resources']['config'].get('rack_awareness_strict')
                
                if actual_value != value:
                    return {
                        'success': False,
                        'error': f"PUT failed to set rack_awareness_strict to {value}, got {actual_value}"
                    }
                
                self.logger.info(f"Successfully set rack_awareness_strict to {value}")
            
            return {
                'success': True,
                'message': "PUT API validation passed for all valid values"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"PUT API test failed: {str(e)}"
            }
    
    def _test_field_validation(self) -> Dict[str, Any]:
        """Test field validation for rack_awareness_strict"""
        try:
            cluster_config = self.rack_workflows.cluster_entity.get_cluster_config()
            entity = cluster_config['entities'][0]
            
            # Test invalid values (should be rejected or converted)
            invalid_values = ["true", "false", 1, 0, None, "invalid", []]
            validation_results = []
            
            for value in invalid_values:
                self.logger.info(f"Testing invalid value: {value}")
                
                test_spec = entity['spec'].copy()
                
                # Ensure config structure exists
                if 'resources' not in test_spec:
                    test_spec['resources'] = {}
                if 'config' not in test_spec['resources']:
                    test_spec['resources']['config'] = {}
                
                test_spec['resources']['config']['rack_awareness_strict'] = value
                
                try:
                    update_data = {
                        'spec': test_spec,
                        'metadata': entity['metadata']
                    }
                    
                    self.rack_workflows.cluster_entity.update_cluster_config(update_data)
                    
                    # Check if value was converted or accepted
                    updated_config = self.rack_workflows.cluster_entity.get_cluster_config()
                    actual_value = updated_config['entities'][0]['spec']['resources']['config'].get('rack_awareness_strict')
                    
                    if actual_value is not None and not isinstance(actual_value, bool):
                        validation_results.append(f"Invalid value {value} not properly handled: got {actual_value}")
                    else:
                        self.logger.info(f"Invalid value {value} handled correctly: converted to {actual_value}")
                
                except Exception as e:
                    # Rejection is acceptable for invalid values
                    self.logger.info(f"Invalid value {value} properly rejected: {str(e)}")
            
            if validation_results:
                return {
                    'success': False,
                    'error': f"Field validation issues: {'; '.join(validation_results)}"
                }
            
            return {
                'success': True,
                'message': "Field validation passed for all test cases"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Field validation test failed: {str(e)}"
            }
    
    def _test_backward_compatibility(self) -> Dict[str, Any]:
        """Test backward compatibility of the rack_awareness_strict field"""
        try:
            cluster_config = self.rack_workflows.cluster_entity.get_cluster_config()
            entity = cluster_config['entities'][0]
            
            # Test removing the field (should not break anything)
            self.logger.info("Testing backward compatibility by removing field")
            
            test_spec = entity['spec'].copy()
            
            # Ensure config structure exists
            if 'resources' not in test_spec:
                test_spec['resources'] = {}
            if 'config' not in test_spec['resources']:
                test_spec['resources']['config'] = {}
            
            # Remove the field if it exists
            if 'rack_awareness_strict' in test_spec['resources']['config']:
                del test_spec['resources']['config']['rack_awareness_strict']
            
            # Apply the update
            update_data = {
                'spec': test_spec,
                'metadata': entity['metadata']
            }
            
            self.rack_workflows.cluster_entity.update_cluster_config(update_data)
            
            # Verify cluster remains stable
            time.sleep(10)  # Brief wait
            
            stable = self.cluster_workflows.wait_for_cluster_stable(timeout_minutes=5)
            if not stable:
                return {
                    'success': False,
                    'error': "Cluster became unstable after removing rack_awareness_strict field"
                }
            
            self.logger.info("Backward compatibility test passed")
            
            return {
                'success': True,
                'message': "Backward compatibility validated successfully"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Backward compatibility test failed: {str(e)}"
            }
    
    def _test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases for API behavior"""
        try:
            cluster_config = self.rack_workflows.cluster_entity.get_cluster_config()
            entity = cluster_config['entities'][0]
            
            # Test case 1: Empty config section
            self.logger.info("Testing edge case: empty config section")
            
            test_spec = entity['spec'].copy()
            test_spec['resources'] = {'config': {}}
            
            update_data = {
                'spec': test_spec,
                'metadata': entity['metadata']
            }
            
            self.rack_workflows.cluster_entity.update_cluster_config(update_data)
            
            # Should succeed without issues
            self.logger.info("Empty config section handled correctly")
            
            # Test case 2: Field with other config options
            self.logger.info("Testing edge case: field with other config options")
            
            test_spec['resources']['config']['rack_awareness_strict'] = True
            test_spec['resources']['config']['test_field'] = 'test_value'
            
            update_data = {
                'spec': test_spec,
                'metadata': entity['metadata']
            }
            
            self.rack_workflows.cluster_entity.update_cluster_config(update_data)
            
            # Verify both fields are preserved
            updated_config = self.rack_workflows.cluster_entity.get_cluster_config()
            updated_config_section = updated_config['entities'][0]['spec']['resources']['config']
            
            if updated_config_section.get('rack_awareness_strict') != True:
                return {
                    'success': False,
                    'error': "rack_awareness_strict field not preserved with other config options"
                }
            
            self.logger.info("Field preserved correctly with other config options")
            
            return {
                'success': True,
                'message': "All edge cases handled correctly"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Edge cases test failed: {str(e)}"
            }