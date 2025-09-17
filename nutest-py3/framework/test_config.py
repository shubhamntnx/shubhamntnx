"""
Test Configuration Management
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class ClusterConfig:
    """Cluster configuration"""
    cluster_ip: str
    username: str
    password: str
    port: int = 9440
    use_https: bool = True


@dataclass
class TestConfig:
    """
    Configuration class for tests
    """
    # Cluster configuration
    cluster_config: ClusterConfig = None
    
    # Test execution settings
    parallel_execution: bool = False
    max_parallel_tests: int = 5
    default_timeout_minutes: int = 30
    
    # Logging configuration
    log_level: str = "INFO"
    log_file_path: str = "/tmp/nutest.log"
    
    # Rack awareness specific settings
    min_racks_required: int = 3
    rack_failure_simulation: bool = True
    
    # API settings
    api_timeout_seconds: int = 300
    api_retry_count: int = 3
    api_retry_delay: int = 5
    
    # Test data
    test_data_path: str = "/tmp/test_data"
    cleanup_on_failure: bool = True
    
    # Additional settings
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, config_file: str) -> 'TestConfig':
        """Load configuration from JSON file"""
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        cluster_data = data.get('cluster', {})
        cluster_config = ClusterConfig(
            cluster_ip=cluster_data.get('ip', 'localhost'),
            username=cluster_data.get('username', 'admin'),
            password=cluster_data.get('password', 'password'),
            port=cluster_data.get('port', 9440),
            use_https=cluster_data.get('use_https', True)
        )
        
        config = cls(cluster_config=cluster_config)
        
        # Update other fields from data
        for key, value in data.items():
            if key != 'cluster' and hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    @classmethod
    def from_env(cls) -> 'TestConfig':
        """Load configuration from environment variables"""
        cluster_config = ClusterConfig(
            cluster_ip=os.getenv('CLUSTER_IP', 'localhost'),
            username=os.getenv('CLUSTER_USERNAME', 'admin'),
            password=os.getenv('CLUSTER_PASSWORD', 'password'),
            port=int(os.getenv('CLUSTER_PORT', '9440')),
            use_https=os.getenv('CLUSTER_USE_HTTPS', 'true').lower() == 'true'
        )
        
        return cls(
            cluster_config=cluster_config,
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file_path=os.getenv('LOG_FILE_PATH', '/tmp/nutest.log'),
            api_timeout_seconds=int(os.getenv('API_TIMEOUT', '300')),
            min_racks_required=int(os.getenv('MIN_RACKS', '3'))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'cluster': {
                'ip': self.cluster_config.cluster_ip,
                'username': self.cluster_config.username,
                'password': self.cluster_config.password,
                'port': self.cluster_config.port,
                'use_https': self.cluster_config.use_https
            },
            'parallel_execution': self.parallel_execution,
            'max_parallel_tests': self.max_parallel_tests,
            'default_timeout_minutes': self.default_timeout_minutes,
            'log_level': self.log_level,
            'log_file_path': self.log_file_path,
            'min_racks_required': self.min_racks_required,
            'rack_failure_simulation': self.rack_failure_simulation,
            'api_timeout_seconds': self.api_timeout_seconds,
            'api_retry_count': self.api_retry_count,
            'api_retry_delay': self.api_retry_delay,
            'test_data_path': self.test_data_path,
            'cleanup_on_failure': self.cleanup_on_failure,
            'extra_config': self.extra_config
        }
    
    def save_to_file(self, config_file: str) -> None:
        """Save configuration to JSON file"""
        with open(config_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)