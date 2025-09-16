#!/usr/bin/env python3
"""
Script to run Storage Policy RBAC tests
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def install_dependencies():
    """Install required dependencies."""
    logger.info("Installing dependencies...")
    try:
        subprocess.check_call(["python3", "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False
    return True


def setup_chrome_driver():
    """Setup Chrome driver for Selenium."""
    logger.info("Setting up Chrome driver...")
    try:
        # Install webdriver-manager to handle Chrome driver automatically
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        
        # This will automatically download and setup Chrome driver
        service = Service(ChromeDriverManager().install())
        logger.info("Chrome driver setup completed")
        return True
    except Exception as e:
        logger.error(f"Failed to setup Chrome driver: {e}")
        logger.info("Please ensure Chrome browser is installed")
        return False


def run_tests(test_type="all", verbose=True, headless=True):
    """
    Run the RBAC tests.
    
    Args:
        test_type: Type of tests to run ('all', 'unit', 'integration', 'slow')
        verbose: Enable verbose output
        headless: Run browser in headless mode
    """
    logger.info(f"Running {test_type} tests...")
    
    # Setup environment variables
    os.environ["BROWSER_HEADLESS"] = str(headless).lower()
    
    # Create necessary directories
    os.makedirs("reports", exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)
    
    # Build pytest command
    cmd = [
        "python3", "-m", "pytest",
        "testcases/cdp/stargate/storage_policy/rbac/test_storage_policy_rbac.py"
    ]
    
    if verbose:
        cmd.append("-v")
    
    # Add markers based on test type
    if test_type == "unit":
        cmd.extend(["-m", "not integration and not slow"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "slow":
        cmd.extend(["-m", "slow"])
    # For "all", no marker filter is added
    
    # Add HTML report
    cmd.extend(["--html=reports/rbac_test_report.html", "--self-contained-html"])
    
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=False, capture_output=False)
        if result.returncode == 0:
            logger.info("Tests completed successfully")
        else:
            logger.warning(f"Tests completed with exit code: {result.returncode}")
        return result.returncode
    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        return 1


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run Storage Policy RBAC tests")
    parser.add_argument(
        "--test-type", 
        choices=["all", "unit", "integration", "slow"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip dependency installation"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (not headless)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce verbosity"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Storage Policy RBAC test execution")
    
    # Install dependencies if not skipped
    if not args.no_install:
        if not install_dependencies():
            logger.error("Dependency installation failed")
            return 1
    
    # Setup Chrome driver
    if not setup_chrome_driver():
        logger.error("Chrome driver setup failed")
        return 1
    
    # Run tests
    exit_code = run_tests(
        test_type=args.test_type,
        verbose=not args.quiet,
        headless=not args.no_headless
    )
    
    # Print summary
    if exit_code == 0:
        logger.info("✅ All tests completed successfully")
        logger.info("📊 Check reports/rbac_test_report.html for detailed results")
    else:
        logger.warning("⚠️  Some tests failed or had issues")
        logger.info("📊 Check reports/rbac_test_report.html for detailed results")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())