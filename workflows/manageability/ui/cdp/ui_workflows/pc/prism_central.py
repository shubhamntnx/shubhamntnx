"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: shubham.shrivastava@nutanix.com

This module contains the main PrismCentral UI workflow class.
"""

import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from framework.lib.nulog import INFO, DEBUG, ERROR, STEP
from framework.exceptions.nutest_error import NuTestError

from workflows.manageability.ui.cdp.ui_workflows.pc.storage.storage_policies import StoragePolicies


class Storage:
    """Storage workflows container class."""
    
    def __init__(self, pc_dashboard):
        """Initialize Storage workflows."""
        self.pc_dashboard = pc_dashboard
        self.storage_policies = StoragePolicies(pc_dashboard)


class PrismCentral:
    """
    Main PrismCentral UI workflow class for automating Prism Central operations.
    """
    
    def __init__(self, test_args, pc_ip=None):
        """
        Initialize PrismCentral UI workflow.
        
        Args:
            test_args: Test arguments dictionary
            pc_ip: Prism Central IP address
        """
        self.test_args = test_args
        self.pc_ip = pc_ip or test_args.get('pc_ip')
        self.pc_user = test_args.get('pc_user', 'admin')
        self.pc_passwd = test_args.get('pc_passwd', 'admin')
        self.selenium_server = test_args.get('selenium_server')
        
        # Initialize driver
        self.driver = None
        self.wait = None
        
        # Initialize workflow modules
        self.storage = None
        
        # Setup browser and login
        self._setup_driver()
        self._login_to_prism_central()
        
        # Initialize workflow modules after login
        self.storage = Storage(self)
    
    def _setup_driver(self):
        """Setup Chrome WebDriver for UI automation."""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-extensions')
            
            # Use headless mode if specified
            if self.test_args.get('headless', True):
                chrome_options.add_argument('--headless')
            
            # Setup remote driver if selenium server is specified
            if self.selenium_server:
                from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
                chrome_options.add_experimental_option("useAutomationExtension", False)
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                
                self.driver = webdriver.Remote(
                    command_executor=f'http://{self.selenium_server}:4444/wd/hub',
                    desired_capabilities=DesiredCapabilities.CHROME,
                    options=chrome_options
                )
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.wait = WebDriverWait(self.driver, 30)
            
            INFO("Chrome WebDriver setup completed successfully")
            
        except Exception as e:
            ERROR(f"Failed to setup Chrome WebDriver: {str(e)}")
            raise NuTestError(f"WebDriver setup failed: {str(e)}")
    
    def _login_to_prism_central(self):
        """Login to Prism Central with provided credentials."""
        try:
            prism_url = f"https://{self.pc_ip}:9440/"
            INFO(f"Navigating to Prism Central: {prism_url}")
            
            self.driver.get(prism_url)
            
            # Wait for login form to load
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            
            # Enter credentials
            username_field.clear()
            username_field.send_keys(self.pc_user)
            password_field.clear()
            password_field.send_keys(self.pc_passwd)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for successful login (dashboard or main page)
            self.wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CLASS_NAME, "dashboard")),
                    EC.presence_of_element_located((By.CLASS_NAME, "main-content")),
                    EC.url_contains("dashboard"),
                    EC.url_contains("home")
                )
            )
            
            INFO(f"Successfully logged in to Prism Central as {self.pc_user}")
            
        except TimeoutException:
            ERROR(f"Login failed for user {self.pc_user}")
            raise NuTestError(f"Login to Prism Central failed for user {self.pc_user}")
        except Exception as e:
            ERROR(f"Error during login: {str(e)}")
            raise NuTestError(f"Login error: {str(e)}")
    
    def logout(self):
        """Logout from Prism Central."""
        try:
            # Look for logout/profile menu
            logout_selectors = [
                "//a[contains(text(), 'Logout') or contains(text(), 'Sign Out')]",
                "//button[contains(text(), 'Logout') or contains(text(), 'Sign Out')]",
                "//div[contains(@class, 'user-menu')]//a[contains(text(), 'Logout')]",
                "//span[contains(@class, 'logout')]",
                "//i[contains(@class, 'logout')]"
            ]
            
            for selector in logout_selectors:
                try:
                    logout_element = self.driver.find_element(By.XPATH, selector)
                    logout_element.click()
                    time.sleep(2)
                    INFO("Successfully logged out from Prism Central")
                    return True
                except:
                    continue
            
            # If no logout button found, clear session by navigating to login page
            self.driver.get(f"https://{self.pc_ip}:9440/login")
            INFO("Logged out by navigating to login page")
            return True
            
        except Exception as e:
            ERROR(f"Error during logout: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up WebDriver resources."""
        try:
            if self.driver:
                self.logout()
                self.driver.quit()
                self.driver = None
                self.wait = None
                INFO("WebDriver cleanup completed")
        except Exception as e:
            DEBUG(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()