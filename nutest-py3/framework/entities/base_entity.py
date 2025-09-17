"""
Base Entity for Nutanix Framework
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseEntity(ABC):
    """
    Base class for all Nutanix entities
    """
    
    def __init__(self, session=None):
        self.session = session
        self.logger = logging.getLogger(self.__class__.__name__)
        self._entity_data = {}
    
    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Return the entity type"""
        pass
    
    @abstractmethod
    def get_entity_info(self, entity_uuid: str) -> Dict[str, Any]:
        """Get entity information by UUID"""
        pass
    
    @abstractmethod
    def list_entities(self, **kwargs) -> Dict[str, Any]:
        """List all entities of this type"""
        pass
    
    def update_entity_data(self, data: Dict[str, Any]) -> None:
        """Update cached entity data"""
        self._entity_data.update(data)
    
    def get_cached_data(self, key: str, default=None) -> Any:
        """Get cached entity data"""
        return self._entity_data.get(key, default)