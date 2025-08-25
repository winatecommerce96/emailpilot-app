"""
Firestore service with in-memory service account credentials.
No files written to disk, no environment variables needed.
"""
import os
from google.cloud import firestore
from google.oauth2 import service_account
from app.services.secrets import SecretError

def build_firestore_client(project_id: str, sa_json: dict = None) -> firestore.Client:
    """Build Firestore client with service account credentials or default credentials."""
    try:
        if sa_json:
            # Use provided service account credentials
            creds = service_account.Credentials.from_service_account_info(sa_json)
            client = firestore.Client(project=project_id, credentials=creds)
        else:
            # Use default credentials (from environment or ADC)
            client = firestore.Client(project=project_id)
        
        # Set environment variable to force REST transport for development
        # This helps avoid DNS resolution issues with gRPC
        os.environ["GOOGLE_CLOUD_DISABLE_GRPC"] = "true"
        
        return client
    except Exception as e:
        raise SecretError(f"Could not build Firestore client: {e}") from e

def ping(client: firestore.Client) -> None:
    """Lightweight connectivity check."""
    try:
        _ = next(client.collections(), None)
    except StopIteration:
        return
    except Exception as e:
        raise SecretError(f"Firestore connectivity check failed: {e}") from e

