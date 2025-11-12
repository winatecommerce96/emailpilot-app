import os
import json
import logging
from google.cloud import firestore
from google.oauth2 import service_account
from app.services.secrets import SecretManagerService

logger = logging.getLogger(__name__)

_DB_CLIENT: firestore.Client | None = None


def get_db() -> firestore.Client:
    global _DB_CLIENT
    if _DB_CLIENT is not None:
        return _DB_CLIENT
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    
    if not project_id:
        logger.error("No Google Cloud project ID found in environment")
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
    
    # Try to get credentials from Secret Manager
    try:
        secret_manager = SecretManagerService(project_id=project_id)
        credentials_json = secret_manager.get_secret("firestore-service-account")
        if credentials_json:
            logger.info("Using Firestore credentials from Secret Manager")
            credentials_dict = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/datastore"]
            )
            _DB_CLIENT = firestore.Client(project=project_id, credentials=credentials)
            return _DB_CLIENT
    except Exception as e:
        logger.warning(f"Could not load credentials from Secret Manager: {e}")

    # Fallback to default credentials
    logger.info("Using Application Default Credentials for Firestore")
    _DB_CLIENT = firestore.Client(project=project_id)
    return _DB_CLIENT
