import requests
import base64
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import urllib.parse  # Add this import

logger = logging.getLogger(__name__)

class AzureDevOpsAuthenticationError(Exception):
    """Custom exception for Azure DevOps authentication errors"""
    pass

class AzureDevOpsService:
    def __init__(self, pat: str, organization: str, project: str):
        self.organization = organization
        self.project = project
        # URL-encode project name to handle spaces/special characters
        encoded_project = urllib.parse.quote(project)
        self.base_url = f"https://dev.azure.com/{organization}/{encoded_project}/_apis"
        # Ensure PAT is properly encoded
        encoded_pat = self._encode_pat(pat)
        self.headers = {
            "Authorization": f"Basic {encoded_pat}",
            "Content-Type": "application/json"
        }
        self.api_version = "7.0"
    
    def _encode_pat(self, pat: str) -> str:
        """Encode the Personal Access Token for use in the Authorization header"""
        # Azure DevOps expects the PAT to be encoded as "username:pat"
        # where username can be empty
        token = f":{pat}"
        # Encode to base64 and ensure it's a string
        encoded = base64.b64encode(token.encode()).decode('utf-8')
        return encoded
    
    def get_timestamp(self) -> str:
        """Get current timestamp formatted for filenames"""
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
            # Use only the date part without time component
            date_clauses.append(f"[System.CreatedDate] <= '{filter_enddate}'")
        
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

    def _build_wiql_query(self, work_item_type: str, assigned_to: str = None, 
                         filter_startdate: str = None, filter_enddate: str = None,
                         filter_workitemtype: List[str] = None) -> str:
        """
        Build a robust WIQL query with proper escaping and encoding
        """
        # Escape single quotes by doubling them
        clean_work_item_type = work_item_type.replace("'", "''")
        
        # Create a list to store query parts
        query_parts = []
        
        # Add work item type filter with proper escaping
        query_parts.append(f"[System.WorkItemType] = '{clean_work_item_type}'")
        
        # Add assigned to filter if provided
        if assigned_to:
            clean_assigned_to = assigned_to.replace("'", "''")
            query_parts.append(f"[System.AssignedTo] = '{clean_assigned_to}'")
        
        # Add date filters if provided and if this work item type should be filtered
        should_apply_date_filter = self._should_apply_date_filter(work_item_type, filter_workitemtype)
        if should_apply_date_filter:
            if filter_startdate:
                query_parts.append(f"[System.CreatedDate] >= '{filter_startdate}'")
            if filter_enddate:
                query_parts.append(f"[System.CreatedDate] <= '{filter_enddate}'")
        
        # Build the final query
        where_clause = " AND ".join(query_parts)
        return f"SELECT [System.Id] FROM WorkItems WHERE {where_clause}"

    def fetch_epics(self, custom_field_filters: List[Dict[str, str]] = None, 
               filter_date: str = None, filter_startdate: str = None, 
               filter_enddate: str = None, filter_workitemtype: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch Epic work items with enhanced error handling
        """
        try:
            logger.info("Fetching Epic work items...")
            
            # Debug the parameters
            logger.debug(f"Parameters - custom_field_filters: {custom_field_filters}")
            logger.debug(f"filter_startdate: {filter_startdate}, filter_enddate: {filter_enddate}")
            
            # Use the generic fetch_work_items method
            epics = self.fetch_work_items(
                work_item_type="Epic",  # Hard-coded clean string
                custom_field_filters=custom_field_filters,
                filter_startdate=filter_startdate,
                filter_enddate=filter_enddate,
                filter_workitemtype=filter_workitemtype
            )
            
            logger.info(f"Found {len(epics)} Epic work items")
            return epics
            
        except Exception as e:
            logger.error(f"Error fetching Epics: {str(e)}")
            raise

    def fetch_work_items(self, work_item_type: str, assigned_to: str = None,
                        custom_field_filters: List[Dict[str, str]] = None,
                        filter_startdate: str = None, filter_enddate: str = None,
                        filter_workitemtype: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generic method to fetch work items of any type with filters
        """
        try:
            # Build the WIQL query with proper escaping
            wiql_query = self._build_wiql_query(
                work_item_type=work_item_type,
                assigned_to=assigned_to,
                filter_startdate=filter_startdate,
                filter_enddate=filter_enddate,
                filter_workitemtype=filter_workitemtype
            )

            # Prepare the request payload
            payload = {"query": wiql_query}
            
            # Log the query for debugging
            logger.debug(f"Executing WIQL query: {wiql_query}")
            
            # Execute the query
            response = requests.post(
                f"{self.base_url}/wit/wiql?api-version={self.api_version}",
                headers=self.headers,
                json=payload
            )
            
            # Handle authentication errors specifically
            if response.status_code == 401:
                logger.error("Azure DevOps authentication failed - Invalid PAT token")
                raise Exception("Invalid Azure DevOps PAT token. Please check your credentials.")
            
            # Handle other errors with detailed logging
            if not response.ok:
                error_msg = (f"WIQL API Error: {response.status_code} - {response.text}\n"
                            f"Query: {wiql_query}")
                logger.error(error_msg)
                raise requests.exceptions.HTTPError(error_msg)
            
            try:
                # Parse the response
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Azure DevOps response: {response.text}")
                if response.status_code == 401:
                    raise Exception("Invalid Azure DevOps PAT token. Please check your credentials.")
                raise Exception("Failed to parse Azure DevOps response. Please check your credentials and try again.")
            
            work_item_ids = [item["id"] for item in data.get("workItems", [])]
            
            if not work_item_ids:
                logger.info(f"No {work_item_type} work items found matching the criteria")
                return []
            
            # Get detailed work item data
            work_items = self._get_work_items_details_with_parents(work_item_ids)
            
            # Apply custom field filters if provided
            if custom_field_filters:
                work_items = self._filter_work_items_by_custom_fields(work_items, custom_field_filters)
            
            return work_items
            
        except Exception as e:
            if "Invalid Azure DevOps PAT token" in str(e):
                raise
            logger.error(f"Error fetching {work_item_type} work items: {str(e)}")
            raise

    def fetch_user_work_items(self, assigned_to: str, custom_field_filters: List[Dict[str, str]] = None, 
                             filter_date: str = None, filter_startdate: str = None, 
                             filter_enddate: str = None, filter_workitemtype: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch all work items assigned to a specific user with enhanced error handling
        """
        try:
            logger.info(f"Fetching work items assigned to {assigned_to}...")
            
            # Define work item types to fetch
            work_item_types = ["Epic", "Feature", "User Story", "Task", "Bug", "QA Validation Task"]
            all_work_items = []
            
            # Fetch each work item type
            for work_item_type in work_item_types:
                try:
                    items = self.fetch_work_items(
                        work_item_type=work_item_type,
                        assigned_to=assigned_to,
                        filter_startdate=filter_startdate,
                        filter_enddate=filter_enddate,
                        filter_workitemtype=filter_workitemtype
                    )
                    all_work_items.extend(items)
                    logger.info(f"Found {len(items)} {work_item_type} items for {assigned_to}")
                except Exception as e:
                    logger.error(f"Error fetching {work_item_type} items: {str(e)}")
                    # Continue with other work item types even if one fails
                    continue
            
            return all_work_items
            
        except Exception as e:
            logger.error(f"Error fetching user work items: {str(e)}")
            raise

    def _filter_work_items_by_custom_fields(self, work_items: List[Dict[str, Any]], 
                                          custom_field_filters: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Filter work items based on custom field criteria
        """
        if not custom_field_filters:
            return work_items
            
        filtered_items = []
        
        for item in work_items:
            matches_all_filters = True
            
            for field_filter in custom_field_filters:
                if not field_filter.get("key") or "value" not in field_filter:
                    continue
                    
                field_name = field_filter["key"]
                expected_value = field_filter["value"]
                
                # Find the actual field value
                actual_value = None
                
                # Strategy 1: Check if field name already has Custom. prefix
                if field_name.startswith("Custom."):
                    # Look in original_fields with exact key
                    if "original_fields" in item:
                        actual_value = item["original_fields"].get(field_name)
                        
                    # Also check the simplified name in the item
                    simple_name = field_name[7:]  # Remove "Custom." prefix
                    if actual_value is None and simple_name in item:
                        actual_value = item[simple_name]
                else:
                    # Strategy 2: Field name without prefix - check both ways
                    # First check the item directly
                    if field_name in item:
                        actual_value = item[field_name]
                    
                    # Then check with Custom. prefix in original_fields
                    if actual_value is None and "original_fields" in item:
                        actual_value = item["original_fields"].get(f"Custom.{field_name}")
                
                # Compare values (case-insensitive)
                if actual_value is None:
                    logger.debug(f"Field '{field_name}' not found in work item {item['id']}")
                    matches_all_filters = False
                    break
                elif str(actual_value).strip().lower() != str(expected_value).strip().lower():
                    logger.debug(f"Field '{field_name}' value mismatch in work item {item['id']}: '{actual_value}' != '{expected_value}'")
                    matches_all_filters = False
                    break
            
            if matches_all_filters:
                filtered_items.append(item)
                
        return filtered_items
    
    def _get_work_items_details_with_parents(self, work_item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get detailed information for multiple work items including parent information
        """
        # First get the basic work item details
        work_items = self._get_work_items_details(work_item_ids)
        
        # Now populate parent information for each work item
        for work_item in work_items:
            parent_info = self._get_parent_work_item_info(work_item["id"])
            work_item.update(parent_info)
        
        return work_items
    
    def _get_parent_work_item_info(self, work_item_id: int) -> Dict[str, str]:
        """
        Get parent work item information for a given work item ID
        Returns dict with parent_id, parent_type, and parent_title
        """
        try:
            # Use WIQL to find parent work item using hierarchy links
            wiql = {
                "query": f"""
                SELECT [System.Id] 
                FROM WorkItemLinks 
                WHERE ([Target].[System.Id] = {work_item_id}) 
                AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward')
                """
            }
            
            logger.debug(f"Getting parent info for work item {work_item_id}")
            
            response = requests.post(
                f"{self.base_url}/wit/wiql?api-version={self.api_version}",
                headers=self.headers,
                json=wiql
            )
            
            if not response.ok:
                logger.debug(f"Failed to get parent info for work item {work_item_id}: {response.status_code}")
                return {"parent_id": "", "parent_type": "", "parent_title": ""}
            
            data = response.json()
            work_item_relations = data.get("workItemRelations", [])
            
            # Find the parent (source) of the current work item
            parent_id = None
            for relation in work_item_relations:
                source = relation.get("source")
                if source and source.get("id"):
                    parent_id = source["id"]
                    break
            
            if not parent_id:
                logger.debug(f"No parent found for work item {work_item_id}")
                return {"parent_id": "", "parent_type": "", "parent_title": ""}
            
            # Get detailed information about the parent work item
            parent_details = self._get_work_items_details([parent_id])
            
            if parent_details:
                parent = parent_details[0]
                return {
                    "parent_id": str(parent_id),
                    "parent_type": parent.get("type", ""),
                    "parent_title": parent.get("title", "")
                }
            else:
                logger.debug(f"Failed to get parent details for parent ID {parent_id}")
                return {"parent_id": str(parent_id), "parent_type": "", "parent_title": ""}
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error getting parent info for work item {work_item_id}: {str(e)}")
            return {"parent_id": "", "parent_type": "", "parent_title": ""}
        except Exception as e:
            logger.debug(f"Unexpected error getting parent info for work item {work_item_id}: {str(e)}")
            return {"parent_id": "", "parent_type": "", "parent_title": ""}
    
    def _get_work_items_details(self, work_item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get detailed information for multiple work items
        """
        # Batch requests in groups of 200 (Azure DevOps API limit)
        batch_size = 200
        all_items = []
        
        for i in range(0, len(work_item_ids), batch_size):
            batch_ids = work_item_ids[i:i+batch_size]
            ids_string = ",".join(map(str, batch_ids))
            
            try:
                # Request work item details with $expand=all to get all fields including custom fields
                url = f"{self.base_url}/wit/workitems?ids={ids_string}&$expand=all&api-version={self.api_version}"
                logger.info(f"API Call 2: GET {url}")
                
                response = requests.get(url, headers=self.headers)
                
                logger.info(f"API Call 2 Response Status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"API Call 2 Response Body: {response.text}")
                
                response.raise_for_status()
                
                batch_data = response.json()
                logger.info(f"API Call 2 Response: Found {len(batch_data.get('value', []))} work items")
                
                all_items.extend(batch_data.get("value", []))
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching work item details: {str(e)}")
                raise
        
        # Transform response into a more usable format
        transformed_items = []
        for item in all_items:
            transformed = self._transform_work_item(item)
            transformed_items.append(transformed)
        
        return transformed_items
    
    def _transform_work_item(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a work item response into a more usable format
        """
        fields = work_item.get("fields", {})
        work_item_type = fields.get("System.WorkItemType", "")
        
        # Basic fields that are present in all work items
        result = {
            "id": work_item.get("id"),
            "url": work_item.get("url"),
            "type": work_item_type,
            "work_item_type": work_item_type,
            "title": fields.get("System.Title", ""),
            "state": fields.get("System.State", ""),
            "created_date": fields.get("System.CreatedDate", ""),
            "assigned_to": fields.get("System.AssignedTo", {}).get("displayName", "") if isinstance(fields.get("System.AssignedTo"), dict) else fields.get("System.AssignedTo", ""),
            # Store the original fields for reference in filtering
            "original_fields": fields,
            # Initialize parent info - will be populated by _get_parent_work_item_info if needed
            "parent_type": "",
            "parent_id": "",
            "parent_title": ""
        }
        
        # Metrics - handle fields that may not exist in some work items
        result["estimated_hours"] = float(fields.get("Microsoft.VSTS.Scheduling.OriginalEstimate", 0) or 0)
        result["completed_work"] = float(fields.get("Microsoft.VSTS.Scheduling.CompletedWork", 0) or 0)
        result["remaining_work"] = float(fields.get("Microsoft.VSTS.Scheduling.RemainingWork", 0) or 0)
        
        # Calculate percent complete (as decimal between 0 and 1)
        est = result["estimated_hours"]
        comp = result["completed_work"]
        result["percent_complete"] = comp / est if est > 0 else 0
        
        # Add all custom fields to the result
        for field_name, field_value in fields.items():
            if field_name.startswith("Custom."):
                simple_name = field_name.split('.')[-1]
                result[simple_name] = field_value
        
        return result
    
    def _get_all_descendant_work_items(self, epic_ids: List[int], filter_workitemtype: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all work items that are descendants of the given epic IDs, regardless of hierarchy violations
        """
        all_descendants = []
        processed_ids = set()
        
        # Start with the epic IDs
        current_level = epic_ids
        
        while current_level:
            next_level = []
            
            for parent_id in current_level:
                if parent_id in processed_ids:
                    continue
                    
                processed_ids.add(parent_id)
                
                # Get direct children
                children = self._get_child_work_items(parent_id)
                
                for child in children:
                    child_id = child["id"]
                    if child_id not in processed_ids:
                        # Set parent information
                        child["parent_id"] = parent_id
                        
                        # Find parent info from already processed items
                        parent_item = None
                        for item in all_descendants:
                            if item["id"] == parent_id:
                                parent_item = item
                                break
                        
                        if parent_item:
                            child["parent_type"] = parent_item["type"]
                            child["parent_title"] = parent_item["title"]
                        
                        all_descendants.append(child)
                        next_level.append(child_id)
            
            current_level = next_level
        
        # Categorize by work item type
        epics = []
        features = []
        stories = []
        leaf_items = []
        
        for item in all_descendants:
            item_type = item.get("type", "").lower()
            
            if item_type == "epic":
                epics.append(item)
            elif item_type == "feature":
                features.append(item)
            elif item_type == "user story":
                stories.append(item)
            elif item_type in ["task", "bug", "qa validation task"]:
                leaf_items.append(item)
            else:
                # Handle unknown types - add to leaf items
                leaf_items.append(item)
        
        return {
            "epics": epics,
            "features": features,
            "stories": stories,
            "leaf_items": leaf_items
        }
    
    def _get_child_work_items(self, parent_id: int) -> List[Dict[str, Any]]:
        """
        Get child work items for a given parent work item
        """
        try:
            # Use WIQL to find child work items
            wiql = {
                "query": f"""
                SELECT [System.Id] 
                FROM WorkItemLinks 
                WHERE ([Source].[System.Id] = {parent_id}) 
                AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward')
                """
            }
            
            logger.debug(f"Getting children for work item {parent_id}")
            
            # Execute WIQL query
            response = requests.post(
                f"{self.base_url}/wit/wiql?api-version={self.api_version}",
                headers=self.headers,
                json=wiql
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract child work item IDs from the workItemRelations
            child_ids = []
            work_item_relations = data.get("workItemRelations", [])
            
            for relation in work_item_relations:
                # Skip the source item (parent)
                if relation.get("source") is not None:
                    target = relation.get("target")
                    if target and target.get("id"):
                        child_ids.append(target["id"])
            
            if not child_ids:
                return []
            
            # Get detailed information for child work items
            return self._get_work_items_details(child_ids)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching child work items for parent {parent_id}: {str(e)}")
            return []

    def _aggregate_hours_from_descendants(self, work_items: List[Dict[str, Any]], 
                                         all_work_items: List[Dict[str, Any]]) -> None:
        """
        Aggregate hours from descendant work items for parent work items
        """
        logger.info("Starting hour aggregation for parent work items...")
        
        # Create lookup dict for fast access
        work_item_lookup = {item["id"]: item for item in all_work_items}
        
        # Build parent-child relationships
        children_map = {}
        for item in all_work_items:
            parent_id = item.get("parent_id")
            if parent_id:
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(item["id"])
        
        def get_all_descendants(parent_id: int) -> List[int]:
            """Recursively get all descendant IDs"""
            descendants = []
            direct_children = children_map.get(parent_id, [])
            
            for child_id in direct_children:
                descendants.append(child_id)
                descendants.extend(get_all_descendants(child_id))
            
            return descendants
        
        # Process each work item for aggregation
        for item in work_items:
            item_type = item.get("type", "").lower()
            
            # Only aggregate for parent work items (Epic, Feature, User Story)
            if item_type in ["epic", "feature", "user story"]:
                descendant_ids = get_all_descendants(item["id"])
                
                if descendant_ids:
                    total_estimated = 0
                    total_completed = 0
                    total_remaining = 0
                    
                    # Aggregate from all descendants
                    for desc_id in descendant_ids:
                        if desc_id in work_item_lookup:
                            desc_item = work_item_lookup[desc_id]
                            total_estimated += desc_item.get("estimated_hours", 0)
                            total_completed += desc_item.get("completed_work", 0)
                            total_remaining += desc_item.get("remaining_work", 0)
                    
                    # Update the parent item with aggregated values
                    item["estimated_hours"] = total_estimated
                    item["completed_work"] = total_completed
                    item["remaining_work"] = total_remaining
                    
                    # Recalculate percentage
                    if total_estimated > 0:
                        item["percent_complete"] = total_completed / total_estimated
                    else:
                        item["percent_complete"] = 0
                    
                    logger.debug(f"Aggregated hours for {item_type} {item['id']}: "
                               f"Est={total_estimated}, Comp={total_completed}, Rem={total_remaining}")

    def calculate_capex_percentage(self, user_work_items: List[Dict[str, Any]], 
                                 capex_epics: List[Dict[str, Any]]) -> float:
        """
        Calculate what percentage of user's work corresponds to CAPEX epics
        """
        if not user_work_items or not capex_epics:
            return 0.0
        
        capex_epic_ids = {epic["id"] for epic in capex_epics}
        
        # Get all descendants of CAPEX epics
        capex_descendants = self._get_all_descendant_work_items(list(capex_epic_ids))
        all_capex_items = []
        all_capex_items.extend(capex_descendants["epics"])
        all_capex_items.extend(capex_descendants["features"])
        all_capex_items.extend(capex_descendants["stories"])
        all_capex_items.extend(capex_descendants["leaf_items"])
        
        capex_item_ids = {item["id"] for item in all_capex_items}
        
        # Calculate totals
        total_estimated = sum(item.get("estimated_hours", 0) for item in user_work_items)
        capex_estimated = sum(item.get("estimated_hours", 0) for item in user_work_items 
                            if item["id"] in capex_item_ids)
        
        if total_estimated == 0:
            return 0.0
        
        return capex_estimated / total_estimated

    def traverse_hierarchy(self, epics: List[Dict[str, Any]], custom_field_filters: List[Dict[str, str]] = None,
                          filter_workitemtype: List[str] = None) -> Dict[str, Any]:
        """
        Traverse the work item hierarchy starting from epics, including items that don't follow strict hierarchy
        """
        logger.info(f"Starting hierarchy traversal with {len(epics)} epics")
        
        epic_ids = [epic["id"] for epic in epics]
        
        # Get all descendants of these epics
        descendants = self._get_all_descendant_work_items(epic_ids, filter_workitemtype)
        
        # Add the original epics to the results
        all_epics = epics + descendants["epics"]
        
        # Combine all work items for aggregation
        all_work_items = all_epics + descendants["features"] + descendants["stories"] + descendants["leaf_items"]
        
        # Perform hour aggregation
        self._aggregate_hours_from_descendants(all_work_items, all_work_items)
        
        logger.info(f"Hierarchy traversal complete:")
        logger.info(f"  - {len(all_epics)} epics")
        logger.info(f"  - {len(descendants['features'])} features")
        logger.info(f"  - {len(descendants['stories'])} stories")
        logger.info(f"  - {len(descendants['leaf_items'])} leaf items")
        
        return {
            "epics": all_epics,
            "features": descendants["features"],
            "stories": descendants["stories"],
            "leaf_items": descendants["leaf_items"]
        }

    def organize_user_work_items(self, user_work_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Organize user work items by type and perform hour aggregation
        """
        epics = []
        features = []
        stories = []
        leaf_items = []
        
        for item in user_work_items:
            item_type = item.get("type", "").lower()
            
            if item_type == "epic":
                epics.append(item)
            elif item_type == "feature":
                features.append(item)
            elif item_type == "user story":
                stories.append(item)
            elif item_type in ["task", "bug", "qa validation task"]:
                leaf_items.append(item)
            else:
                # Handle unknown types - add to leaf items
                leaf_items.append(item)
        
        # Perform hour aggregation for user work items
        all_user_items = epics + features + stories + leaf_items
        self._aggregate_hours_from_descendants(all_user_items, all_user_items)
        
        return {
            "epics": epics,
            "features": features,
            "stories": stories,
            "leaf_items": leaf_items
        }
    
    def _belongs_to_capex_epic(self, work_item: Dict[str, Any], capex_epic_ids: Set[int]) -> bool:
        """
        Check if a work item belongs to any of the CAPEX epics
        This method checks if the work item is directly a CAPEX epic or is a descendant of one
        """
        work_item_id = work_item.get("id")
        
        # Direct check: if this work item is itself a CAPEX epic
        if work_item_id in capex_epic_ids:
            return True
        
        # Check if this work item is a descendant of any CAPEX epic
        # We need to traverse up the hierarchy to find if any parent is a CAPEX epic
        try:
            # Get the parent chain for this work item
            parent_ids = self._get_parent_chain(work_item_id)
            
            # Check if any parent is in the CAPEX epic IDs
            for parent_id in parent_ids:
                if parent_id in capex_epic_ids:
                    return True
                    
        except Exception as e:
            logger.debug(f"Error checking parent chain for work item {work_item_id}: {str(e)}")
            # Fallback: if we can't determine hierarchy, assume non-CAPEX
            return False
        
        return False

    def _get_parent_chain(self, work_item_id: int) -> List[int]:
        """
        Get the chain of parent IDs for a given work item
        Returns list of parent IDs from immediate parent to root
        """
        parent_chain = []
        current_id = work_item_id
        processed_ids = set()  # Prevent infinite loops
        
        while current_id and current_id not in processed_ids:
            processed_ids.add(current_id)
            
            try:
                # Use WIQL to find parent work item
                wiql = {
                    "query": f"""
                    SELECT [System.Id] 
                    FROM WorkItemLinks 
                    WHERE ([Target].[System.Id] = {current_id}) 
                    AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward')
                    """
                }
                
                response = requests.post(
                    f"{self.base_url}/wit/wiql?api-version={self.api_version}",
                    headers=self.headers,
                    json=wiql
                )
                
                if not response.ok:
                    break
                    
                data = response.json()
                work_item_relations = data.get("workItemRelations", [])
                
                # Find the parent (source) of the current work item
                parent_id = None
                for relation in work_item_relations:
                    source = relation.get("source")
                    if source and source.get("id"):
                        parent_id = source["id"]
                        break
                
                if parent_id and parent_id != current_id:
                    parent_chain.append(parent_id)
                    current_id = parent_id
                else:
                    break
                    
            except Exception as e:
                logger.debug(f"Error getting parent for work item {current_id}: {str(e)}")
                break
        
        return parent_chain
