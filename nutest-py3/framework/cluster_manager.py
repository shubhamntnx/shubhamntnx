"""
Cluster Management Utilities
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from .test_config import TestConfig
from .api_client import APIClient


class RackInfo:
    """Information about a rack"""
    def __init__(self, rack_id: str, hosts: List[str]):
        self.rack_id = rack_id
        self.hosts = hosts
        self.is_available = True
        self.failed_hosts = []
    
    @property
    def available_hosts(self) -> List[str]:
        """Get list of available hosts in this rack"""
        return [host for host in self.hosts if host not in self.failed_hosts]
    
    @property
    def host_count(self) -> int:
        """Get total number of hosts in this rack"""
        return len(self.hosts)
    
    @property
    def available_host_count(self) -> int:
        """Get number of available hosts in this rack"""
        return len(self.available_hosts)


class ClusterManager:
    """
    High-level cluster management operations
    """
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.api_client = APIClient(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._rack_info_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get comprehensive cluster information"""
        return self.api_client.get_cluster_info()
    
    def get_rack_configuration(self) -> Dict[str, Any]:
        """Get current rack configuration"""
        try:
            return self.api_client.get_rack_configuration()
        except Exception as e:
            self.logger.warning(f"Failed to get rack configuration: {str(e)}")
            return {}
    
    def get_rack_info(self, force_refresh: bool = False) -> Dict[str, RackInfo]:
        """
        Get detailed rack information with caching
        """
        current_time = time.time()
        
        if (not force_refresh and 
            self._rack_info_cache and 
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._rack_info_cache
        
        rack_info = {}
        
        try:
            # Get hosts information
            hosts_response = self.api_client.get_hosts()
            hosts = hosts_response.get('entities', [])
            
            # Group hosts by rack
            rack_to_hosts = defaultdict(list)
            
            for host in hosts:
                rack_id = host.get('rackableUnitUuid', 'default_rack')
                host_uuid = host.get('uuid')
                if host_uuid:
                    rack_to_hosts[rack_id].append(host_uuid)
            
            # Create RackInfo objects
            for rack_id, host_list in rack_to_hosts.items():
                rack_info[rack_id] = RackInfo(rack_id, host_list)
            
            self._rack_info_cache = rack_info
            self._cache_timestamp = current_time
            
        except Exception as e:
            self.logger.error(f"Failed to get rack information: {str(e)}")
            # Return cached data if available
            if self._rack_info_cache:
                return self._rack_info_cache
            raise
        
        return rack_info
    
    def get_rack_count(self) -> int:
        """Get number of racks in the cluster"""
        rack_info = self.get_rack_info()
        return len(rack_info)
    
    def validate_rack_requirements(self, min_racks: Optional[int] = None) -> Tuple[bool, str]:
        """
        Validate that cluster meets rack requirements
        
        Returns:
            Tuple of (is_valid, message)
        """
        min_racks = min_racks or self.config.min_racks_required
        
        try:
            rack_info = self.get_rack_info()
            rack_count = len(rack_info)
            
            if rack_count < min_racks:
                return False, f"Insufficient racks: {rack_count} < {min_racks} required"
            
            # Check if racks have sufficient hosts
            for rack_id, rack in rack_info.items():
                if rack.available_host_count == 0:
                    return False, f"Rack {rack_id} has no available hosts"
            
            return True, f"Rack requirements met: {rack_count} racks available"
            
        except Exception as e:
            return False, f"Failed to validate rack requirements: {str(e)}"
    
    def is_strict_rack_awareness_enabled(self) -> bool:
        """Check if strict rack awareness is currently enabled"""
        try:
            cluster_config = self.api_client.get_cluster_config()
            entities = cluster_config.get('entities', [])
            
            if entities:
                config = entities[0].get('spec', {}).get('resources', {}).get('config', {})
                return config.get('rack_awareness_strict', False)
            
        except Exception as e:
            self.logger.warning(f"Failed to check strict rack awareness status: {str(e)}")
        
        return False
    
    def enable_strict_rack_awareness(self) -> bool:
        """Enable strict rack awareness"""
        try:
            self.logger.info("Enabling strict rack awareness")
            self.api_client.update_rack_awareness(True)
            
            # Wait for the change to take effect
            return self._wait_for_rack_awareness_state(True)
            
        except Exception as e:
            self.logger.error(f"Failed to enable strict rack awareness: {str(e)}")
            return False
    
    def disable_strict_rack_awareness(self) -> bool:
        """Disable strict rack awareness"""
        try:
            self.logger.info("Disabling strict rack awareness")
            self.api_client.update_rack_awareness(False)
            
            # Wait for the change to take effect
            return self._wait_for_rack_awareness_state(False)
            
        except Exception as e:
            self.logger.error(f"Failed to disable strict rack awareness: {str(e)}")
            return False
    
    def _wait_for_rack_awareness_state(self, expected_state: bool, timeout_seconds: int = 300) -> bool:
        """Wait for rack awareness to reach expected state"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            if self.is_strict_rack_awareness_enabled() == expected_state:
                state_str = "enabled" if expected_state else "disabled"
                self.logger.info(f"Strict rack awareness is now {state_str}")
                return True
            
            time.sleep(10)
        
        self.logger.warning("Timeout waiting for rack awareness state change")
        return False
    
    def get_fault_tolerance_status(self) -> Dict[str, Any]:
        """Get current fault tolerance status"""
        return self.api_client.get_fault_tolerance_status()
    
    def simulate_rack_failure(self, rack_id: str) -> bool:
        """
        Simulate rack failure by powering off all hosts in the rack
        
        Args:
            rack_id: ID of the rack to fail
            
        Returns:
            True if simulation was successful
        """
        if not self.config.rack_failure_simulation:
            self.logger.warning("Rack failure simulation is disabled in configuration")
            return False
        
        try:
            rack_info = self.get_rack_info()
            
            if rack_id not in rack_info:
                self.logger.error(f"Rack {rack_id} not found")
                return False
            
            rack = rack_info[rack_id]
            self.logger.info(f"Simulating failure of rack {rack_id} with {rack.host_count} hosts")
            
            # Power off all hosts in the rack
            failed_hosts = []
            for host_uuid in rack.hosts:
                try:
                    self.api_client.power_off_host(host_uuid)
                    failed_hosts.append(host_uuid)
                    self.logger.debug(f"Powered off host {host_uuid}")
                except Exception as e:
                    self.logger.warning(f"Failed to power off host {host_uuid}: {str(e)}")
            
            # Update rack info
            rack.failed_hosts = failed_hosts
            rack.is_available = len(failed_hosts) == 0
            
            self.logger.info(f"Rack failure simulation completed: {len(failed_hosts)} hosts failed")
            return len(failed_hosts) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to simulate rack failure: {str(e)}")
            return False
    
    def recover_rack(self, rack_id: str) -> bool:
        """
        Recover from rack failure by powering on all hosts in the rack
        
        Args:
            rack_id: ID of the rack to recover
            
        Returns:
            True if recovery was successful
        """
        try:
            rack_info = self.get_rack_info()
            
            if rack_id not in rack_info:
                self.logger.error(f"Rack {rack_id} not found")
                return False
            
            rack = rack_info[rack_id]
            self.logger.info(f"Recovering rack {rack_id}")
            
            # Power on all failed hosts
            recovered_hosts = []
            for host_uuid in rack.failed_hosts:
                try:
                    self.api_client.power_on_host(host_uuid)
                    recovered_hosts.append(host_uuid)
                    self.logger.debug(f"Powered on host {host_uuid}")
                except Exception as e:
                    self.logger.warning(f"Failed to power on host {host_uuid}: {str(e)}")
            
            # Update rack info
            for host_uuid in recovered_hosts:
                if host_uuid in rack.failed_hosts:
                    rack.failed_hosts.remove(host_uuid)
            
            rack.is_available = len(rack.failed_hosts) == 0
            
            self.logger.info(f"Rack recovery completed: {len(recovered_hosts)} hosts recovered")
            return len(recovered_hosts) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to recover rack: {str(e)}")
            return False
    
    def wait_for_cluster_stable(self, timeout_minutes: int = 30) -> bool:
        """Wait for cluster to reach stable state"""
        return self.api_client.wait_for_cluster_stable(timeout_minutes)
    
    def get_cluster_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive cluster health summary"""
        try:
            cluster_info = self.get_cluster_info()
            rack_info = self.get_rack_info()
            ft_status = self.get_fault_tolerance_status()
            
            total_hosts = sum(rack.host_count for rack in rack_info.values())
            available_hosts = sum(rack.available_host_count for rack in rack_info.values())
            failed_hosts = total_hosts - available_hosts
            
            return {
                'cluster_status': cluster_info.get('clusterStatus', 'UNKNOWN'),
                'rack_count': len(rack_info),
                'total_hosts': total_hosts,
                'available_hosts': available_hosts,
                'failed_hosts': failed_hosts,
                'strict_rack_awareness_enabled': self.is_strict_rack_awareness_enabled(),
                'fault_tolerance_status': ft_status,
                'rack_details': {
                    rack_id: {
                        'total_hosts': rack.host_count,
                        'available_hosts': rack.available_host_count,
                        'failed_hosts': len(rack.failed_hosts),
                        'is_available': rack.is_available
                    }
                    for rack_id, rack in rack_info.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cluster health summary: {str(e)}")
            return {'error': str(e)}