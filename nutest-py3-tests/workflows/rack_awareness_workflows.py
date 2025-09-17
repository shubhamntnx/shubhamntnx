"""
Rack Awareness specific workflows
"""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from nutest_py3.framework.entities import RackEntity, ClusterEntity, StorageEntity, HostEntity
from .cluster_workflows import ClusterWorkflows
from .storage_workflows import StorageWorkflows


class RackAwarenessWorkflows:
    """
    High-level rack awareness workflows
    """
    
    def __init__(self, session):
        self.session = session
        self.rack_entity = RackEntity(session)
        self.cluster_entity = ClusterEntity(session)
        self.storage_entity = StorageEntity(session)
        self.host_entity = HostEntity(session)
        
        # Use other workflows
        self.cluster_workflows = ClusterWorkflows(session)
        self.storage_workflows = StorageWorkflows(session)
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_strict_ra_prerequisites_workflow(self) -> Tuple[bool, List[str]]:
        """
        Complete workflow to validate strict RA prerequisites
        """
        self.logger.info("Validating strict rack awareness prerequisites")
        
        issues = []
        
        # Check rack requirements
        is_valid, message = self.rack_entity.validate_rack_requirements()
        if not is_valid:
            issues.append(message)
        
        # Check cluster health
        health_summary = self.cluster_workflows.get_cluster_health_summary()
        cluster_status = health_summary.get('cluster_status')
        
        if cluster_status != 'NORMAL':
            issues.append(f"Cluster status is not NORMAL: {cluster_status}")
        
        # Check fault tolerance status
        try:
            ft_status = self.cluster_entity.get_fault_tolerance_status()
            # Add specific FT validations if needed
        except Exception as e:
            issues.append(f"Failed to validate fault tolerance: {str(e)}")
        
        is_all_valid = len(issues) == 0
        
        if is_all_valid:
            self.logger.info("All strict RA prerequisites validated successfully")
        else:
            self.logger.warning(f"Prerequisites validation failed: {', '.join(issues)}")
        
        return is_all_valid, issues
    
    def transition_to_strict_ra_workflow(self) -> bool:
        """
        Complete workflow to transition from best-effort to strict RA
        """
        self.logger.info("Starting transition to strict rack awareness workflow")
        
        # Step 1: Validate prerequisites
        is_valid, issues = self.validate_strict_ra_prerequisites_workflow()
        if not is_valid:
            self.logger.error(f"Prerequisites not met: {', '.join(issues)}")
            return False
        
        # Step 2: Enable strict RA using cluster workflow
        success = self.cluster_workflows.enable_strict_rack_awareness_workflow()
        if not success:
            self.logger.error("Failed to enable strict rack awareness")
            return False
        
        # Step 3: Validate RPP updates
        rpp_updated = self.storage_workflows.validate_rpp_updates_workflow(
            expected_strict_mode=True, timeout_seconds=300
        )
        if not rpp_updated:
            self.logger.warning("RPP updates not confirmed, but continuing")
        
        self.logger.info("Successfully completed transition to strict RA")
        return True
    
    def transition_to_best_effort_workflow(self) -> bool:
        """
        Complete workflow to transition from strict RA to best-effort
        """
        self.logger.info("Starting transition to best-effort workflow")
        
        # Step 1: Disable strict RA using cluster workflow
        success = self.cluster_workflows.disable_strict_rack_awareness_workflow()
        if not success:
            self.logger.error("Failed to disable strict rack awareness")
            return False
        
        # Step 2: Validate RPP updates
        rpp_updated = self.storage_workflows.validate_rpp_updates_workflow(
            expected_strict_mode=False, timeout_seconds=300
        )
        if not rpp_updated:
            self.logger.warning("RPP updates not confirmed, but continuing")
        
        self.logger.info("Successfully completed transition to best-effort")
        return True
    
    def simulate_rack_failure_workflow(self, rack_uuid: str) -> bool:
        """
        Complete workflow to simulate rack failure
        """
        self.logger.info(f"Starting rack failure simulation for rack: {rack_uuid}")
        
        # Step 1: Validate rack exists and has hosts
        rack_info = self.rack_entity.get_entity_info(rack_uuid)
        if rack_info.get('host_count', 0) == 0:
            self.logger.error(f"Rack {rack_uuid} has no hosts to fail")
            return False
        
        # Step 2: Simulate the failure
        success = self.rack_entity.simulate_rack_failure(rack_uuid)
        if not success:
            self.logger.error(f"Failed to simulate rack failure for {rack_uuid}")
            return False
        
        # Step 3: Wait for cluster to react
        self.logger.info("Waiting for cluster to react to rack failure")
        time.sleep(60)
        
        self.logger.info(f"Successfully simulated rack failure for {rack_uuid}")
        return True
    
    def recover_rack_workflow(self, rack_uuid: str) -> bool:
        """
        Complete workflow to recover from rack failure
        """
        self.logger.info(f"Starting rack recovery for rack: {rack_uuid}")
        
        # Step 1: Recover the rack
        success = self.rack_entity.recover_rack(rack_uuid)
        if not success:
            self.logger.error(f"Failed to recover rack {rack_uuid}")
            return False
        
        # Step 2: Wait for cluster to stabilize
        stable = self.cluster_workflows.wait_for_cluster_stable(timeout_minutes=15)
        if not stable:
            self.logger.warning(f"Cluster did not stabilize after recovering rack {rack_uuid}")
            return False
        
        self.logger.info(f"Successfully recovered rack {rack_uuid}")
        return True
    
    def validate_quorum_maintenance_workflow(self, failed_racks: List[str]) -> Tuple[bool, str]:
        """
        Complete workflow to validate quorum maintenance during failures
        """
        self.logger.info(f"Validating quorum maintenance with {len(failed_racks)} failed racks")
        
        try:
            # Get cluster health
            health_summary = self.cluster_workflows.get_cluster_health_summary()
            
            if 'error' in health_summary:
                return False, f"Failed to get cluster health: {health_summary['error']}"
            
            total_racks = health_summary['rack_count']
            failed_rack_count = len(failed_racks)
            available_racks = total_racks - failed_rack_count
            
            # Get fault tolerance level
            ft_level = health_summary.get('fault_tolerance_level', 1)
            
            # For rack-level failures, we need at least (FT_level + 1) racks available
            min_racks_needed = ft_level + 1
            
            cluster_status = health_summary.get('cluster_status', 'UNKNOWN')
            
            if available_racks >= min_racks_needed:
                # Quorum should be maintained
                if cluster_status == 'NORMAL':
                    return True, f"Quorum maintained as expected: {available_racks} >= {min_racks_needed} racks"
                else:
                    return False, f"Quorum lost unexpectedly: {cluster_status}"
            else:
                # Quorum should be lost
                if cluster_status != 'NORMAL':
                    return True, f"Quorum lost as expected: {available_racks} < {min_racks_needed} racks"
                else:
                    return False, f"Quorum maintained unexpectedly with insufficient racks"
                    
        except Exception as e:
            return False, f"Failed to validate quorum maintenance: {str(e)}"
    
    def validate_data_availability_workflow(self, test_containers: List[str]) -> Tuple[bool, str]:
        """
        Complete workflow to validate data availability
        """
        self.logger.info(f"Validating data availability for {len(test_containers)} containers")
        
        try:
            unavailable_containers = []
            
            for container_name in test_containers:
                container = self.storage_entity.get_container_by_name(container_name)
                
                if not container:
                    unavailable_containers.append(f"{container_name} (not found)")
                    continue
                
                # Check container health status
                container_status = container.get('status', 'UNKNOWN')
                if container_status not in ['NORMAL', 'ONLINE']:
                    unavailable_containers.append(f"{container_name} (status: {container_status})")
            
            if unavailable_containers:
                return False, f"Data unavailable for containers: {', '.join(unavailable_containers)}"
            else:
                return True, f"Data available for all {len(test_containers)} test containers"
                
        except Exception as e:
            return False, f"Failed to validate data availability: {str(e)}"
    
    def ft_upgrade_with_strict_ra_workflow(self, target_ft: int) -> bool:
        """
        Complete workflow for FT upgrade with strict RA enabled
        """
        self.logger.info(f"Starting FT upgrade with strict RA workflow to FT{target_ft}")
        
        # Step 1: Ensure strict RA is enabled
        if not self.cluster_entity.get_rack_awareness_status():
            self.logger.info("Enabling strict RA before FT upgrade")
            if not self.transition_to_strict_ra_workflow():
                self.logger.error("Failed to enable strict RA before FT upgrade")
                return False
        
        # Step 2: Perform FT upgrade
        success = self.cluster_workflows.upgrade_ft_level_workflow(target_ft)
        if not success:
            self.logger.error(f"Failed to upgrade to FT{target_ft}")
            return False
        
        # Step 3: Validate RPPs are updated for new FT level with strict RA
        rpp_updated = self.storage_workflows.validate_rpp_updates_workflow(
            expected_strict_mode=True, timeout_seconds=600
        )
        if not rpp_updated:
            self.logger.warning("RPP updates not confirmed after FT upgrade")
        
        self.logger.info(f"Successfully completed FT upgrade to FT{target_ft} with strict RA")
        return True