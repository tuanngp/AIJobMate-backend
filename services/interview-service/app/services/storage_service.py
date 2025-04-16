import os
import logging
from typing import Optional
from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        """Initialize storage service (S3 or local storage)"""
        self.storage_type = settings.STORAGE_TYPE  # "s3" or "local"
        self.local_storage_path = settings.LOCAL_STORAGE_PATH
        
        if self.storage_type == "s3":
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        else:
            # Create local storage directory if it doesn't exist
            os.makedirs(self.local_storage_path, exist_ok=True)

    async def upload_file(self, file: UploadFile, folder: str = "recordings") -> Optional[str]:
        """Upload a file and return its URL/path"""
        try:
            if self.storage_type == "s3":
                return await self._upload_to_s3(file, folder)
            else:
                return await self._save_to_local(file, folder)
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return None

    async def _upload_to_s3(self, file: UploadFile, folder: str) -> str:
        """Upload file to S3 bucket"""
        try:
            file_path = f"{folder}/{file.filename}"
            await self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                file_path,
                ExtraArgs={'ACL': 'public-read'}
            )
            return f"https://{self.bucket_name}.s3.amazonaws.com/{file_path}"
        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            raise

    async def _save_to_local(self, file: UploadFile, folder: str) -> str:
        """Save file to local storage"""
        try:
            folder_path = os.path.join(self.local_storage_path, folder)
            os.makedirs(folder_path, exist_ok=True)
            
            file_path = os.path.join(folder_path, file.filename)
            content = await file.read()
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            return f"/storage/{folder}/{file.filename}"
        except Exception as e:
            logger.error(f"Error saving file locally: {str(e)}")
            raise

    async def delete_file(self, file_url: str) -> bool:
        """Delete a file from storage"""
        try:
            if self.storage_type == "s3":
                # Extract key from S3 URL
                file_key = file_url.split(f"{self.bucket_name}.s3.amazonaws.com/")[1]
                await self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
            else:
                # Remove /storage/ prefix and convert to local path
                file_path = os.path.join(
                    self.local_storage_path,
                    file_url.replace("/storage/", "")
                )
                os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False