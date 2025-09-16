"""
API Client for Nutanix Cluster Operations
"""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional, List
from urllib3.exceptions import InsecureRequestWarning

from .test_config import TestConfig

# Disable SSL warnings for test environments
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class APIClient:
    """
    Client for interacting with Nutanix cluster APIs
    """
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.cluster_config = config.cluster_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Build base URL
        protocol = "https" if self.cluster_config.use_https else "http"
        self.base_url = f"{protocol}://{self.cluster_config.cluster_ip}:{self.cluster_config.port}"
        
        # Setup session
        self.session = requests.Session()
        self.session.auth = (self.cluster_config.username, self.cluster_config.password)
        self.session.verify = False  # For test environments
        
        # Default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        """
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.config.api_timeout_seconds
        
        for attempt in range(self.config.api_retry_count):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=timeout
                )
                
                # Log request/response details
                self.logger.debug(f"Request: {method} {url}")
                if data:
                    self.logger.debug(f"Request body: {json.dumps(data, indent=2)}")
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response body: {response.text}")
                
                response.raise_for_status()
                
                if response.content:
                    return response.json()
                else:
                    return {}
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt == self.config.api_retry_count - 1:
                    raise
                time.sleep(self.config.api_retry_delay)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request"""
        return self._make_request('POST', endpoint, data=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request"""
        return self._make_request('PUT', endpoint, data=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        return self._make_request('DELETE', endpoint)
    
    # Cluster-specific API methods
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information"""
        return self.get('/PrismGateway/services/rest/v2.0/cluster/')
    
    def get_cluster_config(self) -> Dict[str, Any]:
        """Get cluster configuration"""
        return self.get('/api/nutanix/v3/clusters')
    
    def update_cluster_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update cluster configuration"""
        cluster_info = self.get_cluster_config()
        cluster_uuid = cluster_info['entities'][0]['metadata']['uuid']
        
        endpoint = f'/api/nutanix/v3/clusters/{cluster_uuid}'
        return self.put(endpoint, data=config)
    
    def get_rack_configuration(self) -> Dict[str, Any]:
        """Get rack configuration"""
        return self.get('/PrismGateway/services/rest/v2.0/cluster/rack_config')
    
    def update_rack_awareness(self, strict_mode: bool) -> Dict[str, Any]:
        """Enable/disable strict rack awareness"""
        cluster_info = self.get_cluster_config()
        cluster_spec = cluster_info['entities'][0]['spec']
        
        # Update rack awareness setting
        cluster_spec['resources']['config']['rack_awareness_strict'] = strict_mode
        
        return self.update_cluster_config({
            'spec': cluster_spec,
            'metadata': cluster_info['entities'][0]['metadata']
        })
    
    def get_fault_tolerance_status(self) -> Dict[str, Any]:
        """Get fault tolerance status"""
        return self.get('/PrismGateway/services/rest/v2.0/cluster/domain_fault_tolerance_status')
    
    def get_storage_containers(self) -> Dict[str, Any]:
        """Get storage containers"""
        return self.get('/PrismGateway/services/rest/v2.0/storage_containers/')
    
    def create_storage_container(self, name: str, replication_factor: int = 2, 
                                strict_rack_awareness: bool = False) -> Dict[str, Any]:
        """Create storage container with specified settings"""
        container_data = {
            'name': name,
            'replicationFactor': replication_factor,
            'compressionEnabled': True,
            'compressionDelayInSecs': 0,
            'fingerPrintOnWrite': 'OFF',
            'onDiskDedup': 'OFF'
        }
        
        if strict_rack_awareness:
            container_data['rackAwarenessStrict'] = True
        
        return self.post('/PrismGateway/services/rest/v2.0/storage_containers/', data=container_data)
    
    def get_hosts(self) -> Dict[str, Any]:
        """Get host information"""
        return self.get('/PrismGateway/services/rest/v2.0/hosts/')
    
    def get_host_by_uuid(self, host_uuid: str) -> Dict[str, Any]:
        """Get specific host information"""
        return self.get(f'/PrismGateway/services/rest/v2.0/hosts/{host_uuid}')
    
    def power_off_host(self, host_uuid: str) -> Dict[str, Any]:
        """Power off a host (for rack failure simulation)"""
        return self.post(f'/PrismGateway/services/rest/v2.0/hosts/{host_uuid}/power_off')
    
    def power_on_host(self, host_uuid: str) -> Dict[str, Any]:
        """Power on a host"""
        return self.post(f'/PrismGateway/services/rest/v2.0/hosts/{host_uuid}/power_on')
    
    def get_protection_domains(self) -> Dict[str, Any]:
        """Get protection domains"""
        return self.get('/PrismGateway/services/rest/v2.0/protection_domains/')
    
    def get_replication_policies(self) -> Dict[str, Any]:
        """Get replication policies"""
        return self.get('/PrismGateway/services/rest/v2.0/replication_policies/')
    
    def wait_for_cluster_stable(self, timeout_minutes: int = 30) -> bool:
        """
        Wait for cluster to reach stable state
        """
        timeout_seconds = timeout_minutes * 60
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                cluster_info = self.get_cluster_info()
                cluster_status = cluster_info.get('clusterStatus', 'UNKNOWN')
                
                if cluster_status == 'NORMAL':
                    self.logger.info("Cluster is in stable state")
                    return True
                
                self.logger.debug(f"Cluster status: {cluster_status}, waiting...")
                time.sleep(30)
                
            except Exception as e:
                self.logger.debug(f"Error checking cluster status: {str(e)}")
                time.sleep(30)
        
        self.logger.warning("Timeout waiting for cluster to stabilize")
        return False