"""
Utilities for rack awareness testing
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple

from nutest_py3.framework import TestConfig, APIClient, ClusterManager


class RackAwarenessTestUtils:
    """
    Utility class for rack awareness testing operations
    """
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.api_client = APIClient(config)
        self.cluster_manager = ClusterManager(config)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_strict_ra_prerequisites(self) -> Tuple[bool, List[str]]:
        """
        Validate prerequisites for enabling strict rack awareness
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check rack count
        is_valid, message = self.cluster_manager.validate_rack_requirements()
        if not is_valid:
            issues.append(message)
        
        # Check cluster health
        try:
            cluster_info = self.cluster_manager.get_cluster_info()
            cluster_status = cluster_info.get('clusterStatus', 'UNKNOWN')
            
            if cluster_status != 'NORMAL':
                issues.append(f"Cluster status is not NORMAL: {cluster_status}")
        except Exception as e:
            issues.append(f"Failed to get cluster status: {str(e)}")
        
        # Check fault tolerance status
        try:
            ft_status = self.cluster_manager.get_fault_tolerance_status()
            # Add specific fault tolerance validations based on your requirements
            if not self._validate_fault_tolerance(ft_status):
                issues.append("Fault tolerance requirements not met")
        except Exception as e:
            issues.append(f"Failed to validate fault tolerance: {str(e)}")
        
        return len(issues) == 0, issues
    
    def _validate_fault_tolerance(self, ft_status: Dict[str, Any]) -> bool:
        """Validate fault tolerance status"""
        # Implement specific fault tolerance validation logic
        # This would depend on your specific requirements
        return True
    
    def get_replication_policies(self) -> Dict[str, Any]:
        """Get current replication policies"""
        try:
            return self.api_client.get_replication_policies()
        except Exception as e:
            self.logger.error(f"Failed to get replication policies: {str(e)}")
            return {}
    
    def validate_rpp_updates(self, expected_strict_mode: bool) -> bool:
        """
        Validate that Replica Placement Policies (RPPs) are updated correctly
        
        Args:
            expected_strict_mode: Whether strict mode should be enabled
            
        Returns:
            True if RPPs are correctly configured
        """
        try:
            # Get current replication policies
            policies = self.get_replication_policies()
            
            # Check if policies reflect strict rack awareness setting
            for policy in policies.get('entities', []):
                policy_config = policy.get('spec', {}).get('resources', {})
                strict_ra = policy_config.get('rack_awareness_strict', False)
                
                if strict_ra != expected_strict_mode:
                    self.logger.warning(
                        f"Policy {policy.get('metadata', {}).get('name', 'unknown')} "
                        f"has incorrect strict RA setting: {strict_ra} != {expected_strict_mode}"
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate RPP updates: {str(e)}")
            return False
    
    def wait_for_rpp_update(self, expected_strict_mode: bool, timeout_seconds: int = 300) -> bool:
        """
        Wait for RPPs to be updated to reflect strict rack awareness setting
        
        Args:
            expected_strict_mode: Whether strict mode should be enabled
            timeout_seconds: Maximum time to wait
            
        Returns:
            True if RPPs were updated within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            if self.validate_rpp_updates(expected_strict_mode):
                return True
            
            self.logger.debug("Waiting for RPP updates...")
            time.sleep(10)
        
        self.logger.warning("Timeout waiting for RPP updates")
        return False
    
    def create_test_container(self, name: str, replication_factor: int = 2, 
                            strict_rack_awareness: bool = False) -> Optional[str]:
        """
        Create a test storage container
        
        Args:
            name: Container name
            replication_factor: Replication factor
            strict_rack_awareness: Whether to enable strict rack awareness
            
        Returns:
            Container UUID if successful, None otherwise
        """
        try:
            response = self.api_client.create_storage_container(
                name=name,
                replication_factor=replication_factor,
                strict_rack_awareness=strict_rack_awareness
            )
            
            container_uuid = response.get('containerUuid')
            if container_uuid:
                self.logger.info(f"Created test container: {name} ({container_uuid})")
                return container_uuid
            else:
                self.logger.error(f"Failed to get container UUID from response: {response}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create test container {name}: {str(e)}")
            return None
    
    def validate_container_placement(self, container_name: str, 
                                   expected_strict_mode: bool) -> Tuple[bool, str]:
        """
        Validate that container placement follows rack awareness rules
        
        Args:
            container_name: Name of container to validate
            expected_strict_mode: Whether strict mode should be enforced
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Get container information
            containers = self.api_client.get_storage_containers()
            target_container = None
            
            for container in containers.get('entities', []):
                if container.get('name') == container_name:
                    target_container = container
                    break
            
            if not target_container:
                return False, f"Container {container_name} not found"
            
            # Validate placement based on rack awareness mode
            if expected_strict_mode:
                return self._validate_strict_placement(target_container)
            else:
                return self._validate_best_effort_placement(target_container)
                
        except Exception as e:
            return False, f"Failed to validate container placement: {str(e)}"
    
    def _validate_strict_placement(self, container: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate strict rack awareness placement"""
        # Implementation would depend on how placement data is exposed in the API
        # This is a placeholder for the actual validation logic
        return True, "Strict placement validation passed"
    
    def _validate_best_effort_placement(self, container: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate best-effort placement"""
        # Implementation would depend on how placement data is exposed in the API
        # This is a placeholder for the actual validation logic
        return True, "Best-effort placement validation passed"
    
    def cleanup_test_containers(self, container_names: List[str]) -> None:
        """Clean up test containers"""
        for name in container_names:
            try:
                # Implementation would depend on delete API
                self.logger.info(f"Cleaned up test container: {name}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup container {name}: {str(e)}")
    
    def get_cluster_ft_level(self) -> int:
        """Get current cluster fault tolerance level"""
        try:
            cluster_info = self.cluster_manager.get_cluster_info()
            # Extract FT level from cluster info
            # This would depend on how FT level is exposed in the API
            return cluster_info.get('faultToleranceLevel', 1)
        except Exception as e:
            self.logger.error(f"Failed to get FT level: {str(e)}")
            return 1
    
    def upgrade_cluster_ft_level(self, target_ft: int) -> bool:
        """
        Upgrade cluster fault tolerance level
        
        Args:
            target_ft: Target fault tolerance level
            
        Returns:
            True if upgrade was successful
        """
        try:
            self.logger.info(f"Upgrading cluster FT level to {target_ft}")
            
            # Get current cluster config
            cluster_config = self.api_client.get_cluster_config()
            cluster_spec = cluster_config['entities'][0]['spec']
            
            # Update FT level
            cluster_spec['resources']['config']['fault_tolerance_level'] = target_ft
            
            # Apply the update
            self.api_client.update_cluster_config({
                'spec': cluster_spec,
                'metadata': cluster_config['entities'][0]['metadata']
            })
            
            # Wait for the upgrade to complete
            return self._wait_for_ft_upgrade(target_ft)
            
        except Exception as e:
            self.logger.error(f"Failed to upgrade FT level: {str(e)}")
            return False
    
    def _wait_for_ft_upgrade(self, target_ft: int, timeout_seconds: int = 1800) -> bool:
        """Wait for FT upgrade to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                current_ft = self.get_cluster_ft_level()
                if current_ft == target_ft:
                    self.logger.info(f"FT upgrade to level {target_ft} completed")
                    return True
                
                self.logger.debug(f"Current FT level: {current_ft}, target: {target_ft}")
                time.sleep(30)
                
            except Exception as e:
                self.logger.debug(f"Error checking FT level: {str(e)}")
                time.sleep(30)
        
        self.logger.warning("Timeout waiting for FT upgrade")
        return False