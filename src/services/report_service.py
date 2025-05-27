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

EPIC_COLUMNS_USER_REPORT = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
    {'field': 'capex_classification', 'header': 'Work Item Type', 'width': 15},
]

FEATURE_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'parent_type', 'header': 'Parent Type', 'width': 15},
    {'field': 'parent_id', 'header': 'Parent ID', 'width': 15},
    {'field': 'parent_title', 'header': 'Parent Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
]

FEATURE_COLUMNS_USER_REPORT = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'parent_type', 'header': 'Parent Type', 'width': 15},
    {'field': 'parent_id', 'header': 'Parent ID', 'width': 15},
    {'field': 'parent_title', 'header': 'Parent Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
    {'field': 'capex_classification', 'header': 'Work Item Type', 'width': 15},
]

STORY_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'parent_type', 'header': 'Parent Type', 'width': 15},
    {'field': 'parent_id', 'header': 'Parent ID', 'width': 15},
    {'field': 'parent_title', 'header': 'Parent Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
]

STORY_COLUMNS_USER_REPORT = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'parent_type', 'header': 'Parent Type', 'width': 15},
    {'field': 'parent_id', 'header': 'Parent ID', 'width': 15},
    {'field': 'parent_title', 'header': 'Parent Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
    {'field': 'capex_classification', 'header': 'Work Item Type', 'width': 15},
]

TASK_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'work_item_type', 'header': 'Type', 'width': 15},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'parent_type', 'header': 'Parent Type', 'width': 15},
    {'field': 'parent_id', 'header': 'Parent ID', 'width': 15},
    {'field': 'parent_title', 'header': 'Parent Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
]

TASK_COLUMNS_USER_REPORT = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'work_item_type', 'header': 'Type', 'width': 15},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'parent_type', 'header': 'Parent Type', 'width': 15},
    {'field': 'parent_id', 'header': 'Parent ID', 'width': 15},
    {'field': 'parent_title', 'header': 'Parent Title', 'width': 40},
    {'field': 'estimated_hours', 'header': 'Estimated Hours', 'width': 15},
    {'field': 'completed_work', 'header': 'Completed Work', 'width': 15},
    {'field': 'remaining_work', 'header': 'Remaining Work', 'width': 15},
    {'field': 'percent_complete', 'header': '% Complete', 'width': 15},
    {'field': 'assigned_to', 'header': 'Assigned To', 'width': 20},
    {'field': 'capex_classification', 'header': 'Work Item Type', 'width': 15},
]

# ================================================================================
# END COLUMN CONFIGURATION SECTION
# ================================================================================

class ReportService:
    def __init__(self):
        """Initialize the report service"""
        pass
    
    def build_excel_workbook(self, data: Dict[str, Any], output_path: str, sheet_count: int = 4, 
                              custom_fields: List[Dict[str, str]] = None, is_user_report: bool = False,
                              capex_percentage: float = 0.0) -> None:
        """
        Build Excel workbook with work item data
        
        Args:
            data: Hierarchical data structure with work items
            output_path: Path where the Excel file will be saved
            sheet_count: Number of sheets to include (1-4)
            custom_fields: List of custom fields to include in the report
            is_user_report: Whether this is a user-specific report
            capex_percentage: CAPEX percentage for user reports
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
                self._build_epic_sheet(workbook, data["epics"], header_format, cell_format, percent_format, custom_field_names, is_user_report, capex_percentage)
            
            if sheet_count >= 2:
                self._build_feature_sheet(workbook, data["features"], header_format, cell_format, percent_format, is_user_report, capex_percentage)
            
            if sheet_count >= 3:
                self._build_story_sheet(workbook, data["stories"], header_format, cell_format, percent_format, is_user_report, capex_percentage)
            
            if sheet_count >= 4:
                self._build_task_sheet(workbook, data["leaf_items"], header_format, cell_format, percent_format, is_user_report, capex_percentage)
            
            # Close the workbook to save it
            workbook.close()
            logger.info(f"Excel report saved to {output_path}")
            
        except Exception as e:
            logger.exception(f"Error building Excel workbook: {str(e)}")
            raise
    
    def _filter_work_items_by_type(self, items: List[Dict[str, Any]], allowed_types: List[str]) -> List[Dict[str, Any]]:
        """Filter work items by their work item type"""
        logger.info(f"Filtering work items by types: {allowed_types}")
        logger.info(f"Input items count: {len(items)}")
        
        # Debug: Log all work item types found
        if items:
            found_types = set()
            for item in items:
                work_item_type = item.get("type", "").strip()
                if work_item_type:
                    found_types.add(work_item_type)
            logger.info(f"Work item types found in data: {list(found_types)}")
        
        # Filter items - use 'type' field which is mapped from System.WorkItemType
        filtered_items = []
        for item in items:
            work_item_type = item.get("type", "").strip()
            logger.debug(f"Item {item.get('id')}: type='{work_item_type}'")
            
            # Check if the work item type matches any of the allowed types (case-insensitive)
            if any(work_item_type.lower() == allowed_type.lower() for allowed_type in allowed_types):
                filtered_items.append(item)
                logger.debug(f"Item {item.get('id')} included (type matches)")
            else:
                logger.debug(f"Item {item.get('id')} excluded (type '{work_item_type}' not in {allowed_types})")
        
        logger.info(f"Filtered items count: {len(filtered_items)}")
        return filtered_items
    
    def _build_sheet_with_config(self, workbook, worksheet_name: str, items: List[Dict[str, Any]], 
                                 columns_config: List[Dict], header_format, cell_format, percent_format,
                                 custom_field_names: List[str] = None, is_user_report: bool = False,
                                 capex_percentage: float = 0.0) -> None:
        """
        Generic method to build a worksheet using column configuration
        """
        logger.info(f"Building {worksheet_name} sheet with {len(items)} items")
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
                    # Value should already be between 0 and 1
                    if isinstance(value, (int, float)):
                        worksheet.write(row, col_idx, value, percent_format)
                    else:
                        worksheet.write(row, col_idx, 0, percent_format)
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
        
        # Add summary row for user reports
        if is_user_report and items:
            self._add_summary_row(worksheet, items, len(headers), cell_format, percent_format, capex_percentage)
    
    def _add_summary_row(self, worksheet, items: List[Dict[str, Any]], num_cols: int, 
                        cell_format, percent_format, capex_percentage: float) -> None:
        """Add a summary row with totals and CAPEX percentage"""
        if not items:
            return
            
        summary_row = len(items) + 2  # Skip one row after data
        
        # Calculate totals
        total_estimated = sum(item.get('estimated_hours', 0) for item in items)
        total_completed = sum(item.get('completed_work', 0) for item in items)
        total_remaining = sum(item.get('remaining_work', 0) for item in items)
        total_percent = total_completed / total_estimated if total_estimated > 0 else 0
        
        # Write summary labels and values
        worksheet.write(summary_row, 0, "TOTAL", cell_format)
        worksheet.write(summary_row, 1, f"Estimated: {total_estimated}h, Completed: {total_completed}h, Remaining: {total_remaining}h", cell_format)
        worksheet.write(summary_row, 2, total_percent, percent_format)
        
        # Write CAPEX percentage if applicable
        if capex_percentage > 0:
            worksheet.write(summary_row + 1, 0, "CAPEX %", cell_format)
            worksheet.write(summary_row + 1, 1, f"{capex_percentage:.2%} of total work corresponds to CAPEX fields", cell_format)
    
    def _build_epic_sheet(self, workbook, epics: List[Dict[str, Any]], header_format, cell_format, percent_format,
                          custom_field_names: List[str], is_user_report: bool = False, capex_percentage: float = 0.0) -> None:
        """Build the Epic worksheet using configuration"""
        logger.info(f"Building Epic sheet with {len(epics)} total epics before filtering")
        
        # Filter to only Epic work items
        epic_items = self._filter_work_items_by_type(epics, ["Epic"])
        logger.info(f"Epic sheet will contain {len(epic_items)} Epic work items")
        
        # Choose appropriate column configuration
        columns_config = EPIC_COLUMNS_USER_REPORT if is_user_report else EPIC_COLUMNS
        
        self._build_sheet_with_config(workbook, "Epics", epic_items, columns_config, 
                                      header_format, cell_format, percent_format, custom_field_names, is_user_report, capex_percentage)

    def _build_feature_sheet(self, workbook, features: List[Dict[str, Any]], header_format, cell_format, percent_format,
                            is_user_report: bool = False, capex_percentage: float = 0.0) -> None:
        """Build the Feature worksheet using configuration"""
        logger.info(f"Building Feature sheet with {len(features)} total features before filtering")
        
        # Filter to only Feature work items
        feature_items = self._filter_work_items_by_type(features, ["Feature"])
        logger.info(f"Feature sheet will contain {len(feature_items)} Feature work items")
        
        # Choose appropriate column configuration
        columns_config = FEATURE_COLUMNS_USER_REPORT if is_user_report else FEATURE_COLUMNS
        
        self._build_sheet_with_config(workbook, "Features", feature_items, columns_config, 
                                      header_format, cell_format, percent_format, None, is_user_report, capex_percentage)
    
    def _build_story_sheet(self, workbook, stories: List[Dict[str, Any]], header_format, cell_format, percent_format,
                          is_user_report: bool = False, capex_percentage: float = 0.0) -> None:
        """Build the User Story worksheet using configuration"""
        logger.info(f"Building Story sheet with {len(stories)} total stories before filtering")
        
        # Filter to only User Story work items
        story_items = self._filter_work_items_by_type(stories, ["User Story"])
        logger.info(f"Story sheet will contain {len(story_items)} User Story work items")
        
        # Choose appropriate column configuration
        columns_config = STORY_COLUMNS_USER_REPORT if is_user_report else STORY_COLUMNS
        
        self._build_sheet_with_config(workbook, "User Stories", story_items, columns_config, 
                                      header_format, cell_format, percent_format, None, is_user_report, capex_percentage)
    
    def _build_task_sheet(self, workbook, tasks: List[Dict[str, Any]], header_format, cell_format, percent_format,
                         is_user_report: bool = False, capex_percentage: float = 0.0) -> None:
        """Build the Task worksheet using configuration"""
        logger.info(f"Building Task sheet with {len(tasks)} total tasks before filtering")
        
        # Filter to Task, Bug, and QA Validation Task work items
        task_items = self._filter_work_items_by_type(tasks, ["Task", "Bug", "QA Validation Task"])
        logger.info(f"Task sheet will contain {len(task_items)} Task/Bug/QA work items")
        
        # Choose appropriate column configuration
        columns_config = TASK_COLUMNS_USER_REPORT if is_user_report else TASK_COLUMNS
        
        self._build_sheet_with_config(workbook, "Tasks", task_items, columns_config, 
                                      header_format, cell_format, percent_format, None, is_user_report, capex_percentage)
