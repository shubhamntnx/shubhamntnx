#!/usr/bin/env python3
"""
Nutanix Test Runner

This script runs tests based on the configuration pattern described.
Test format: "package.module.ClassName.test_method_name"
"""

import sys
import json
import logging
import importlib
import time
import argparse
from typing import Dict, Any, List
from pathlib import Path

# Add the framework to the path
sys.path.append('/workspace')

from nutest_py3.framework.session import Session


class TestRunner:
    """
    Test runner that executes tests based on configuration
    """
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = {}
        self.session = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load configuration
        self._load_config()
        
        # Setup session
        self._setup_session()
    
    def _load_config(self):
        """Load test configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            
            self.logger.info(f"Loaded configuration from {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise
    
    def _setup_session(self):
        """Setup API session based on configuration"""
        try:
            # Find cluster configuration (look for first class-level config)
            cluster_config = None
            
            for key, value in self.config.items():
                if isinstance(value, dict) and 'cluster_ip' in value:
                    cluster_config = value
                    break
            
            if not cluster_config:
                raise RuntimeError("No cluster configuration found in config file")
            
            # Create session
            self.session = Session(
                cluster_ip=cluster_config['cluster_ip'],
                username=cluster_config['cluster_username'],
                password=cluster_config['cluster_password'],
                port=cluster_config.get('cluster_port', 9440),
                use_https=cluster_config.get('use_https', True)
            )
            
            self.logger.info(f"Session created for cluster: {cluster_config['cluster_ip']}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup session: {str(e)}")
            raise
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all tests found in configuration"""
        test_results = []
        
        # Find all test methods in configuration
        test_methods = self._find_test_methods()
        
        self.logger.info(f"Found {len(test_methods)} test methods to execute")
        
        for test_method in test_methods:
            self.logger.info(f"Running test: {test_method}")
            
            try:
                result = self._run_single_test(test_method)
                test_results.append(result)
                
            except Exception as e:
                self.logger.error(f"Test {test_method} failed with exception: {str(e)}")
                test_results.append({
                    'test_name': test_method,
                    'status': 'ERROR',
                    'message': str(e),
                    'elapsed_time_seconds': 0
                })
        
        return test_results
    
    def run_specific_test(self, test_name: str) -> Dict[str, Any]:
        """Run a specific test method"""
        self.logger.info(f"Running specific test: {test_name}")
        
        try:
            return self._run_single_test(test_name)
            
        except Exception as e:
            self.logger.error(f"Test {test_name} failed with exception: {str(e)}")
            return {
                'test_name': test_name,
                'status': 'ERROR',
                'message': str(e),
                'elapsed_time_seconds': 0
            }
    
    def _find_test_methods(self) -> List[str]:
        """Find all test methods in configuration"""
        test_methods = []
        
        for key in self.config.keys():
            # Check if this is a test method (contains test_ and has 4+ parts)
            parts = key.split('.')
            if len(parts) >= 4 and 'test_' in parts[-1]:
                test_methods.append(key)
        
        return sorted(test_methods)
    
    def _run_single_test(self, test_method: str) -> Dict[str, Any]:
        """Run a single test method"""
        start_time = time.time()
        
        try:
            # Parse test method string
            # Format: "package.module.ClassName.test_method_name"
            parts = test_method.split('.')
            
            if len(parts) < 4:
                raise ValueError(f"Invalid test method format: {test_method}")
            
            # Extract components
            package_parts = parts[:-2]  # Everything except ClassName and method
            class_name = parts[-2]
            method_name = parts[-1]
            
            # Build module path
            module_path = f"nutest_py3_tests.testcases.{'.'.join(package_parts)}"
            
            self.logger.debug(f"Importing module: {module_path}")
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the test class
            test_class = getattr(module, class_name)
            
            # Get test parameters for this method and class
            class_key = '.'.join(parts[:-1])  # Everything except method name
            test_params = self.config.get(class_key, {})
            method_params = self.config.get(test_method, {})
            
            # Merge parameters (method params override class params)
            combined_params = {**test_params, **method_params}
            
            self.logger.debug(f"Test parameters: {combined_params}")
            
            # Create test instance
            test_instance = test_class(self.session, combined_params)
            
            # Run test lifecycle
            try:
                # Setup
                test_instance.setup()
                
                # Execute test method
                test_method_func = getattr(test_instance, method_name)
                result = test_method_func()
                
                # Ensure result is a dict
                if not isinstance(result, dict):
                    result = {
                        'status': 'PASSED',
                        'message': 'Test completed successfully',
                        'result_data': result
                    }
                
            finally:
                # Teardown
                try:
                    test_instance.teardown()
                except Exception as e:
                    self.logger.warning(f"Teardown failed for {test_method}: {str(e)}")
            
            # Add test metadata
            result['test_name'] = test_method
            result['elapsed_time_seconds'] = time.time() - start_time
            
            self.logger.info(f"Test {test_method} completed: {result.get('status', 'UNKNOWN')}")
            
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Test {test_method} failed: {str(e)}")
            
            return {
                'test_name': test_method,
                'status': 'FAILED',
                'message': str(e),
                'elapsed_time_seconds': elapsed_time
            }
    
    def generate_report(self, test_results: List[Dict[str, Any]]):
        """Generate test report"""
        self.logger.info("=" * 80)
        self.logger.info("TEST EXECUTION REPORT")
        self.logger.info("=" * 80)
        
        # Count results by status
        status_counts = {}
        total_time = 0
        
        for result in test_results:
            status = result.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
            total_time += result.get('elapsed_time_seconds', 0)
        
        # Summary
        total_tests = len(test_results)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {status_counts.get('PASSED', 0)}")
        self.logger.info(f"Failed: {status_counts.get('FAILED', 0)}")
        self.logger.info(f"Errors: {status_counts.get('ERROR', 0)}")
        self.logger.info(f"Total Time: {total_time:.2f} seconds")
        
        # Individual results
        self.logger.info("\nDetailed Results:")
        self.logger.info("-" * 80)
        
        for result in test_results:
            status = result.get('status', 'UNKNOWN')
            test_name = result.get('test_name', 'Unknown')
            elapsed_time = result.get('elapsed_time_seconds', 0)
            message = result.get('message', '')
            
            status_symbol = {
                'PASSED': '✓',
                'FAILED': '✗',
                'ERROR': '⚠'
            }.get(status, '?')
            
            self.logger.info(f"{status_symbol} {test_name:<60} {status:<8} {elapsed_time:>8.2f}s")
            
            if status != 'PASSED' and message:
                self.logger.info(f"    {message}")
        
        # Success rate
        success_rate = (status_counts.get('PASSED', 0) / total_tests * 100) if total_tests > 0 else 0
        self.logger.info(f"\nSuccess Rate: {success_rate:.1f}%")
        self.logger.info("=" * 80)


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/nutest_runner.log')
        ]
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run Nutanix CDP Tests')
    
    parser.add_argument('--config', '-c',
                       default='/workspace/nutest-py3-tests/testcases/cdp/strict_rack_awareness/config.json',
                       help='Path to test configuration file')
    
    parser.add_argument('--test', '-t',
                       help='Run specific test by name')
    
    parser.add_argument('--log-level', '-l',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logger = logging.getLogger('main')
    
    try:
        # Create test runner
        runner = TestRunner(args.config)
        
        if args.test:
            # Run specific test
            result = runner.run_specific_test(args.test)
            runner.generate_report([result])
            
            if result.get('status') == 'PASSED':
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            # Run all tests
            results = runner.run_all_tests()
            runner.generate_report(results)
            
            # Check if all tests passed
            failed_tests = [r for r in results if r.get('status') != 'PASSED']
            
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