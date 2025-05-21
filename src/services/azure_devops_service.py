
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
    
    def fetch_epics(self) -> List[Dict[str, Any]]:
        """
        Fetch Epic work items using WIQL query
        """
        url = f"{self.base_url}/wit/wiql?api-version={self.api_version}"
        
        # WIQL query to fetch Epics with custom filter criteria
        # This is a sample query that can be modified based on specific requirements
        wiql = {
            "query": """
                SELECT [System.Id]
                FROM WorkItems
                WHERE [System.WorkItemType] = 'Epic'
                AND [System.State] <> 'Closed'
                ORDER BY [System.CreatedDate] DESC
            """
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=wiql)
            response.raise_for_status()
            
            query_result = response.json()
            work_item_ids = [item["id"] for item in query_result.get("workItems", [])]
            
            if not work_item_ids:
                logger.info("No Epics found matching the criteria")
                return []
            
            # Fetch detailed work item information for all retrieved epic IDs
            return self.get_work_items_details(work_item_ids)
            
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching Epics: {str(e)}")
            raise
    
    def get_work_items_details(self, work_item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for multiple work items
        """
        # API allows retrieval of multiple work items in batches
        batch_size = 200
        all_items = []
        
        for i in range(0, len(work_item_ids), batch_size):
            batch = work_item_ids[i:i + batch_size]
            ids_string = ','.join(map(str, batch))
            
            url = f"{self.base_url}/wit/workitems?ids={ids_string}&$expand=all&api-version={self.api_version}"
            
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                all_items.extend(result.get("value", []))
                
            except requests.exceptions.RequestException as e:
                logger.exception(f"Error fetching work item details: {str(e)}")
                raise
        
        return all_items
    
    def get_work_item_relations(self, work_item_id: int) -> Dict[str, Any]:
        """
        Fetch a single work item with its relations
        """
        url = f"{self.base_url}/wit/workitems/{work_item_id}?$expand=relations&api-version={self.api_version}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching work item {work_item_id}: {str(e)}")
            raise
    
    def traverse_hierarchy(self, epics: List[Dict[str, Any]], custom_fields: List[str]) -> Dict[str, Any]:
        """
        Traverse work item hierarchy and roll up data
        """
        result = {
            "epics": [],
            "features": [],
            "stories": [],
            "leaf_items": []
        }
        
        for epic in epics:
            epic_data = self._extract_work_item_data(epic, "Epic", custom_fields)
            epic_data["children"] = []
            
            # Get child work items (Features under this Epic)
            child_relations = [r for r in epic.get("relations", []) 
                              if r.get("attributes", {}).get("name") == "Child"]
            
            feature_ids = [int(r["url"].split("/")[-1]) for r in child_relations]
            features = self.get_work_items_details(feature_ids) if feature_ids else []
            
            total_estimated_hours = 0
            total_completed_work = 0
            
            for feature in features:
                feature_data = self._extract_work_item_data(feature, "Feature", custom_fields)
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
                    story_data = self._extract_work_item_data(story, "User Story", custom_fields)
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
                        task_data = self._extract_work_item_data(task, "Task", custom_fields)
                        
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
        
        # Add custom fields if present
        for field in custom_fields:
            qualified_field = f"Custom.{field}" if not field.startswith("System.") and not field.startswith("Microsoft.") else field
            data[field] = self._get_field_value(work_item, qualified_field, "N/A")
        
        return data
    
    def _get_field_value(self, work_item: Dict[str, Any], field_name: str, default_value: Any = None) -> Any:
        """
        Safely extract a field value from a work item
        """
        fields = work_item.get("fields", {})
        return fields.get(field_name, default_value)
    
    def _extract_person_name(self, person_field: Any) -> str:
        """
        Extract person name from Azure DevOps person object
        """
        if not person_field:
            return "Unassigned"
            
        if isinstance(person_field, dict):
            return person_field.get("displayName", "Unknown")
        
        return str(person_field)
