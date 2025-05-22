
import logging
import xlsxwriter
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self):
        """Initialize the report service"""
        pass
    
    def build_excel_workbook(self, data: Dict[str, Any], output_path: str, sheet_count: int = 4, 
                              custom_fields: List[Dict[str, str]] = None) -> None:
        """
        Build Excel workbook with work item data
        
        Args:
            data: Hierarchical data structure with work items
            output_path: Path where the Excel file will be saved
            sheet_count: Number of sheets to include (1-4)
            custom_fields: List of custom fields to include in the report
        """
        try:
            # Create a workbook and add worksheets
            workbook = xlsxwriter.Workbook(output_path)
            
            # Define cell formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D0D0D0',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'border': 1
            })
            
            # Extract custom field names from filters
            custom_field_names = []
            if custom_fields:
                for field in custom_fields:
                    if "key" in field:
                        field_name = field["key"]
                        # Strip Custom. prefix if present
                        if field_name.startswith('Custom.'):
                            field_name = field_name[7:]  # Remove 'Custom.' prefix
                        custom_field_names.append(field_name)
            
            # Build sheets based on the requested count
            if sheet_count >= 1:
                self._build_epic_sheet(workbook, data["epics"], header_format, cell_format, custom_field_names)
            
            if sheet_count >= 2:
                self._build_feature_sheet(workbook, data["features"], header_format, cell_format)
            
            if sheet_count >= 3:
                self._build_story_sheet(workbook, data["stories"], header_format, cell_format)
            
            if sheet_count >= 4:
                self._build_task_sheet(workbook, data["leaf_items"], header_format, cell_format)
            
            # Close the workbook to save it
            workbook.close()
            logger.info(f"Excel report saved to {output_path}")
            
        except Exception as e:
            logger.exception(f"Error building Excel workbook: {str(e)}")
            raise
    
    def _build_epic_sheet(self, workbook, epics: List[Dict[str, Any]], header_format, cell_format,
                          custom_field_names: List[str]) -> None:
        """
        Build the Epic worksheet
        
        Args:
            workbook: The Excel workbook
            epics: List of Epic work items
            header_format: Format for header cells
            cell_format: Format for data cells
            custom_field_names: List of custom field names to include
        """
        worksheet = workbook.add_worksheet("Epics")
        
        # Set column widths
        worksheet.set_column('A:A', 10)  # ID
        worksheet.set_column('B:B', 40)  # Title
        worksheet.set_column('C:C', 15)  # State
        worksheet.set_column('D:D', 15)  # Estimated Hours
        worksheet.set_column('E:E', 15)  # Completed Work
        worksheet.set_column('F:F', 15)  # Remaining Work
        worksheet.set_column('G:G', 15)  # % Complete
        worksheet.set_column('H:H', 20)  # Assigned To
        
        # Base headers
        headers = [
            "ID", "Title", "State", "Estimated Hours", 
            "Completed Work", "Remaining Work", "% Complete", "Assigned To"
        ]
        
        # Add custom field headers
        for field_name in custom_field_names:
            headers.append(field_name)
            
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data rows
        for row, epic in enumerate(epics, start=1):
            worksheet.write(row, 0, epic["id"], cell_format)
            worksheet.write(row, 1, epic["title"], cell_format)
            worksheet.write(row, 2, epic["state"], cell_format)
            worksheet.write(row, 3, epic["estimated_hours"], cell_format)
            worksheet.write(row, 4, epic["completed_work"], cell_format)
            worksheet.write(row, 5, epic["remaining_work"], cell_format)
            worksheet.write(row, 6, epic["percent_complete"], cell_format)
            worksheet.write(row, 7, epic["assigned_to"], cell_format)
            
            # Write custom field values
            for col, field_name in enumerate(custom_field_names, start=8):
                # Try to get the value from the item directly
                value = epic.get(field_name, "")
                
                # If not found and original_fields exists, try there with both with and without Custom. prefix
                if not value and "original_fields" in epic:
                    value = epic["original_fields"].get(f"Custom.{field_name}", 
                                                       epic["original_fields"].get(field_name, ""))
                
                worksheet.write(row, col, value, cell_format)

    def _build_feature_sheet(self, workbook, features: List[Dict[str, Any]], header_format, cell_format) -> None:
        """
        Build the Feature worksheet
        
        Args:
            workbook: The Excel workbook
            features: List of Feature work items
            header_format: Format for header cells
            cell_format: Format for data cells
        """
        worksheet = workbook.add_worksheet("Features")
        
        # Set column widths
        worksheet.set_column('A:A', 10)  # ID
        worksheet.set_column('B:B', 40)  # Title
        worksheet.set_column('C:C', 15)  # State
        worksheet.set_column('D:D', 15)  # Epic ID
        worksheet.set_column('E:E', 40)  # Epic Title
        worksheet.set_column('F:F', 15)  # Estimated Hours
        worksheet.set_column('G:G', 15)  # Completed Work
        worksheet.set_column('H:H', 15)  # Remaining Work
        worksheet.set_column('I:I', 15)  # % Complete
        worksheet.set_column('J:J', 20)  # Assigned To
        
        # Write headers
        headers = [
            "ID", "Title", "State", "Epic ID", "Epic Title",
            "Estimated Hours", "Completed Work", "Remaining Work", 
            "% Complete", "Assigned To"
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data rows
        for row, feature in enumerate(features, start=1):
            worksheet.write(row, 0, feature["id"], cell_format)
            worksheet.write(row, 1, feature["title"], cell_format)
            worksheet.write(row, 2, feature["state"], cell_format)
            worksheet.write(row, 3, feature.get("epic_id", ""), cell_format)
            worksheet.write(row, 4, feature.get("epic_title", ""), cell_format)
            worksheet.write(row, 5, feature["estimated_hours"], cell_format)
            worksheet.write(row, 6, feature["completed_work"], cell_format)
            worksheet.write(row, 7, feature["remaining_work"], cell_format)
            worksheet.write(row, 8, feature["percent_complete"], cell_format)
            worksheet.write(row, 9, feature["assigned_to"], cell_format)
    
    def _build_story_sheet(self, workbook, stories: List[Dict[str, Any]], header_format, cell_format) -> None:
        """
        Build the User Story worksheet
        
        Args:
            workbook: The Excel workbook
            stories: List of User Story work items
            header_format: Format for header cells
            cell_format: Format for data cells
        """
        worksheet = workbook.add_worksheet("User Stories")
        
        # Set column widths
        worksheet.set_column('A:A', 10)  # ID
        worksheet.set_column('B:B', 40)  # Title
        worksheet.set_column('C:C', 15)  # State
        worksheet.set_column('D:D', 15)  # Feature ID
        worksheet.set_column('E:E', 40)  # Feature Title
        worksheet.set_column('F:F', 15)  # Estimated Hours
        worksheet.set_column('G:G', 15)  # Completed Work
        worksheet.set_column('H:H', 15)  # Remaining Work
        worksheet.set_column('I:I', 15)  # % Complete
        worksheet.set_column('J:J', 20)  # Assigned To
        
        # Write headers
        headers = [
            "ID", "Title", "State", "Feature ID", "Feature Title",
            "Estimated Hours", "Completed Work", "Remaining Work", 
            "% Complete", "Assigned To"
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data rows
        for row, story in enumerate(stories, start=1):
            worksheet.write(row, 0, story["id"], cell_format)
            worksheet.write(row, 1, story["title"], cell_format)
            worksheet.write(row, 2, story["state"], cell_format)
            worksheet.write(row, 3, story.get("feature_id", ""), cell_format)
            worksheet.write(row, 4, story.get("feature_title", ""), cell_format)
            worksheet.write(row, 5, story["estimated_hours"], cell_format)
            worksheet.write(row, 6, story["completed_work"], cell_format)
            worksheet.write(row, 7, story["remaining_work"], cell_format)
            worksheet.write(row, 8, story["percent_complete"], cell_format)
            worksheet.write(row, 9, story["assigned_to"], cell_format)
    
    def _build_task_sheet(self, workbook, tasks: List[Dict[str, Any]], header_format, cell_format) -> None:
        """
        Build the Task worksheet
        
        Args:
            workbook: The Excel workbook
            tasks: List of Task work items
            header_format: Format for header cells
            cell_format: Format for data cells
        """
        worksheet = workbook.add_worksheet("Tasks")
        
        # Set column widths
        worksheet.set_column('A:A', 10)  # ID
        worksheet.set_column('B:B', 40)  # Title
        worksheet.set_column('C:C', 15)  # State
        worksheet.set_column('D:D', 15)  # Story ID
        worksheet.set_column('E:E', 40)  # Story Title
        worksheet.set_column('F:F', 15)  # Estimated Hours
        worksheet.set_column('G:G', 15)  # Completed Work
        worksheet.set_column('H:H', 15)  # Remaining Work
        worksheet.set_column('I:I', 15)  # % Complete
        worksheet.set_column('J:J', 20)  # Assigned To
        
        # Write headers
        headers = [
            "ID", "Title", "State", "Story ID", "Story Title",
            "Estimated Hours", "Completed Work", "Remaining Work", 
            "% Complete", "Assigned To"
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data rows
        for row, task in enumerate(tasks, start=1):
            worksheet.write(row, 0, task["id"], cell_format)
            worksheet.write(row, 1, task["title"], cell_format)
            worksheet.write(row, 2, task["state"], cell_format)
            worksheet.write(row, 3, task.get("story_id", ""), cell_format)
            worksheet.write(row, 4, task.get("story_title", ""), cell_format)
            worksheet.write(row, 5, task["estimated_hours"], cell_format)
            worksheet.write(row, 6, task["completed_work"], cell_format)
            worksheet.write(row, 7, task["remaining_work"], cell_format)
            worksheet.write(row, 8, task["percent_complete"], cell_format)
            worksheet.write(row, 9, task["assigned_to"], cell_format)
