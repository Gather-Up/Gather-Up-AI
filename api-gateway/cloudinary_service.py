"""
Cloudinary Image Upload Service
"""
import cloudinary
import cloudinary.uploader
import base64
import io
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary (set these in your .env file)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "your_cloud_name"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "your_api_key"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "your_api_secret"),
    secure=True
)


def upload_base64_image(base64_string: str, folder: str = "gatherup/events", public_id: Optional[str] = None) -> dict:
    """
    Upload base64 image to Cloudinary
    
    Args:
        base64_string: Base64 encoded image data (without data:image prefix)
        folder: Cloudinary folder path
        public_id: Optional custom public ID
        
    Returns:
        dict with url, secure_url, public_id, cloudinary_id
    """
    try:
        # Add data URI prefix if not present
        if not base64_string.startswith('data:image'):
            base64_string = f"data:image/png;base64,{base64_string}"
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            base64_string,
            folder=folder,
            public_id=public_id,
            resource_type="image",
            transformation=[
                {'quality': 'auto:good'},
                {'fetch_format': 'auto'}
            ]
        )
        
        return {
            "url": upload_result.get("secure_url"),
            "cloudinary_id": upload_result.get("public_id"),
            "width": upload_result.get("width"),
            "height": upload_result.get("height"),
            "format": upload_result.get("format"),
            "resource_type": upload_result.get("resource_type"),
        }
        
    except Exception as e:
        raise Exception(f"Cloudinary upload failed: {str(e)}")


def delete_image(cloudinary_id: str) -> bool:
    """Delete image from Cloudinary"""
    try:
        cloudinary.uploader.destroy(cloudinary_id)
        return True
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
        return False
