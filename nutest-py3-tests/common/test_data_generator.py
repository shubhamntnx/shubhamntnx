"""
Test data generation utilities
"""

import random
import string
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class TestContainer:
    """Test container configuration"""
    name: str
    replication_factor: int
    size_gb: int
    strict_rack_awareness: bool
    uuid: Optional[str] = None


@dataclass
class TestVDisk:
    """Test vDisk configuration"""
    name: str
    size_gb: int
    container_name: str
    uuid: Optional[str] = None


class TestDataGenerator:
    """
    Utility class for generating test data and configurations
    """
    
    def __init__(self):
        self.generated_names = set()
    
    def generate_unique_name(self, prefix: str = "test") -> str:
        """Generate a unique name with timestamp and random suffix"""
        timestamp = int(time.time())
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        name = f"{prefix}_{timestamp}_{random_suffix}"
        
        # Ensure uniqueness
        counter = 1
        original_name = name
        while name in self.generated_names:
            name = f"{original_name}_{counter}"
            counter += 1
        
        self.generated_names.add(name)
        return name
    
    def generate_test_containers(self, count: int, strict_rack_awareness: bool = False) -> List[TestContainer]:
        """
        Generate test container configurations
        
        Args:
            count: Number of containers to generate
            strict_rack_awareness: Whether to enable strict rack awareness
            
        Returns:
            List of TestContainer objects
        """
        containers = []
        
        for i in range(count):
            container = TestContainer(
                name=self.generate_unique_name("container"),
                replication_factor=random.choice([2, 3]),
                size_gb=random.randint(10, 100),
                strict_rack_awareness=strict_rack_awareness
            )
            containers.append(container)
        
        return containers
    
    def generate_test_vdisks(self, containers: List[TestContainer], vdisks_per_container: int = 2) -> List[TestVDisk]:
        """
        Generate test vDisk configurations
        
        Args:
            containers: List of containers to create vDisks in
            vdisks_per_container: Number of vDisks per container
            
        Returns:
            List of TestVDisk objects
        """
        vdisks = []
        
        for container in containers:
            for i in range(vdisks_per_container):
                vdisk = TestVDisk(
                    name=self.generate_unique_name("vdisk"),
                    size_gb=random.randint(1, 50),
                    container_name=container.name
                )
                vdisks.append(vdisk)
        
        return vdisks
    
    def generate_rack_failure_scenarios(self, total_racks: int, max_failures: int = None) -> List[Dict[str, Any]]:
        """
        Generate rack failure scenarios for testing
        
        Args:
            total_racks: Total number of racks in cluster
            max_failures: Maximum number of racks to fail (default: total_racks - 1)
            
        Returns:
            List of failure scenario configurations
        """
        if max_failures is None:
            max_failures = total_racks - 1
        
        scenarios = []
        rack_ids = [f"rack_{i}" for i in range(total_racks)]
        
        # Single rack failure scenarios
        for rack_id in rack_ids:
            scenarios.append({
                'name': f'single_rack_failure_{rack_id}',
                'description': f'Fail single rack: {rack_id}',
                'failed_racks': [rack_id],
                'expected_quorum': True if total_racks > 2 else False
            })
        
        # Multiple rack failure scenarios
        if total_racks > 3:
            for failure_count in range(2, min(max_failures + 1, total_racks)):
                failed_racks = random.sample(rack_ids, failure_count)
                scenarios.append({
                    'name': f'multi_rack_failure_{failure_count}_racks',
                    'description': f'Fail {failure_count} racks: {", ".join(failed_racks)}',
                    'failed_racks': failed_racks,
                    'expected_quorum': (total_racks - failure_count) > (total_racks // 2)
                })
        
        return scenarios
    
    def generate_skewed_cluster_config(self, total_racks: int) -> Dict[str, Any]:
        """
        Generate configuration for a skewed cluster
        
        Args:
            total_racks: Total number of racks
            
        Returns:
            Skewed cluster configuration
        """
        rack_configs = []
        
        for i in range(total_racks):
            # Create uneven distribution of resources
            if i == 0:  # First rack gets more resources
                host_count = random.randint(4, 6)
                storage_per_host = random.randint(2000, 4000)  # GB
            elif i == total_racks - 1:  # Last rack gets fewer resources
                host_count = random.randint(1, 2)
                storage_per_host = random.randint(500, 1000)  # GB
            else:  # Middle racks get moderate resources
                host_count = random.randint(2, 4)
                storage_per_host = random.randint(1000, 2000)  # GB
            
            rack_configs.append({
                'rack_id': f'rack_{i}',
                'host_count': host_count,
                'storage_per_host_gb': storage_per_host,
                'total_storage_gb': host_count * storage_per_host
            })
        
        return {
            'total_racks': total_racks,
            'rack_configs': rack_configs,
            'is_skewed': True,
            'skew_ratio': max(config['total_storage_gb'] for config in rack_configs) / 
                          min(config['total_storage_gb'] for config in rack_configs)
        }
    
    def generate_policy_violation_tests(self) -> List[Dict[str, Any]]:
        """
        Generate test cases for storage policy violations
        
        Returns:
            List of policy violation test configurations
        """
        violations = []
        
        # Test invalid rack awareness override
        violations.append({
            'type': 'invalid_override',
            'name': 'test_invalid_rack_awareness_override',
            'description': 'Attempt to override strict rack awareness with invalid configuration',
            'container_config': {
                'replication_factor': 3,
                'rack_awareness_strict': True,
                'override_rack_placement': True,  # This should be blocked
                'target_racks': ['rack_0', 'rack_0']  # Invalid: same rack
            },
            'expected_result': 'blocked'
        })
        
        # Test placement with insufficient racks
        violations.append({
            'type': 'insufficient_racks',
            'name': 'test_insufficient_racks_placement',
            'description': 'Attempt to create container requiring more racks than available',
            'container_config': {
                'replication_factor': 5,  # Requires 5 racks
                'rack_awareness_strict': True
            },
            'cluster_setup': {
                'available_racks': 3  # Only 3 racks available
            },
            'expected_result': 'blocked'
        })
        
        # Test replication factor vs rack count mismatch
        violations.append({
            'type': 'replication_rack_mismatch',
            'name': 'test_replication_rack_mismatch',
            'description': 'Test replication factor higher than available racks with strict RA',
            'container_config': {
                'replication_factor': 4,
                'rack_awareness_strict': True
            },
            'cluster_setup': {
                'available_racks': 3
            },
            'expected_result': 'warning_or_blocked'
        })
        
        return violations
    
    def generate_ft_upgrade_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generate fault tolerance upgrade scenarios
        
        Returns:
            List of FT upgrade test configurations
        """
        scenarios = []
        
        # FT1 to FT2 upgrade scenarios
        scenarios.append({
            'name': 'ft1_to_ft2_basic',
            'description': 'Basic FT1 to FT2 upgrade with strict rack awareness',
            'initial_ft': 1,
            'target_ft': 2,
            'strict_rack_awareness': True,
            'expected_rpp': 'kRF3_Strict',
            'min_racks_required': 3
        })
        
        scenarios.append({
            'name': 'ft1_to_ft2_without_strict_ra',
            'description': 'FT1 to FT2 upgrade without strict rack awareness',
            'initial_ft': 1,
            'target_ft': 2,
            'strict_rack_awareness': False,
            'expected_rpp': 'kRF3_BestEffort',
            'min_racks_required': 1
        })
        
        # FT0 to FT1 upgrade scenarios
        scenarios.append({
            'name': 'ft0_to_ft1_with_strict_ra',
            'description': 'FT0 to FT1 upgrade with strict rack awareness',
            'initial_ft': 0,
            'target_ft': 1,
            'strict_rack_awareness': True,
            'expected_rpp': 'kRF2_Strict',
            'min_racks_required': 2
        })
        
        return scenarios
    
    def generate_test_workloads(self, container_names: List[str]) -> List[Dict[str, Any]]:
        """
        Generate test workloads for validating rack awareness
        
        Args:
            container_names: List of container names to run workloads on
            
        Returns:
            List of workload configurations
        """
        workloads = []
        
        for container_name in container_names:
            # Read-heavy workload
            workloads.append({
                'name': f'read_heavy_{container_name}',
                'type': 'read_heavy',
                'container': container_name,
                'duration_minutes': 10,
                'read_percentage': 90,
                'write_percentage': 10,
                'io_size_kb': 64,
                'threads': 4
            })
            
            # Write-heavy workload
            workloads.append({
                'name': f'write_heavy_{container_name}',
                'type': 'write_heavy',
                'container': container_name,
                'duration_minutes': 5,
                'read_percentage': 20,
                'write_percentage': 80,
                'io_size_kb': 256,
                'threads': 2
            })
        
        return workloads
    
    def cleanup_generated_names(self):
        """Clear the generated names cache"""
        self.generated_names.clear()