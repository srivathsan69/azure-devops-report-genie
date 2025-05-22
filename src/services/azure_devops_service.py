
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
        
        # Add date filter if provided - this is simple enough to include in the query
        if filter_date:
            logger.info(f"Filtering work items created on or after {filter_date}")
            wiql["query"] += f" AND [System.CreatedDate] >= '{filter_date}'"
        
        try:
            # Log the WIQL query for debugging
            logger.debug(f"WIQL Query: {wiql['query']}")
            
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
            
            for field_filter in custom_field_filters:
                if not field_filter.get("key") or "value" not in field_filter:
                    continue
                    
                field_name = field_filter["key"]
                expected_value = field_filter["value"]
                
                # Handle field names with or without Custom. prefix
                field_key = field_name
                if field_name.startswith("Custom."):
                    # For fields specified as "Custom.FieldName" in the filter
                    short_name = field_name[7:]  # Remove "Custom." prefix
                    
                    # First check if the simple name exists in transformed item
                    if short_name in item:
                        actual_value = item[short_name]
                    else:
                        # Otherwise check the original fields
                        field_key = field_name
                        actual_value = None
                        
                        # Look in the original fields dictionary if it was preserved
                        if "original_fields" in item:
                            actual_value = item["original_fields"].get(field_name)
                else:
                    # For fields specified without prefix, check both with and without custom prefix
                    if field_name in item:
                        actual_value = item[field_name]
                    elif f"Custom.{field_name}" in item.get("original_fields", {}):
                        actual_value = item["original_fields"].get(f"Custom.{field_name}")
                    else:
                        actual_value = None
                
                # Compare values
                if actual_value is None or str(actual_value).lower() != str(expected_value).lower():
                    matches_all_filters = False
                    break
            
            if matches_all_filters:
                filtered_items.append(item)
                
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
                # Request work item details with all fields
                response = requests.get(
                    f"{self.base_url}/wit/workitems?ids={ids_string}&$expand=all&api-version={self.api_version}",
                    headers=self.headers
                )
                response.raise_for_status()
                
                batch_data = response.json()
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
        
        # Basic fields that are present in all work items
        result = {
            "id": work_item.get("id"),
            "url": work_item.get("url"),
            "type": fields.get("System.WorkItemType", ""),
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
        
        return result
    
    # ... keep existing code (other methods)

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
                
                # Only update if the item doesn't have its own values
                if not item.get("estimated_hours"):
                    item["estimated_hours"] = estimated_hours
                    
                if not item.get("completed_work"):
                    item["completed_work"] = completed_work
                    
                if not item.get("remaining_work"):
                    item["remaining_work"] = remaining_work
            
            # Calculate percent complete
            est = item.get("estimated_hours", 0)
            comp = item.get("completed_work", 0)
            item["percent_complete"] = comp / est if est > 0 else 0

    def traverse_hierarchy(self, epics: List[Dict[str, Any]], custom_field_filters: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Traverse the work item hierarchy starting from epics
        
        Args:
            epics: List of Epic work items to traverse
            custom_field_filters: List of custom fields to include in results
            
        Returns:
            Hierarchical data structure with all work items
        """
        # Lists to store different types of work items
        features = []
        stories = []
        leaf_items = []  # Tasks, bugs, etc.
        
        # Process each epic and its children
        for epic in epics:
            epic_id = epic["id"]
            
            # Get feature children of this epic
            epic_features = self._get_child_work_items(epic_id)
            epic["children"] = epic_features
            
            # Process each feature and its children
            for feature in epic_features:
                feature["epic_id"] = epic_id
                feature["epic_title"] = epic["title"]
                features.append(feature)
                
                feature_id = feature["id"]
                
                # Get user story children of this feature
                feature_stories = self._get_child_work_items(feature_id)
                feature["children"] = feature_stories
                
                # Process each user story and its children
                for story in feature_stories:
                    story["feature_id"] = feature_id
                    story["feature_title"] = feature["title"]
                    stories.append(story)
                    
                    story_id = story["id"]
                    
                    # Get task children of this story
                    story_tasks = self._get_child_work_items(story_id)
                    story["children"] = story_tasks
                    
                    # Process each task
                    for task in story_tasks:
                        task["story_id"] = story_id
                        task["story_title"] = story["title"]
                        leaf_items.append(task)
        
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
        self._roll_up_metrics(epics)
        
        return {
            "epics": epics,
            "features": features,
            "stories": stories,
            "leaf_items": leaf_items,
            "custom_fields": custom_fields
        }
