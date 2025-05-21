

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
  "file_url": "https://storage-account.blob.core.windows.net/container/report_20220101_120000.xlsx"
}
```

### Example API Call (cURL)

```bash
curl -X POST \
  http://localhost:5000/ado-report/generate-report \
  -H 'Content-Type: application/json' \
  -d '{
    "AZURE_PAT": "your-azure-devops-personal-access-token",
    "ORGANIZATION": "your-azure-devops-organization",
    "PROJECT": "your-azure-devops-project",
    "CUSTOM_FIELDS": [
      {
        "key": "Custom.Business_Value",
        "value": "High"
      }
    ],
    "filter_date": "2025-01-01",
    "SHEET_COUNT": 4,
    "storage_account_name": "your-storage-account-name",
    "container_name": "your-container-name", 
    "storage_account_sas": "your-storage-account-sas-token"
  }'
```

### Example API Call (Python)

```python
import requests
import json

url = "http://localhost:5000/ado-report/generate-report"
payload = {
    "AZURE_PAT": "your-azure-devops-personal-access-token",
    "ORGANIZATION": "your-azure-devops-organization",
    "PROJECT": "your-azure-devops-project",
    "CUSTOM_FIELDS": [
      {
        "key": "Custom.Business_Value",
        "value": "High"
      }
    ],
    "filter_date": "2025-01-01",
    "SHEET_COUNT": 4,
    "storage_account_name": "your-storage-account-name",
    "container_name": "your-container-name",
    "storage_account_sas": "your-storage-account-sas-token"
}
headers = {"Content-Type": "application/json"}

response = requests.post(url, data=json.dumps(payload), headers=headers)
print(response.json())
```

## Configuration Options

- **AZURE_PAT**: Azure DevOps Personal Access Token
- **ORGANIZATION**: Azure DevOps Organization name
- **PROJECT**: Azure DevOps Project name
- **CUSTOM_FIELDS**: List of objects with key-value pairs for custom field filtering:
  - **key**: Custom field name
  - **value**: Custom field value to filter on
- **filter_date**: Optional date string (YYYY-MM-DD) to filter work items created on or after this date
- **SHEET_COUNT**: Integer (1-4) indicating how many Excel sheets to generate (default = 4)
  - 1: Epic Summary
  - 2: + Feature Breakdown
  - 3: + Story Breakdown
  - 4: + Leaf Tasks (full detail)
- **storage_account_name**: Azure Storage account name
- **container_name**: Azure Storage container name
- **storage_account_sas**: SAS token for Azure Storage authentication

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

- Column definitions are centralized in the `report_service.py` file
- Custom field handling is extensible in `azure_devops_service.py`
- Sheet structure can be modified by updating the `build_excel_workbook` method

## License

This project is licensed under the MIT License - see the LICENSE file for details.

