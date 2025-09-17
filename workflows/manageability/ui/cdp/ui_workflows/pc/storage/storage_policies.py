"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: shubham.shrivastava@nutanix.com

This module contains UI workflows for Storage Policy operations in Prism Central.
"""

import time
from typing import List, Set, Optional, Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from framework.lib.nulog import INFO, DEBUG, ERROR, STEP
from framework.exceptions.nutest_error import NuTestError


class StoragePolicies:
    """
    UI workflow class for Storage Policy operations in Prism Central.
    """
    
    def __init__(self, pc_dashboard):
        """
        Initialize Storage Policies UI workflow.
        
        Args:
            pc_dashboard: PrismCentral dashboard object
        """
        self.pc_dashboard = pc_dashboard
        self.driver = pc_dashboard.driver
        self.wait = WebDriverWait(self.driver, 30)
        
        # Common UI selectors for Storage Policies
        self.selectors = {
            # Navigation selectors
            'storage_menu': [
                "//a[contains(text(), 'Storage')]",
                "//span[contains(text(), 'Storage')]",
                "//div[contains(@class, 'nav-item') and contains(., 'Storage')]",
                "//button[contains(text(), 'Storage')]"
            ],
            'storage_policies_submenu': [
                "//a[contains(text(), 'Storage Policies') or contains(text(), 'Storage Policy')]",
                "//span[contains(text(), 'Storage Policies') or contains(text(), 'Storage Policy')]",
                "//div[contains(text(), 'Storage Policies') or contains(text(), 'Storage Policy')]",
                "//li[contains(., 'Storage Policies')]//a",
                "//button[contains(text(), 'Storage Policies')]"
            ],
            
            # Storage Policies page selectors
            'page_title': [
                "//h1[contains(text(), 'Storage Policies')]",
                "//h2[contains(text(), 'Storage Policies')]",
                "//div[contains(@class, 'page-title') and contains(., 'Storage')]",
                "//span[contains(@class, 'title') and contains(., 'Storage')]"
            ],
            'loading_indicator': [
                "//div[contains(@class, 'loading')]",
                "//div[contains(@class, 'spinner')]",
                "//div[contains(@class, 'progress')]"
            ],
            
            # Table and list selectors
            'storage_policy_table': [
                "//table[contains(@class, 'storage-policy')]",
                "//table//th[contains(text(), 'Name')]//ancestor::table",
                "//div[contains(@class, 'table-container')]//table",
                "//table[contains(@class, 'data-table')]"
            ],
            'policy_rows': [
                "//table//tbody//tr[contains(@class, 'policy-row')]",
                "//table//tbody//tr[td[contains(@class, 'name')]]",
                "//table//tbody//tr[not(contains(@class, 'header'))]",
                "//div[contains(@class, 'policy-item')]"
            ],
            'policy_names': [
                "//table//tbody//tr//td[1]",
                "//table//tbody//tr//td[contains(@class, 'name')]",
                "//table//tbody//tr//td//a[contains(@href, 'storage-policy')]",
                "//div[contains(@class, 'policy-name')]//span"
            ],
            
            # Action selectors
            'create_button': [
                "//button[contains(text(), 'Create') and contains(text(), 'Storage Policy')]",
                "//button[contains(text(), 'Create Policy')]",
                "//button[contains(text(), 'New Policy')]",
                "//a[contains(text(), 'Create Storage Policy')]"
            ],
            'actions_menu': [
                "//button[contains(@class, 'actions')]",
                "//div[contains(@class, 'actions-dropdown')]",
                "//button[contains(text(), 'Actions')]"
            ],
            
            # Search and filter selectors
            'search_box': [
                "//input[contains(@placeholder, 'Search')]",
                "//input[contains(@class, 'search')]",
                "//input[@type='search']"
            ],
            'filter_dropdown': [
                "//button[contains(text(), 'Filter')]",
                "//div[contains(@class, 'filter-dropdown')]"
            ]
        }
    
    def navigate_to_storage_policies(self) -> bool:
        """
        Navigate to Storage Policies page in Prism Central.
        
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            STEP("Navigating to Storage Policies page")
            
            # First, try to find and click Storage menu
            storage_element = self._find_element_by_selectors(
                self.selectors['storage_menu'], 
                "Storage menu"
            )
            
            if storage_element:
                self._click_element(storage_element, "Storage menu")
                time.sleep(2)  # Wait for submenu to appear
            
            # Then find and click Storage Policies submenu
            policies_element = self._find_element_by_selectors(
                self.selectors['storage_policies_submenu'],
                "Storage Policies submenu"
            )
            
            if policies_element:
                self._click_element(policies_element, "Storage Policies submenu")
                
                # Wait for page to load
                self._wait_for_page_load()
                
                INFO("Successfully navigated to Storage Policies page")
                return True
            else:
                ERROR("Could not find Storage Policies navigation element")
                return False
                
        except Exception as e:
            ERROR(f"Error navigating to storage policies: {str(e)}")
            return False
    
    def get_visible_storage_policies(self) -> List[str]:
        """
        Get list of storage policies visible on the current page.
        
        Returns:
            List[str]: List of visible storage policy names
        """
        try:
            DEBUG("Getting visible storage policies from UI")
            
            # Wait for table to load
            self._wait_for_table_load()
            
            # Find policy names using multiple selector strategies
            policy_names = []
            
            for selector_group in self.selectors['policy_names']:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector_group)
                    for element in elements:
                        name = element.text.strip()
                        if name and name not in policy_names:
                            # Filter out header text and non-policy names
                            if not self._is_header_text(name):
                                policy_names.append(name)
                    
                    if policy_names:
                        break
                        
                except NoSuchElementException:
                    continue
            
            # If no policies found with table selectors, try list view
            if not policy_names:
                policy_names = self._get_policies_from_list_view()
            
            DEBUG(f"Found {len(policy_names)} visible storage policies: {policy_names}")
            return policy_names
            
        except Exception as e:
            ERROR(f"Error getting visible storage policies: {str(e)}")
            return []
    
    def verify_sp_list(self, expected_policies: Set[str]) -> bool:
        """
        Verify that the visible storage policies match the expected set.
        
        Args:
            expected_policies: Set of expected storage policy names
            
        Returns:
            bool: True if verification successful, False otherwise
            
        Raises:
            NuTestError: If verification fails
        """
        try:
            STEP(f"Verifying storage policy list visibility for {len(expected_policies)} expected policies")
            
            # Navigate to storage policies if not already there
            if not self._is_on_storage_policies_page():
                if not self.navigate_to_storage_policies():
                    raise NuTestError("Failed to navigate to Storage Policies page")
            
            # Get visible policies
            visible_policies = set(self.get_visible_storage_policies())
            
            # Compare sets
            missing_policies = expected_policies - visible_policies
            unexpected_policies = visible_policies - expected_policies
            
            if missing_policies:
                error_msg = f"Missing expected policies: {missing_policies}"
                ERROR(error_msg)
                raise NuTestError(error_msg)
            
            if unexpected_policies:
                error_msg = f"Unexpected visible policies: {unexpected_policies}"
                ERROR(error_msg)
                raise NuTestError(error_msg)
            
            INFO(f"Successfully verified storage policy list - {len(visible_policies)} policies visible as expected")
            return True
            
        except Exception as e:
            error_msg = f"Storage policy list verification failed: {str(e)}"
            ERROR(error_msg)
            raise NuTestError(error_msg)
    
    def view_storage_policy(self, policy_name: str) -> Dict[str, Any]:
        """
        View details of a specific storage policy.
        
        Args:
            policy_name: Name of the storage policy to view
            
        Returns:
            Dict containing policy details
            
        Raises:
            NuTestError: If policy cannot be found or viewed
        """
        try:
            STEP(f"Viewing storage policy: {policy_name}")
            
            # Navigate to storage policies if not already there
            if not self._is_on_storage_policies_page():
                if not self.navigate_to_storage_policies():
                    raise NuTestError("Failed to navigate to Storage Policies page")
            
            # Find the policy in the list
            policy_element = self._find_policy_element(policy_name)
            if not policy_element:
                raise NuTestError(f"Storage policy '{policy_name}' not found in the list")
            
            # Click on the policy to view details
            self._click_element(policy_element, f"Storage policy '{policy_name}'")
            
            # Wait for policy details page to load
            self._wait_for_policy_details_load()
            
            # Extract policy details
            policy_details = self._extract_policy_details(policy_name)
            
            INFO(f"Successfully viewed storage policy: {policy_name}")
            return policy_details
            
        except Exception as e:
            error_msg = f"Failed to view storage policy '{policy_name}': {str(e)}"
            ERROR(error_msg)
            raise NuTestError(error_msg)
    
    def search_storage_policy(self, search_term: str) -> List[str]:
        """
        Search for storage policies by name.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of matching policy names
        """
        try:
            DEBUG(f"Searching for storage policies with term: {search_term}")
            
            # Find search box
            search_box = self._find_element_by_selectors(
                self.selectors['search_box'],
                "Search box"
            )
            
            if search_box:
                # Clear and enter search term
                search_box.clear()
                search_box.send_keys(search_term)
                time.sleep(2)  # Wait for search results
                
                # Get filtered results
                filtered_policies = self.get_visible_storage_policies()
                DEBUG(f"Search returned {len(filtered_policies)} policies")
                return filtered_policies
            else:
                DEBUG("Search box not found, returning all visible policies")
                return self.get_visible_storage_policies()
                
        except Exception as e:
            ERROR(f"Error searching storage policies: {str(e)}")
            return []
    
    def _find_element_by_selectors(self, selectors: List[str], element_name: str):
        """
        Find element using multiple selector strategies.
        
        Args:
            selectors: List of XPath selectors to try
            element_name: Name of element for logging
            
        Returns:
            WebElement or None if not found
        """
        for selector in selectors:
            try:
                element = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                DEBUG(f"Found {element_name} using selector: {selector}")
                return element
            except TimeoutException:
                continue
        
        DEBUG(f"{element_name} not found with any selector")
        return None
    
    def _click_element(self, element, element_name: str):
        """
        Click an element with error handling.
        
        Args:
            element: WebElement to click
            element_name: Name for logging
        """
        try:
            # Try regular click first
            element.click()
            DEBUG(f"Clicked {element_name}")
        except Exception:
            try:
                # Try JavaScript click if regular click fails
                self.driver.execute_script("arguments[0].click();", element)
                DEBUG(f"Clicked {element_name} using JavaScript")
            except Exception as e:
                ERROR(f"Failed to click {element_name}: {str(e)}")
                raise
    
    def _wait_for_page_load(self):
        """Wait for Storage Policies page to load."""
        try:
            # Wait for page title to appear
            self.wait.until(
                EC.any_of(
                    *[EC.presence_of_element_located((By.XPATH, selector)) 
                      for selector in self.selectors['page_title']]
                )
            )
            
            # Wait for loading indicators to disappear
            self._wait_for_loading_complete()
            
            DEBUG("Storage Policies page loaded successfully")
            
        except TimeoutException:
            DEBUG("Page load timeout - continuing anyway")
    
    def _wait_for_table_load(self):
        """Wait for storage policies table to load."""
        try:
            # Wait for table to appear
            self.wait.until(
                EC.any_of(
                    *[EC.presence_of_element_located((By.XPATH, selector)) 
                      for selector in self.selectors['storage_policy_table']]
                )
            )
            
            # Wait for loading to complete
            self._wait_for_loading_complete()
            
            DEBUG("Storage policies table loaded")
            
        except TimeoutException:
            DEBUG("Table load timeout - continuing anyway")
    
    def _wait_for_loading_complete(self):
        """Wait for loading indicators to disappear."""
        try:
            for selector in self.selectors['loading_indicator']:
                try:
                    self.wait.until(
                        EC.invisibility_of_element_located((By.XPATH, selector))
                    )
                except TimeoutException:
                    continue
        except Exception:
            pass  # Continue if loading indicators not found
    
    def _wait_for_policy_details_load(self):
        """Wait for policy details page to load."""
        try:
            # Wait for policy details elements to appear
            detail_selectors = [
                "//div[contains(@class, 'policy-details')]",
                "//div[contains(@class, 'storage-policy-detail')]",
                "//h1[contains(text(), 'Storage Policy')]",
                "//div[contains(@class, 'detail-view')]"
            ]
            
            self.wait.until(
                EC.any_of(
                    *[EC.presence_of_element_located((By.XPATH, selector)) 
                      for selector in detail_selectors]
                )
            )
            
            DEBUG("Policy details page loaded")
            
        except TimeoutException:
            DEBUG("Policy details load timeout - continuing anyway")
    
    def _is_on_storage_policies_page(self) -> bool:
        """Check if currently on Storage Policies page."""
        try:
            for selector in self.selectors['page_title']:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        return True
                except NoSuchElementException:
                    continue
            return False
        except Exception:
            return False
    
    def _find_policy_element(self, policy_name: str):
        """Find a specific policy element in the list."""
        try:
            # Try different strategies to find the policy
            policy_selectors = [
                f"//table//tbody//tr//td[contains(text(), '{policy_name}')]",
                f"//table//tbody//tr//td//a[contains(text(), '{policy_name}')]",
                f"//div[contains(@class, 'policy-name') and contains(text(), '{policy_name}')]",
                f"//span[contains(text(), '{policy_name}')]//ancestor::tr",
                f"//td[text()='{policy_name}']"
            ]
            
            for selector in policy_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        return element
                except NoSuchElementException:
                    continue
            
            return None
            
        except Exception as e:
            DEBUG(f"Error finding policy element for '{policy_name}': {str(e)}")
            return None
    
    def _extract_policy_details(self, policy_name: str) -> Dict[str, Any]:
        """Extract policy details from the details page."""
        try:
            details = {
                'name': policy_name,
                'status': 'viewed',
                'timestamp': time.time()
            }
            
            # Try to extract common policy details
            detail_selectors = {
                'description': [
                    "//div[contains(@class, 'description')]//span",
                    "//td[contains(text(), 'Description')]//following-sibling::td",
                    "//label[contains(text(), 'Description')]//following-sibling::*"
                ],
                'replication_factor': [
                    "//td[contains(text(), 'Replication')]//following-sibling::td",
                    "//div[contains(@class, 'replication')]//span"
                ],
                'compression': [
                    "//td[contains(text(), 'Compression')]//following-sibling::td",
                    "//div[contains(@class, 'compression')]//span"
                ]
            }
            
            for field, selectors in detail_selectors.items():
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        if element.is_displayed():
                            details[field] = element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
            
            return details
            
        except Exception as e:
            DEBUG(f"Error extracting policy details: {str(e)}")
            return {'name': policy_name, 'status': 'viewed', 'timestamp': time.time()}
    
    def _get_policies_from_list_view(self) -> List[str]:
        """Get policies from list view if table view is not available."""
        try:
            list_selectors = [
                "//div[contains(@class, 'list-item')]//span[contains(@class, 'name')]",
                "//div[contains(@class, 'policy-item')]//div[contains(@class, 'name')]",
                "//ul//li[contains(@class, 'policy')]//span"
            ]
            
            policy_names = []
            for selector in list_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        name = element.text.strip()
                        if name and name not in policy_names:
                            policy_names.append(name)
                    
                    if policy_names:
                        break
                        
                except NoSuchElementException:
                    continue
            
            return policy_names
            
        except Exception as e:
            DEBUG(f"Error getting policies from list view: {str(e)}")
            return []
    
    def _is_header_text(self, text: str) -> bool:
        """Check if text is likely a header rather than a policy name."""
        header_keywords = [
            'Name', 'Status', 'Description', 'Created', 'Modified',
            'Actions', 'Type', 'Replication', 'Compression', 'Storage Policy'
        ]
        
        return any(keyword.lower() in text.lower() for keyword in header_keywords)