
import logging
from azure.storage.blob import BlobServiceClient
from typing import Optional

logger = logging.getLogger(__name__)

class AzureBlobStorageService:
    def __init__(self, account_name: str, container_name: str, sas_token: str):
        self.account_name = account_name
        self.container_name = container_name
        self.sas_token = sas_token
        
        # Build connection string
        self.conn_str = f"https://{account_name}.blob.core.windows.net?{sas_token}"
        
    def upload_file(self, file_path: str, blob_name: Optional[str] = None) -> str:
        """
        Upload a file to Azure Blob Storage
        
        Args:
            file_path: Local path to the file
            blob_name: Name to give the blob (file) in storage
            
        Returns:
            URL to the uploaded blob
        """
        if blob_name is None:
            import os
            blob_name = os.path.basename(file_path)
            
        try:
            # Create a blob client using the connection string
            blob_service_client = BlobServiceClient(account_url=f"https://{self.account_name}.blob.core.windows.net", 
                                                   credential=self.sas_token)
            
            # Get container client
            container_client = blob_service_client.get_container_client(self.container_name)
            
            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)
            
            # Upload file
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
                
            # Generate a SAS URL for the blob
            blob_url = blob_client.url
            logger.info(f"File uploaded successfully to: {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.exception(f"Error uploading file to Azure Blob Storage: {str(e)}")
            raise
