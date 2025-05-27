
import logging
import xlsxwriter
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ================================================================================
# COLUMN CONFIGURATION SECTION
# ================================================================================
# 
# To modify columns in any sheet, update the configurations below:
# - Add/remove columns by modifying the column definitions
# - Change column order by reordering items in the lists
# - Modify column widths by updating the 'width' values
# - Change headers by updating the 'header' values
# 
# Each column definition contains:
# - 'field': The field name in the work item data
# - 'header': The column header text in Excel
# - 'width': The column width in Excel
# ================================================================================

EPIC_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
]

FEATURE_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'epic_id', 'header': 'Epic ID', 'width': 15},
    {'field': 'epic_title', 'header': 'Epic Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
]

STORY_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'feature_id', 'header': 'Feature ID', 'width': 15},
    {'field': 'feature_title', 'header': 'Feature Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
]

TASK_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'work_item_type', 'header': 'Type', 'width': 15},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'story_id', 'header': 'Story ID', 'width': 15},
    {'field': 'story_title', 'header': 'Story Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
]

# ================================================================================
# END COLUMN CONFIGURATION SECTION
# ================================================================================

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
            
            # Format for percentage values
            percent_format = workbook.add_format({
                'border': 1,
                'num_format': '0.00%'
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
                self._build_epic_sheet(workbook, data["epics"], header_format, cell_format, percent_format, custom_field_names)
            
            if sheet_count >= 2:
                self._build_feature_sheet(workbook, data["features"], header_format, cell_format, percent_format)
            
            if sheet_count >= 3:
                self._build_story_sheet(workbook, data["stories"], header_format, cell_format, percent_format)
            
            if sheet_count >= 4:
                self._build_task_sheet(workbook, data["leaf_items"], header_format, cell_format, percent_format)
            
            # Close the workbook to save it
            workbook.close()
            logger.info(f"Excel report saved to {output_path}")
            
        except Exception as e:
            logger.exception(f"Error building Excel workbook: {str(e)}")
            raise
    
    def _filter_work_items_by_type(self, items: List[Dict[str, Any]], allowed_types: List[str]) -> List[Dict[str, Any]]:
        """Filter work items by their work item type"""
        return [item for item in items if item.get("work_item_type", "").lower() in [t.lower() for t in allowed_types]]
    
    def _build_sheet_with_config(self, workbook, worksheet_name: str, items: List[Dict[str, Any]], 
                                 columns_config: List[Dict], header_format, cell_format, percent_format,
                                 custom_field_names: List[str] = None) -> None:
        """
        Generic method to build a worksheet using column configuration
        
        Args:
            workbook: The Excel workbook
            worksheet_name: Name of the worksheet
            items: List of work items
            columns_config: Column configuration list
            header_format: Format for header cells
            cell_format: Format for data cells
            percent_format: Format for percentage cells
            custom_field_names: List of custom field names to include
        """
        worksheet = workbook.add_worksheet(worksheet_name)
        
        # Set column widths and write headers
        headers = []
        for col_idx, col_config in enumerate(columns_config):
            worksheet.set_column(col_idx, col_idx, col_config['width'])
            headers.append(col_config['header'])
        
        # Add custom field headers if provided
        if custom_field_names:
            for field_name in custom_field_names:
                headers.append(field_name)
                worksheet.set_column(len(headers)-1, len(headers)-1, 20)  # Default width for custom fields
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data rows
        for row, item in enumerate(items, start=1):
            # Write configured columns
            for col_idx, col_config in enumerate(columns_config):
                field_name = col_config['field']
                value = item.get(field_name, "")
                
                # Use percentage format for percent_complete field
                if field_name == 'percent_complete':
                    # Convert to decimal if it's a percentage (divide by 100)
                    if isinstance(value, (int, float)) and value > 1:
                        value = value / 100
                    worksheet.write(row, col_idx, value, percent_format)
                else:
                    worksheet.write(row, col_idx, value, cell_format)
            
            # Write custom field values if provided
            if custom_field_names:
                for col_offset, field_name in enumerate(custom_field_names):
                    col_idx = len(columns_config) + col_offset
                    # Try to get the value from the item directly
                    value = item.get(field_name, "")
                    
                    # If not found and original_fields exists, try there with both with and without Custom. prefix
                    if not value and "original_fields" in item:
                        value = item["original_fields"].get(f"Custom.{field_name}", 
                                                           item["original_fields"].get(field_name, ""))
                    
                    worksheet.write(row, col_idx, value, cell_format)
    
    def _build_epic_sheet(self, workbook, epics: List[Dict[str, Any]], header_format, cell_format, percent_format,
                          custom_field_names: List[str]) -> None:
        """Build the Epic worksheet using configuration"""
        # Filter to only Epic work items
        epic_items = self._filter_work_items_by_type(epics, ["Epic"])
        self._build_sheet_with_config(workbook, "Epics", epic_items, EPIC_COLUMNS, 
                                      header_format, cell_format, percent_format, custom_field_names)

    def _build_feature_sheet(self, workbook, features: List[Dict[str, Any]], header_format, cell_format, percent_format) -> None:
        """Build the Feature worksheet using configuration"""
        # Filter to only Feature work items
        feature_items = self._filter_work_items_by_type(features, ["Feature"])
        self._build_sheet_with_config(workbook, "Features", feature_items, FEATURE_COLUMNS, 
                                      header_format, cell_format, percent_format)
    
    def _build_story_sheet(self, workbook, stories: List[Dict[str, Any]], header_format, cell_format, percent_format) -> None:
        """Build the User Story worksheet using configuration"""
        # Filter to only User Story work items
        story_items = self._filter_work_items_by_type(stories, ["User Story"])
        self._build_sheet_with_config(workbook, "User Stories", story_items, STORY_COLUMNS, 
                                      header_format, cell_format, percent_format)
    
    def _build_task_sheet(self, workbook, tasks: List[Dict[str, Any]], header_format, cell_format, percent_format) -> None:
        """Build the Task worksheet using configuration"""
        # Filter to Task, Bug, and QA Validation Task work items
        task_items = self._filter_work_items_by_type(tasks, ["Task", "Bug", "QA Validation Task"])
        self._build_sheet_with_config(workbook, "Tasks", task_items, TASK_COLUMNS, 
                                      header_format, cell_format, percent_format)
