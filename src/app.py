
from flask import Flask, request, jsonify
import logging
import os
import tempfile
from datetime import datetime
from services.azure_devops_service import AzureDevOpsService
from services.report_service import ReportService
from services.storage_service import AzureBlobStorageService
from services.logging_service import setup_logging
from flasgger import Swagger
import json
import traceback

# Configure logging
logger = setup_logging(log_level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# Configure Swagger with proper configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/ado-report/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/ado-report/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/ado-report/docs/"
}

swagger_template = {
    "info": {
        "title": "Azure DevOps Work Item Report API",
        "description": "API for generating reports from Azure DevOps work items",
        "version": "1.0",
        "contact": {
            "name": "API Support"
        }
    }
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Health check endpoints for container readiness/liveness probes
@app.route('/health', methods=['GET'])
@app.route('/ado-report/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    ---
    responses:
      200:
        description: Service is healthy
    """
    return jsonify({"status": "healthy"}), 200

@app.route('/ado-report/generate-report', methods=['POST'])
def generate_report_api():
    """
    Generate Azure DevOps work item report
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - AZURE_PAT
            - ORGANIZATION
            - PROJECT
            - storage_account_name
            - container_name
            - storage_account_sas
          properties:
            AZURE_PAT:
              type: string
              description: Azure DevOps Personal Access Token
            ORGANIZATION:
              type: string
              description: Azure DevOps Organization name
            PROJECT:
              type: string
              description: Azure DevOps Project name
            CUSTOM_FIELDS:
              type: array
              description: List of custom field objects with key and value for filtering
              items:
                type: object
                properties:
                  key:
                    type: string
                    description: Custom field name (prefix 'Custom.' is optional for custom fields)
                  value:
                    type: string
                    description: Custom field value for filtering
            filter_date:
              type: string
              description: Optional date string (YYYY-MM-DD) to filter work items created on or after this date
            output_file_name:
              type: string
              description: Optional custom filename for the output report (without extension)
            SHEET_COUNT:
              type: integer
              description: Number of sheets to include in the report (1-4)
              default: 4
            storage_account_name:
              type: string
              description: Azure Storage account name
            container_name:
              type: string
              description: Azure Storage container name
            storage_account_sas:
              type: string
              description: SAS token for Azure Storage authentication
    responses:
      200:
        description: Report generated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              description: Success message
            file_url:
              type: string
              description: URL to the generated report
      400:
        description: Bad request - missing required parameters
      500:
        description: Internal server error
    """
    return generate_report()

@app.route('/api/generate-report', methods=['POST'])
def legacy_generate_report():
    """Legacy endpoint that redirects to the new path"""
    return generate_report()

# ... keep existing code (generate_report function implementation)

def generate_report():
    """Shared implementation of the report generation endpoint"""
    try:
        # Extract parameters from JSON request
        data = request.get_json()
        logger.info("Received report generation request")
        logger.debug(f"Request parameters: {data}")
        
        # Required parameters
        azure_pat = data.get('AZURE_PAT')
        organization = data.get('ORGANIZATION')
        project = data.get('PROJECT')
        
        # Optional parameters
        custom_fields = data.get('CUSTOM_FIELDS', [])
        sheet_count = int(data.get('SHEET_COUNT', 4))
        filter_date = data.get('filter_date')  # Date filtering parameter
        output_file_name = data.get('output_file_name')  # Custom filename parameter
        
        # Storage account parameters
        storage_account_name = data.get('storage_account_name')
        container_name = data.get('container_name')
        storage_account_sas = data.get('storage_account_sas')
        
        # Validate required parameters
        if not all([azure_pat, organization, project]):
            logger.error("Missing required parameters")
            return jsonify({
                "error": "Missing required parameters. Please provide AZURE_PAT, ORGANIZATION, and PROJECT."
            }), 400
            
        if not all([storage_account_name, container_name, storage_account_sas]):
            logger.error("Missing storage parameters")
            return jsonify({
                "error": "Missing storage parameters. Please provide storage_account_name, container_name, and storage_account_sas."
            }), 400
            
        if not 1 <= sheet_count <= 4:
            logger.error(f"Invalid SHEET_COUNT: {sheet_count}")
            return jsonify({
                "error": "SHEET_COUNT must be between 1 and 4."
            }), 400
            
        # Validate date format if provided
        if filter_date:
            try:
                datetime.strptime(filter_date, '%Y-%m-%d')
            except ValueError:
                logger.error(f"Invalid date format: {filter_date}")
                return jsonify({
                    "error": "Invalid filter_date format. Please use YYYY-MM-DD format."
                }), 400

        # Initialize services
        logger.info("Initializing services")
        azure_devops = AzureDevOpsService(azure_pat, organization, project)
        report_service = ReportService()
        storage_service = AzureBlobStorageService(
            storage_account_name, 
            container_name, 
            storage_account_sas
        )
        
        # Step 1: Fetch Epics from Azure DevOps using the custom field filters and date filter
        logger.info("Fetching Epics from Azure DevOps...")
        epics = azure_devops.fetch_epics(custom_fields, filter_date)
        
        if not epics:
            logger.warning("No Epics found matching the criteria")
            return jsonify({
                "message": "No Epics found matching the criteria.",
                "file_url": None
            }), 200
        
        # Step 2: Process work item hierarchy and roll up data
        logger.info(f"Processing {len(epics)} Epics and their hierarchies...")
        processed_data = azure_devops.traverse_hierarchy(epics, custom_fields)
        
        # Step 3: Generate Excel report
        logger.info("Generating Excel report...")
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        report_service.build_excel_workbook(
            processed_data, 
            temp_file_path, 
            sheet_count,
            custom_fields
        )
        
        # Step 4: Upload to Azure Blob Storage
        logger.info("Uploading report to Azure Blob Storage...")
        timestamp = azure_devops.get_timestamp()
        
        # Use custom filename if provided, otherwise use the default format
        if output_file_name:
            # Ensure the filename is safe by removing any problematic characters
            safe_filename = ''.join(c for c in output_file_name if c.isalnum() or c in ['-', '_', '.'])
            blob_name = f"{safe_filename}.xlsx"
        else:
            blob_name = f"azure_devops_report_{timestamp}.xlsx"
        
        file_url = storage_service.upload_file(temp_file_path, blob_name)
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        logger.info("Report generation completed successfully")
        return jsonify({
            "message": "Report generated successfully",
            "file_url": file_url
        }), 200
        
    except Exception as e:
        logger.exception("Error generating report")
        # Provide more detailed error information in the response
        error_details = {
            "error": f"Failed to generate report: {str(e)}",
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        return jsonify(error_details), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
