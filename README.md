
# Azure DevOps Work Item Report API

A Flask-based API service for generating comprehensive Excel reports from Azure DevOps work items with advanced filtering and hierarchy support.

## Features

### General Report Generation (`/ado-report/generate-report`)
- Fetch and process Epic work items and their complete hierarchy
- Support for custom field filtering
- **Enhanced date filtering with selective work item type filtering**
- Flexible hierarchy support (handles non-standard parent-child relationships)
- Automatic hour aggregation from child to parent work items
- Multi-sheet Excel output (Epic, Feature, User Story, Task/Bug/QA sheets)
- Parent information tracking (Parent Type, Parent ID, Parent Title)
- Date range filtering with start and end dates
- Azure Blob Storage integration

### User-Specific Reports (`/ado-report/user-report`)
- Generate reports for work items assigned to specific users
- CAPEX percentage calculation based on configurable CAPEX fields
- Work item classification as CAPEX or non-CAPEX
- Complete parent information and hour aggregation
- **Enhanced date filtering with selective work item type filtering**
- Summary totals with CAPEX breakdown
- Same multi-sheet Excel format as general reports

## API Endpoints

### 1. Generate Report
**POST** `/ado-report/generate-report`

Generates a comprehensive report of Epic work items and their complete hierarchy.

**Request Body:**
```json
{
  "AZURE_PAT": "your_azure_devops_pat",
  "ORGANIZATION": "your_organization",
  "PROJECT": "your_project",
  "CUSTOM_FIELDS": [
    {
      "key": "Custom.BusinessValue",
      "value": "High"
    }
  ],
  "filter_date": "2024-01-01",
  "filter_startdate": "2024-01-01",
  "filter_enddate": "2024-12-31",
  "filter_workitemtype": ["Epic", "Task"],
  "output_file_name": "my_report",
  "SHEET_COUNT": 4,
  "storage_account_name": "your_storage_account",
  "container_name": "your_container",
  "storage_account_sas": "your_sas_token"
}
```

### 2. User Report
**POST** `/ado-report/user-report`

Generates a user-specific report with CAPEX analysis.

**Request Body:**
```json
{
  "AZURE_PAT": "your_azure_devops_pat",
  "ORGANIZATION": "your_organization",
  "PROJECT": "your_project",
  "ASSIGNEDTO": "user@example.com",
  "CUSTOM_FIELDS": [
    {
      "key": "Custom.Team",
      "value": "Development"
    }
  ],
  "CAPEX_FIELDS": [
    {
      "key": "Custom.Business_Value",
      "value": "High"
    },
    {
      "key": "Custom.Targeted_environment",
      "value": "Prod"
    }
  ],
  "filter_date": "2024-01-01",
  "filter_startdate": "2024-01-01",
  "filter_enddate": "2024-12-31",
  "filter_workitemtype": ["Epic", "User Story", "Task"],
  "output_file_name": "user_report",
  "SHEET_COUNT": 4,
  "storage_account_name": "your_storage_account",
  "container_name": "your_container",
  "storage_account_sas": "your_sas_token"
}
```

## Enhanced Date Filtering

### New Parameters

- **`filter_startdate`** (string, optional): Start date in YYYY-MM-DD format. Filters work items created on or after this date.
- **`filter_enddate`** (string, optional): End date in YYYY-MM-DD format. Filters work items created on or before this date.
- **`filter_workitemtype`** (array, optional): List of work item types to apply date filtering to. Valid types: `["Epic", "Feature", "User Story", "Task", "Bug", "QA Validation Task"]`
- **`filter_date`** (string, optional): **DEPRECATED** - Use `filter_startdate` instead. Maintained for backward compatibility.

### Date Filtering Examples

#### Filter all work items created after a specific date:
```json
{
  "filter_startdate": "2024-01-01"
}
```

#### Filter work items within a date range:
```json
{
  "filter_startdate": "2024-01-01",
  "filter_enddate": "2024-12-31"
}
```

#### Filter only specific work item types by date:
```json
{
  "filter_startdate": "2024-01-01",
  "filter_workitemtype": ["Epic", "Task"]
}
```

#### Filter all work items (no type restriction):
```json
{
  "filter_startdate": "2024-01-01"
}
```

### How Date Filtering Works

1. **No `filter_workitemtype` specified**: Date filter applies to ALL work item types
2. **`filter_workitemtype` specified**: Date filter applies ONLY to the specified work item types
3. **Backward compatibility**: `filter_date` parameter still works and is treated as `filter_startdate`

## Excel Report Structure

### General Reports
Each sheet includes:
- **ID**: Work item ID
- **Title**: Work item title
- **State**: Current state
- **Parent Type**: Type of parent work item
- **Parent ID**: ID of parent work item
- **Parent Title**: Title of parent work item
- **Estimated Hours**: Original estimate (aggregated for parent items)
- **Completed Work**: Work completed (aggregated for parent items)
- **Remaining Work**: Work remaining (aggregated for parent items)
- **% Complete**: Percentage completion
- **Assigned To**: Assigned user
- **Custom Fields**: Any specified custom fields

### User Reports
User reports include all general report columns plus:
- **Work Item Type**: CAPEX or non-CAPEX classification
- **Summary Row**: Total hours and CAPEX percentage

## Key Features

### Flexible Hierarchy Support
The API handles non-standard Azure DevOps hierarchies where work items may not follow the typical Epic → Feature → User Story → Task pattern. All work items that are direct or indirect descendants of filtered Epics are included.

### Hour Aggregation
Parent work items (Epics, Features, User Stories) automatically aggregate hours from all their descendant work items, providing accurate rolled-up metrics.

### CAPEX Analysis
For user reports, work items are classified as CAPEX or non-CAPEX based on whether they belong to Epics that match the specified CAPEX field criteria. A percentage calculation shows what portion of the user's work corresponds to CAPEX projects.

### Custom Field Support
Both endpoints support filtering by custom fields. Custom fields can be specified with or without the "Custom." prefix.

## Docker Support

The application includes Docker support for easy deployment:

```bash
docker build -t azure-devops-reporter .
docker run -p 5000:5000 azure-devops-reporter
```

## API Documentation

Interactive API documentation is available at `/ado-report/docs` when the service is running.

## Health Check

Health check endpoint available at `/health` and `/ado-report/health`.

## Environment Variables

- `PORT`: Service port (default: 5000)

## Requirements

See `requirements.txt` for Python dependencies.
