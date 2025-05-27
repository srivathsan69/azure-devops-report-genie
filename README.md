
# Azure DevOps Work Item Report Generator

A containerized Python API service that connects to Azure DevOps, rolls up hierarchical work item data, and generates Excel reports.

## Features

- Connects to Azure DevOps REST API
- Extracts work item hierarchy (Epics → Features → Stories → Tasks)
- Filters Epics based on custom field values
- Filters work items by creation date
- Rolls up metrics (estimated hours, completed work)
- Generates Excel report with configurable detail levels
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

- Swagger UI: `/ado-report/docs/`
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

**Response**:

```json
{
  "message": "Report generated successfully",
  "file_url": "https://storage-account.blob.core.windows.net/container/my_custom_report_name.xlsx"
}
```

## Configuration Options

- **AZURE_PAT**: Azure DevOps Personal Access Token
- **ORGANIZATION**: Azure DevOps Organization name
- **PROJECT**: Azure DevOps Project name
- **CUSTOM_FIELDS**: List of objects with key-value pairs for custom field filtering:
  - **key**: Custom field name (with or without 'Custom.' prefix)
  - **value**: Custom field value to filter on
- **filter_date**: Optional date string (YYYY-MM-DD) to filter work items created on or after this date
- **output_file_name**: Optional custom filename for the output report (without extension)
- **SHEET_COUNT**: Integer (1-4) indicating how many Excel sheets to generate (default = 4)
  - 1: Epic Summary
  - 2: + Feature Breakdown
  - 3: + Story Breakdown
  - 4: + Leaf Tasks (full detail)
- **storage_account_name**: Azure Storage account name
- **container_name**: Azure Storage container name
- **storage_account_sas**: SAS token for Azure Storage authentication

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
    # Add more columns here...
]
```

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

## Work Item Hours Calculation Logic

### Overview

The system calculates three key metrics for work items:

1. **Estimated Hours**: The total estimated effort for the work item and all its children
2. **Completed Work**: The total hours actually worked on the work item and all its children
3. **Remaining Work**: The estimated hours still remaining to complete the work item and all its children

### Calculation Logic with Example

Let's use a simple hierarchy to explain the calculations:

```
Epic 1000: "E-commerce Platform"
├── Feature 1001: "User Authentication"
│   ├── Story 1002: "User Login"
│   │   ├── Task 1003: "Create Login UI" (Est: 8h, Completed: 6h, Remaining: 2h)
│   │   └── Task 1004: "Backend API" (Est: 12h, Completed: 12h, Remaining: 0h)
│   └── Story 1005: "User Registration"
│       └── Task 1006: "Registration Form" (Est: 6h, Completed: 3h, Remaining: 3h)
└── Feature 1007: "Product Catalog"
    └── Story 1008: "Product Listing"
        └── Task 1009: "Display Products" (Est: 10h, Completed: 4h, Remaining: 6h)
```

**Individual Work Item Values (from Azure DevOps fields):**
- Task 1003: Estimated=8h, Completed=6h, Remaining=2h
- Task 1004: Estimated=12h, Completed=12h, Remaining=0h
- Task 1006: Estimated=6h, Completed=3h, Remaining=3h
- Task 1009: Estimated=10h, Completed=4h, Remaining=6h

**Rolled-up Calculations:**

1. **Story 1002** (User Login):
   - Estimated Hours: 8h + 12h = 20h
   - Completed Work: 6h + 12h = 18h
   - Remaining Work: 2h + 0h = 2h
   - % Complete: (18h / 20h) × 100 = 90%

2. **Story 1005** (User Registration):
   - Estimated Hours: 6h
   - Completed Work: 3h
   - Remaining Work: 3h
   - % Complete: (3h / 6h) × 100 = 50%

3. **Feature 1001** (User Authentication):
   - Estimated Hours: 20h + 6h = 26h
   - Completed Work: 18h + 3h = 21h
   - Remaining Work: 2h + 3h = 5h
   - % Complete: (21h / 26h) × 100 = 80.77%

4. **Story 1008** (Product Listing):
   - Estimated Hours: 10h
   - Completed Work: 4h
   - Remaining Work: 6h
   - % Complete: (4h / 10h) × 100 = 40%

5. **Feature 1007** (Product Catalog):
   - Estimated Hours: 10h
   - Completed Work: 4h
   - Remaining Work: 6h
   - % Complete: (4h / 10h) × 100 = 40%

6. **Epic 1000** (E-commerce Platform):
   - Estimated Hours: 26h + 10h = 36h
   - Completed Work: 21h + 4h = 25h
   - Remaining Work: 5h + 6h = 11h
   - % Complete: (25h / 36h) × 100 = 69.44%

### Key Points

- **Bottom-up aggregation**: Values are calculated from the leaf tasks up to parent items
- **Hierarchical rollup**: Each parent item's values are the sum of all its children
- **Percentage calculation**: % Complete = (Completed Work / Estimated Hours) × 100
- **Zero handling**: If Estimated Hours is 0, % Complete is set to 0
- **Data sources**: Individual task values come from Azure DevOps work item fields

## Work Item Type Filtering

The report now properly filters work items by type for each sheet:

- **Epic Sheet**: Contains only Epic work items
- **Feature Sheet**: Contains only Feature work items  
- **User Stories Sheet**: Contains only User Story work items
- **Tasks Sheet**: Contains Task, Bug, and QA Validation Task work items

This ensures each sheet shows only the appropriate work item types without mixing different types together.

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.
