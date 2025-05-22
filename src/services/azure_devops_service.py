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
        Fetch Epic work items using WIQL query with optional custom field filters and date filter
        
        Args:
            custom_field_filters: List of dicts with 'key' and 'value' to filter epics
                                  Example: [{'key': 'Custom.Feasible', 'value': 'Yes'}]
            filter_date: Optional date string (YYYY-MM-DD) to filter work items created on or after this date
        """
        url = f"{self.base_url}/wit/wiql?api-version={self.api_version}"
        
        # Start with base query filtering by project and work item type
        query = f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.WorkItemType] = 'Epic'
            AND [System.TeamProject] = '{self.project}'
            AND [System.State] <> 'Closed'
        """
        
        # Add date filter if provided
        if filter_date:
            try:
                # Validate date format
                datetime.strptime(filter_date, '%Y-%m-%d')
                logger.info(f"Filtering work items created on or after {filter_date}")
                query += f"AND [System.CreatedDate] >= '{filter_date}'\n"
            except ValueError:
                logger.warning(f"Invalid date format for filter_date: {filter_date}. Expected YYYY-MM-DD. Ignoring date filter.")
        
        # Add custom field filters if provided
        if custom_field_filters and isinstance(custom_field_filters, list):
            logger.info(f"Applying {len(custom_field_filters)} custom field filters")
            try:
                for filter_item in custom_field_filters:
                    if not isinstance(filter_item, dict) or 'key' not in filter_item or 'value' not in filter_item:
                        logger.warning(f"Skipping invalid filter item: {filter_item}")
                        continue
                        
                    field_name = filter_item['key']
                    field_value = filter_item['value']
                    
                    # Handle field name formatting - ensure it's properly formatted for WIQL
                    if not field_name.startswith('System.') and not field_name.startswith('Microsoft.'):
                        # For custom fields, escape field names with single quotes if they contain spaces
                        if ' ' in field_name:
                            # Remove any Custom. prefix if it exists
                            if field_name.startswith('Custom.'):
                                clean_name = field_name[7:]
                            else:
                                clean_name = field_name
                            field_name = f"[Custom.'{clean_name}']"
                        elif not field_name.startswith('Custom.'):
                            field_name = f"Custom.{field_name}"
                    
                    # Add to query - use equals operators for exact match
                    logger.debug(f"Adding filter: {field_name} = '{field_value}'")
                    query += f"AND {field_name} = '{field_value}'\n"
            
                # Log the complete query for debugging
                logger.debug(f"Complete WIQL query: {query}")
            except Exception as e:
                logger.error(f"Error building custom field filter: {str(e)}")
                raise
        
        # Finish query
        query += "ORDER BY [System.CreatedDate] DESC"
        
        wiql = {"query": query}
        
        try:
            response = requests.post(url, headers=self.headers, json=wiql)
            # Log response for debugging
            logger.debug(f"WIQL API Response Status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Error response from WIQL API: {response.text}")
            
            response.raise_for_status()
            
            query_result = response.json()
            
            work_item_ids = [item["id"] for item in query_result.get("workItems", [])]
            logger.info(f"Found {len(work_item_ids)} epics matching the criteria")
            
            if not work_item_ids:
                return []
            
            # Fetch detailed work item information for all retrieved epic IDs
            return self.get_work_items_details(work_item_ids)
            
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching Epics: {str(e)}")
            raise
    
    def get_work_items_details(self, work_item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get detailed information for the specified work items
        
        Args:
            work_item_ids: List of work item IDs
        """
        if not work_item_ids:
            return []
            
        # Azure DevOps API has a limit on the number of IDs in a single request
        batch_size = 200
        batched_ids = [work_item_ids[i:i + batch_size] for i in range(0, len(work_item_ids), batch_size)]
        
        all_work_items = []
        
        for batch in batched_ids:
            ids_string = ",".join(map(str, batch))
            url = f"{self.base_url}/wit/workitems?ids={ids_string}&$expand=relations&api-version={self.api_version}"
            
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                batch_results = response.json().get("value", [])
                all_work_items.extend(batch_results)
                
            except requests.exceptions.RequestException as e:
                logger.exception(f"Error fetching work item details: {str(e)}")
                raise
                
        return all_work_items
    
    def get_work_item_relations(self, work_item_id: int) -> Dict[str, Any]:
        """
        Get work item with all its relations
        
        Args:
            work_item_id: ID of the work item
        """
        url = f"{self.base_url}/wit/workitems/{work_item_id}?$expand=relations&api-version={self.api_version}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching work item relations: {str(e)}")
            raise
    
    def traverse_hierarchy(self, epics: List[Dict[str, Any]], custom_fields: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Traverse work item hierarchy and roll up data
        
        Args:
            epics: List of epic work items
            custom_fields: List of dicts with 'key' and optional 'value' to include in output
        """
        # Extract just the field names for data extraction
        custom_field_names = []
        if custom_fields:
            for field_item in custom_fields:
                if isinstance(field_item, dict) and 'key' in field_item:
                    field_key = field_item['key']
                    # Handle field name formatting
                    if not field_key.startswith('System.') and not field_key.startswith('Microsoft.') and not field_key.startswith('Custom.'):
                        field_key = f"Custom.{field_key}"
                    custom_field_names.append(field_key)
                elif isinstance(field_item, str):  # For backward compatibility
                    field_key = field_item
                    if not field_key.startswith('System.') and not field_key.startswith('Microsoft.') and not field_key.startswith('Custom.'):
                        field_key = f"Custom.{field_key}"
                    custom_field_names.append(field_key)
                    
        result = {
            "epics": [],
            "features": [],
            "stories": [],
            "leaf_items": []
        }
        
        logger.info(f"Processing {len(epics)} epics and their hierarchies")
        
        # Update the _extract_work_item_data method to handle custom fields from the custom_field_names list
        for epic in epics:
            epic_data = self._extract_work_item_data(epic, "Epic", custom_field_names)
            epic_data["children"] = []
            
            # Get child work items (Features under this Epic)
            child_relations = [r for r in epic.get("relations", []) 
                              if r.get("attributes", {}).get("name") == "Child"]
            
            feature_ids = [int(r["url"].split("/")[-1]) for r in child_relations]
            features = self.get_work_items_details(feature_ids) if feature_ids else []
            
            total_estimated_hours = 0
            total_completed_work = 0
            
            for feature in features:
                feature_data = self._extract_work_item_data(feature, "Feature", custom_field_names)
                feature_data["children"] = []
                
                # Get child work items (User Stories under this Feature)
                feature_with_relations = self.get_work_item_relations(feature["id"])
                story_relations = [r for r in feature_with_relations.get("relations", []) 
                                 if r.get("attributes", {}).get("name") == "Child"]
                
                story_ids = [int(r["url"].split("/")[-1]) for r in story_relations]
                stories = self.get_work_items_details(story_ids) if story_ids else []
                
                feature_estimated_hours = 0
                feature_completed_work = 0
                
                for story in stories:
                    story_data = self._extract_work_item_data(story, "User Story", custom_field_names)
                    story_data["children"] = []
                    
                    # Get child work items (Tasks, Bugs, etc. under this Story)
                    story_with_relations = self.get_work_item_relations(story["id"])
                    task_relations = [r for r in story_with_relations.get("relations", []) 
                                   if r.get("attributes", {}).get("name") == "Child"]
                    
                    task_ids = [int(r["url"].split("/")[-1]) for r in task_relations]
                    tasks = self.get_work_items_details(task_ids) if task_ids else []
                    
                    story_estimated_hours = 0
                    story_completed_work = 0
                    
                    for task in tasks:
                        task_data = self._extract_work_item_data(task, "Task", custom_field_names)
                        
                        # Extract effort metrics
                        task_estimated = self._get_field_value(task, "Microsoft.VSTS.Scheduling.OriginalEstimate", 0)
                        task_completed = self._get_field_value(task, "Microsoft.VSTS.Scheduling.CompletedWork", 0)
                        
                        task_data["estimated_hours"] = task_estimated
                        task_data["completed_work"] = task_completed
                        
                        story_estimated_hours += task_estimated
                        story_completed_work += task_completed
                        
                        # Add to leaf items collection
                        result["leaf_items"].append(task_data)
                        
                        # Add to story's children
                        story_data["children"].append(task_data)
                    
                    # Roll up metrics to story level
                    story_data["estimated_hours"] = story_estimated_hours
                    story_data["completed_work"] = story_completed_work
                    
                    feature_estimated_hours += story_estimated_hours
                    feature_completed_work += story_completed_work
                    
                    # Add to stories collection
                    result["stories"].append(story_data)
                    
                    # Add to feature's children
                    feature_data["children"].append(story_data)
                
                # Roll up metrics to feature level
                feature_data["estimated_hours"] = feature_estimated_hours
                feature_data["completed_work"] = feature_completed_work
                
                total_estimated_hours += feature_estimated_hours
                total_completed_work += feature_completed_work
                
                # Add to features collection
                result["features"].append(feature_data)
                
                # Add to epic's children
                epic_data["children"].append(feature_data)
            
            # Roll up metrics to epic level
            epic_data["estimated_hours"] = total_estimated_hours
            epic_data["completed_work"] = total_completed_work
            
            # Add to epics collection
            result["epics"].append(epic_data)
        
        return result
    
    def _extract_work_item_data(self, work_item: Dict[str, Any], item_type: str, custom_fields: List[str]) -> Dict[str, Any]:
        """
        Extract relevant data from a work item
        
        Args:
            work_item: The work item data from Azure DevOps
            item_type: The type of work item (Epic, Feature, etc.)
            custom_fields: List of custom field names to extract
        """
        fields = work_item.get("fields", {})
        
        # Basic work item data
        data = {
            "id": work_item.get("id"),
            "type": item_type,
            "title": self._get_field_value(work_item, "System.Title", "No Title"),
            "state": self._get_field_value(work_item, "System.State", "Unknown"),
            "assigned_to": self._extract_person_name(self._get_field_value(work_item, "System.AssignedTo")),
            "estimated_hours": 0,  # Will be populated for leaf items or rolled up for parents
            "completed_work": 0,   # Will be populated for leaf items or rolled up for parents
            "remaining_work": self._get_field_value(work_item, "Microsoft.VSTS.Scheduling.RemainingWork", 0),
            "created_date": self._get_field_value(work_item, "System.CreatedDate"),
            "url": work_item.get("url", "")
        }
        
        # Add custom fields if present in the work item
        if custom_fields:
            for field_name in custom_fields:
                # Use the field name as is, since it should already be properly formatted
                field_value = self._get_field_value(work_item, field_name, "N/A")
                # Use the unqualified field name as the key in our data structure
                simple_name = field_name.split('.')[-1] if '.' in field_name else field_name
                data[simple_name] = field_value
        
        return data
    
    def _get_field_value(self, work_item: Dict[str, Any], field_name: str, default_value: Any = None) -> Any:
        """Get field value from work item"""
        return work_item.get("fields", {}).get(field_name, default_value)
    
    def _extract_person_name(self, person_data: Any) -> str:
        """Extract display name from person data"""
        if not person_data:
            return "Unassigned"
            
        if isinstance(person_data, dict) and "displayName" in person_data:
            return person_data["displayName"]
            
        return str(person_data)
