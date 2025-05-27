import requests
import base64
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

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
        
        Args:
            custom_field_filters: List of objects with key-value pairs for custom field filtering
            filter_date: Optional date string (YYYY-MM-DD) to filter work items created on or after
            
        Returns:
            List of Epic work items with their fields
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
            
            # DETAILED LOGGING: Log all fields for each Epic for debugging
            self._log_epic_fields_for_debugging(all_epics, custom_field_filters)
            
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

    def _log_epic_fields_for_debugging(self, epics: List[Dict[str, Any]], custom_field_filters: List[Dict[str, str]] = None):
        """
        Log detailed field information for each Epic to help with debugging
        
        Args:
            epics: List of Epic work items
            custom_field_filters: Custom field filters being applied
        """
        logger.info("=" * 80)
        logger.info("DEBUGGING: DETAILED EPIC FIELDS ANALYSIS")
        logger.info("=" * 80)
        
        if custom_field_filters:
            logger.info(f"Looking for custom field filters:")
            for i, field_filter in enumerate(custom_field_filters):
                logger.info(f"  Filter {i+1}: '{field_filter.get('key', 'N/A')}' = '{field_filter.get('value', 'N/A')}'")
        
        for epic_idx, epic in enumerate(epics):
            logger.info(f"\n--- EPIC {epic_idx + 1}: ID {epic.get('id', 'N/A')} ---")
            logger.info(f"Title: {epic.get('title', 'N/A')}")
            
            # Log all original fields from Azure DevOps
            original_fields = epic.get('original_fields', {})
            logger.info(f"Total fields available: {len(original_fields)}")
            
            # Separate system, Microsoft, and custom fields
            system_fields = {k: v for k, v in original_fields.items() if k.startswith('System.')}
            microsoft_fields = {k: v for k, v in original_fields.items() if k.startswith('Microsoft.')}
            custom_fields = {k: v for k, v in original_fields.items() if k.startswith('Custom.')}
            other_fields = {k: v for k, v in original_fields.items() if not k.startswith(('System.', 'Microsoft.', 'Custom.'))}
            
            logger.info(f"  System fields ({len(system_fields)}): {list(system_fields.keys())}")
            logger.info(f"  Microsoft fields ({len(microsoft_fields)}): {list(microsoft_fields.keys())}")
            logger.info(f"  Custom fields ({len(custom_fields)}): {list(custom_fields.keys())}")
            logger.info(f"  Other fields ({len(other_fields)}): {list(other_fields.keys())}")
            
            # Log ALL field details for debugging
            logger.info(f"\n  ALL FIELDS DETAILS:")
            for field_name, field_value in original_fields.items():
                logger.info(f"    Field: '{field_name}' = '{field_value}' (type: {type(field_value)})")
            
            # Log custom field details
            if custom_fields:
                logger.info(f"\n  CUSTOM FIELDS DETAILS:")
                for field_name, field_value in custom_fields.items():
                    # Show both the full field name and simplified name
                    simple_name = field_name[7:] if field_name.startswith('Custom.') else field_name
                    logger.info(f"    Full name: '{field_name}'")
                    logger.info(f"    Simple name: '{simple_name}'")
                    logger.info(f"    Value: '{field_value}'")
                    logger.info(f"    Value type: {type(field_value)}")
                    logger.info(f"    ---")
            else:
                logger.info(f"  NO CUSTOM FIELDS FOUND")
            
            # If we have custom field filters, check matching for this epic
            if custom_field_filters:
                logger.info(f"\n  FILTER MATCHING FOR THIS EPIC:")
                for filter_idx, field_filter in enumerate(custom_field_filters):
                    filter_key = field_filter.get('key', '')
                    filter_value = field_filter.get('value', '')
                    
                    logger.info(f"    Filter {filter_idx + 1}: Looking for '{filter_key}' = '{filter_value}'")
                    
                    # Check all possible field name variations
                    possible_matches = []
                    
                    # Check exact match with Custom. prefix
                    if f"Custom.{filter_key}" in original_fields:
                        possible_matches.append(f"Custom.{filter_key}")
                    
                    # Check exact match without prefix
                    if filter_key in original_fields:
                        possible_matches.append(filter_key)
                    
                    # Check if filter_key already has Custom. prefix
                    if filter_key.startswith('Custom.') and filter_key in original_fields:
                        possible_matches.append(filter_key)
                    
                    # Check partial matches (case insensitive)
                    for field_name in original_fields.keys():
                        if field_name.lower().find(filter_key.lower()) != -1:
                            possible_matches.append(f"PARTIAL_MATCH: {field_name}")
                    
                    if possible_matches:
                        logger.info(f"      Possible matches found: {possible_matches}")
                        for match in possible_matches:
                            if not match.startswith('PARTIAL_MATCH:'):
                                actual_value = original_fields.get(match, 'N/A')
                                logger.info(f"      '{match}' value: '{actual_value}'")
                                logger.info(f"      Match check: '{actual_value}' == '{filter_value}' ? {str(actual_value).strip().lower() == str(filter_value).strip().lower()}")
                    else:
                        logger.info(f"      NO MATCHES FOUND for '{filter_key}'")
            
            logger.info(f"--- END EPIC {epic_idx + 1} ---\n")
        
        logger.info("=" * 80)
        logger.info("END DEBUGGING: DETAILED EPIC FIELDS ANALYSIS")
        logger.info("=" * 80)
    
    def _filter_work_items_by_custom_fields(self, work_items: List[Dict[str, Any]], 
                                          custom_field_filters: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Filter work items based on custom field criteria
        
        Args:
            work_items: List of work items to filter
            custom_field_filters: List of objects with key-value pairs for custom field filtering
            
        Returns:
            Filtered list of work items
        """
        if not custom_field_filters:
            return work_items
            
        filtered_items = []
        
        for item in work_items:
            matches_all_filters = True
            
            # Debug: Log all available fields for the first item
            if item == work_items[0]:
                logger.debug(f"Available fields for Epic {item['id']}: {list(item.get('original_fields', {}).keys())}")
                # Also log custom fields specifically
                custom_fields_found = {k: v for k, v in item.get('original_fields', {}).items() if k.startswith('Custom.')}
                logger.debug(f"Custom fields found: {custom_fields_found}")
            
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
                
                # Debug logging for field matching
                logger.debug(f"Field '{field_name}': expected='{expected_value}', actual='{actual_value}'")
                
                # Compare values (case-insensitive)
                if actual_value is None:
                    logger.debug(f"Field '{field_name}' not found in Epic {item['id']}")
                    matches_all_filters = False
                    break
                elif str(actual_value).strip().lower() != str(expected_value).strip().lower():
                    logger.debug(f"Field '{field_name}' value mismatch in Epic {item['id']}: '{actual_value}' != '{expected_value}'")
                    matches_all_filters = False
                    break
                else:
                    logger.debug(f"Field '{field_name}' matches in Epic {item['id']}")
            
            if matches_all_filters:
                logger.debug(f"Epic {item['id']} matches all filters")
                filtered_items.append(item)
            else:
                logger.debug(f"Epic {item['id']} filtered out")
                
        return filtered_items
    
    def _get_work_items_details(self, work_item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get detailed information for multiple work items
        
        Args:
            work_item_ids: List of work item IDs to fetch details for
            
        Returns:
            List of work items with detailed information
        """
        # Batch requests in groups of 200 (Azure DevOps API limit)
        batch_size = 200
        all_items = []
        
        for i in range(0, len(work_item_ids), batch_size):
            batch_ids = work_item_ids[i:i+batch_size]
            ids_string = ",".join(map(str, batch_ids))
            
            try:
                # Request work item details with $expand=all to get all fields including custom fields
                # Note: Cannot use both $expand=all and fields=* together per Azure DevOps API
                url = f"{self.base_url}/wit/workitems?ids={ids_string}&$expand=all&api-version={self.api_version}"
                logger.info(f"API Call 2: GET {url}")
                
                response = requests.get(url, headers=self.headers)
                
                logger.info(f"API Call 2 Response Status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"API Call 2 Response Body: {response.text}")
                
                response.raise_for_status()
                
                batch_data = response.json()
                logger.info(f"API Call 2 Response: Found {len(batch_data.get('value', []))} work items")
                
                # Log the first work item's fields for debugging
                if batch_data.get('value') and len(batch_data['value']) > 0:
                    first_item = batch_data['value'][0]
                    logger.info(f"Sample work item fields: {list(first_item.get('fields', {}).keys())}")
                
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
        
        Args:
            work_item: Raw work item data from Azure DevOps API
            
        Returns:
            Transformed work item with simplified field access
        """
        fields = work_item.get("fields", {})
        work_item_type = fields.get("System.WorkItemType", "")
        
        # Log the work item being transformed
        logger.debug(f"Transforming work item {work_item.get('id')}: type='{work_item_type}'")
        
        # Basic fields that are present in all work items
        result = {
            "id": work_item.get("id"),
            "url": work_item.get("url"),
            "type": work_item_type,  # This is the key field for filtering
            "work_item_type": work_item_type,  # Add this as an alias for compatibility
            "title": fields.get("System.Title", ""),
            "state": fields.get("System.State", ""),
            "created_date": fields.get("System.CreatedDate", ""),
            "assigned_to": fields.get("System.AssignedTo", {}).get("displayName", "") if isinstance(fields.get("System.AssignedTo"), dict) else fields.get("System.AssignedTo", ""),
            # Store the original fields for reference in filtering
            "original_fields": fields
        }
        
        # Metrics - handle fields that may not exist in some work items
        result["estimated_hours"] = float(fields.get("Microsoft.VSTS.Scheduling.OriginalEstimate", 0) or 0)
        result["completed_work"] = float(fields.get("Microsoft.VSTS.Scheduling.CompletedWork", 0) or 0)
        result["remaining_work"] = float(fields.get("Microsoft.VSTS.Scheduling.RemainingWork", 0) or 0)
        
        # Add all custom fields to the result
        for field_name, field_value in fields.items():
            if field_name.startswith("Custom."):
                simple_name = field_name.split('.')[-1]
                result[simple_name] = field_value
        
        logger.debug(f"Transformed work item {result['id']}: type='{result['type']}'")
        return result
    
    def _get_child_work_items(self, parent_id: int) -> List[Dict[str, Any]]:
        """
        Get child work items for a given parent work item
        
        Args:
            parent_id: ID of the parent work item
            
        Returns:
            List of child work items with their details
        """
        try:
            # Use WIQL to find child work items
            wiql = {
                "query": f"""
                SELECT [System.Id] 
                FROM WorkItemLinks 
                WHERE ([Source].[System.Id] = {parent_id}) 
                AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward') 
                MODE (Recursive)
                """
            }
            
            logger.info(f"API Call 3: POST {self.base_url}/wit/wiql?api-version={self.api_version}")
            logger.info(f"API Call 3 Body: {json.dumps(wiql)}")
            
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
    
    def _roll_up_metrics(self, items: List[Dict[str, Any]]) -> None:
        """
        Roll up metrics from children to parent items
        
        This recursively calculates estimated_hours, completed_work, and remaining_work
        for each level in the hierarchy based on children's values.
        
        Args:
            items: List of work items with children to process
        """
        for item in items:
            children = item.get("children", [])
            
            if children:
                # Recursively process children first
                self._roll_up_metrics(children)
                
                # Roll up metrics from children
                estimated_hours = sum(child.get("estimated_hours", 0) for child in children)
                completed_work = sum(child.get("completed_work", 0) for child in children)
                remaining_work = sum(child.get("remaining_work", 0) for child in children)
                
                # Update the parent's metrics with rolled-up values
                item["estimated_hours"] = estimated_hours
                item["completed_work"] = completed_work
                item["remaining_work"] = remaining_work
            
            # Calculate percent complete (as decimal between 0 and 1)
            est = item.get("estimated_hours", 0)
            comp = item.get("completed_work", 0)
            item["percent_complete"] = comp / est if est > 0 else 0
            
            logger.debug(f"Work item {item.get('id')}: est={est}, comp={comp}, remaining={item.get('remaining_work', 0)}, pct={item['percent_complete']}")

    def traverse_hierarchy(self, epics: List[Dict[str, Any]], custom_field_filters: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Traverse the work item hierarchy starting from epics
        
        Args:
            epics: List of Epic work items to traverse
            custom_field_filters: List of custom fields to include in results
            
        Returns:
            Hierarchical data structure with all work items
        """
        logger.info(f"Starting hierarchy traversal with {len(epics)} epics")
        
        # Lists to store different types of work items
        features = []
        stories = []
        leaf_items = []  # Tasks, bugs, etc.
        
        # Process each epic and its children
        for epic in epics:
            epic_id = epic["id"]
            logger.info(f"Processing Epic {epic_id}: {epic['title']}")
            
            # Get feature children of this epic
            epic_features = self._get_child_work_items(epic_id)
            epic["children"] = epic_features
            logger.info(f"Epic {epic_id} has {len(epic_features)} direct children")
            
            # Process each feature and its children
            for feature in epic_features:
                feature["epic_id"] = epic_id
                feature["epic_title"] = epic["title"]
                features.append(feature)
                
                feature_id = feature["id"]
                logger.debug(f"Processing Feature {feature_id}: {feature['title']} (type: {feature.get('type')})")
                
                # Get user story children of this feature
                feature_stories = self._get_child_work_items(feature_id)
                feature["children"] = feature_stories
                logger.debug(f"Feature {feature_id} has {len(feature_stories)} direct children")
                
                # Process each user story and its children
                for story in feature_stories:
                    story["feature_id"] = feature_id
                    story["feature_title"] = feature["title"]
                    stories.append(story)
                    
                    story_id = story["id"]
                    logger.debug(f"Processing Story {story_id}: {story['title']} (type: {story.get('type')})")
                    
                    # Get task children of this story
                    story_tasks = self._get_child_work_items(story_id)
                    story["children"] = story_tasks
                    logger.debug(f"Story {story_id} has {len(story_tasks)} direct children")
                    
                    # Process each task
                    for task in story_tasks:
                        task["story_id"] = story_id
                        task["story_title"] = story["title"]
                        leaf_items.append(task)
                        logger.debug(f"Added Task {task['id']}: {task['title']} (type: {task.get('type')})")
        
        logger.info(f"Hierarchy traversal complete:")
        logger.info(f"  - {len(epics)} epics")
        logger.info(f"  - {len(features)} features")
        logger.info(f"  - {len(stories)} stories")
        logger.info(f"  - {len(leaf_items)} leaf items")
        
        # Collect all custom field names from the filter
        custom_fields = []
        if custom_field_filters:
            for field in custom_field_filters:
                if "key" in field:
                    field_name = field["key"]
                    # Strip Custom. prefix if present
                    if field_name.startswith('Custom.'):
                        field_name = field_name[7:]  # Remove 'Custom.' prefix
                    custom_fields.append(field_name)
        
        # Roll up metrics from children to parents
        logger.info("Rolling up metrics from children to parents")
        self._roll_up_metrics(epics)
        
        return {
            "epics": epics,
            "features": features,
            "stories": stories,
            "leaf_items": leaf_items,
            "custom_fields": custom_fields
        }
