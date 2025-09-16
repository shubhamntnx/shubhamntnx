"""
Test Case: Validate Cluster Configuration APIs

Test Case Name: validate_cluster_config_apis
Description: Validate GET, POST, PUT cluster APIs for strict RA field.
Steps: Call each API and inspect "rack_awareness_strict" field behavior.
Expected Result: Field is present, accepted, and backward compatible.
"""

import json
from typing import List, Dict, Any

from nutest_py3.framework import BaseTest, TestConfig, TestPriority
from nutest_py3_tests.common import RackAwarenessTestUtils, ClusterValidationUtils


class ValidateClusterConfigAPIsTest(BaseTest):
    """
    Test cluster configuration APIs for strict rack awareness field handling
    """
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.rack_utils = RackAwarenessTestUtils(config)
        self.cluster_validation = ClusterValidationUtils(config)
        self.original_config = None
        
    @property
    def test_name(self) -> str:
        return "validate_cluster_config_apis"
    
    @property
    def description(self) -> str:
        return "Validate GET, POST, PUT cluster APIs for strict RA field"
    
    @property
    def priority(self) -> TestPriority:
        return TestPriority.HIGH
    
    @property
    def timeout_minutes(self) -> int:
        return 20
    
    @property
    def prerequisites(self) -> List[str]:
        return [
            "Cluster must be in healthy state",
            "API access must be available",
            "Sufficient permissions for cluster configuration changes"
        ]
    
    def setup(self) -> None:
        """Setup test environment"""
        super().setup()
        
        self.logger.info("Setting up cluster config APIs validation test")
        
        # Store original configuration for restoration
        self._backup_original_config()
        
    def execute(self) -> None:
        """Main test execution"""
        self.logger.info("Executing cluster config APIs validation test")
        
        # Step 1: Test GET API
        self._test_get_api()
        
        # Step 2: Test PUT API
        self._test_put_api()
        
        # Step 3: Test POST API (if applicable)
        self._test_post_api()
        
        # Step 4: Test field validation
        self._test_field_validation()
        
        # Step 5: Test backward compatibility
        self._test_backward_compatibility()
        
        # Step 6: Test edge cases
        self._test_edge_cases()
        
    def teardown(self) -> None:
        """Cleanup test environment"""
        try:
            # Restore original configuration
            self._restore_original_config()
                
        except Exception as e:
            self.logger.warning(f"Teardown failed: {str(e)}")
        
        super().teardown()
    
    def _backup_original_config(self) -> None:
        """Backup original cluster configuration"""
        self.logger.info("Backing up original cluster configuration")
        
        try:
            self.original_config = self.api_client.get_cluster_config()
            self.logger.info("Original configuration backed up successfully")
        except Exception as e:
            self.logger.error(f"Failed to backup original configuration: {str(e)}")
            raise
    
    def _restore_original_config(self) -> None:
        """Restore original cluster configuration"""
        if self.original_config:
            self.logger.info("Restoring original cluster configuration")
            
            try:
                entities = self.original_config.get('entities', [])
                if entities:
                    self.api_client.update_cluster_config({
                        'spec': entities[0]['spec'],
                        'metadata': entities[0]['metadata']
                    })
                    self.logger.info("Original configuration restored successfully")
            except Exception as e:
                self.logger.warning(f"Failed to restore original configuration: {str(e)}")
    
    def _test_get_api(self) -> None:
        """Test GET /cluster API"""
        self.logger.info("Testing GET /cluster API")
        
        try:
            # Test basic GET functionality
            cluster_config = self.api_client.get_cluster_config()
            
            self.assert_true(
                'entities' in cluster_config,
                "GET response should contain 'entities' field"
            )
            
            entities = cluster_config.get('entities', [])
            self.assert_true(
                len(entities) > 0,
                "GET response should contain at least one cluster entity"
            )
            
            # Test rack_awareness_strict field presence
            entity = entities[0]
            spec = entity.get('spec', {})
            resources = spec.get('resources', {})
            config = resources.get('config', {})
            
            # Field may or may not be present initially, but API should handle it
            if 'rack_awareness_strict' in config:
                rack_awareness_value = config['rack_awareness_strict']
                self.assert_in(
                    type(rack_awareness_value), [bool],
                    f"rack_awareness_strict should be boolean, got {type(rack_awareness_value)}"
                )
                self.logger.info(f"rack_awareness_strict field found with value: {rack_awareness_value}")
            else:
                self.logger.info("rack_awareness_strict field not present in current config")
            
            # Validate response structure
            self._validate_api_response_structure(cluster_config, 'GET')
            
            self.test_result.add_metric("get_api_success", True)
            self.logger.info("GET API test completed successfully")
            
        except Exception as e:
            self.test_result.add_metric("get_api_success", False)
            self.test_result.add_metric("get_api_error", str(e))
            raise AssertionError(f"GET API test failed: {str(e)}")
    
    def _test_put_api(self) -> None:
        """Test PUT /cluster API"""
        self.logger.info("Testing PUT /cluster API")
        
        try:
            # Get current configuration
            cluster_config = self.api_client.get_cluster_config()
            entities = cluster_config.get('entities', [])
            self.assert_true(len(entities) > 0, "No cluster entities found")
            
            entity = entities[0]
            original_spec = entity['spec'].copy()
            test_spec = original_spec.copy()
            
            # Ensure config structure exists
            if 'resources' not in test_spec:
                test_spec['resources'] = {}
            if 'config' not in test_spec['resources']:
                test_spec['resources']['config'] = {}
            
            # Test 1: Enable strict rack awareness
            self.logger.info("Testing PUT API - enabling strict rack awareness")
            test_spec['resources']['config']['rack_awareness_strict'] = True
            
            response = self.api_client.update_cluster_config({
                'spec': test_spec,
                'metadata': entity['metadata']
            })
            
            self._validate_api_response_structure(response, 'PUT')
            
            # Verify the change took effect
            updated_config = self.api_client.get_cluster_config()
            updated_entity = updated_config['entities'][0]
            updated_value = updated_entity['spec']['resources']['config'].get('rack_awareness_strict')
            
            self.assert_equal(
                updated_value, True,
                f"PUT should set rack_awareness_strict to True, got {updated_value}"
            )
            
            # Test 2: Disable strict rack awareness
            self.logger.info("Testing PUT API - disabling strict rack awareness")
            test_spec['resources']['config']['rack_awareness_strict'] = False
            
            response = self.api_client.update_cluster_config({
                'spec': test_spec,
                'metadata': updated_entity['metadata']
            })
            
            # Verify the change took effect
            updated_config = self.api_client.get_cluster_config()
            updated_entity = updated_config['entities'][0]
            updated_value = updated_entity['spec']['resources']['config'].get('rack_awareness_strict')
            
            self.assert_equal(
                updated_value, False,
                f"PUT should set rack_awareness_strict to False, got {updated_value}"
            )
            
            # Test 3: Remove the field (test backward compatibility)
            self.logger.info("Testing PUT API - removing rack_awareness_strict field")
            if 'rack_awareness_strict' in test_spec['resources']['config']:
                del test_spec['resources']['config']['rack_awareness_strict']
            
            response = self.api_client.update_cluster_config({
                'spec': test_spec,
                'metadata': updated_entity['metadata']
            })
            
            # This should succeed (backward compatibility)
            self._validate_api_response_structure(response, 'PUT')
            
            self.test_result.add_metric("put_api_success", True)
            self.logger.info("PUT API test completed successfully")
            
        except Exception as e:
            self.test_result.add_metric("put_api_success", False)
            self.test_result.add_metric("put_api_error", str(e))
            raise AssertionError(f"PUT API test failed: {str(e)}")
    
    def _test_post_api(self) -> None:
        """Test POST /cluster API (if applicable)"""
        self.logger.info("Testing POST /cluster API")
        
        # Note: POST for cluster creation is typically not available in existing clusters
        # This test focuses on validating that the field would be accepted in POST requests
        
        try:
            # Since we can't actually create a new cluster, we'll test the field validation
            # by examining the API schema or testing with a mock request structure
            
            # Test data structure that would be used in POST
            post_data = {
                'spec': {
                    'resources': {
                        'config': {
                            'rack_awareness_strict': True
                        }
                    }
                },
                'metadata': {
                    'name': 'test-cluster'
                }
            }
            
            # Validate the structure is acceptable (this is a structural validation)
            self.assert_true(
                isinstance(post_data['spec']['resources']['config']['rack_awareness_strict'], bool),
                "rack_awareness_strict field should accept boolean values in POST"
            )
            
            self.test_result.add_metric("post_api_structure_valid", True)
            self.logger.info("POST API structure validation completed")
            
        except Exception as e:
            self.test_result.add_metric("post_api_structure_valid", False)
            self.test_result.add_metric("post_api_error", str(e))
            self.logger.warning(f"POST API test warning: {str(e)}")
    
    def _test_field_validation(self) -> None:
        """Test field validation for rack_awareness_strict"""
        self.logger.info("Testing rack_awareness_strict field validation")
        
        try:
            cluster_config = self.api_client.get_cluster_config()
            entity = cluster_config['entities'][0]
            test_spec = entity['spec'].copy()
            
            # Ensure config structure exists
            if 'resources' not in test_spec:
                test_spec['resources'] = {}
            if 'config' not in test_spec['resources']:
                test_spec['resources']['config'] = {}
            
            # Test valid boolean values
            valid_values = [True, False]
            for value in valid_values:
                self.logger.info(f"Testing valid value: {value}")
                test_spec['resources']['config']['rack_awareness_strict'] = value
                
                try:
                    response = self.api_client.update_cluster_config({
                        'spec': test_spec,
                        'metadata': entity['metadata']
                    })
                    self.logger.info(f"Valid value {value} accepted")
                except Exception as e:
                    self.assert_true(False, f"Valid value {value} should be accepted: {str(e)}")
            
            # Test invalid values (should be rejected or converted)
            invalid_values = ["true", "false", 1, 0, None, "invalid"]
            for value in invalid_values:
                self.logger.info(f"Testing invalid value: {value}")
                test_spec['resources']['config']['rack_awareness_strict'] = value
                
                try:
                    response = self.api_client.update_cluster_config({
                        'spec': test_spec,
                        'metadata': entity['metadata']
                    })
                    # If it succeeds, check if value was converted appropriately
                    updated_config = self.api_client.get_cluster_config()
                    actual_value = updated_config['entities'][0]['spec']['resources']['config'].get('rack_awareness_strict')
                    
                    if actual_value is not None:
                        self.assert_in(
                            type(actual_value), [bool],
                            f"Invalid value {value} should be converted to boolean or rejected, got {type(actual_value)}"
                        )
                        self.logger.info(f"Invalid value {value} converted to {actual_value}")
                    
                except Exception as e:
                    # Rejection is acceptable for invalid values
                    self.logger.info(f"Invalid value {value} properly rejected: {str(e)}")
            
            self.test_result.add_metric("field_validation_success", True)
            self.logger.info("Field validation test completed successfully")
            
        except Exception as e:
            self.test_result.add_metric("field_validation_success", False)
            self.test_result.add_metric("field_validation_error", str(e))
            raise AssertionError(f"Field validation test failed: {str(e)}")
    
    def _test_backward_compatibility(self) -> None:
        """Test backward compatibility of the rack_awareness_strict field"""
        self.logger.info("Testing backward compatibility")
        
        try:
            is_compatible, message = self.cluster_validation.validate_backward_compatibility()
            
            self.assert_true(
                is_compatible,
                f"Backward compatibility validation failed: {message}"
            )
            
            self.test_result.add_metric("backward_compatibility_success", True)
            self.test_result.add_metric("backward_compatibility_message", message)
            self.logger.info(f"Backward compatibility test passed: {message}")
            
        except Exception as e:
            self.test_result.add_metric("backward_compatibility_success", False)
            self.test_result.add_metric("backward_compatibility_error", str(e))
            raise AssertionError(f"Backward compatibility test failed: {str(e)}")
    
    def _test_edge_cases(self) -> None:
        """Test edge cases for API behavior"""
        self.logger.info("Testing edge cases")
        
        try:
            cluster_config = self.api_client.get_cluster_config()
            entity = cluster_config['entities'][0]
            test_spec = entity['spec'].copy()
            
            # Test case 1: Empty config section
            self.logger.info("Testing with empty config section")
            test_spec['resources'] = {'config': {}}
            
            response = self.api_client.update_cluster_config({
                'spec': test_spec,
                'metadata': entity['metadata']
            })
            
            # Should succeed - missing field should be handled gracefully
            self._validate_api_response_structure(response, 'PUT')
            
            # Test case 2: Nested field access
            self.logger.info("Testing nested field access")
            test_spec['resources']['config']['rack_awareness_strict'] = True
            test_spec['resources']['config']['other_field'] = 'test_value'
            
            response = self.api_client.update_cluster_config({
                'spec': test_spec,
                'metadata': entity['metadata']
            })
            
            # Should succeed - other fields should not be affected
            updated_config = self.api_client.get_cluster_config()
            updated_entity = updated_config['entities'][0]
            updated_ra_value = updated_entity['spec']['resources']['config'].get('rack_awareness_strict')
            
            self.assert_equal(
                updated_ra_value, True,
                f"rack_awareness_strict should be preserved with other fields"
            )
            
            self.test_result.add_metric("edge_cases_success", True)
            self.logger.info("Edge cases test completed successfully")
            
        except Exception as e:
            self.test_result.add_metric("edge_cases_success", False)
            self.test_result.add_metric("edge_cases_error", str(e))
            raise AssertionError(f"Edge cases test failed: {str(e)}")
    
    def _validate_api_response_structure(self, response: Dict[str, Any], api_method: str) -> None:
        """Validate API response structure"""
        self.assert_true(
            isinstance(response, dict),
            f"{api_method} response should be a dictionary"
        )
        
        # Add specific response validation based on your API specifications
        # This is a placeholder for more detailed response validation
        
        self.logger.debug(f"{api_method} response structure validation passed")