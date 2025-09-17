"""
Session wrapper for API requests
"""

import requests
import json
import logging
from typing import Dict, Any, Optional
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for test environments
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Session:
    """
    Session wrapper for making API requests to Nutanix cluster
    """
    
    def __init__(self, cluster_ip: str, username: str, password: str, 
                 port: int = 9440, use_https: bool = True):
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password
        self.port = port
        self.use_https = use_https
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Build base URL
        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{cluster_ip}:{port}"
        
        # Setup requests session
        self._session = requests.Session()
        self._session.auth = (username, password)
        self._session.verify = False  # For test environments
        
        # Default headers
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, json: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request"""
        return self._make_request('POST', endpoint, json=json, data=data)
    
    def put(self, endpoint: str, json: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request"""
        return self._make_request('PUT', endpoint, json=json, data=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        return self._make_request('DELETE', endpoint)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            
            response = self._session.request(method, url, **kwargs)
            
            # Log request/response details
            self.logger.debug(f"Response status: {response.status_code}")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            else:
                return {}
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {method} {url} - {str(e)}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON response: {str(e)}")
            raise