"""
Test Result Classes
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json


class TestStatus(Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """
    Class to store test execution results
    """
    test_name: str = ""
    description: str = ""
    status: TestStatus = TestStatus.NOT_STARTED
    duration_seconds: float = 0.0
    error_message: str = ""
    stack_trace: str = ""
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary"""
        return {
            "test_name": self.test_name,
            "description": self.description,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "logs": self.logs,
            "metrics": self.metrics,
            "artifacts": self.artifacts
        }
    
    def to_json(self) -> str:
        """Convert test result to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def add_log(self, message: str) -> None:
        """Add a log message to the test result"""
        self.logs.append(message)
    
    def add_metric(self, name: str, value: Any) -> None:
        """Add a metric to the test result"""
        self.metrics[name] = value
    
    def add_artifact(self, name: str, path: str) -> None:
        """Add an artifact to the test result"""
        self.artifacts[name] = path