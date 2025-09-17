"""
Rack Entity for Nutanix Framework
"""

from typing import Dict, Any, Optional, List
from collections import defaultdict
from .base_entity import BaseEntity


class RackEntity(BaseEntity):
    """
    Rack entity operations
    """
    
    @property
    def entity_type(self) -> str:
        return "rack"
    
    def get_entity_info(self, entity_uuid: str) -> Dict[str, Any]:
        """Get rack information"""
        # Racks don't have direct API endpoints, so we get info from hosts
        from .host_entity import HostEntity
        
        host_entity = HostEntity(self.session)
        hosts = host_entity.get_hosts_by_rack(entity_uuid)
        
        return {
            'rack_uuid': entity_uuid,
            'host_count': len(hosts),
            'hosts': hosts
        }
    
    def list_entities(self, **kwargs) -> Dict[str, Any]:
        """List all racks by analyzing host distribution"""
        from .host_entity import HostEntity
        
        host_entity = HostEntity(self.session)
        hosts_response = host_entity.list_entities()
        
        # Group hosts by rack
        rack_to_hosts = defaultdict(list)
        
        for host in hosts_response.get('entities', []):
            rack_uuid = host.get('rackableUnitUuid', 'default_rack')
            rack_to_hosts[rack_uuid].append(host)
        
        # Build rack information
        racks = []
        for rack_uuid, hosts in rack_to_hosts.items():
            racks.append({
                'rack_uuid': rack_uuid,
                'host_count': len(hosts),
                'hosts': hosts
            })
        
        return {'entities': racks}
    
    def get_rack_configuration(self) -> Dict[str, Any]:
        """Get rack configuration"""
        if not self.session:
            raise RuntimeError("Session not available")
        
        try:
            response = self.session.get('/PrismGateway/services/rest/v2.0/cluster/rack_config')
            return response
        except Exception as e:
            self.logger.warning(f"Failed to get rack configuration: {str(e)}")
            return {}
    
    def get_rack_count(self) -> int:
        """Get total number of racks"""
        racks_info = self.list_entities()
        return len(racks_info.get('entities', []))
    
    def simulate_rack_failure(self, rack_uuid: str) -> bool:
        """Simulate rack failure by powering off all hosts in the rack"""
        from .host_entity import HostEntity
        
        host_entity = HostEntity(self.session)
        hosts_in_rack = host_entity.get_hosts_by_rack(rack_uuid)
        
        if not hosts_in_rack:
            self.logger.warning(f"No hosts found in rack {rack_uuid}")
            return False
        
        success_count = 0
        for host in hosts_in_rack:
            host_uuid = host.get('uuid')
            if host_uuid and host_entity.power_off_host(host_uuid):
                success_count += 1
        
        self.logger.info(f"Powered off {success_count}/{len(hosts_in_rack)} hosts in rack {rack_uuid}")
        return success_count > 0
    
    def recover_rack(self, rack_uuid: str) -> bool:
        """Recover rack by powering on all hosts"""
        from .host_entity import HostEntity
        
        host_entity = HostEntity(self.session)
        hosts_in_rack = host_entity.get_hosts_by_rack(rack_uuid)
        
        if not hosts_in_rack:
            self.logger.warning(f"No hosts found in rack {rack_uuid}")
            return False
        
        success_count = 0
        for host in hosts_in_rack:
            host_uuid = host.get('uuid')
            if host_uuid and host_entity.power_on_host(host_uuid):
                success_count += 1
        
        self.logger.info(f"Powered on {success_count}/{len(hosts_in_rack)} hosts in rack {rack_uuid}")
        return success_count > 0
    
    def validate_rack_requirements(self, min_racks: int = 3) -> tuple:
        """Validate rack requirements for strict RA"""
        racks_info = self.list_entities()
        rack_count = len(racks_info.get('entities', []))
        
        if rack_count < min_racks:
            return False, f"Insufficient racks: {rack_count} < {min_racks}"
        
        # Check if racks have sufficient hosts
        for rack in racks_info.get('entities', []):
            if rack.get('host_count', 0) == 0:
                return False, f"Rack {rack.get('rack_uuid')} has no hosts"
        
        return True, f"Rack requirements met: {rack_count} racks available"