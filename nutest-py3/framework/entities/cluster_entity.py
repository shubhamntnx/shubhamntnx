"""
Cluster Entity for Nutanix Framework
"""

import time
from typing import Dict, Any, Optional, List
from .base_entity import BaseEntity


class ClusterEntity(BaseEntity):
    """
    Cluster entity operations
    """
    
    @property
    def entity_type(self) -> str:
        return "cluster"
    
    def get_entity_info(self, entity_uuid: str = None) -> Dict[str, Any]:
        """Get cluster information"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get('/PrismGateway/services/rest/v2.0/cluster/')
        return response
    
    def list_entities(self, **kwargs) -> Dict[str, Any]:
        """List clusters (usually just one)"""
        return self.get_entity_info()
    
    def get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster configuration via v3 API"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get('/api/nutanix/v3/clusters')
        return response
    
    def update_cluster_config(self, cluster_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Update cluster configuration"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        cluster_config = self.get_cluster_config()
        cluster_uuid = cluster_config['entities'][0]['metadata']['uuid']
        
        endpoint = f'/api/nutanix/v3/clusters/{cluster_uuid}'
        response = self.session.put(endpoint, json=cluster_spec)
        return response
    
    def get_rack_awareness_status(self) -> bool:
        """Get current rack awareness status"""
        try:
            cluster_config = self.get_cluster_config()
            entities = cluster_config.get('entities', [])
            
            if entities:
                config = entities[0].get('spec', {}).get('resources', {}).get('config', {})
                return config.get('rack_awareness_strict', False)
        except Exception as e:
            self.logger.warning(f"Failed to get rack awareness status: {str(e)}")
        
        return False
    
    def set_rack_awareness_strict(self, strict_mode: bool) -> bool:
        """Enable/disable strict rack awareness"""
        try:
            cluster_config = self.get_cluster_config()
            entities = cluster_config.get('entities', [])
            
            if not entities:
                return False
            
            cluster_spec = entities[0]['spec'].copy()
            
            # Ensure config structure exists
            if 'resources' not in cluster_spec:
                cluster_spec['resources'] = {}
            if 'config' not in cluster_spec['resources']:
                cluster_spec['resources']['config'] = {}
            
            # Update rack awareness setting
            cluster_spec['resources']['config']['rack_awareness_strict'] = strict_mode
            
            # Apply the update
            update_data = {
                'spec': cluster_spec,
                'metadata': entities[0]['metadata']
            }
            
            self.update_cluster_config(update_data)
            
            # Wait for change to take effect
            return self._wait_for_rack_awareness_state(strict_mode)
            
        except Exception as e:
            self.logger.error(f"Failed to set rack awareness: {str(e)}")
            return False
    
    def _wait_for_rack_awareness_state(self, expected_state: bool, timeout_seconds: int = 300) -> bool:
        """Wait for rack awareness to reach expected state"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            current_state = self.get_rack_awareness_status()
            if current_state == expected_state:
                self.logger.info(f"Rack awareness state reached: {expected_state}")
                return True
            
            time.sleep(10)
        
        self.logger.warning("Timeout waiting for rack awareness state change")
        return False
    
    def get_fault_tolerance_status(self) -> Dict[str, Any]:
        """Get fault tolerance status"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get('/PrismGateway/services/rest/v2.0/cluster/domain_fault_tolerance_status')
        return response
    
    def get_ft_level(self) -> int:
        """Get current fault tolerance level"""
        try:
            cluster_info = self.get_entity_info()
            return cluster_info.get('faultToleranceLevel', 1)
        except Exception as e:
            self.logger.error(f"Failed to get FT level: {str(e)}")
            return 1
    
    def set_ft_level(self, target_ft: int) -> bool:
        """Set fault tolerance level"""
        try:
            cluster_config = self.get_cluster_config()
            cluster_spec = cluster_config['entities'][0]['spec'].copy()
            
            # Update FT level
            if 'resources' not in cluster_spec:
                cluster_spec['resources'] = {}
            if 'config' not in cluster_spec['resources']:
                cluster_spec['resources']['config'] = {}
            
            cluster_spec['resources']['config']['fault_tolerance_level'] = target_ft
            
            # Apply the update
            update_data = {
                'spec': cluster_spec,
                'metadata': cluster_config['entities'][0]['metadata']
            }
            
            self.update_cluster_config(update_data)
            
            # Wait for the upgrade to complete
            return self._wait_for_ft_level(target_ft)
            
        except Exception as e:
            self.logger.error(f"Failed to set FT level: {str(e)}")
            return False
    
    def _wait_for_ft_level(self, target_ft: int, timeout_seconds: int = 1800) -> bool:
        """Wait for FT level change to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            current_ft = self.get_ft_level()
            if current_ft == target_ft:
                self.logger.info(f"FT level reached: {target_ft}")
                return True
            
            self.logger.debug(f"Current FT: {current_ft}, target: {target_ft}")
            time.sleep(30)
        
        self.logger.warning("Timeout waiting for FT level change")
        return False