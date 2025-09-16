"""
Storage Policy RBAC Helper Module

This module provides utilities for verifying Role-Based Access Control (RBAC) 
for storage policies in Prism Central UI.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

logger = logging.getLogger(__name__)


class StoragePolicyRBACHelper:
    """Helper class for Storage Policy RBAC verification in Prism Central UI."""
    
    def __init__(self, prism_central_url: str = "https://10.46.100.3:9440/"):
        """
        Initialize the RBAC helper.
        
        Args:
            prism_central_url: URL of the Prism Central instance
        """
        self.prism_central_url = prism_central_url
        self.driver = None
        self.wait = None
        
        # User entities data structure
        self.user_entities = {
            'vo_user2@qa.nutanix.com': {
                'category': ['c222da3c-4d38-48df-6701-34255b2e4ae5',
                           '8ad71460-299e-4ca9-712b-057ea1d3170c',
                           '8ec4c0a7-f877-4d2c-6b77-be28a6bcd3be',
                           'ALL',
                           '9c64b796-fcb2-4aa1-6bb7-61334bc40014'],
                'sps': ['SP2', 'Del_SP2', 'SP1', 'Del_SP1']
            },
            'vo_user4@qa.nutanix.com': {
                'category': ['82ab3d45-212e-43e7-6614-474976afc577'],
                'sps': ['SP1', 'SP2', 'Del_SP2']
            },
            'ca_user21@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['SP5', 'SP4', 'Del_SP4', 'Del_SP2']
            },
            'vo_user3@qa.nutanix.com': {
                'category': ['c222da3c-4d38-48df-6701-34255b2e4ae5',
                           '49adf393-b404-47a0-7f5e-09951f0eec0e',
                           '9a121a3c-91fe-4f58-60b1-120b995b78b4',
                           '807facc3-7fed-42b8-46e5-191b3474680b',
                           '0b204dc8-3c96-4221-6981-7f2a89a27a0c',
                           '6db3cfe6-1316-48d3-46de-5bb6547884aa'],
                'sps': ['SP1', 'Del_SP3', 'SP3', 'SP4', 'Del_SP4', 'SP2']
            },
            'ca_user12@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            },
            'ca_user11@qa.nutanix.com': {
                'category': ['e127a91d-5848-405f-58bf-d5eb5f2093e3',
                           'f9f9666c-cac0-4bf6-7e48-d104c404d465',
                           'a4fcfe42-2223-4713-61e4-1254972e0870',
                           'f317f55f-5e57-42be-4b05-237e85c86419',
                           'ALL'],
                'sps': ['SP5', 'DEL_SP6', 'SP3', 'DEL_SP5', 'SP6', 'Del_SP1', 'Del_SP2']
            },
            'ca_user13@qa.nutanix.com': {
                'category': ['c222da3c-4d38-48df-6701-34255b2e4ae5',
                           '24fd6fc6-d447-41c4-44fb-083fb167f6a6',
                           '12ce9e15-e853-4f76-61d5-12f0bad0fe3e',
                           '63964a96-4ded-42bb-494c-2a6dfaa3b938',
                           'ALL'],
                'sps': ['SP1', 'SP7', 'SP3', 'DEL_SP8', 'DEL_SP7', 'Del_SP2']
            },
            'ca_user14@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            },
            'cdp_user2@qa.nutanix.com': {
                'category': ['ALL', '4d72e60f-5631-4037-72e3-fb4e093692c0',
                           '9a121a3c-91fe-4f58-60b1-120b995b78b4'],
                'sps': ['DEL_SP9', 'SP3']
            },
            'cdp_user1@qa.nutanix.com': {
                'category': ['a1006244-ffc7-4a0d-4689-6f04bdcbda69'],
                'sps': ['SP4', 'Del_SP3']
            },
            'cdp_user3@qa.nutanix.com': {
                'category': ['ALL', '7101b2bd-c849-489e-42b3-366668b347c5',
                           'f9f9666c-cac0-4bf6-7e48-d104c404d465',
                           'eb6a2944-ef4f-4ddc-4071-4d8ad0060774',
                           'acc48a1f-2b71-4f41-5202-24143569b8f2',
                           'be95eade-0ee5-41c7-606f-ed46d266af89',
                           'a3638bf7-4459-46e7-6b9c-b7b54903f226',
                           '12ce9e15-e853-4f76-61d5-12f0bad0fe3e',
                           '63964a96-4ded-42bb-494c-2a6dfaa3b938',
                           '4d72e60f-5631-4037-72e3-fb4e093692c0',
                           'a4fcfe42-2223-4713-61e4-1254972e0870',
                           '8e872651-37a8-4963-5370-29e328fd9c52'],
                'sps': ['DEL_SP11', 'DEL_SP14', 'DEL_SP6', 'DEL_SP12', 'DEL_SP10',
                       'DEL_SP13', 'SP13', 'DEL_SP8', 'DEL_SP7', 'DEL_SP5', 'SP6', 'DEL_SP9']
            },
            'cdp_user4@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            },
            'ca_user19@qa.nutanix.com': {
                'category': ['c222da3c-4d38-48df-6701-34255b2e4ae5',
                           '49adf393-b404-47a0-7f5e-09951f0eec0e',
                           '9a121a3c-91fe-4f58-60b1-120b995b78b4',
                           '807facc3-7fed-42b8-46e5-191b3474680b',
                           '0b204dc8-3c96-4221-6981-7f2a89a27a0c',
                           '6db3cfe6-1316-48d3-46de-5bb6547884aa'],
                'sps': ['SP1', 'Del_SP3', 'SP3', 'SP4', 'Del_SP4', 'SP2']
            },
            'ca_user17@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            },
            'ca_user20@qa.nutanix.com': {
                'category': ['82ab3d45-212e-43e7-6614-474976afc577'],
                'sps': ['SP5', 'SP1', 'Del_SP4', 'SP2', 'Del_SP2']
            },
            'ca_user18@qa.nutanix.com': {
                'category': ['e127a91d-5848-405f-58bf-d5eb5f2093e3',
                           'f9f9666c-cac0-4bf6-7e48-d104c404d465',
                           'a4fcfe42-2223-4713-61e4-1254972e0870',
                           'f317f55f-5e57-42be-4b05-237e85c86419',
                           '21b05845-ad2d-4bfe-54c8-bc72957995df'],
                'sps': ['SP5', 'DEL_SP6', 'SP3', 'DEL_SP5', 'SP6', 'Del_SP1', 'Del_SP2']
            },
            'vo_user7@qa.nutanix.com': {
                'category': ['c222da3c-4d38-48df-6701-34255b2e4ae5',
                           '24fd6fc6-d447-41c4-44fb-083fb167f6a6',
                           '12ce9e15-e853-4f76-61d5-12f0bad0fe3e',
                           '63964a96-4ded-42bb-494c-2a6dfaa3b938',
                           'ALL'],
                'sps': ['SP1', 'SP7', 'SP3', 'DEL_SP8', 'DEL_SP7', 'Del_SP2']
            },
            'vo_user8@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            },
            'vo_user9@qa.nutanix.com': {
                'category': ['a1006244-ffc7-4a0d-4689-6f04bdcbda69'],
                'sps': ['SP4', 'Del_SP3']
            },
            'ca_user1@qa.nutanix.com': {
                'category': ['ALL', '4d72e60f-5631-4037-72e3-fb4e093692c0',
                           '9a121a3c-91fe-4f58-60b1-120b995b78b4'],
                'sps': ['DEL_SP9', 'SP3']
            },
            'ca_user3@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            },
            'ca_user2@qa.nutanix.com': {
                'category': ['ALL', '1c3d9e03-7a72-48b2-551d-5f22dcbe9dc0',
                           'f9f9666c-cac0-4bf6-7e48-d104c404d465',
                           '529f0a50-58b9-47e4-5145-660aa1971378',
                           'acc48a1f-2b71-4f41-5202-24143569b8f2',
                           '9c351c41-a88d-446f-7fa1-bdff43ff4f44',
                           '12ce9e15-e853-4f76-61d5-12f0bad0fe3e',
                           '63964a96-4ded-42bb-494c-2a6dfaa3b938',
                           'a4fcfe42-2223-4713-61e4-1254972e0870',
                           '09c0e312-1ff6-42c2-73fd-37371343494a',
                           '4d72e60f-5631-4037-72e3-fb4e093692c0',
                           'bba7291b-c1dd-4a66-6dbc-67729325f8bf'],
                'sps': ['DEL_SP4', 'DEL_SP6', 'DEL_SP2', 'DEL_SP10', 'DEL_SP3', 'DEL_SP8',
                       'DEL_SP7', 'DEL_SP5', 'SP6', 'DEL_SP1', 'DEL_SP9', 'SP8']
            },
            'ca_user4@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            },
            'ca_user16@qa.nutanix.com': {
                'category': ['ALL'],
                'sps': ['Default-Storage', 'SP1', 'SP2', 'Del_SP1', 'Del_SP2', 'SP3', 'SP4',
                       'Del_SP3', 'Del_SP4', 'SP5', 'SP6', 'DEL_SP5', 'DEL_SP6', 'SP7',
                       'DEL_SP7', 'DEL_SP8', 'DEL_SP9', 'SP13', 'DEL_SP11', 'DEL_SP12',
                       'DEL_SP13', 'DEL_SP14', 'DEL_SP10', 'SP8', 'DEL_SP1', 'DEL_SP2',
                       'DEL_SP3', 'DEL_SP4']
            }
        }
    
    def setup_driver(self, headless: bool = False) -> webdriver.Chrome:
        """
        Setup Chrome WebDriver for UI automation.
        
        Args:
            headless: Whether to run browser in headless mode
            
        Returns:
            WebDriver instance
        """
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-web-security')
        
        if headless:
            chrome_options.add_argument('--headless')
            
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        return self.driver
    
    def login_to_prism_central(self, username: str, password: str) -> bool:
        """
        Login to Prism Central with given credentials.
        
        Args:
            username: Username for login
            password: Password for login
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info(f"Navigating to Prism Central: {self.prism_central_url}")
            self.driver.get(self.prism_central_url)
            
            # Wait for login form to load
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            
            # Enter credentials
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for successful login (dashboard or main page)
            self.wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CLASS_NAME, "dashboard")),
                    EC.presence_of_element_located((By.CLASS_NAME, "main-content")),
                    EC.url_contains("dashboard")
                )
            )
            
            logger.info(f"Successfully logged in as {username}")
            return True
            
        except TimeoutException:
            logger.error(f"Login failed for user {username}")
            return False
        except Exception as e:
            logger.error(f"Error during login for {username}: {str(e)}")
            return False
    
    def navigate_to_storage_policies(self) -> bool:
        """
        Navigate to Storage Policies page in Prism Central.
        
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            # Look for Storage menu or direct navigation
            storage_menu_selectors = [
                "//a[contains(text(), 'Storage')]",
                "//span[contains(text(), 'Storage')]",
                "//div[contains(text(), 'Storage')]",
                "//a[@href*='storage']",
                "//button[contains(text(), 'Storage')]"
            ]
            
            storage_element = None
            for selector in storage_menu_selectors:
                try:
                    storage_element = self.driver.find_element(By.XPATH, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if storage_element:
                storage_element.click()
                time.sleep(2)
            
            # Look for Storage Policies submenu or page
            policy_selectors = [
                "//a[contains(text(), 'Storage Policy') or contains(text(), 'Storage Policies')]",
                "//span[contains(text(), 'Storage Policy') or contains(text(), 'Storage Policies')]",
                "//div[contains(text(), 'Storage Policy') or contains(text(), 'Storage Policies')]",
                "//a[@href*='storage-polic']",
                "//button[contains(text(), 'Storage Polic')]"
            ]
            
            policy_element = None
            for selector in policy_selectors:
                try:
                    policy_element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if policy_element:
                policy_element.click()
                
                # Wait for storage policies page to load
                self.wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Storage')]")),
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'storage-policy')]")),
                        EC.url_contains("storage")
                    )
                )
                
                logger.info("Successfully navigated to Storage Policies page")
                return True
            else:
                logger.error("Could not find Storage Policies navigation element")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to storage policies: {str(e)}")
            return False
    
    def get_visible_storage_policies(self) -> List[str]:
        """
        Get list of storage policies visible to current user.
        
        Returns:
            List of visible storage policy names
        """
        try:
            # Wait for storage policies list to load
            time.sleep(3)
            
            # Common selectors for storage policy names in tables/lists
            policy_selectors = [
                "//table//td[contains(@class, 'name')]",
                "//div[contains(@class, 'policy-name')]",
                "//span[contains(@class, 'policy-name')]",
                "//a[contains(@href, 'policy')]",
                "//tr//td[1]",  # First column typically contains names
                "//div[contains(@class, 'list-item')]//span[1]"
            ]
            
            visible_policies = []
            
            for selector in policy_selectors:
                try:
                    policy_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in policy_elements:
                        policy_name = element.text.strip()
                        if policy_name and policy_name not in visible_policies:
                            visible_policies.append(policy_name)
                    
                    if visible_policies:
                        break
                        
                except NoSuchElementException:
                    continue
            
            logger.info(f"Found {len(visible_policies)} visible storage policies")
            return visible_policies
            
        except Exception as e:
            logger.error(f"Error getting visible storage policies: {str(e)}")
            return []
    
    def verify_user_rbac_permissions(self, username: str) -> Dict[str, Any]:
        """
        Verify RBAC permissions for a specific user.
        
        Args:
            username: Username to verify permissions for
            
        Returns:
            Dictionary containing verification results
        """
        result = {
            'username': username,
            'expected_sps': [],
            'visible_sps': [],
            'expected_categories': [],
            'rbac_verified': False,
            'errors': []
        }
        
        try:
            if username not in self.user_entities:
                result['errors'].append(f"User {username} not found in entities data")
                return result
            
            user_data = self.user_entities[username]
            result['expected_sps'] = user_data.get('sps', [])
            result['expected_categories'] = user_data.get('category', [])
            
            # Get visible storage policies in UI
            result['visible_sps'] = self.get_visible_storage_policies()
            
            # Check if user can see expected storage policies
            missing_policies = []
            unexpected_policies = []
            
            for expected_sp in result['expected_sps']:
                if expected_sp not in result['visible_sps']:
                    missing_policies.append(expected_sp)
            
            for visible_sp in result['visible_sps']:
                if visible_sp not in result['expected_sps']:
                    unexpected_policies.append(visible_sp)
            
            if missing_policies:
                result['errors'].append(f"Missing expected policies: {missing_policies}")
            
            if unexpected_policies:
                result['errors'].append(f"Unexpected visible policies: {unexpected_policies}")
            
            # RBAC is verified if no errors
            result['rbac_verified'] = len(result['errors']) == 0
            
            logger.info(f"RBAC verification for {username}: {'PASSED' if result['rbac_verified'] else 'FAILED'}")
            
        except Exception as e:
            result['errors'].append(f"Error during RBAC verification: {str(e)}")
            logger.error(f"Error verifying RBAC for {username}: {str(e)}")
        
        return result
    
    def verify_all_users_rbac(self, user_credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Verify RBAC permissions for all users.
        
        Args:
            user_credentials: Dictionary mapping usernames to passwords
            
        Returns:
            Dictionary containing all verification results
        """
        results = {
            'total_users': 0,
            'passed_users': 0,
            'failed_users': 0,
            'user_results': {},
            'summary': {}
        }
        
        try:
            for username in self.user_entities.keys():
                if username not in user_credentials:
                    logger.warning(f"No credentials provided for user {username}")
                    continue
                
                results['total_users'] += 1
                logger.info(f"Verifying RBAC for user: {username}")
                
                # Login as user
                login_success = self.login_to_prism_central(username, user_credentials[username])
                if not login_success:
                    results['user_results'][username] = {
                        'rbac_verified': False,
                        'errors': ['Login failed']
                    }
                    results['failed_users'] += 1
                    continue
                
                # Navigate to storage policies
                nav_success = self.navigate_to_storage_policies()
                if not nav_success:
                    results['user_results'][username] = {
                        'rbac_verified': False,
                        'errors': ['Navigation to storage policies failed']
                    }
                    results['failed_users'] += 1
                    continue
                
                # Verify RBAC permissions
                user_result = self.verify_user_rbac_permissions(username)
                results['user_results'][username] = user_result
                
                if user_result['rbac_verified']:
                    results['passed_users'] += 1
                else:
                    results['failed_users'] += 1
                
                # Logout before next user
                self.logout()
                time.sleep(2)
            
            # Generate summary
            results['summary'] = {
                'success_rate': f"{results['passed_users']}/{results['total_users']} ({(results['passed_users']/results['total_users']*100):.1f}%)" if results['total_users'] > 0 else "0/0 (0%)",
                'overall_status': 'PASSED' if results['failed_users'] == 0 else 'FAILED'
            }
            
        except Exception as e:
            logger.error(f"Error during batch RBAC verification: {str(e)}")
            results['summary']['error'] = str(e)
        
        return results
    
    def logout(self) -> bool:
        """
        Logout from Prism Central.
        
        Returns:
            True if logout successful, False otherwise
        """
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
                    return True
                except NoSuchElementException:
                    continue
            
            # If no logout button found, clear session by navigating to login page
            self.driver.get(f"{self.prism_central_url}login")
            return True
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up WebDriver resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
    
    def generate_report(self, results: Dict[str, Any], output_file: str = None) -> str:
        """
        Generate a detailed RBAC verification report.
        
        Args:
            results: Results from verify_all_users_rbac
            output_file: Optional file path to save report
            
        Returns:
            Report content as string
        """
        report_lines = [
            "=" * 80,
            "STORAGE POLICY RBAC VERIFICATION REPORT",
            "=" * 80,
            f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Prism Central URL: {self.prism_central_url}",
            "",
            "SUMMARY:",
            f"  Total Users Tested: {results['total_users']}",
            f"  Passed: {results['passed_users']}",
            f"  Failed: {results['failed_users']}",
            f"  Success Rate: {results['summary'].get('success_rate', 'N/A')}",
            f"  Overall Status: {results['summary'].get('overall_status', 'UNKNOWN')}",
            "",
            "DETAILED RESULTS:",
            "-" * 40
        ]
        
        for username, user_result in results.get('user_results', {}).items():
            report_lines.extend([
                f"",
                f"User: {username}",
                f"  Status: {'PASSED' if user_result['rbac_verified'] else 'FAILED'}",
                f"  Expected Storage Policies: {len(user_result.get('expected_sps', []))}",
                f"  Visible Storage Policies: {len(user_result.get('visible_sps', []))}",
                f"  Expected Categories: {user_result.get('expected_categories', [])}",
            ])
            
            if user_result.get('errors'):
                report_lines.append(f"  Errors:")
                for error in user_result['errors']:
                    report_lines.append(f"    - {error}")
        
        report_lines.extend([
            "",
            "=" * 80
        ])
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report_content)
                logger.info(f"Report saved to {output_file}")
            except Exception as e:
                logger.error(f"Error saving report to {output_file}: {str(e)}")
        
        return report_content