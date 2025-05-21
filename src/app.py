
from flask import Flask, request, jsonify
import logging
import os
import tempfile
from services.azure_devops_service import AzureDevOpsService
from services.report_service import ReportService
from services.storage_service import AzureBlobStorageService
from services.logging_service import setup_logging

# Configure logging
logger = setup_logging(log_level=logging.INFO)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
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
        
        # Step 1: Fetch Epics from Azure DevOps using the custom field filters
        logger.info("Fetching Epics from Azure DevOps...")
        epics = azure_devops.fetch_epics(custom_fields)
        
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
        return jsonify({
            "error": f"Failed to generate report: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
