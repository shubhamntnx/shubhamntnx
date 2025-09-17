"""
Strict Rack Awareness Test Package

This package contains comprehensive tests for Nutanix CDP strict rack awareness functionality.
"""

__version__ = "1.0.0"
__author__ = "Nutanix CDP Test Team"

from .tests.test_transition_best_effort_to_strict_ra import TransitionBestEffortToStrictRATest
from .tests.test_transition_strict_ra_to_best_effort import TransitionStrictRATobestEffortTest
from .tests.test_ft1_to_ft2_with_strict_ra import FT1ToFT2WithStrictRATest
from .tests.test_validate_cluster_config_apis import ValidateClusterConfigAPIsTest
from .tests.test_simulate_rack_failure_and_validate_quorum import SimulateRackFailureAndValidateQuorumTest
from .tests.test_validate_skewed_cluster_behavior import ValidateSkewedClusterBehaviorTest
from .tests.test_validate_storage_policy_enforcement import ValidateStoragePolicyEnforcementTest

__all__ = [
    "TransitionBestEffortToStrictRATest",
    "TransitionStrictRATobestEffortTest", 
    "FT1ToFT2WithStrictRATest",
    "ValidateClusterConfigAPIsTest",
    "SimulateRackFailureAndValidateQuorumTest",
    "ValidateSkewedClusterBehaviorTest",
    "ValidateStoragePolicyEnforcementTest"
]