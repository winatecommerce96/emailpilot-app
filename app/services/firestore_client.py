"""
Firestore client with proper authentication using Secret Manager
"""
import os
import json
import tempfile
from typing import Optional
from google.cloud import firestore
from google.oauth2 import service_account
import logging
from .secret_manager import SecretManagerService

logger = logging.getLogger(__name__)

_firestore_client = None

def get_firestore_client() -> firestore.Client:
    """
    Get or create a Firestore client with proper authentication
    
    Returns:
        firestore.Client: Authenticated Firestore client
    """
    global _firestore_client
    
    if _firestore_client is not None:
        return _firestore_client
    
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        
        # Method 1: Try to get credentials from Secret Manager
        try:
            secret_manager = SecretManagerService(project_id=project_id)
            
            # Try to get service account credentials from Secret Manager
            credentials_json = secret_manager.get_secret("firestore-service-account")
            
            if credentials_json:
                logger.info("Using Firestore credentials from Secret Manager")
                credentials_dict = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=["https://www.googleapis.com/auth/datastore"]
                )
                _firestore_client = firestore.Client(
                    project=project_id,
                    credentials=credentials
                )
                return _firestore_client
        except Exception as e:
            logger.warning(f"Could not load credentials from Secret Manager: {e}")
        
        # Method 2: Try GOOGLE_APPLICATION_CREDENTIALS environment variable
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            logger.info("Using GOOGLE_APPLICATION_CREDENTIALS from environment")
            _firestore_client = firestore.Client(project=project_id)
            return _firestore_client
        
        # Method 3: Try default credentials (works in Google Cloud environments)
        logger.info("Using Application Default Credentials")
        _firestore_client = firestore.Client(project=project_id)
        return _firestore_client
        
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")
        # Fallback to basic client (may work with default credentials)
        logger.warning("Falling back to basic Firestore client initialization")
        _firestore_client = firestore.Client(project="emailpilot-438321")
        return _firestore_client

def store_firestore_credentials(service_account_json: dict) -> bool:
    """
    Store Firestore service account credentials in Secret Manager
    
    Args:
        service_account_json: Service account JSON as dictionary
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        secret_manager = SecretManagerService()
        credentials_str = json.dumps(service_account_json)
        
        secret_manager.create_secret(
            secret_id="firestore-service-account",
            secret_value=credentials_str,
            labels={"type": "service-account", "service": "firestore"}
        )
        
        logger.info("Successfully stored Firestore credentials in Secret Manager")
        
        # Reset the global client to use new credentials
        global _firestore_client
        _firestore_client = None
        
        return True
    except Exception as e:
        logger.error(f"Failed to store Firestore credentials: {e}")
        return False