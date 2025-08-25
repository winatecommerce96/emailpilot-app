import os
import logging
from google.cloud import secretmanager
from google.auth import default as get_adc

logger = logging.getLogger(__name__)

class SecretLoadError(Exception):
    """Custom exception for secret loading failures."""
    pass

def get_secret_value(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """Access the payload for the given secret version if one exists.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to load Secret '{secret_id}' from project '{project_id}': {e}")
        raise SecretLoadError(f"Secret '{secret_id}' not found or accessible.") from e

def get_project_id() -> str:
    """Attempts to get the Google Cloud Project ID from environment or ADC."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        try:
            _, project_id = get_adc()
        except Exception as e:
            logger.warning(f"Could not determine project ID from ADC: {e}")
    if not project_id:
        raise SecretLoadError("Google Cloud Project ID not found in environment or ADC.")
    return project_id
