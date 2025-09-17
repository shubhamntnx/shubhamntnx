"""
Storage Entity for Nutanix Framework
"""

from typing import Dict, Any, Optional, List
from .base_entity import BaseEntity


class StorageEntity(BaseEntity):
    """
    Storage entity operations (containers, vDisks, etc.)
    """
    
    @property
    def entity_type(self) -> str:
        return "storage"
    
    def get_entity_info(self, entity_uuid: str) -> Dict[str, Any]:
        """Get storage container information"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get(f'/PrismGateway/services/rest/v2.0/storage_containers/{entity_uuid}')
        return response
    
    def list_entities(self, **kwargs) -> Dict[str, Any]:
        """List all storage containers"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get('/PrismGateway/services/rest/v2.0/storage_containers/')
        return response
    
    def create_container(self, name: str, replication_factor: int = 2, 
                        strict_rack_awareness: bool = False, **kwargs) -> Dict[str, Any]:
        """Create storage container"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        container_data = {
            'name': name,
            'replicationFactor': replication_factor,
            'compressionEnabled': kwargs.get('compression_enabled', True),
            'compressionDelayInSecs': kwargs.get('compression_delay', 0),
            'fingerPrintOnWrite': kwargs.get('fingerprint_on_write', 'OFF'),
            'onDiskDedup': kwargs.get('on_disk_dedup', 'OFF')
        }
        
        if strict_rack_awareness:
            container_data['rackAwarenessStrict'] = True
        
        response = self.session.post('/PrismGateway/services/rest/v2.0/storage_containers/', 
                                   json=container_data)
        return response
    
    def delete_container(self, container_uuid: str) -> bool:
        """Delete storage container"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        try:
            self.session.delete(f'/PrismGateway/services/rest/v2.0/storage_containers/{container_uuid}')
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete container {container_uuid}: {str(e)}")
            return False
    
    def get_container_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get container by name"""
        containers = self.list_entities()
        
        for container in containers.get('entities', []):
            if container.get('name') == name:
                return container
        
        return None
    
    def validate_container_placement(self, container_name: str, expected_strict_mode: bool) -> tuple:
        """Validate container placement follows rack awareness rules"""
        container = self.get_container_by_name(container_name)
        
        if not container:
            return False, f"Container {container_name} not found"
        
        # Check container configuration
        strict_ra_enabled = container.get('rackAwarenessStrict', False)
        
        if expected_strict_mode and not strict_ra_enabled:
            return False, f"Container should have strict RA enabled but doesn't"
        
        if not expected_strict_mode and strict_ra_enabled:
            return False, f"Container has strict RA enabled but shouldn't"
        
        # Additional placement validation would go here
        # This would involve checking actual replica placement across racks
        
        return True, f"Container placement validation passed"
    
    def get_protection_domains(self) -> Dict[str, Any]:
        """Get protection domains"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get('/PrismGateway/services/rest/v2.0/protection_domains/')
        return response
    
    def get_replication_policies(self) -> Dict[str, Any]:
        """Get replication policies"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get('/PrismGateway/services/rest/v2.0/replication_policies/')
        return response