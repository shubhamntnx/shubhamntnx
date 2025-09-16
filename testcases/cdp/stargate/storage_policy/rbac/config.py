"""
Configuration file for Storage Policy RBAC tests
"""

import os
from typing import Dict, Any

class RBACTestConfig:
    """Configuration class for RBAC tests."""
    
    # Prism Central Configuration
    PRISM_CENTRAL_URL = os.getenv("PRISM_CENTRAL_URL", "https://10.46.100.3:9440/")
    
    # Browser Configuration
    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30"))
    
    # Test Configuration
    ENABLE_SCREENSHOTS = os.getenv("ENABLE_SCREENSHOTS", "true").lower() == "true"
    SCREENSHOT_PATH = os.getenv("SCREENSHOT_PATH", "screenshots/")
    REPORT_PATH = os.getenv("REPORT_PATH", "reports/")
    
    # Credentials Configuration
    # In production, these should be loaded from a secure credential store
    USER_CREDENTIALS = {
        'vo_user2@qa.nutanix.com': os.getenv('VO_USER2_PASSWORD', 'password123'),
        'vo_user4@qa.nutanix.com': os.getenv('VO_USER4_PASSWORD', 'password123'),
        'ca_user21@qa.nutanix.com': os.getenv('CA_USER21_PASSWORD', 'password123'),
        'vo_user3@qa.nutanix.com': os.getenv('VO_USER3_PASSWORD', 'password123'),
        'ca_user12@qa.nutanix.com': os.getenv('CA_USER12_PASSWORD', 'password123'),
        'ca_user11@qa.nutanix.com': os.getenv('CA_USER11_PASSWORD', 'password123'),
        'ca_user13@qa.nutanix.com': os.getenv('CA_USER13_PASSWORD', 'password123'),
        'ca_user14@qa.nutanix.com': os.getenv('CA_USER14_PASSWORD', 'password123'),
        'cdp_user2@qa.nutanix.com': os.getenv('CDP_USER2_PASSWORD', 'password123'),
        'cdp_user1@qa.nutanix.com': os.getenv('CDP_USER1_PASSWORD', 'password123'),
        'cdp_user3@qa.nutanix.com': os.getenv('CDP_USER3_PASSWORD', 'password123'),
        'cdp_user4@qa.nutanix.com': os.getenv('CDP_USER4_PASSWORD', 'password123'),
        'ca_user19@qa.nutanix.com': os.getenv('CA_USER19_PASSWORD', 'password123'),
        'ca_user17@qa.nutanix.com': os.getenv('CA_USER17_PASSWORD', 'password123'),
        'ca_user20@qa.nutanix.com': os.getenv('CA_USER20_PASSWORD', 'password123'),
        'ca_user18@qa.nutanix.com': os.getenv('CA_USER18_PASSWORD', 'password123'),
        'vo_user7@qa.nutanix.com': os.getenv('VO_USER7_PASSWORD', 'password123'),
        'vo_user8@qa.nutanix.com': os.getenv('VO_USER8_PASSWORD', 'password123'),
        'vo_user9@qa.nutanix.com': os.getenv('VO_USER9_PASSWORD', 'password123'),
        'ca_user1@qa.nutanix.com': os.getenv('CA_USER1_PASSWORD', 'password123'),
        'ca_user3@qa.nutanix.com': os.getenv('CA_USER3_PASSWORD', 'password123'),
        'ca_user2@qa.nutanix.com': os.getenv('CA_USER2_PASSWORD', 'password123'),
        'ca_user4@qa.nutanix.com': os.getenv('CA_USER4_PASSWORD', 'password123'),
        'ca_user16@qa.nutanix.com': os.getenv('CA_USER16_PASSWORD', 'password123')
    }
    
    # Test Execution Configuration
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary."""
        return {
            'prism_central_url': cls.PRISM_CENTRAL_URL,
            'browser_headless': cls.BROWSER_HEADLESS,
            'browser_timeout': cls.BROWSER_TIMEOUT,
            'enable_screenshots': cls.ENABLE_SCREENSHOTS,
            'screenshot_path': cls.SCREENSHOT_PATH,
            'report_path': cls.REPORT_PATH,
            'user_credentials': cls.USER_CREDENTIALS,
            'max_retry_attempts': cls.MAX_RETRY_ATTEMPTS,
            'retry_delay': cls.RETRY_DELAY
        }
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories for test execution."""
        os.makedirs(cls.SCREENSHOT_PATH, exist_ok=True)
        os.makedirs(cls.REPORT_PATH, exist_ok=True)