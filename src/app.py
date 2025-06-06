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
    "specs_route": "/ado-report/docs"
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
              description: DEPRECATED - Use filter_startdate and filter_enddate instead. Optional date string (YYYY-MM-DD) to filter work items created on or after this date
            filter_startdate:
              type: string
              description: Optional start date string (YYYY-MM-DD) to filter work items created on or after this date
            filter_enddate:
              type: string
              description: Optional end date string (YYYY-MM-DD) to filter work items created on or before this date
            filter_workitemtype:
              type: array
              description: List of work item types to apply date filtering to (e.g., ["Epic", "Task"]). If not provided, date filter applies to all types.
              items:
                type: string
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
        headers:
          file_name:
            type: string
            description: The filename of the generated report              
      400:
        description: Bad request - missing required parameters
      500:
        description: Internal server error
    """
    return generate_report()

@app.route('/ado-report/user-report', methods=['POST'])
def generate_user_report_api():
    """
    Generate Azure DevOps user-specific work item report
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
            - ASSIGNEDTO
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
            ASSIGNEDTO:
              type: string
              description: Name of the user to filter work items by assignment
            CUSTOM_FIELDS:
              type: array
              description: List of custom field objects with key and value for filtering
              items:
                type: object
                properties:
                  key:
                    type: string
                    description: Custom field name
                  value:
                    type: string
                    description: Custom field value for filtering
            CAPEX_FIELDS:
              type: array
              description: List of custom field objects for CAPEX calculation
              items:
                type: object
                properties:
                  key:
                    type: string
                    description: Custom field name for CAPEX filtering
                  value:
                    type: string
                    description: Custom field value for CAPEX filtering
            filter_date:
              type: string
              description: DEPRECATED - Use filter_startdate and filter_enddate instead. Optional date string (YYYY-MM-DD) to filter work items created on or after this date
            filter_startdate:
              type: string
              description: Optional start date string (YYYY-MM-DD) to filter work items created on or after this date
            filter_enddate:
              type: string
              description: Optional end date string (YYYY-MM-DD) to filter work items created on or before this date
            filter_workitemtype:
              type: array
              description: List of work item types to apply date filtering to (e.g., ["Epic", "Task"]). If not provided, date filter applies to all types.
              items:
                type: string
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
        description: User report generated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              description: Success message
            file_url:
              type: string
              description: URL to the generated report
            capex_percentage:
              type: number
              description: Percentage of work corresponding to CAPEX fields
            capex_classification:
              type: string
              description: Work items are classified as CAPEX or non-CAPEX based on whether they belong to CAPEX epics
        headers:
          file_name:
            type: string
            description: The filename of the generated report     
        headers:
          file_name:
            type: string
            description: The filename of the generated report                     
      400:
        description: Bad request - missing required parameters
      500:
        description: Internal server error
    """
    return generate_user_report()

@app.route('/api/generate-report', methods=['POST'])
def legacy_generate_report():
    """Legacy endpoint that redirects to the new path"""
    return generate_report()

def _validate_date_parameters(data: dict) -> tuple:
    """
    Validate and process date parameters with backward compatibility
    
    Returns:
        tuple: (filter_startdate, filter_enddate, filter_workitemtype, error_message)
    """
    filter_startdate = data.get('filter_startdate')
    filter_enddate = data.get('filter_enddate')
    filter_workitemtype = data.get('filter_workitemtype', [])
    legacy_filter_date = data.get('filter_date')
    
    # Handle backward compatibility with legacy filter_date
    if legacy_filter_date and not filter_startdate:
        logger.info("Using legacy filter_date parameter as filter_startdate")
        filter_startdate = legacy_filter_date
    
    # Validate date formats
    try:
        if filter_startdate:
            datetime.strptime(filter_startdate, '%Y-%m-%d')
        if filter_enddate:
            datetime.strptime(filter_enddate, '%Y-%m-%d')
    except ValueError:
        return None, None, None, "Invalid date format. Please use YYYY-MM-DD format."
    
    # Validate date range
    if filter_startdate and filter_enddate:
        start_date = datetime.strptime(filter_startdate, '%Y-%m-%d')
        end_date = datetime.strptime(filter_enddate, '%Y-%m-%d')
        if start_date > end_date:
            return None, None, None, "filter_startdate must be before or equal to filter_enddate."
    
    # Validate work item types
    valid_work_item_types = ["Epic", "Feature", "User Story", "Task", "Bug", "QA Validation Task"]
    if filter_workitemtype:
        invalid_types = [wit for wit in filter_workitemtype if wit not in valid_work_item_types]
        if invalid_types:
            return None, None, None, f"Invalid work item types: {invalid_types}. Valid types are: {valid_work_item_types}"
    
    return filter_startdate, filter_enddate, filter_workitemtype, None

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
        output_file_name = data.get('output_file_name')
        
        # Enhanced date filtering parameters
        filter_startdate, filter_enddate, filter_workitemtype, date_error = _validate_date_parameters(data)
        if date_error:
            logger.error(f"Date validation error: {date_error}")
            return jsonify({"error": date_error}), 400
        
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

        # Initialize services
        logger.info("Initializing services")
        azure_devops = AzureDevOpsService(azure_pat, organization, project)
        report_service = ReportService()
        storage_service = AzureBlobStorageService(
            storage_account_name, 
            container_name, 
            storage_account_sas
        )
        
        # Step 1: Fetch Epics from Azure DevOps using the enhanced filtering
        logger.info("Fetching Epics from Azure DevOps...")
        try:
            epics = azure_devops.fetch_epics(
                custom_field_filters=custom_fields,
                filter_startdate=filter_startdate,
                filter_enddate=filter_enddate,
                filter_workitemtype=filter_workitemtype
            )
        except Exception as e:
            error_message = str(e)
            if "Invalid Azure DevOps PAT token" in error_message:
                logger.error("Authentication failed with Azure DevOps")
                return jsonify({
                    "error": "Invalid Azure DevOps PAT token. Please check your credentials.",
                    "status": "unauthorized"
                }), 401
            elif "Failed to parse Azure DevOps response" in error_message:
                logger.error("Failed to parse Azure DevOps response")
                return jsonify({
                    "error": "Failed to connect to Azure DevOps. Please check your credentials and try again.",
                    "status": "error"
                }), 500
            raise
        
        if not epics:
            logger.warning("No Epics found matching the criteria")
            response_data = {
                "message": "No Epics found matching the criteria.",
                "file_url": None
            }
            response = jsonify(response_data)
            response.headers['file_name'] = ""
            return response, 200      
        
        # Step 2: Process work item hierarchy and roll up data
        logger.info(f"Processing {len(epics)} Epics and their hierarchies...")
        processed_data = azure_devops.traverse_hierarchy(
            epics, 
            custom_fields,
            filter_workitemtype=filter_workitemtype
        )
        
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
        
        # Create response with headers
        response_data = {
            "message": "Report generated successfully",
            "file_url": file_url
        }
        response = jsonify(response_data)
        response.headers['file_name'] = blob_name
        return response, 200
        
    except Exception as e:
        logger.exception("Error generating report")
        error_message = str(e)
        
        # Handle specific error cases
        if "Invalid Azure DevOps PAT token" in error_message:
            return jsonify({
                "error": "Invalid Azure DevOps PAT token. Please check your credentials.",
                "status": "unauthorized"
            }), 401
        elif "Failed to parse Azure DevOps response" in error_message:
            return jsonify({
                "error": "Failed to connect to Azure DevOps. Please check your credentials and try again.",
                "status": "error"
            }), 500
        
        # For other errors, provide a generic error message
        return jsonify({
            "error": "An error occurred while generating the report. Please try again.",
            "status": "error"
        }), 500

def generate_user_report():
    """Implementation of the user-specific report generation endpoint"""
    try:
        # Extract parameters from JSON request
        data = request.get_json()
        logger.info("Received user report generation request")
        
        # Required parameters
        azure_pat = data.get('AZURE_PAT')
        organization = data.get('ORGANIZATION')
        project = data.get('PROJECT')
        assigned_to = data.get('ASSIGNEDTO')
        
        # Optional parameters
        custom_fields = data.get('CUSTOM_FIELDS', [])
        capex_fields = data.get('CAPEX_FIELDS', [])
        sheet_count = int(data.get('SHEET_COUNT', 4))
        output_file_name = data.get('output_file_name')
        
        # Enhanced date filtering parameters
        filter_startdate, filter_enddate, filter_workitemtype, date_error = _validate_date_parameters(data)
        if date_error:
            logger.error(f"Date validation error: {date_error}")
            return jsonify({"error": date_error}), 400
        
        # Storage account parameters
        storage_account_name = data.get('storage_account_name')
        container_name = data.get('container_name')
        storage_account_sas = data.get('storage_account_sas')
        
        # Validate required parameters
        if not all([azure_pat, organization, project, assigned_to]):
            logger.error("Missing required parameters")
            return jsonify({
                "error": "Missing required parameters. Please provide AZURE_PAT, ORGANIZATION, PROJECT, and ASSIGNEDTO."
            }), 400
            
        if not all([storage_account_name, container_name, storage_account_sas]):
            logger.error("Missing storage parameters")
            return jsonify({
                "error": "Missing storage parameters. Please provide storage_account_name, container_name, and storage_account_sas."
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
        
        # Step 1: Fetch user's work items with enhanced filtering
        logger.info(f"Fetching work items assigned to {assigned_to}...")
        # For user work items
        user_work_items = azure_devops.fetch_user_work_items(
            assigned_to=assigned_to,
            custom_field_filters=custom_fields,
            filter_startdate=filter_startdate,
            filter_enddate=filter_enddate,
            filter_workitemtype=filter_workitemtype
        )
        
        if not user_work_items:
            logger.warning(f"No work items found assigned to {assigned_to}")
            response_data = {
                "message": f"No work items found assigned to {assigned_to}.",
                "file_url": None,
                "capex_percentage": 0.0
            }
            response = jsonify(response_data)
            response.headers['file_name'] = ""
            return response, 200     
        
        # Step 2: Calculate CAPEX percentage and add classification if CAPEX fields are provided
        capex_percentage = 0.0
        capex_epic_ids = set()

        if capex_fields:
            logger.info("Calculating CAPEX percentage...")
            # Find EPICs that match CAPEX fields using enhanced filtering
            # For CAPEX epics
            capex_epics = azure_devops.fetch_epics(
                custom_field_filters=capex_fields,
                filter_startdate=filter_startdate,
                filter_enddate=filter_enddate,
                filter_workitemtype=filter_workitemtype
            )

            capex_epic_ids = {epic['id'] for epic in capex_epics}
            capex_percentage = azure_devops.calculate_capex_percentage(user_work_items, capex_epics)
            logger.info(f"CAPEX percentage calculated: {capex_percentage:.2%}")
        
        # Step 3: Add CAPEX classification to work items
        for work_item in user_work_items:
            if capex_epic_ids:
                is_capex = azure_devops._belongs_to_capex_epic(work_item, capex_epic_ids)
                work_item['capex_classification'] = 'CAPEX' if is_capex else 'non-CAPEX'
            else:
                work_item['capex_classification'] = 'non-CAPEX'
        
        # Step 4: Organize work items by type (without rollup calculation)
        logger.info(f"Organizing {len(user_work_items)} work items by type...")
        organized_data = azure_devops.organize_user_work_items(user_work_items)
        
        # Step 5: Generate Excel report
        logger.info("Generating user Excel report...")
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        report_service.build_excel_workbook(
            organized_data,
            temp_file_path,
            sheet_count,
            custom_fields,
            is_user_report=True,
            capex_percentage=capex_percentage
        )
        
        # Step 6: Upload to Azure Blob Storage
        logger.info("Uploading user report to Azure Blob Storage...")
        timestamp = azure_devops.get_timestamp()
        
        # Use custom filename if provided, otherwise use the default format
        if output_file_name:
            safe_filename = ''.join(c for c in output_file_name if c.isalnum() or c in ['-', '_', '.'])
            blob_name = f"{safe_filename}.xlsx"
        else:
            blob_name = f"user_report_{assigned_to}_{timestamp}.xlsx"
        
        file_url = storage_service.upload_file(temp_file_path, blob_name)
        
        # Clean up temp file
        os.unlink(temp_file_path)

        logger.info("User report generation completed successfully")
        
        # Create response with headers
        response_data = {
            "message": f"User report generated successfully for {assigned_to}",
            "file_url": file_url,
            "capex_percentage": capex_percentage,
            "capex_classification": "Work items are classified as CAPEX or non-CAPEX based on whether they belong to CAPEX epics"
        }
        response = jsonify(response_data)
        response.headers['file_name'] = blob_name
        return response, 200
        
    except Exception as e:
        logger.exception("Error generating user report")
        error_details = {
            "error": f"Failed to generate user report: {str(e)}",
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        response = jsonify(error_details)
        response.headers['file_name'] = ""
        return response, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

