#!/usr/bin/env python3
"""
Strict Rack Awareness Test Runner

This script runs all the strict rack awareness tests in sequence or parallel.
"""

import sys
import time
import logging
import argparse
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the framework to the path
sys.path.append('/workspace')

from nutest_py3.framework import TestConfig, TestResult, TestStatus
from testcases.cdp.strict_rack_awareness.tests.test_transition_best_effort_to_strict_ra import TransitionBestEffortToStrictRATest
from testcases.cdp.strict_rack_awareness.tests.test_transition_strict_ra_to_best_effort import TransitionStrictRATobestEffortTest
from testcases.cdp.strict_rack_awareness.tests.test_ft1_to_ft2_with_strict_ra import FT1ToFT2WithStrictRATest
from testcases.cdp.strict_rack_awareness.tests.test_validate_cluster_config_apis import ValidateClusterConfigAPIsTest
from testcases.cdp.strict_rack_awareness.tests.test_simulate_rack_failure_and_validate_quorum import SimulateRackFailureAndValidateQuorumTest
from testcases.cdp.strict_rack_awareness.tests.test_validate_skewed_cluster_behavior import ValidateSkewedClusterBehaviorTest
from testcases.cdp.strict_rack_awareness.tests.test_validate_storage_policy_enforcement import ValidateStoragePolicyEnforcementTest


class TestRunner:
    """
    Test runner for strict rack awareness tests
    """
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_results = []
        
        # Define test classes in execution order
        self.test_classes = [
            ValidateClusterConfigAPIsTest,  # Start with API validation
            TransitionBestEffortToStrictRATest,  # Test enabling strict RA
            TransitionStrictRATobestEffortTest,  # Test disabling strict RA
            ValidateStoragePolicyEnforcementTest,  # Test policy enforcement
            FT1ToFT2WithStrictRATest,  # Test FT upgrade
            ValidateSkewedClusterBehaviorTest,  # Test skewed scenarios
            SimulateRackFailureAndValidateQuorumTest,  # Test failure scenarios (last due to potential disruption)
        ]
    
    def run_all_tests(self, parallel: bool = False) -> List[TestResult]:
        """
        Run all tests either in sequence or parallel
        
        Args:
            parallel: Whether to run tests in parallel
            
        Returns:
            List of test results
        """
        self.logger.info(f"Starting strict rack awareness test suite ({len(self.test_classes)} tests)")
        
        start_time = time.time()
        
        if parallel and self.config.parallel_execution:
            results = self._run_tests_parallel()
        else:
            results = self._run_tests_sequential()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        self.logger.info(f"Test suite completed in {total_duration:.2f} seconds")
        
        # Generate summary
        self._generate_test_summary(results, total_duration)
        
        return results
    
    def _run_tests_sequential(self) -> List[TestResult]:
        """Run tests sequentially"""
        self.logger.info("Running tests sequentially")
        
        results = []
        
        for i, test_class in enumerate(self.test_classes, 1):
            self.logger.info(f"Running test {i}/{len(self.test_classes)}: {test_class.__name__}")
            
            try:
                test_instance = test_class(self.config)
                result = test_instance.run()
                results.append(result)
                
                self.logger.info(f"Test {test_class.__name__} completed: {result.status.value}")
                
                # Add delay between tests if configured
                if hasattr(self.config, 'inter_test_delay_seconds'):
                    time.sleep(self.config.inter_test_delay_seconds)
                    
            except Exception as e:
                self.logger.error(f"Test {test_class.__name__} failed with exception: {str(e)}")
                
                # Create error result
                error_result = TestResult()
                error_result.test_name = test_class.__name__
                error_result.status = TestStatus.ERROR
                error_result.error_message = str(e)
                results.append(error_result)
        
        return results
    
    def _run_tests_parallel(self) -> List[TestResult]:
        """Run tests in parallel"""
        self.logger.info(f"Running tests in parallel (max {self.config.max_parallel_tests} concurrent)")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_parallel_tests) as executor:
            # Submit all tests
            future_to_test = {
                executor.submit(self._run_single_test, test_class): test_class
                for test_class in self.test_classes
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_test):
                test_class = future_to_test[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Test {test_class.__name__} completed: {result.status.value}")
                    
                except Exception as e:
                    self.logger.error(f"Test {test_class.__name__} failed with exception: {str(e)}")
                    
                    # Create error result
                    error_result = TestResult()
                    error_result.test_name = test_class.__name__
                    error_result.status = TestStatus.ERROR
                    error_result.error_message = str(e)
                    results.append(error_result)
        
        return results
    
    def _run_single_test(self, test_class) -> TestResult:
        """Run a single test"""
        test_instance = test_class(self.config)
        return test_instance.run()
    
    def _generate_test_summary(self, results: List[TestResult], total_duration: float) -> None:
        """Generate and log test summary"""
        self.logger.info("=" * 80)
        self.logger.info("STRICT RACK AWARENESS TEST SUITE SUMMARY")
        self.logger.info("=" * 80)
        
        # Count results by status
        status_counts = {
            TestStatus.PASSED: 0,
            TestStatus.FAILED: 0,
            TestStatus.ERROR: 0,
            TestStatus.SKIPPED: 0
        }
        
        for result in results:
            status_counts[result.status] += 1
        
        # Log summary
        total_tests = len(results)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {status_counts[TestStatus.PASSED]}")
        self.logger.info(f"Failed: {status_counts[TestStatus.FAILED]}")
        self.logger.info(f"Errors: {status_counts[TestStatus.ERROR]}")
        self.logger.info(f"Skipped: {status_counts[TestStatus.SKIPPED]}")
        self.logger.info(f"Total Duration: {total_duration:.2f} seconds")
        
        # Log individual test results
        self.logger.info("\nIndividual Test Results:")
        self.logger.info("-" * 80)
        
        for result in results:
            status_symbol = {
                TestStatus.PASSED: "✓",
                TestStatus.FAILED: "✗",
                TestStatus.ERROR: "⚠",
                TestStatus.SKIPPED: "○"
            }.get(result.status, "?")
            
            self.logger.info(
                f"{status_symbol} {result.test_name:<50} "
                f"{result.status.value:<10} "
                f"{result.duration_seconds:>8.2f}s"
            )
            
            if result.error_message:
                self.logger.info(f"    Error: {result.error_message}")
        
        # Calculate success rate
        success_rate = (status_counts[TestStatus.PASSED] / total_tests * 100) if total_tests > 0 else 0
        self.logger.info(f"\nSuccess Rate: {success_rate:.1f}%")
        
        self.logger.info("=" * 80)
    
    def run_specific_test(self, test_name: str) -> TestResult:
        """
        Run a specific test by name
        
        Args:
            test_name: Name of the test to run
            
        Returns:
            Test result
        """
        test_class = None
        
        for cls in self.test_classes:
            if cls.__name__.lower() == test_name.lower() or cls.__name__ == test_name:
                test_class = cls
                break
        
        if not test_class:
            raise ValueError(f"Test not found: {test_name}")
        
        self.logger.info(f"Running specific test: {test_class.__name__}")
        
        test_instance = test_class(self.config)
        result = test_instance.run()
        
        self.logger.info(f"Test {test_class.__name__} completed: {result.status.value}")
        
        return result


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """Setup logging configuration"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # Setup file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run Strict Rack Awareness Tests')
    
    parser.add_argument('--config', '-c', 
                       default='/workspace/testcases/cdp/strict_rack_awareness/config.json',
                       help='Path to test configuration file')
    
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='Run tests in parallel')
    
    parser.add_argument('--test', '-t', 
                       help='Run specific test by name')
    
    parser.add_argument('--log-level', '-l', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Logging level')
    
    parser.add_argument('--log-file', 
                       help='Log file path')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    logger = logging.getLogger('main')
    
    try:
        # Load configuration
        if args.config:
            config = TestConfig.from_file(args.config)
        else:
            config = TestConfig.from_env()
        
        # Create test runner
        runner = TestRunner(config)
        
        if args.test:
            # Run specific test
            result = runner.run_specific_test(args.test)
            
            if result.status == TestStatus.PASSED:
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            # Run all tests
            results = runner.run_all_tests(parallel=args.parallel)
            
            # Check if all tests passed
            failed_tests = [r for r in results if r.status != TestStatus.PASSED]
            
            if failed_tests:
                logger.error(f"{len(failed_tests)} tests failed or had errors")
                sys.exit(1)
            else:
                logger.info("All tests passed!")
                sys.exit(0)
                
    except Exception as e:
        logger.error(f"Test runner failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()