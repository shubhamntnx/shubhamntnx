"""
Base Test Class for Nutanix CDP Tests
"""

import time
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum

from .test_result import TestResult, TestStatus
from .test_config import TestConfig
from .cluster_manager import ClusterManager
from .api_client import APIClient


class TestPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class BaseTest(ABC):
    """
    Base class for all Nutanix CDP tests
    """
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cluster_manager = ClusterManager(config)
        self.api_client = APIClient(config)
        self.test_result = TestResult()
        self.start_time = None
        self.end_time = None
        
    @property
    @abstractmethod
    def test_name(self) -> str:
        """Return the name of the test"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the description of the test"""
        pass
    
    @property
    def priority(self) -> TestPriority:
        """Return the priority of the test (default: MEDIUM)"""
        return TestPriority.MEDIUM
    
    @property
    def timeout_minutes(self) -> int:
        """Return the timeout for the test in minutes (default: 30)"""
        return 30
    
    @property
    def prerequisites(self) -> List[str]:
        """Return list of prerequisites for the test"""
        return []
    
    def setup(self) -> None:
        """Setup method called before test execution"""
        self.logger.info(f"Setting up test: {self.test_name}")
        self._validate_prerequisites()
        
    def teardown(self) -> None:
        """Teardown method called after test execution"""
        self.logger.info(f"Tearing down test: {self.test_name}")
        
    @abstractmethod
    def execute(self) -> None:
        """Main test execution logic"""
        pass
    
    def run(self) -> TestResult:
        """
        Run the complete test lifecycle
        """
        self.start_time = time.time()
        self.test_result.test_name = self.test_name
        self.test_result.description = self.description
        
        try:
            self.logger.info(f"Starting test: {self.test_name}")
            self.test_result.status = TestStatus.RUNNING
            
            # Setup
            self.setup()
            
            # Execute main test logic
            self.execute()
            
            # If we reach here, test passed
            self.test_result.status = TestStatus.PASSED
            self.logger.info(f"Test passed: {self.test_name}")
            
        except AssertionError as e:
            self.test_result.status = TestStatus.FAILED
            self.test_result.error_message = str(e)
            self.test_result.stack_trace = traceback.format_exc()
            self.logger.error(f"Test failed: {self.test_name} - {str(e)}")
            
        except Exception as e:
            self.test_result.status = TestStatus.ERROR
            self.test_result.error_message = str(e)
            self.test_result.stack_trace = traceback.format_exc()
            self.logger.error(f"Test error: {self.test_name} - {str(e)}")
            
        finally:
            try:
                self.teardown()
            except Exception as e:
                self.logger.warning(f"Teardown failed: {str(e)}")
                
            self.end_time = time.time()
            self.test_result.duration_seconds = self.end_time - self.start_time
            
        return self.test_result
    
    def _validate_prerequisites(self) -> None:
        """Validate test prerequisites"""
        for prereq in self.prerequisites:
            self.logger.debug(f"Validating prerequisite: {prereq}")
            # Add prerequisite validation logic here
    
    def assert_true(self, condition: bool, message: str = "") -> None:
        """Assert that condition is True"""
        if not condition:
            raise AssertionError(f"Assertion failed: {message}")
    
    def assert_false(self, condition: bool, message: str = "") -> None:
        """Assert that condition is False"""
        if condition:
            raise AssertionError(f"Assertion failed: {message}")
    
    def assert_equal(self, actual: Any, expected: Any, message: str = "") -> None:
        """Assert that actual equals expected"""
        if actual != expected:
            raise AssertionError(f"Assertion failed: Expected {expected}, got {actual}. {message}")
    
    def assert_not_equal(self, actual: Any, expected: Any, message: str = "") -> None:
        """Assert that actual does not equal expected"""
        if actual == expected:
            raise AssertionError(f"Assertion failed: Expected {actual} != {expected}. {message}")
    
    def assert_in(self, item: Any, container: Any, message: str = "") -> None:
        """Assert that item is in container"""
        if item not in container:
            raise AssertionError(f"Assertion failed: {item} not found in {container}. {message}")
    
    def wait_for_condition(self, condition_func, timeout_seconds: int = 300, 
                          poll_interval: int = 5, description: str = "") -> bool:
        """
        Wait for a condition to become true
        
        Args:
            condition_func: Function that returns True when condition is met
            timeout_seconds: Maximum time to wait
            poll_interval: Time between checks
            description: Description of what we're waiting for
            
        Returns:
            True if condition was met, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                if condition_func():
                    self.logger.info(f"Condition met: {description}")
                    return True
            except Exception as e:
                self.logger.debug(f"Condition check failed: {str(e)}")
            
            time.sleep(poll_interval)
            
        self.logger.warning(f"Timeout waiting for condition: {description}")
        return False