
import requests
import base64
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

class AzureDevOpsService:
    def __init__(self, pat: str, organization: str, project: str):
        self.organization = organization
        self.project = project
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
        self.headers = {
            "Authorization": f"Basic {self._encode_pat(pat)}",
            "Content-Type": "application/json"
        }
        self.api_version = "7.0"  # Using a recent API version
    
    def _encode_pat(self, pat: str) -> str:
        """Encode the Personal Access Token for use in the Authorization header"""
        token = f":{pat}"
        return base64.b64encode(token.encode()).decode()
    
    def get_timestamp(self) -> str:
        """Get current timestamp formatted for filenames"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def fetch_epics(self, custom_field_filters: List[Dict[str, str]] = None, filter_date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch Epics from Azure DevOps with filtering done locally
        """
        # Base WIQL query to fetch only Epic work items
        wiql = {
            "query": "SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Epic'"
        }
        
        # Add date filter if provided
        if filter_date:
            logger.info(f"Filtering work items created on or after {filter_date}")
            wiql["query"] += f" AND [System.CreatedDate] >= '{filter_date}'"
        
        try:
            # Log the WIQL query for debugging
            logger.debug(f"WIQL Query: {wiql['query']}")
            logger.info(f"API Call 1: POST {self.base_url}/wit/wiql?api-version={self.api_version}")
            logger.info(f"API Call 1 Body: {json.dumps(wiql)}")
            
            # Make API call to execute WIQL query
            response = requests.post(
                f"{self.base_url}/wit/wiql?api-version={self.api_version}",
                headers=self.headers,
                json=wiql
            )
            
            # Check for error in the response
            if not response.ok:
                try:
                    error_data = response.json()
                    logger.error(f"Error response from WIQL API: {json.dumps(error_data)}")
                except:
                    logger.error(f"Error response from WIQL API: {response.text}")
                
                response.raise_for_status()
            
            # Parse response and extract work item IDs
            data = response.json()
            work_item_ids = [item["id"] for item in data.get("workItems", [])]
            
            if not work_item_ids:
                logger.info("No Epic work items found matching the date criteria")
                return []
            
            logger.info(f"Found {len(work_item_ids)} Epic work items before custom field filtering")
            
            # Fetch detailed work item data for the IDs
            all_epics = self._get_work_items_details(work_item_ids)
            
            # If no custom field filters, return all epics
            if not custom_field_filters:
                return all_epics
            
            # Apply custom field filters locally
            logger.info(f"Applying {len(custom_field_filters)} custom field filters locally")
            filtered_epics = self._filter_work_items_by_custom_fields(all_epics, custom_field_filters)
            
            logger.info(f"{len(filtered_epics)} epics remain after applying custom field filters")
            return filtered_epics
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Epics: {str(e)}")
            raise

    def fetch_user_work_items(self, assigned_to: str, custom_field_filters: List[Dict[str, str]] = None, 
                             filter_date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch all work items assigned to a specific user
        """
        # Build WIQL query to fetch work items assigned to the user
        wiql = {
            "query": f"SELECT [System.Id] FROM WorkItems WHERE [System.AssignedTo] = '{assigned_to}'"
        }
        
        # Add date filter if provided
        if filter_date:
            logger.info(f"Filtering work items created on or after {filter_date}")
            wiql["query"] += f" AND [System.CreatedDate] >= '{filter_date}'"
        
        try:
            logger.info(f"Fetching work items for user: {assigned_to}")
            logger.debug(f"WIQL Query: {wiql['query']}")
            
            # Make API call to execute WIQL query
            response = requests.post(
                f"{self.base_url}/wit/wiql?api-version={self.api_version}",
                headers=self.headers,
                json=wiql
            )
            
            response.raise_for_status()
            
            # Parse response and extract work item IDs
            data = response.json()
            work_item_ids = [item["id"] for item in data.get("workItems", [])]
            
            if not work_item_ids:
                logger.info(f"No work items found assigned to {assigned_to}")
                return []
            
            logger.info(f"Found {len(work_item_ids)} work items assigned to {assigned_to}")
            
            # Fetch detailed work item data for the IDs
            user_work_items = self._get_work_items_details(work_item_ids)
            
            return user_work_items
            
        except requests.exceptions.RequestException as e:
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
            # Initialize parent info
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
    
    def _get_all_descendant_work_items(self, epic_ids: List[int]) -> Dict[str, List[Dict[str, Any]]]:
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

    def traverse_hierarchy(self, epics: List[Dict[str, Any]], custom_field_filters: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Traverse the work item hierarchy starting from epics, including items that don't follow strict hierarchy
        """
        logger.info(f"Starting hierarchy traversal with {len(epics)} epics")
        
        epic_ids = [epic["id"] for epic in epics]
        
        # Get all descendants of these epics
        descendants = self._get_all_descendant_work_items(epic_ids)
        
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
