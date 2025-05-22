
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

    def _get_field_reference(self, field_name: str) -> str:
        """
        Format field names for WIQL query according to Azure DevOps rules
        
        Args:
            field_name: The name of the field to format
        
        Returns:
            Properly formatted field reference for WIQL query
        """
        # Extract the proper field name (with or without 'Custom.' prefix)
        if field_name.startswith('Custom.'):
            # Use the original field name including the prefix
            # Azure DevOps requires fields to be referenced as [Custom.FieldName] in WIQL
            return f"[{field_name}]"
        elif field_name.startswith('System.') or field_name.startswith('Microsoft.'):
            # System and Microsoft fields use their full name
            return f"[{field_name}]"
        else:
            # For custom fields without the 'Custom.' prefix, add it
            return f"[Custom.{field_name}]"
    
    def fetch_epics(self, custom_field_filters: List[Dict[str, str]] = None, filter_date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch Epics from Azure DevOps with optional custom field and date filtering
        
        Args:
            custom_field_filters: List of objects with key-value pairs for custom field filtering
            filter_date: Optional date string (YYYY-MM-DD) to filter work items created on or after
            
        Returns:
            List of Epic work items with their fields
        """
        # Base WIQL query to fetch Epic work items
        wiql = {
            "query": "SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate], [System.AssignedTo] FROM WorkItems WHERE [System.WorkItemType] = 'Epic'"
        }
        
        # Add date filter if provided
        if filter_date:
            logger.info(f"Filtering work items created on or after {filter_date}")
            wiql["query"] += f" AND [System.CreatedDate] >= '{filter_date}'"
        
        # Add custom field filters if provided
        if custom_field_filters:
            logger.info(f"Applying {len(custom_field_filters)} custom field filters")
            for field in custom_field_filters:
                if "key" in field and "value" in field:
                    field_name = field["key"]
                    field_value = field["value"]
                    
                    field_ref = self._get_field_reference(field_name)
                    # For string values, wrap in single quotes
                    if isinstance(field_value, str):
                        field_value = f"'{field_value}'"
                    
                    wiql["query"] += f" AND {field_ref} = {field_value}"
        
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
                logger.info("No Epic work items found matching the criteria")
                return []
            
            logger.info(f"Found {len(work_item_ids)} Epic work items")
            
            # Fetch detailed work item data for the IDs
            return self._get_work_items_details(work_item_ids)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Epics: {str(e)}")
            raise
    
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
    
    # ... keep existing code (other methods)

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
    
    def _get_child_work_items(self, parent_id: int) -> List[Dict[str, Any]]:
        """
        Get the child work items of a parent work item
        
        Args:
            parent_id: ID of the parent work item
            
        Returns:
            List of child work items
        """
        try:
            # Query for child IDs using the relationships API
            response = requests.get(
                f"{self.base_url}/wit/workitems/{parent_id}?$expand=relations&api-version={self.api_version}",
                headers=self.headers
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract child work item IDs
            child_ids = []
            for relation in data.get("relations", []):
                if relation.get("rel") == "System.LinkTypes.Hierarchy-Forward":
                    child_url = relation.get("url", "")
                    if child_url:
                        # Extract ID from URL
                        child_id = int(child_url.split("/")[-1])
                        child_ids.append(child_id)
            
            if not child_ids:
                return []
            
            # Get detailed information for child work items
            return self._get_work_items_details(child_ids)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching child work items: {str(e)}")
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
