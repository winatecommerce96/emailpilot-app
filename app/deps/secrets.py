import os
import logging
from typing import Optional
from app.services.secrets import SecretManagerService, SecretError

logger = logging.getLogger(__name__)

def get_secret_manager_service() -> Optional[SecretManagerService]:
    """
    Get Secret Manager service with graceful fallback for development environments.
    Returns None if Secret Manager is not available or disabled.
    """
    # Check if Secret Manager is explicitly disabled
    if os.getenv("SECRET_MANAGER_ENABLED", "true").lower() == "false":
        logger.info("Secret Manager disabled via SECRET_MANAGER_ENABLED=false")
        return None
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "development":
            logger.warning("GOOGLE_CLOUD_PROJECT not set in development environment - Secret Manager unavailable")
            return None
        else:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT environment variable not set.")
    
    try:
        service = SecretManagerService(project_id=project_id)
        # Quick test to ensure the service is actually accessible
        service.list_secrets()
        return service
    except Exception as e:
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "development":
            logger.warning(f"Secret Manager not available in development: {e}")
            return None
        else:
            logger.error(f"Secret Manager service failed in production: {e}")
            raise RuntimeError(f"Secret Manager service required in production but failed: {e}") from e
