"""
Cluster-related workflows
"""

import time
import logging
from typing import Dict, Any, Optional
from nutest_py3.framework.entities import ClusterEntity


class ClusterWorkflows:
    """
    High-level cluster workflows built on top of ClusterEntity
    """
    
    def __init__(self, session):
        self.session = session
        self.cluster_entity = ClusterEntity(session)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def wait_for_cluster_stable(self, timeout_minutes: int = 30) -> bool:
        """
        Wait for cluster to reach stable state
        """
        timeout_seconds = timeout_minutes * 60
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                cluster_info = self.cluster_entity.get_entity_info()
                cluster_status = cluster_info.get('clusterStatus', 'UNKNOWN')
                
                if cluster_status == 'NORMAL':
                    self.logger.info("Cluster is stable")
                    return True
                
                self.logger.debug(f"Cluster status: {cluster_status}, waiting...")
                time.sleep(30)
                
            except Exception as e:
                self.logger.debug(f"Error checking cluster status: {str(e)}")
                time.sleep(30)
        
        self.logger.warning("Timeout waiting for cluster to stabilize")
        return False
    
    def get_cluster_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive cluster health summary
        """
        try:
            cluster_info = self.cluster_entity.get_entity_info()
            
            from nutest_py3.framework.entities import RackEntity
            rack_entity = RackEntity(self.session)
            racks_info = rack_entity.list_entities()
            
            # Calculate host statistics
            total_hosts = 0
            available_hosts = 0
            rack_details = {}
            
            for rack in racks_info.get('entities', []):
                rack_uuid = rack.get('rack_uuid')
                host_count = rack.get('host_count', 0)
                total_hosts += host_count
                
                # Assume all hosts are available unless we detect failures
                available_hosts += host_count
                
                rack_details[rack_uuid] = {
                    'total_hosts': host_count,
                    'available_hosts': host_count,
                    'failed_hosts': 0,
                    'is_available': True
                }
            
            return {
                'cluster_status': cluster_info.get('clusterStatus', 'UNKNOWN'),
                'rack_count': len(racks_info.get('entities', [])),
                'total_hosts': total_hosts,
                'available_hosts': available_hosts,
                'failed_hosts': 0,
                'strict_rack_awareness_enabled': self.cluster_entity.get_rack_awareness_status(),
                'fault_tolerance_level': self.cluster_entity.get_ft_level(),
                'rack_details': rack_details
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cluster health summary: {str(e)}")
            return {'error': str(e)}
    
    def enable_strict_rack_awareness_workflow(self) -> bool:
        """
        Complete workflow to enable strict rack awareness
        """
        self.logger.info("Starting enable strict rack awareness workflow")
        
        # Step 1: Validate prerequisites
        from nutest_py3.framework.entities import RackEntity
        rack_entity = RackEntity(self.session)
        
        is_valid, message = rack_entity.validate_rack_requirements()
        if not is_valid:
            self.logger.error(f"Prerequisites not met: {message}")
            return False
        
        # Step 2: Check cluster health
        if not self.wait_for_cluster_stable(timeout_minutes=5):
            self.logger.error("Cluster not stable before enabling strict RA")
            return False
        
        # Step 3: Enable strict rack awareness
        success = self.cluster_entity.set_rack_awareness_strict(True)
        if not success:
            self.logger.error("Failed to enable strict rack awareness")
            return False
        
        # Step 4: Wait for cluster to stabilize
        if not self.wait_for_cluster_stable(timeout_minutes=10):
            self.logger.warning("Cluster did not stabilize after enabling strict RA")
            return False
        
        self.logger.info("Successfully enabled strict rack awareness")
        return True
    
    def disable_strict_rack_awareness_workflow(self) -> bool:
        """
        Complete workflow to disable strict rack awareness
        """
        self.logger.info("Starting disable strict rack awareness workflow")
        
        # Step 1: Disable strict rack awareness
        success = self.cluster_entity.set_rack_awareness_strict(False)
        if not success:
            self.logger.error("Failed to disable strict rack awareness")
            return False
        
        # Step 2: Wait for cluster to stabilize
        if not self.wait_for_cluster_stable(timeout_minutes=10):
            self.logger.warning("Cluster did not stabilize after disabling strict RA")
            return False
        
        self.logger.info("Successfully disabled strict rack awareness")
        return True
    
    def upgrade_ft_level_workflow(self, target_ft: int) -> bool:
        """
        Complete workflow to upgrade fault tolerance level
        """
        self.logger.info(f"Starting FT upgrade workflow to level {target_ft}")
        
        # Step 1: Check current FT level
        current_ft = self.cluster_entity.get_ft_level()
        if current_ft >= target_ft:
            self.logger.info(f"Cluster already at FT{current_ft}")
            return True
        
        # Step 2: Validate cluster health
        if not self.wait_for_cluster_stable(timeout_minutes=5):
            self.logger.error("Cluster not stable before FT upgrade")
            return False
        
        # Step 3: Initiate FT upgrade
        success = self.cluster_entity.set_ft_level(target_ft)
        if not success:
            self.logger.error(f"Failed to upgrade to FT{target_ft}")
            return False
        
        # Step 4: Wait for cluster to stabilize
        if not self.wait_for_cluster_stable(timeout_minutes=30):
            self.logger.warning("Cluster did not stabilize after FT upgrade")
            return False
        
        self.logger.info(f"Successfully upgraded to FT{target_ft}")
        return True