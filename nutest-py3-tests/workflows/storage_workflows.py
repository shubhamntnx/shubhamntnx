"""
Storage-related workflows
"""

import time
import logging
from typing import Dict, Any, Optional, List
from nutest_py3.framework.entities import StorageEntity


class StorageWorkflows:
    """
    High-level storage workflows built on top of StorageEntity
    """
    
    def __init__(self, session):
        self.session = session
        self.storage_entity = StorageEntity(session)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_test_container_workflow(self, name: str, replication_factor: int = 2,
                                     strict_rack_awareness: bool = False, **kwargs) -> Optional[str]:
        """
        Complete workflow to create a test storage container
        """
        self.logger.info(f"Creating test container: {name}")
        
        try:
            # Check if container already exists
            existing = self.storage_entity.get_container_by_name(name)
            if existing:
                self.logger.warning(f"Container {name} already exists")
                return existing.get('containerUuid')
            
            # Create the container
            response = self.storage_entity.create_container(
                name=name,
                replication_factor=replication_factor,
                strict_rack_awareness=strict_rack_awareness,
                **kwargs
            )
            
            container_uuid = response.get('containerUuid')
            if container_uuid:
                self.logger.info(f"Successfully created container {name}: {container_uuid}")
                
                # Wait for container to be ready
                if self._wait_for_container_ready(name):
                    return container_uuid
                else:
                    self.logger.warning(f"Container {name} may not be fully ready")
                    return container_uuid
            else:
                self.logger.error(f"Failed to get container UUID from response: {response}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create container {name}: {str(e)}")
            return None
    
    def _wait_for_container_ready(self, container_name: str, timeout_seconds: int = 300) -> bool:
        """Wait for container to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                container = self.storage_entity.get_container_by_name(container_name)
                if container:
                    # Check container status
                    status = container.get('status', 'UNKNOWN')
                    if status in ['NORMAL', 'ONLINE']:
                        return True
                    
                    self.logger.debug(f"Container {container_name} status: {status}")
                
                time.sleep(10)
                
            except Exception as e:
                self.logger.debug(f"Error checking container status: {str(e)}")
                time.sleep(10)
        
        self.logger.warning(f"Timeout waiting for container {container_name} to be ready")
        return False
    
    def cleanup_test_containers_workflow(self, container_names: List[str]) -> int:
        """
        Complete workflow to clean up test containers
        """
        self.logger.info(f"Cleaning up {len(container_names)} test containers")
        
        cleaned_count = 0
        
        for name in container_names:
            try:
                container = self.storage_entity.get_container_by_name(name)
                if container:
                    container_uuid = container.get('containerUuid')
                    if container_uuid and self.storage_entity.delete_container(container_uuid):
                        cleaned_count += 1
                        self.logger.info(f"Successfully cleaned up container: {name}")
                    else:
                        self.logger.warning(f"Failed to clean up container: {name}")
                else:
                    self.logger.debug(f"Container not found (may already be cleaned): {name}")
                    
            except Exception as e:
                self.logger.warning(f"Error cleaning up container {name}: {str(e)}")
        
        self.logger.info(f"Cleaned up {cleaned_count}/{len(container_names)} containers")
        return cleaned_count
    
    def validate_container_placement_workflow(self, container_name: str, 
                                            expected_strict_mode: bool) -> tuple:
        """
        Complete workflow to validate container placement
        """
        self.logger.info(f"Validating placement for container: {container_name}")
        
        try:
            is_valid, message = self.storage_entity.validate_container_placement(
                container_name, expected_strict_mode
            )
            
            if is_valid:
                self.logger.info(f"Container placement validation passed: {message}")
            else:
                self.logger.warning(f"Container placement validation failed: {message}")
            
            return is_valid, message
            
        except Exception as e:
            error_msg = f"Container placement validation error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def validate_rpp_updates_workflow(self, expected_strict_mode: bool, 
                                    timeout_seconds: int = 300) -> bool:
        """
        Complete workflow to validate RPP updates
        """
        self.logger.info(f"Validating RPP updates (strict mode: {expected_strict_mode})")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                policies = self.storage_entity.get_replication_policies()
                
                # Check if policies reflect the expected mode
                all_correct = True
                for policy in policies.get('entities', []):
                    policy_config = policy.get('spec', {}).get('resources', {})
                    strict_ra = policy_config.get('rack_awareness_strict', False)
                    
                    if strict_ra != expected_strict_mode:
                        all_correct = False
                        break
                
                if all_correct:
                    self.logger.info("RPP updates validation passed")
                    return True
                
                self.logger.debug("Waiting for RPP updates...")
                time.sleep(10)
                
            except Exception as e:
                self.logger.debug(f"Error checking RPP updates: {str(e)}")
                time.sleep(10)
        
        self.logger.warning("Timeout waiting for RPP updates")
        return False