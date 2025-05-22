
import xlsxwriter
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self):
        """
        Initialize the report service with base column definitions.
        
        Note: These column definitions can be easily modified to change the order or add/remove columns.
        Each column is defined as a dictionary with the following keys:
        - header: The display name of the column
        - field: The field name in the data structure
        - width: The width of the column in the Excel sheet
        """
        # Define column headers and mappings for each report level
        # CUSTOMIZATION POINT: Modify these lists to change column order or add/remove standard columns
        self.epic_columns = [
            {"header": "ID", "field": "id", "width": 10},
            {"header": "Title", "field": "title", "width": 40},
            {"header": "State", "field": "state", "width": 15},
            {"header": "Assigned To", "field": "assigned_to", "width": 20},
            {"header": "Estimated Hours", "field": "estimated_hours", "width": 15},
            {"header": "Completed Work", "field": "completed_work", "width": 15},
            {"header": "% Complete", "field": "percent_complete", "width": 15},
            {"header": "Created Date", "field": "created_date", "width": 20}
            # Custom fields will be dynamically added to these columns
        ]
        
        # ... keep existing code (other column definitions)
        self.feature_columns = [
            {"header": "Epic ID", "field": "epic_id", "width": 10},
            {"header": "Epic", "field": "epic_title", "width": 30},
            {"header": "Feature ID", "field": "id", "width": 10},
            {"header": "Feature Title", "field": "title", "width": 40},
            {"header": "State", "field": "state", "width": 15},
            {"header": "Assigned To", "field": "assigned_to", "width": 20},
            {"header": "Estimated Hours", "field": "estimated_hours", "width": 15},
            {"header": "Completed Work", "field": "completed_work", "width": 15},
            {"header": "% Complete", "field": "percent_complete", "width": 15}
            # Custom fields will be dynamically added to these columns
        ]
        
        self.story_columns = [
            {"header": "Feature ID", "field": "feature_id", "width": 10},
            {"header": "Feature", "field": "feature_title", "width": 30},
            {"header": "Story ID", "field": "id", "width": 10},
            {"header": "Story Title", "field": "title", "width": 40},
            {"header": "State", "field": "state", "width": 15},
            {"header": "Assigned To", "field": "assigned_to", "width": 20},
            {"header": "Estimated Hours", "field": "estimated_hours", "width": 15},
            {"header": "Completed Work", "field": "completed_work", "width": 15},
            {"header": "% Complete", "field": "percent_complete", "width": 15}
            # Custom fields will be dynamically added to these columns
        ]
        
        self.task_columns = [
            {"header": "Story ID", "field": "story_id", "width": 10},
            {"header": "Story", "field": "story_title", "width": 30},
            {"header": "Task ID", "field": "id", "width": 10},
            {"header": "Task Title", "field": "title", "width": 40},
            {"header": "Type", "field": "type", "width": 15},
            {"header": "State", "field": "state", "width": 15},
            {"header": "Assigned To", "field": "assigned_to", "width": 20},
            {"header": "Estimated Hours", "field": "estimated_hours", "width": 15},
            {"header": "Completed Work", "field": "completed_work", "width": 15},
            {"header": "Remaining Work", "field": "remaining_work", "width": 15}
            # Custom fields will be dynamically added to these columns
        ]
    
    def _add_custom_field_columns(self, custom_fields: List[str]):
        """
        Add custom field columns to all column definitions
        
        Args:
            custom_fields: List of custom field names to add
        """
        # CUSTOMIZATION POINT: Modify this method to change how custom fields are added or formatted
        if not custom_fields:
            return
            
        logger.info(f"Adding {len(custom_fields)} custom fields to report columns")
        
        for field in custom_fields:
            # Get simple field name (without namespace)
            simple_name = field.split('.')[-1] if '.' in field else field
            field_column = {"header": simple_name, "field": simple_name, "width": 25}
            
            # Add to all column sets
            self.epic_columns.append(field_column)
            self.feature_columns.append(field_column)
            self.story_columns.append(field_column)
            self.task_columns.append(field_column)
            
            logger.debug(f"Added custom field column: {simple_name}")
    
    def build_excel_workbook(self, 
                           data: Dict[str, Any], 
                           output_path: str, 
                           sheet_count: int = 4,
                           custom_fields: List[Any] = None) -> None:
        """
        Build Excel workbook with up to 4 sheets based on the sheet_count parameter
        
        Args:
            data: The hierarchical work item data
            output_path: Path where the Excel file will be saved
            sheet_count: Number of sheets to include (1-4)
            custom_fields: List of custom fields to include in the report
        """
        # Extract just the field names from custom_fields if it's a list of dicts
        custom_field_names = []
        if custom_fields:
            logger.debug(f"Processing custom fields: {custom_fields}")
            for field_item in custom_fields:
                if isinstance(field_item, dict) and 'key' in field_item:
                    field_name = field_item['key']
                    # Get simple field name (without namespace)
                    simple_name = field_name.split('.')[-1] if '.' in field_name else field_name
                    custom_field_names.append(simple_name)
                elif isinstance(field_item, str):  # For backward compatibility
                    simple_name = field_item.split('.')[-1] if '.' in field_item else field_item
                    custom_field_names.append(simple_name)
        
        # Add custom field columns to all column definitions
        self._add_custom_field_columns(custom_field_names)
            
        try:
            # Create a new Excel workbook and add worksheets based on sheet_count
            logger.info(f"Creating Excel workbook with {sheet_count} sheets")
            workbook = xlsxwriter.Workbook(output_path)
            
            # Define styles
            header_style = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',  # Dark blue
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            row_style = workbook.add_format({
                'border': 1,
                'valign': 'vcenter'
            })
            
            percent_style = workbook.add_format({
                'border': 1,
                'num_format': '0.00%',
                'valign': 'vcenter'
            })
            
            date_style = workbook.add_format({
                'border': 1,
                'num_format': 'yyyy-mm-dd',
                'valign': 'vcenter'
            })
            
            # Sheet 1: Epic Summary (always included)
            if sheet_count >= 1:
                epic_sheet = workbook.add_worksheet('Epic Summary')
                self._write_sheet(workbook, epic_sheet, self.epic_columns, header_style, 
                                row_style, percent_style, date_style)
                
                # Write Epic data
                row = 1
                for epic in data["epics"]:
                    self._write_epic_row(epic_sheet, row, epic, row_style, percent_style, date_style)
                    row += 1
            
            # ... keep existing code (other sheet writing code)
            # Sheet 2: Feature Breakdown
            if sheet_count >= 2:
                feature_sheet = workbook.add_worksheet('Feature Breakdown')
                self._write_sheet(workbook, feature_sheet, self.feature_columns, header_style, 
                                row_style, percent_style, date_style)
                
                # Write Feature data
                row = 1
                for epic in data["epics"]:
                    for feature in epic.get("children", []):
                        feature_data = {
                            "epic_id": epic["id"],
                            "epic_title": epic["title"],
                            **feature
                        }
                        self._write_feature_row(feature_sheet, row, feature_data, row_style, percent_style)
                        row += 1
            
            # Sheet 3: Story Breakdown
            if sheet_count >= 3:
                story_sheet = workbook.add_worksheet('Story Breakdown')
                self._write_sheet(workbook, story_sheet, self.story_columns, header_style, 
                               row_style, percent_style, date_style)
                
                # Write Story data
                row = 1
                for epic in data["epics"]:
                    for feature in epic.get("children", []):
                        for story in feature.get("children", []):
                            story_data = {
                                "feature_id": feature["id"],
                                "feature_title": feature["title"],
                                **story
                            }
                            self._write_story_row(story_sheet, row, story_data, row_style, percent_style)
                            row += 1
            
            # Sheet 4: Task Detail
            if sheet_count >= 4:
                task_sheet = workbook.add_worksheet('Task Detail')
                self._write_sheet(workbook, task_sheet, self.task_columns, header_style, 
                               row_style, percent_style, date_style)
                
                # Write Task data
                row = 1
                for epic in data["epics"]:
                    for feature in epic.get("children", []):
                        for story in feature.get("children", []):
                            for task in story.get("children", []):
                                task_data = {
                                    "story_id": story["id"],
                                    "story_title": story["title"],
                                    **task
                                }
                                self._write_task_row(task_sheet, row, task_data, row_style)
                                row += 1
            
            # Add a report summary page with metadata
            summary_sheet = workbook.add_worksheet('Report Info')
            summary_sheet.write(0, 0, "Azure DevOps Work Item Report", header_style)
            summary_sheet.write(1, 0, "Generated:", row_style)
            summary_sheet.write(1, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row_style)
            summary_sheet.write(2, 0, "Total Epics:", row_style)
            summary_sheet.write(2, 1, len(data["epics"]), row_style)
            summary_sheet.write(3, 0, "Total Features:", row_style)
            summary_sheet.write(3, 1, len(data["features"]), row_style)
            summary_sheet.write(4, 0, "Total Stories:", row_style)
            summary_sheet.write(4, 1, len(data["stories"]), row_style)
            summary_sheet.write(5, 0, "Total Tasks:", row_style)
            summary_sheet.write(5, 1, len(data["leaf_items"]), row_style)
            
            # Adjust column widths for summary sheet
            summary_sheet.set_column(0, 0, 20)
            summary_sheet.set_column(1, 1, 30)
            
            # Close the workbook
            workbook.close()
            logger.info(f"Excel workbook created at: {output_path}")
            
        except Exception as e:
            logger.exception(f"Error building Excel workbook: {str(e)}")
            raise
    
    # ... keep existing code (writing functions)
    def _write_sheet(self, workbook, sheet, columns, header_style, row_style, percent_style, date_style):
        """
        Write column headers to a sheet and set column widths
        """
        # Write headers
        for col, column in enumerate(columns):
            sheet.write(0, col, column["header"], header_style)
            sheet.set_column(col, col, column["width"])
    
    def _write_epic_row(self, sheet, row, epic, row_style, percent_style, date_style):
        """
        Write an Epic row to the Epic Summary sheet
        """
        col = 0
        sheet.write(row, col, epic["id"], row_style); col += 1
        sheet.write(row, col, epic["title"], row_style); col += 1
        sheet.write(row, col, epic["state"], row_style); col += 1
        sheet.write(row, col, epic["assigned_to"], row_style); col += 1
        sheet.write(row, col, epic["estimated_hours"], row_style); col += 1
        sheet.write(row, col, epic["completed_work"], row_style); col += 1
        
        # Calculate percent complete
        est = epic["estimated_hours"]
        complete = epic["completed_work"]
        percent = complete / est if est > 0 else 0
        sheet.write(row, col, percent, percent_style); col += 1
        
        # Format date properly if available
        if isinstance(epic.get("created_date"), str):
            try:
                # Parse ISO format date
                date_obj = datetime.fromisoformat(epic["created_date"].replace('Z', '+00:00'))
                sheet.write_datetime(row, col, date_obj, date_style)
            except (ValueError, TypeError):
                sheet.write(row, col, epic.get("created_date", ""), row_style)
        else:
            sheet.write(row, col, "", row_style)
        col += 1
        
        # Write custom fields if any
        for field, value in epic.items():
            if field not in ["id", "title", "state", "assigned_to", "estimated_hours", 
                           "completed_work", "created_date", "children", "url", "type",
                           "remaining_work", "percent_complete"]:
                sheet.write(row, col, value, row_style)
                col += 1
    
    def _write_feature_row(self, sheet, row, feature, row_style, percent_style):
        """
        Write a Feature row to the Feature Breakdown sheet
        """
        col = 0
        sheet.write(row, col, feature["epic_id"], row_style); col += 1
        sheet.write(row, col, feature["epic_title"], row_style); col += 1
        sheet.write(row, col, feature["id"], row_style); col += 1
        sheet.write(row, col, feature["title"], row_style); col += 1
        sheet.write(row, col, feature["state"], row_style); col += 1
        sheet.write(row, col, feature["assigned_to"], row_style); col += 1
        sheet.write(row, col, feature["estimated_hours"], row_style); col += 1
        sheet.write(row, col, feature["completed_work"], row_style); col += 1
        
        # Calculate percent complete
        est = feature["estimated_hours"]
        complete = feature["completed_work"]
        percent = complete / est if est > 0 else 0
        sheet.write(row, col, percent, percent_style); col += 1
        
        # Write custom fields if any
        for field, value in feature.items():
            if field not in ["id", "title", "state", "assigned_to", "estimated_hours", 
                           "completed_work", "children", "url", "type", "epic_id",
                           "epic_title", "remaining_work", "percent_complete", "created_date"]:
                sheet.write(row, col, value, row_style)
                col += 1
    
    def _write_story_row(self, sheet, row, story, row_style, percent_style):
        """
        Write a Story row to the Story Breakdown sheet
        """
        col = 0
        sheet.write(row, col, story["feature_id"], row_style); col += 1
        sheet.write(row, col, story["feature_title"], row_style); col += 1
        sheet.write(row, col, story["id"], row_style); col += 1
        sheet.write(row, col, story["title"], row_style); col += 1
        sheet.write(row, col, story["state"], row_style); col += 1
        sheet.write(row, col, story["assigned_to"], row_style); col += 1
        sheet.write(row, col, story["estimated_hours"], row_style); col += 1
        sheet.write(row, col, story["completed_work"], row_style); col += 1
        
        # Calculate percent complete
        est = story["estimated_hours"]
        complete = story["completed_work"]
        percent = complete / est if est > 0 else 0
        sheet.write(row, col, percent, percent_style); col += 1
        
        # Write custom fields if any
        for field, value in story.items():
            if field not in ["id", "title", "state", "assigned_to", "estimated_hours", 
                           "completed_work", "children", "url", "type", "feature_id",
                           "feature_title", "remaining_work", "percent_complete", "created_date"]:
                sheet.write(row, col, value, row_style)
                col += 1
    
    def _write_task_row(self, sheet, row, task, row_style):
        """
        Write a Task row to the Task Detail sheet
        """
        col = 0
        sheet.write(row, col, task["story_id"], row_style); col += 1
        sheet.write(row, col, task["story_title"], row_style); col += 1
        sheet.write(row, col, task["id"], row_style); col += 1
        sheet.write(row, col, task["title"], row_style); col += 1
        sheet.write(row, col, task["type"], row_style); col += 1
        sheet.write(row, col, task["state"], row_style); col += 1
        sheet.write(row, col, task["assigned_to"], row_style); col += 1
        sheet.write(row, col, task["estimated_hours"], row_style); col += 1
        sheet.write(row, col, task["completed_work"], row_style); col += 1
        sheet.write(row, col, task["remaining_work"], row_style); col += 1
        
        # Write custom fields if any
        for field, value in task.items():
            if field not in ["id", "title", "state", "assigned_to", "estimated_hours", 
                           "completed_work", "remaining_work", "url", "type", "story_id", 
                           "story_title", "children", "created_date", "percent_complete"]:
                sheet.write(row, col, value, row_style)
                col += 1
