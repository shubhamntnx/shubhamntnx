"""
Host Entity for Nutanix Framework
"""

from typing import Dict, Any, Optional, List
from .base_entity import BaseEntity


class HostEntity(BaseEntity):
    """
    Host entity operations
    """
    
    @property
    def entity_type(self) -> str:
        return "host"
    
    def get_entity_info(self, entity_uuid: str) -> Dict[str, Any]:
        """Get host information"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get(f'/PrismGateway/services/rest/v2.0/hosts/{entity_uuid}')
        return response
    
    def list_entities(self, **kwargs) -> Dict[str, Any]:
        """List all hosts"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        response = self.session.get('/PrismGateway/services/rest/v2.0/hosts/')
        return response
    
    def get_hosts_by_rack(self, rack_uuid: str) -> List[Dict[str, Any]]:
        """Get all hosts in a specific rack"""
        hosts_response = self.list_entities()
        hosts_in_rack = []
        
        for host in hosts_response.get('entities', []):
            if host.get('rackableUnitUuid') == rack_uuid:
                hosts_in_rack.append(host)
        
        return hosts_in_rack
    
    def power_off_host(self, host_uuid: str) -> bool:
        """Power off a host"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        try:
            response = self.session.post(f'/PrismGateway/services/rest/v2.0/hosts/{host_uuid}/power_off')
            return True
        except Exception as e:
            self.logger.error(f"Failed to power off host {host_uuid}: {str(e)}")
            return False
    
    def power_on_host(self, host_uuid: str) -> bool:
        """Power on a host"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        try:
            response = self.session.post(f'/PrismGateway/services/rest/v2.0/hosts/{host_uuid}/power_on')
            return True
        except Exception as e:
            self.logger.error(f"Failed to power on host {host_uuid}: {str(e)}")
            return False
    
    def get_host_status(self, host_uuid: str) -> str:
        """Get host status"""
        try:
            host_info = self.get_entity_info(host_uuid)
            return host_info.get('state', 'UNKNOWN')
        except Exception as e:
            self.logger.error(f"Failed to get host status {host_uuid}: {str(e)}")
            return 'UNKNOWN'