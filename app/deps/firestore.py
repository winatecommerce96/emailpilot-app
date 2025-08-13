import os
import logging
from google.cloud import firestore

logger = logging.getLogger(__name__)

def get_db():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    
    if not project_id:
        logger.error("No Google Cloud project ID found in environment")
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
    
    logger.info(f"Initializing Firestore client for project: {project_id}")
    
    # Check if we're using the emulator
    emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST")
    if emulator_host:
        logger.info(f"Using Firestore emulator at: {emulator_host}")
    else:
        logger.info("Using production Firestore")
        # Log credentials path if available
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path:
            logger.info(f"Using credentials from: {creds_path}")
    
    # Create client - it will automatically use emulator if FIRESTORE_EMULATOR_HOST is set
    try:
        client = firestore.Client(project=project_id)
        logger.info("Firestore client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")
        raise
