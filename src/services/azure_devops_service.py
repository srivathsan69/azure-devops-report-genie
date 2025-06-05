
import requests
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

class AzureDevOpsService:
    def __init__(self, pat: str, organization: str, project: str):
        self.pat = pat
        self.organization = organization
        self.project = project
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis/wit"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self._encode_pat(pat)}'
        }

    def _encode_pat(self, pat: str) -> str:
        """Encode PAT for basic authentication"""
        import base64
        return base64.b64encode(f":{pat}".encode()).decode()

    def get_timestamp(self) -> str:
        """Get current timestamp for file naming"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _build_date_filter_clause(self, filter_startdate: str = None, filter_enddate: str = None) -> str:
        """
        Build WIQL date filter clause for date range
        
        Args:
            filter_startdate: Start date string (YYYY-MM-DD)
            filter_enddate: End date string (YYYY-MM-DD)
            
        Returns:
            WIQL date filter clause
        """
        date_clauses = []
        
        if filter_startdate:
            date_clauses.append(f"[System.CreatedDate] >= '{filter_startdate}'")
        
        if filter_enddate:
            # Add 23:59:59 to include the entire end date
            date_clauses.append(f"[System.CreatedDate] <= '{filter_enddate}T23:59:59'")
        
        return " AND ".join(date_clauses)

    def _should_apply_date_filter(self, work_item_type: str, filter_workitemtype: List[str]) -> bool:
        """
        Check if date filter should be applied to a specific work item type
        
        Args:
            work_item_type: The work item type to check
            filter_workitemtype: List of work item types to apply date filtering to
            
        Returns:
            True if date filter should be applied, False otherwise
        """
        # If no specific work item types are specified, apply filter to all types
        if not filter_workitemtype:
            return True
        
        # Check if the work item type is in the filter list (case-insensitive)
        return any(work_item_type.lower() == filter_type.lower() for filter_type in filter_workitemtype)

    def fetch_epics(self, custom_fields: List[Dict[str, str]] = None, filter_date: str = None) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use fetch_epics_enhanced instead.
        Fetch Epics from Azure DevOps with optional custom field filtering and date filtering
        
        Args:
            custom_fields: List of custom field objects with key and value for filtering
            filter_date: Optional date string (YYYY-MM-DD) to filter work items created on or after this date
            
        Returns:
            List of Epic work items
        """
        logger.warning("fetch_epics is deprecated. Use fetch_epics_enhanced instead.")
        return self.fetch_epics_enhanced(custom_fields, filter_date, None, None)

    def fetch_epics_enhanced(self, custom_fields: List[Dict[str, str]] = None, 
                           filter_startdate: str = None, filter_enddate: str = None, 
                           filter_workitemtype: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch Epics from Azure DevOps with enhanced filtering
        
        Args:
            custom_fields: List of custom field objects with key and value for filtering
            filter_startdate: Optional start date string (YYYY-MM-DD) to filter work items created on or after this date
            filter_enddate: Optional end date string (YYYY-MM-DD) to filter work items created on or before this date
            filter_workitemtype: List of work item types to apply date filtering to
            
        Returns:
            List of Epic work items
        """
        try:
            logger.info("Fetching Epics from Azure DevOps with enhanced filtering...")
            
            # Build WIQL query for Epics
            wiql_query = "SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Epic'"
            
            # Add custom field filters if provided
            if custom_fields:
                for field in custom_fields:
                    field_name = field.get("key", "")
                    field_value = field.get("value", "")
                    
                    if field_name and field_value:
                        # Add Custom. prefix if not already present and it's a custom field
                        if not field_name.startswith('Custom.') and not field_name.startswith('System.'):
                            field_name = f"Custom.{field_name}"
                        
                        wiql_query += f" AND [{field_name}] = '{field_value}'"
            
            # Add enhanced date filter if applicable
            if (filter_startdate or filter_enddate) and self._should_apply_date_filter("Epic", filter_workitemtype):
                date_clause = self._build_date_filter_clause(filter_startdate, filter_enddate)
                if date_clause:
                    wiql_query += f" AND {date_clause}"
                    logger.info(f"Applied date filter to Epics: {date_clause}")
            else:
                logger.info("Date filter not applied to Epics (not in filter_workitemtype or no dates provided)")
            
            logger.info(f"WIQL Query for Epics: {wiql_query}")
            
            # Execute WIQL query
            wiql_url = f"{self.base_url}/wiql?api-version=6.0"
            wiql_payload = {"query": wiql_query}
            
            logger.debug(f"Making WIQL request to: {wiql_url}")
            wiql_response = requests.post(wiql_url, headers=self.headers, json=wiql_payload)
            wiql_response.raise_for_status()
            
            work_item_ids = [item['id'] for item in wiql_response.json().get('workItems', [])]
            logger.info(f"Found {len(work_item_ids)} Epic IDs matching criteria")
            
            if not work_item_ids:
                logger.warning("No Epic work items found matching the criteria")
                return []
            
            # Fetch detailed work item information
            epics = self._fetch_work_items_details(work_item_ids)
            logger.info(f"Successfully fetched {len(epics)} Epic work items")
            
            return epics
            
        except Exception as e:
            logger.exception(f"Error fetching Epics: {str(e)}")
            raise

    def fetch_user_work_items(self, assigned_to: str, custom_fields: List[Dict[str, str]] = None, filter_date: str = None) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use fetch_user_work_items_enhanced instead.
        Fetch work items assigned to a specific user
        
        Args:
            assigned_to: Name of the user to filter work items by assignment
            custom_fields: List of custom field objects with key and value for filtering
            filter_date: Optional date string (YYYY-MM-DD) to filter work items created on or after this date
            
        Returns:
            List of work items assigned to the user
        """
        logger.warning("fetch_user_work_items is deprecated. Use fetch_user_work_items_enhanced instead.")
        return self.fetch_user_work_items_enhanced(assigned_to, custom_fields, filter_date, None, None)

    def fetch_user_work_items_enhanced(self, assigned_to: str, custom_fields: List[Dict[str, str]] = None,
                                     filter_startdate: str = None, filter_enddate: str = None,
                                     filter_workitemtype: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch work items assigned to a specific user with enhanced filtering
        
        Args:
            assigned_to: Name of the user to filter work items by assignment
            custom_fields: List of custom field objects with key and value for filtering
            filter_startdate: Optional start date string (YYYY-MM-DD) to filter work items created on or after this date
            filter_enddate: Optional end date string (YYYY-MM-DD) to filter work items created on or before this date
            filter_workitemtype: List of work item types to apply date filtering to
            
        Returns:
            List of work items assigned to the user
        """
        try:
            logger.info(f"Fetching work items assigned to {assigned_to} with enhanced filtering...")
            
            # Get all work item types to fetch
            all_work_item_types = ["Epic", "Feature", "User Story", "Task", "Bug", "QA Validation Task"]
            work_items = []
            
            # Fetch work items for each type separately to apply selective date filtering
            for work_item_type in all_work_item_types:
                logger.info(f"Fetching {work_item_type} work items for {assigned_to}...")
                
                # Build WIQL query for specific work item type
                wiql_query = f"SELECT [System.Id] FROM WorkItems WHERE [System.AssignedTo] = '{assigned_to}' AND [System.WorkItemType] = '{work_item_type}'"
                
                # Add custom field filters if provided
                if custom_fields:
                    for field in custom_fields:
                        field_name = field.get("key", "")
                        field_value = field.get("value", "")
                        
                        if field_name and field_value:
                            # Add Custom. prefix if not already present and it's a custom field
                            if not field_name.startswith('Custom.') and not field_name.startswith('System.'):
                                field_name = f"Custom.{field_name}"
                            
                            wiql_query += f" AND [{field_name}] = '{field_value}'"
                
                # Add enhanced date filter if applicable for this work item type
                if (filter_startdate or filter_enddate) and self._should_apply_date_filter(work_item_type, filter_workitemtype):
                    date_clause = self._build_date_filter_clause(filter_startdate, filter_enddate)
                    if date_clause:
                        wiql_query += f" AND {date_clause}"
                        logger.info(f"Applied date filter to {work_item_type}: {date_clause}")
                else:
                    logger.info(f"Date filter not applied to {work_item_type} (not in filter_workitemtype or no dates provided)")
                
                logger.debug(f"WIQL Query for {work_item_type}: {wiql_query}")
                
                # Execute WIQL query
                wiql_url = f"{self.base_url}/wiql?api-version=6.0"
                wiql_payload = {"query": wiql_query}
                
                wiql_response = requests.post(wiql_url, headers=self.headers, json=wiql_payload)
                wiql_response.raise_for_status()
                
                work_item_ids = [item['id'] for item in wiql_response.json().get('workItems', [])]
                logger.info(f"Found {len(work_item_ids)} {work_item_type} IDs for user {assigned_to}")
                
                if work_item_ids:
                    # Fetch detailed work item information
                    type_work_items = self._fetch_work_items_details(work_item_ids)
                    work_items.extend(type_work_items)
                    logger.info(f"Successfully fetched {len(type_work_items)} {work_item_type} work items for user {assigned_to}")
            
            logger.info(f"Total work items fetched for {assigned_to}: {len(work_items)}")
            return work_items
            
        except Exception as e:
            logger.exception(f"Error fetching user work items: {str(e)}")
            raise

    def fetch_work_items_with_enhanced_filter(self, base_wiql: str, filter_startdate: str = None, 
                                            filter_enddate: str = None, filter_workitemtype: List[str] = None,
                                            work_item_type: str = None) -> List[Dict[str, Any]]:
        """
        Generic method to fetch work items with enhanced date filtering
        
        Args:
            base_wiql: Base WIQL query without date filters
            filter_startdate: Optional start date string (YYYY-MM-DD)
            filter_enddate: Optional end date string (YYYY-MM-DD)
            filter_workitemtype: List of work item types to apply date filtering to
            work_item_type: The work item type being queried (for filtering logic)
            
        Returns:
            List of work items
        """
        try:
            wiql_query = base_wiql
            
            # Add enhanced date filter if applicable
            if (filter_startdate or filter_enddate) and self._should_apply_date_filter(work_item_type, filter_workitemtype):
                date_clause = self._build_date_filter_clause(filter_startdate, filter_enddate)
                if date_clause:
                    wiql_query += f" AND {date_clause}"
                    logger.info(f"Applied date filter to {work_item_type}: {date_clause}")
            
            logger.info(f"Executing WIQL: {wiql_query}")
            
            # Execute WIQL query
            wiql_url = f"{self.base_url}/wiql?api-version=6.0"
            wiql_payload = {"query": wiql_query}
            
            wiql_response = requests.post(wiql_url, headers=self.headers, json=wiql_payload)
            wiql_response.raise_for_status()
            
            work_item_ids = [item['id'] for item in wiql_response.json().get('workItems', [])]
            logger.info(f"Found {len(work_item_ids)} work item IDs")
            
            if not work_item_ids:
                return []
            
            # Fetch detailed work item information
            return self._fetch_work_items_details(work_item_ids)
            
        except Exception as e:
            logger.exception(f"Error fetching work items: {str(e)}")
            raise

    def populate_parent_details(self, work_items: List[Dict[str, Any]]) -> None:
        """
        Populate parent details for work items that may be missing this information
        
        Args:
            work_items: List of work items to populate parent details for
        """
        try:
            logger.info(f"Populating parent details for {len(work_items)} work items...")
            
            for item in work_items:
                parent_url = item.get('parent_url')
                if parent_url and not item.get('parent_id'):
                    try:
                        parent_id = int(parent_url.split('/')[-1])
                        
                        # Fetch parent details
                        parent_details = self._fetch_work_items_details([parent_id])
                        if parent_details:
                            parent = parent_details[0]
                            item['parent_type'] = parent.get('type', '')
                            item['parent_id'] = parent_id
                            item['parent_title'] = parent.get('title', '')
                            logger.debug(f"Populated parent details for item {item['id']}: parent_id={parent_id}")
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse parent URL: {parent_url}")
            
            logger.info("Finished populating parent details")
            
        except Exception as e:
            logger.exception(f"Error populating parent details: {str(e)}")

    def traverse_hierarchy(self, epics: List[Dict[str, Any]], custom_fields: List[Dict[str, str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        DEPRECATED: Use traverse_hierarchy_enhanced instead.
        Traverse the Epic hierarchy and collect all related work items with flexible hierarchy support
        
        Args:
            epics: List of Epic work items to traverse
            custom_fields: List of custom fields for filtering
            
        Returns:
            Dictionary containing organized work items by type
        """
        logger.warning("traverse_hierarchy is deprecated. Use traverse_hierarchy_enhanced instead.")
        return self.traverse_hierarchy_enhanced(epics, custom_fields, None, None, None)

    def traverse_hierarchy_enhanced(self, epics: List[Dict[str, Any]], custom_fields: List[Dict[str, str]] = None,
                                  filter_startdate: str = None, filter_enddate: str = None,
                                  filter_workitemtype: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Traverse the Epic hierarchy and collect all related work items with enhanced filtering
        
        Args:
            epics: List of Epic work items to traverse
            custom_fields: List of custom fields for filtering
            filter_startdate: Optional start date for filtering descendants
            filter_enddate: Optional end date for filtering descendants
            filter_workitemtype: List of work item types to apply date filtering to
            
        Returns:
            Dictionary containing organized work items by type
        """
        try:
            logger.info(f"Starting enhanced hierarchy traversal for {len(epics)} Epics...")
            
            all_work_items = []
            processed_ids = set()
            
            # Process each Epic and collect all descendants
            for epic in epics:
                logger.info(f"Processing Epic {epic['id']}: {epic.get('title', 'No Title')}")
                epic_descendants = self._get_all_descendants_enhanced(epic['id'], processed_ids, filter_startdate, filter_enddate, filter_workitemtype)
                all_work_items.extend(epic_descendants)
                
                # Add the epic itself if not already processed
                if epic['id'] not in processed_ids:
                    all_work_items.append(epic)
                    processed_ids.add(epic['id'])
            
            logger.info(f"Collected {len(all_work_items)} total work items in hierarchy")
            
            # Populate parent information for all work items
            all_work_items = self._populate_parent_information_for_hierarchy(all_work_items)
            
            # Aggregate hours from children to parents
            all_work_items = self._aggregate_hours_from_descendants(all_work_items)
            
            # Organize work items by type
            organized_data = {
                "epics": [],
                "features": [],
                "stories": [],
                "leaf_items": []
            }
            
            for item in all_work_items:
                work_item_type = item.get("type", "").strip()
                
                if work_item_type.lower() == "epic":
                    organized_data["epics"].append(item)
                elif work_item_type.lower() == "feature":
                    organized_data["features"].append(item)
                elif work_item_type.lower() == "user story":
                    organized_data["stories"].append(item)
                elif work_item_type.lower() in ["task", "bug", "qa validation task"]:
                    organized_data["leaf_items"].append(item)
                else:
                    # For unknown types, add them to leaf_items
                    organized_data["leaf_items"].append(item)
            
            logger.info(f"Organized hierarchy: {len(organized_data['epics'])} epics, {len(organized_data['features'])} features, {len(organized_data['stories'])} stories, {len(organized_data['leaf_items'])} tasks/bugs/qa")
            
            return organized_data
            
        except Exception as e:
            logger.exception(f"Error traversing hierarchy: {str(e)}")
            raise

    def _get_all_descendants_enhanced(self, work_item_id: int, processed_ids: set,
                                    filter_startdate: str = None, filter_enddate: str = None,
                                    filter_workitemtype: List[str] = None) -> List[Dict[str, Any]]:
        """
        Recursively get all descendants of a work item with enhanced filtering
        
        Args:
            work_item_id: ID of the work item to get descendants for
            processed_ids: Set of already processed work item IDs to avoid duplicates
            filter_startdate: Optional start date for filtering
            filter_enddate: Optional end date for filtering
            filter_workitemtype: List of work item types to apply date filtering to
            
        Returns:
            List of all descendant work items
        """
        try:
            descendants = []
            
            if work_item_id in processed_ids:
                return descendants
            
            # Get direct children using relations
            children = self._get_direct_children_enhanced(work_item_id, filter_startdate, filter_enddate, filter_workitemtype)
            
            for child in children:
                child_id = child['id']
                
                if child_id not in processed_ids:
                    descendants.append(child)
                    processed_ids.add(child_id)
                    
                    # Recursively get descendants of this child
                    child_descendants = self._get_all_descendants_enhanced(child_id, processed_ids, filter_startdate, filter_enddate, filter_workitemtype)
                    descendants.extend(child_descendants)
            
            return descendants
            
        except Exception as e:
            logger.exception(f"Error getting descendants for work item {work_item_id}: {str(e)}")
            return []

    def _get_direct_children_enhanced(self, work_item_id: int, filter_startdate: str = None,
                                    filter_enddate: str = None, filter_workitemtype: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get direct children of a work item with enhanced filtering
        
        Args:
            work_item_id: ID of the parent work item
            filter_startdate: Optional start date for filtering
            filter_enddate: Optional end date for filtering
            filter_workitemtype: List of work item types to apply date filtering to
            
        Returns:
            List of direct child work items
        """
        try:
            # Fetch work item with relations
            url = f"{self.base_url}/workitems/{work_item_id}?$expand=relations&api-version=6.0"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            work_item_data = response.json()
            relations = work_item_data.get('relations', [])
            
            # Extract child work item IDs from relations
            child_ids = []
            for relation in relations:
                rel_type = relation.get('rel', '')
                if rel_type == 'System.LinkTypes.Hierarchy-Forward':  # This indicates a child relationship
                    child_url = relation.get('url', '')
                    if child_url:
                        try:
                            child_id = int(child_url.split('/')[-1])
                            child_ids.append(child_id)
                        except (ValueError, IndexError):
                            logger.warning(f"Could not parse child URL: {child_url}")
            
            if not child_ids:
                return []
            
            # Fetch details for all children
            all_children = self._fetch_work_items_details(child_ids)
            
            # Apply enhanced filtering to children based on their work item types
            filtered_children = []
            for child in all_children:
                child_type = child.get('type', '')
                
                # Check if date filtering should be applied to this child type
                if self._should_apply_date_filter(child_type, filter_workitemtype):
                    # Check if child meets date criteria
                    if self._meets_date_criteria(child, filter_startdate, filter_enddate):
                        filtered_children.append(child)
                    else:
                        logger.debug(f"Child {child['id']} filtered out by date criteria")
                else:
                    # Include child regardless of date (not in filter_workitemtype)
                    filtered_children.append(child)
            
            logger.debug(f"Found {len(filtered_children)} filtered children out of {len(all_children)} total children for work item {work_item_id}")
            
            return filtered_children
            
        except Exception as e:
            logger.exception(f"Error getting direct children for work item {work_item_id}: {str(e)}")
            return []

    def _meets_date_criteria(self, work_item: Dict[str, Any], filter_startdate: str = None, filter_enddate: str = None) -> bool:
        """
        Check if a work item meets the date criteria
        
        Args:
            work_item: Work item to check
            filter_startdate: Optional start date
            filter_enddate: Optional end date
            
        Returns:
            True if work item meets criteria, False otherwise
        """
        if not filter_startdate and not filter_enddate:
            return True
        
        # Get creation date from work item
        created_date_str = None
        if 'original_fields' in work_item:
            created_date_str = work_item['original_fields'].get('System.CreatedDate')
        
        if not created_date_str:
            # If no creation date available, include the item
            return True
        
        try:
            # Parse creation date (Azure DevOps returns ISO format)
            if isinstance(created_date_str, str):
                created_date = datetime.fromisoformat(created_date_str.replace('Z', '+00:00'))
            else:
                created_date = created_date_str
            
            # Check start date
            if filter_startdate:
                start_date = datetime.strptime(filter_startdate, '%Y-%m-%d')
                if created_date.date() < start_date.date():
                    return False
            
            # Check end date
            if filter_enddate:
                end_date = datetime.strptime(filter_enddate, '%Y-%m-%d')
                if created_date.date() > end_date.date():
                    return False
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing date for work item {work_item.get('id')}: {e}")
            # If date parsing fails, include the item
            return True

    # ... keep existing code (calculate_capex_percentage, _belongs_to_capex_epic, organize_user_work_items, etc.) the same ...

    def calculate_capex_percentage(self, user_work_items: List[Dict[str, Any]], capex_epics: List[Dict[str, Any]]) -> float:
        """
        Calculate the percentage of user's work that corresponds to CAPEX epics
        
        Args:
            user_work_items: List of work items assigned to the user
            capex_epics: List of Epic work items that match CAPEX criteria
            
        Returns:
            Percentage of work corresponding to CAPEX epics
        """
        try:
            if not user_work_items or not capex_epics:
                return 0.0
            
            capex_epic_ids = {epic['id'] for epic in capex_epics}
            logger.info(f"CAPEX Epic IDs: {capex_epic_ids}")
            
            total_hours = 0.0
            capex_hours = 0.0
            
            for work_item in user_work_items:
                estimated_hours = work_item.get('estimated_hours', 0) or 0
                total_hours += estimated_hours
                
                # Check if this work item belongs to a CAPEX epic
                if self._belongs_to_capex_epic(work_item, capex_epic_ids):
                    capex_hours += estimated_hours
                    logger.debug(f"Work item {work_item['id']} belongs to CAPEX epic")
            
            if total_hours == 0:
                return 0.0
            
            percentage = capex_hours / total_hours
            logger.info(f"CAPEX calculation: {capex_hours}/{total_hours} = {percentage:.2%}")
            
            return percentage
            
        except Exception as e:
            logger.exception(f"Error calculating CAPEX percentage: {str(e)}")
            return 0.0

    def _belongs_to_capex_epic(self, work_item: Dict[str, Any], capex_epic_ids: set) -> bool:
        """Check if a work item belongs to any of the CAPEX epics"""
        try:
            # Check if the work item itself is a CAPEX epic
            if work_item['id'] in capex_epic_ids:
                return True
            
            # Traverse up the hierarchy to find if it belongs to a CAPEX epic
            current_item = work_item
            visited = set()  # Prevent infinite loops
            
            while current_item and current_item['id'] not in visited:
                visited.add(current_item['id'])
                
                # Get parent information
                parent_url = current_item.get('parent_url')
                if not parent_url:
                    break
                
                try:
                    parent_id = int(parent_url.split('/')[-1])
                    if parent_id in capex_epic_ids:
                        return True
                    
                    # Fetch parent details to continue traversal
                    parent_details = self._fetch_work_items_details([parent_id])
                    if parent_details:
                        current_item = parent_details[0]
                    else:
                        break
                        
                except (ValueError, IndexError, requests.RequestException):
                    break
            
            return False
            
        except Exception as e:
            logger.exception(f"Error checking CAPEX epic membership: {str(e)}")
            return False

    def organize_user_work_items(self, work_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize user work items by type without rollup calculations.
        This shows individual work item hours, not aggregated values.
        """
        logger.info(f"Organizing {len(work_items)} user work items by type...")
        
        organized = {
            "epics": [],
            "features": [],
            "stories": [],
            "leaf_items": []
        }
        
        for item in work_items:
            work_item_type = item.get("type", "").strip().lower()
            
            if work_item_type == "epic":
                organized["epics"].append(item)
            elif work_item_type == "feature":
                organized["features"].append(item)
            elif work_item_type in ["user story", "story"]:
                organized["stories"].append(item)
            else:
                # Tasks, Bugs, QA items, etc.
                organized["leaf_items"].append(item)
        
        logger.info(f"Organized work items: {len(organized['epics'])} epics, {len(organized['features'])} features, {len(organized['stories'])} stories, {len(organized['leaf_items'])} tasks/bugs/qa")
        return organized

    def _populate_parent_information(self, work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Populate parent information for work items
        
        Args:
            work_items: List of work items to process
            
        Returns:
            List of work items with parent information populated
        """
        try:
            logger.info("Populating parent information for work items...")
            
            # Create a mapping of work item IDs to work items for quick lookup
            work_item_map = {item['id']: item for item in work_items}
            
            for item in work_items:
                parent_url = item.get('parent_url')
                if parent_url:
                    try:
                        parent_id = int(parent_url.split('/')[-1])
                        
                        # Check if parent is in our current work items
                        if parent_id in work_item_map:
                            parent_item = work_item_map[parent_id]
                            item['parent_type'] = parent_item.get('type', '')
                            item['parent_id'] = parent_id
                            item['parent_title'] = parent_item.get('title', '')
                        else:
                            # Fetch parent details from API
                            parent_details = self._fetch_work_items_details([parent_id])
                            if parent_details:
                                parent = parent_details[0]
                                item['parent_type'] = parent.get('type', '')
                                item['parent_id'] = parent_id
                                item['parent_title'] = parent.get('title', '')
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse parent URL: {parent_url}")
                        item['parent_type'] = ''
                        item['parent_id'] = ''
                        item['parent_title'] = ''
                else:
                    item['parent_type'] = ''
                    item['parent_id'] = ''
                    item['parent_title'] = ''
            
            return work_items
            
        except Exception as e:
            logger.exception(f"Error populating parent information: {str(e)}")
            return work_items

    def _populate_parent_information_for_hierarchy(self, work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Populate parent information for work items in hierarchy
        
        Args:
            work_items: List of work items to process
            
        Returns:
            List of work items with parent information populated
        """
        try:
            logger.info("Populating parent information for hierarchy...")
            
            # Create a mapping of work item IDs to work items for quick lookup
            work_item_map = {item['id']: item for item in work_items}
            
            for item in work_items:
                parent_url = item.get('parent_url')
                if parent_url:
                    try:
                        parent_id = int(parent_url.split('/')[-1])
                        
                        # Check if parent is in our current work items
                        if parent_id in work_item_map:
                            parent_item = work_item_map[parent_id]
                            item['parent_type'] = parent_item.get('type', '')
                            item['parent_id'] = parent_id
                            item['parent_title'] = parent_item.get('title', '')
                        else:
                            # Fetch parent details from API
                            parent_details = self._fetch_work_items_details([parent_id])
                            if parent_details:
                                parent = parent_details[0]
                                item['parent_type'] = parent.get('type', '')
                                item['parent_id'] = parent_id
                                item['parent_title'] = parent.get('title', '')
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse parent URL: {parent_url}")
                        item['parent_type'] = ''
                        item['parent_id'] = ''
                        item['parent_title'] = ''
                else:
                    item['parent_type'] = ''
                    item['parent_id'] = ''
                    item['parent_title'] = ''
            
            return work_items
            
        except Exception as e:
            logger.exception(f"Error populating parent information: {str(e)}")
            return work_items

    def _aggregate_hours_from_descendants(self, work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregate hours from descendant work items to parent work items
        
        Args:
            work_items: List of work items to process
            
        Returns:
            List of work items with aggregated hours
        """
        try:
            logger.info("Aggregating hours from descendants to parents...")
            
            # Create a mapping for quick lookups
            work_item_map = {item['id']: item for item in work_items}
            
            # Create parent-child relationships
            children_map = {}  # parent_id -> [child_ids]
            for item in work_items:
                parent_id = item.get('parent_id')
                if parent_id and parent_id in work_item_map:
                    if parent_id not in children_map:
                        children_map[parent_id] = []
                    children_map[parent_id].append(item['id'])
            
            # Function to recursively calculate aggregated hours
            def calculate_aggregated_hours(work_item_id):
                item = work_item_map[work_item_id]
                
                # If this item has children, aggregate their hours
                if work_item_id in children_map:
                    total_estimated = 0
                    total_completed = 0
                    total_remaining = 0
                    
                    for child_id in children_map[work_item_id]:
                        child_estimated, child_completed, child_remaining = calculate_aggregated_hours(child_id)
                        total_estimated += child_estimated
                        total_completed += child_completed
                        total_remaining += child_remaining
                    
                    # Update the parent with aggregated values
                    item['estimated_hours'] = total_estimated
                    item['completed_work'] = total_completed
                    item['remaining_work'] = total_remaining
                    
                    # Recalculate percentage
                    if total_estimated > 0:
                        item['percent_complete'] = total_completed / total_estimated
                    else:
                        item['percent_complete'] = 0
                    
                    return total_estimated, total_completed, total_remaining
                else:
                    # Leaf item, return its own values
                    estimated = item.get('estimated_hours', 0) or 0
                    completed = item.get('completed_work', 0) or 0
                    remaining = item.get('remaining_work', 0) or 0
                    return estimated, completed, remaining
            
            # Calculate aggregated hours for all items
            for item in work_items:
                calculate_aggregated_hours(item['id'])
            
            return work_items
            
        except Exception as e:
            logger.exception(f"Error aggregating hours: {str(e)}")
            return work_items

    def _fetch_work_items_details(self, work_item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for multiple work items
        
        Args:
            work_item_ids: List of work item IDs to fetch
            
        Returns:
            List of work items with detailed information
        """
        try:
            if not work_item_ids:
                return []
            
            # Split into batches of 200 (Azure DevOps API limit)
            batch_size = 200
            all_work_items = []
            
            for i in range(0, len(work_item_ids), batch_size):
                batch_ids = work_item_ids[i:i + batch_size]
                ids_param = ','.join(map(str, batch_ids))
                
                url = f"{self.base_url}/workitems"
                params = {
                    'ids': ids_param,
                    'api-version': '6.0',
                    '$expand': 'relations'
                }
                
                logger.debug(f"Fetching work items batch: {len(batch_ids)} items")
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                batch_work_items = response.json().get('value', [])
                processed_items = self._process_work_items(batch_work_items)
                all_work_items.extend(processed_items)
            
            logger.info(f"Successfully fetched details for {len(all_work_items)} work items")
            return all_work_items
            
        except Exception as e:
            logger.exception(f"Error fetching work item details: {str(e)}")
            raise

    def _process_work_items(self, work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw work items from Azure DevOps API into standardized format
        
        Args:
            work_items: Raw work items from API
            
        Returns:
            List of processed work items
        """
        try:
            processed_items = []
            
            for item in work_items:
                fields = item.get('fields', {})
                relations = item.get('relations', [])
                
                # Extract parent URL from relations
                parent_url = None
                for relation in relations:
                    if relation.get('rel') == 'System.LinkTypes.Hierarchy-Reverse':
                        parent_url = relation.get('url')
                        break
                
                # Get numeric values with proper handling
                estimated_hours = self._get_numeric_value(fields.get('Microsoft.VSTS.Scheduling.OriginalEstimate'))
                completed_work = self._get_numeric_value(fields.get('Microsoft.VSTS.Scheduling.CompletedWork'))
                remaining_work = self._get_numeric_value(fields.get('Microsoft.VSTS.Scheduling.RemainingWork'))
                
                # Calculate percentage complete
                percent_complete = 0
                if estimated_hours and estimated_hours > 0:
                    percent_complete = completed_work / estimated_hours
                
                processed_item = {
                    'id': item.get('id'),
                    'title': fields.get('System.Title', ''),
                    'type': fields.get('System.WorkItemType', ''),
                    'state': fields.get('System.State', ''),
                    'assigned_to': self._extract_assigned_to(fields.get('System.AssignedTo')),
                    'estimated_hours': estimated_hours,
                    'completed_work': completed_work,
                    'remaining_work': remaining_work,
                    'percent_complete': percent_complete,
                    'parent_url': parent_url,
                    'work_item_type': fields.get('System.WorkItemType', ''),
                    'original_fields': fields  # Keep original fields for custom field access
                }
                
                processed_items.append(processed_item)
            
            return processed_items
            
        except Exception as e:
            logger.exception(f"Error processing work items: {str(e)}")
            raise

    def _get_numeric_value(self, value: Any) -> float:
        """
        Safely convert a value to float, returning 0 if conversion fails
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or 0 if conversion fails
        """
        if value is None:
            return 0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0

    def _extract_assigned_to(self, assigned_to_field: Any) -> str:
        """
        Extract assigned to name from the field value
        
        Args:
            assigned_to_field: Raw assigned to field from API
            
        Returns:
            Clean assigned to name
        """
        if not assigned_to_field:
            return ""
        
        if isinstance(assigned_to_field, dict):
            return assigned_to_field.get('displayName', '')
        elif isinstance(assigned_to_field, str):
            return assigned_to_field
        else:
            return str(assigned_to_field)
