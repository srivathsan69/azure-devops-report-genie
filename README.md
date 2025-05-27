
# Azure DevOps Work Item Report Generator

A containerized Python API service that connects to Azure DevOps, rolls up hierarchical work item data, and generates Excel reports.

## Features

- Connects to Azure DevOps REST API
- Extracts work item hierarchy with flexible parent-child relationships
- Filters Epics based on custom field values
- Filters work items by creation date and assignment
- Rolls up metrics (estimated hours, completed work)
- Generates Excel report with configurable detail levels
- User-specific reports with CAPEX percentage calculation
- Uploads report to Azure Blob Storage
- Containerized for easy deployment
- Swagger API documentation
- Health probe endpoint

## Project Structure

```
.
├── src/
│   ├── app.py                        # Main Flask API
│   ├── services/
│   │   ├── azure_devops_service.py   # Azure DevOps API integration
│   │   ├── report_service.py         # Excel report generation
│   │   ├── storage_service.py        # Azure Blob Storage integration
│   │   └── logging_service.py        # Logging configuration
│   ├── logs/                         # Log file directory
│   └── requirements.txt              # Python dependencies
├── Dockerfile                        # Container definition
├── docker-compose.yml                # Local development setup
└── README.md                         # Documentation
```

## Setup & Deployment

### Prerequisites

- Docker and Docker Compose
- Azure DevOps organization and project
- Azure DevOps Personal Access Token (PAT) with read access to work items
- Azure Storage Account with a container for report storage

### Building the Docker Image

```bash
docker build -t azure-devops-reporter .
```

### Running with Docker Compose

```bash
docker-compose up -d
```

### Running with Docker

```bash
docker run -p 5000:5000 azure-devops-reporter
```

## API Endpoints

### API Documentation

- Swagger UI: `/ado-report/docs`
- API Spec: `/ado-report/apispec.json`

### Health Check

**Endpoint**: `/ado-report/health`

**Method**: GET

**Response**:
```json
{
  "status": "healthy"
}
```

### Generate Report

**Endpoint**: `/ado-report/generate-report`

**Method**: POST

**Headers**:
- Content-Type: application/json

**Request Body**:

```json
{
  "AZURE_PAT": "your-azure-devops-personal-access-token",
  "ORGANIZATION": "your-azure-devops-organization",
  "PROJECT": "your-azure-devops-project",
  "CUSTOM_FIELDS": [
    {
      "key": "Custom.Business_Value",
      "value": "High"
    },
    {
      "key": "Custom.Priority",
      "value": "1"
    }
  ],
  "filter_date": "2025-01-01",
  "output_file_name": "my_custom_report_name",
  "SHEET_COUNT": 4,
  "storage_account_name": "your-storage-account-name",
  "container_name": "your-container-name",
  "storage_account_sas": "your-storage-account-sas-token"
}
```

### Generate User Report

**Endpoint**: `/ado-report/user-report`

**Method**: POST

**Request Body**:

```json
{
  "AZURE_PAT": "your-azure-devops-personal-access-token",
  "ORGANIZATION": "your-azure-devops-organization",
  "PROJECT": "your-azure-devops-project",
  "ASSIGNEDTO": "John Doe",
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
      "value": "Production"
    }
  ],
  "filter_date": "2025-01-01",
  "output_file_name": "user_report_john_doe",
  "SHEET_COUNT": 4,
  "storage_account_name": "your-storage-account-name",
  "container_name": "your-container-name",
  "storage_account_sas": "your-storage-account-sas-token"
}
```

**Response**:

```json
{
  "message": "User report generated successfully for John Doe",
  "file_url": "https://storage-account.blob.core.windows.net/container/user_report_john_doe.xlsx",
  "capex_percentage": 0.65
}
```

## Configuration Options

### Common Parameters
- **AZURE_PAT**: Azure DevOps Personal Access Token
- **ORGANIZATION**: Azure DevOps Organization name
- **PROJECT**: Azure DevOps Project name
- **CUSTOM_FIELDS**: List of objects with key-value pairs for custom field filtering
- **filter_date**: Optional date string (YYYY-MM-DD) to filter work items created on or after this date
- **output_file_name**: Optional custom filename for the output report (without extension)
- **SHEET_COUNT**: Integer (1-4) indicating how many Excel sheets to generate (default = 4)
- **storage_account_name**: Azure Storage account name
- **container_name**: Azure Storage container name
- **storage_account_sas**: SAS token for Azure Storage authentication

### User Report Specific Parameters
- **ASSIGNEDTO**: Name of the user to filter work items by assignment
- **CAPEX_FIELDS**: List of custom field objects for CAPEX percentage calculation

## Excel Report Column Configuration

### How to Modify Columns

The Excel report columns are easily configurable. To add, remove, or reorder columns:

1. **Open the file**: `src/services/report_service.py`
2. **Find the configuration section**: Look for the comment block starting with "COLUMN CONFIGURATION SECTION"
3. **Modify the column definitions**: Each sheet has its own column configuration:
   - `EPIC_COLUMNS`: Controls Epic sheet columns
   - `FEATURE_COLUMNS`: Controls Feature sheet columns
   - `STORY_COLUMNS`: Controls User Stories sheet columns
   - `TASK_COLUMNS`: Controls Tasks sheet columns

### Column Definition Format

Each column is defined as a dictionary with:
- `'field'`: The field name in the work item data
- `'header'`: The column header text that appears in Excel
- `'width'`: The column width in Excel

**Example**:
```python
EPIC_COLUMNS = [
    {'field': 'id', 'header': 'ID', 'width': 10},
    {'field': 'title', 'header': 'Title', 'width': 40},
    {'field': 'state', 'header': 'State', 'width': 15},
    {'field': 'parent_type', 'header': 'Parent Type', 'width': 15},
    {'field': 'parent_id', 'header': 'Parent ID', 'width': 15},
    # Add more columns here...
]
```

### Available Fields

The following fields are available for all work item types:
- `id`: Work item ID
- `title`: Work item title
- `type`: Work item type (Epic, Feature, User Story, Task, Bug, etc.)
- `state`: Work item state
- `assigned_to`: Person assigned to the work item
- `estimated_hours`: Original estimate in hours
- `completed_work`: Completed work in hours
- `remaining_work`: Remaining work in hours
- `percent_complete`: Completion percentage (0.0 to 1.0)
- `parent_type`: Type of parent work item
- `parent_id`: ID of parent work item
- `parent_title`: Title of parent work item
- `created_date`: When the work item was created

### Adding New Columns

To add a new column:
1. Add a new dictionary to the appropriate column configuration
2. Ensure the `'field'` name matches the data field from Azure DevOps
3. Set appropriate `'header'` and `'width'` values

### Removing Columns

To remove a column:
1. Delete the corresponding dictionary from the column configuration

### Reordering Columns

To change column order:
1. Reorder the dictionaries in the column configuration list

## Work Item Hierarchy Logic

### Flexible Hierarchy Support

The system now supports flexible work item hierarchies that don't strictly follow the Epic → Feature → User Story → Task pattern. Work items that have non-standard parent-child relationships (e.g., Tasks directly under Features) are still included in the report.

### Hierarchy Traversal

1. **Starting Point**: Filtered Epic work items
2. **Descendant Discovery**: All work items that are direct or indirect children of the filtered Epics
3. **Type Classification**: Work items are categorized by type into appropriate sheets
4. **Parent Information**: Each work item includes parent type, ID, and title for traceability

### Example Hierarchy

```
Epic 1000: "E-commerce Platform"
├── Feature 1001: "User Authentication"
│   ├── User Story 1002: "User Login"
│   │   ├── Task 1003: "Create Login UI"
│   │   └── Task 1004: "Backend API"
│   └── Task 1005: "Setup Authentication" (Direct task under feature)
└── Feature 1007: "Product Catalog"
    ├── User Story 1008: "Product Listing"
    │   └── Task 1009: "Display Products"
    └── Bug 1010: "Fix Product Images" (Direct bug under feature)
```

All work items in this hierarchy would be included in the report, regardless of hierarchy violations.

## Work Item Hours Calculation Logic

### Overview

The system calculates three key metrics for work items:

1. **Estimated Hours**: From the `Microsoft.VSTS.Scheduling.OriginalEstimate` field
2. **Completed Work**: From the `Microsoft.VSTS.Scheduling.CompletedWork` field
3. **Remaining Work**: From the `Microsoft.VSTS.Scheduling.RemainingWork` field
4. **Percent Complete**: Calculated as (Completed Work / Estimated Hours) × 100

### Calculation Logic with Example

Using the hierarchy example above:

**Individual Work Item Values (from Azure DevOps fields):**
- Task 1003: Estimated=8h, Completed=6h, Remaining=2h
- Task 1004: Estimated=12h, Completed=12h, Remaining=0h
- Task 1005: Estimated=4h, Completed=4h, Remaining=0h
- Task 1009: Estimated=10h, Completed=4h, Remaining=6h
- Bug 1010: Estimated=2h, Completed=1h, Remaining=1h

**Work Item Calculations:**

1. **Task 1003**: 
   - % Complete: (6h / 8h) × 100 = 75%

2. **User Story 1002** (if it had child aggregation):
   - Estimated Hours: 8h + 12h = 20h
   - Completed Work: 6h + 12h = 18h
   - % Complete: (18h / 20h) × 100 = 90%

3. **Feature 1001** (aggregating all descendants):
   - Estimated Hours: 20h + 4h = 24h
   - Completed Work: 18h + 4h = 22h
   - % Complete: (22h / 24h) × 100 = 91.67%

### Key Points

- **Individual Values**: Each work item shows its own estimated, completed, and remaining hours
- **No Automatic Rollup**: Parent items show their own values, not aggregated child values
- **Percentage Calculation**: % Complete = (Completed Work / Estimated Hours) × 100
- **Decimal Format**: Percentages are stored as decimals (0.0 to 1.0) and displayed as percentages in Excel

## Work Item Type Filtering

The report properly filters work items by type for each sheet:

- **Epic Sheet**: Contains only Epic work items
- **Feature Sheet**: Contains only Feature work items  
- **User Stories Sheet**: Contains only User Story work items
- **Tasks Sheet**: Contains Task, Bug, and QA Validation Task work items

This ensures each sheet shows only the appropriate work item types without mixing different types together.

## User Reports and CAPEX Calculation

### User Report Features

User reports provide the following capabilities:

1. **Assignment Filtering**: Show only work items assigned to a specific user
2. **Type Organization**: Organize user's work items by type into separate sheets
3. **Summary Rows**: Include total hours and percentages at the bottom of each sheet
4. **CAPEX Percentage**: Calculate what percentage of user's work corresponds to CAPEX projects

### CAPEX Calculation Logic

The CAPEX percentage shows what portion of a user's work corresponds to Epic work items that match the CAPEX_FIELDS criteria:

1. **Find CAPEX Epics**: Epics that match all CAPEX_FIELDS criteria
2. **Get Descendants**: All work items under those CAPEX Epics
3. **Calculate User's CAPEX Work**: User's work items that are descendants of CAPEX Epics
4. **Calculate Percentage**: (CAPEX Hours / Total User Hours) × 100

### Example CAPEX Calculation

**User's Total Work**: 80 hours estimated
**CAPEX Epic Work**: 40 hours estimated (descendant work items of CAPEX Epics)
**CAPEX Percentage**: 40h / 80h = 50%

This means 50% of the user's work corresponds to CAPEX projects.

## Logging

The service logs detailed information about each API call:

- **Console logs**: High-level information for main steps
- **File logs**: Detailed logs stored in the container's `/app/logs` directory
  - Format: `azure_devops_reporter_YYYYMMDD.log`
  - Rotated when size exceeds 10MB (keeps 5 backups)

## Security Considerations

- The API expects all sensitive information (PAT tokens, SAS tokens) to be passed in the request body
- For production use, consider implementing proper authentication and authorization
- SAS tokens should be generated with limited permissions and expiration time

## Error Handling

The API returns appropriate HTTP status codes:

- 200: Success
- 400: Invalid or missing parameters
- 500: Internal server error (with error details)

## Customization

The service is designed to be easily customized:

- Column definitions are centralized in the `report_service.py` file under the "COLUMN CONFIGURATION SECTION"
- Custom field handling is extensible in `azure_devops_service.py`
- Sheet structure can be modified by updating the column configuration arrays
- Hierarchy traversal logic accommodates non-standard parent-child relationships

## License

This project is licensed under the MIT License - see the LICENSE file for details.
