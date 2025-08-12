"""
Google Secret Manager service for secure API key storage
"""
import os
import json
from typing import Optional, Dict, Any
from google.cloud import secretmanager
from google.api_core import exceptions
import logging

logger = logging.getLogger(__name__)


class SecretManagerService:
    """Service for managing secrets in Google Secret Manager"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        self.client = secretmanager.SecretManagerServiceClient()
        self.parent = f"projects/{self.project_id}"
    
    def create_secret(self, secret_id: str, secret_value: str, labels: Dict[str, str] = None) -> str:
        """
        Create a new secret in Secret Manager
        
        Args:
            secret_id: Unique identifier for the secret
            secret_value: The secret value to store
            labels: Optional labels for the secret
        
        Returns:
            The full resource name of the created secret
        """
        try:
            # Create the secret
            secret = {
                "replication": {"automatic": {}},
            }
            if labels:
                secret["labels"] = labels
            
            response = self.client.create_secret(
                request={
                    "parent": self.parent,
                    "secret_id": secret_id,
                    "secret": secret,
                }
            )
            
            # Add the secret version with the actual value
            self.add_secret_version(secret_id, secret_value)
            
            logger.info(f"Created secret: {secret_id}")
            return response.name
            
        except exceptions.AlreadyExists:
            logger.warning(f"Secret {secret_id} already exists, updating version")
            self.add_secret_version(secret_id, secret_value)
            return f"{self.parent}/secrets/{secret_id}"
        except Exception as e:
            logger.error(f"Error creating secret {secret_id}: {e}")
            raise
    
    def add_secret_version(self, secret_id: str, secret_value: str) -> str:
        """
        Add a new version of a secret
        
        Args:
            secret_id: The secret identifier
            secret_value: The new secret value
        
        Returns:
            The version resource name
        """
        try:
            parent = f"{self.parent}/secrets/{secret_id}"
            
            # Convert secret value to bytes
            payload = secret_value.encode("UTF-8")
            
            response = self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": payload},
                }
            )
            
            logger.info(f"Added secret version for: {secret_id}")
            return response.name
            
        except Exception as e:
            logger.error(f"Error adding secret version for {secret_id}: {e}")
            raise
    
    def get_secret(self, secret_id: str, version: str = "latest") -> Optional[str]:
        """
        Retrieve a secret value from Secret Manager
        
        Args:
            secret_id: The secret identifier
            version: The version to retrieve (default: "latest")
        
        Returns:
            The secret value or None if not found
        """
        try:
            name = f"{self.parent}/secrets/{secret_id}/versions/{version}"
            response = self.client.access_secret_version(request={"name": name})
            
            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"Retrieved secret: {secret_id}")
            return secret_value
            
        except exceptions.NotFound:
            logger.warning(f"Secret not found: {secret_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_id}: {e}")
            raise
    
    def delete_secret(self, secret_id: str) -> bool:
        """
        Delete a secret from Secret Manager
        
        Args:
            secret_id: The secret identifier
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            name = f"{self.parent}/secrets/{secret_id}"
            self.client.delete_secret(request={"name": name})
            
            logger.info(f"Deleted secret: {secret_id}")
            return True
            
        except exceptions.NotFound:
            logger.warning(f"Secret not found for deletion: {secret_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting secret {secret_id}: {e}")
            raise
    
    def list_secrets(self, filter_str: str = None) -> list:
        """
        List all secrets in the project
        
        Args:
            filter_str: Optional filter string
        
        Returns:
            List of secret names
        """
        try:
            request = {"parent": self.parent}
            if filter_str:
                request["filter"] = filter_str
            
            secrets = []
            for secret in self.client.list_secrets(request=request):
                secrets.append(secret.name.split("/")[-1])
            
            return secrets
            
        except Exception as e:
            logger.error(f"Error listing secrets: {e}")
            raise
    
    def update_secret_labels(self, secret_id: str, labels: Dict[str, str]) -> bool:
        """
        Update labels on a secret
        
        Args:
            secret_id: The secret identifier
            labels: Dictionary of labels to apply
        
        Returns:
            True if updated successfully
        """
        try:
            name = f"{self.parent}/secrets/{secret_id}"
            
            # Get current secret
            secret = self.client.get_secret(request={"name": name})
            
            # Update labels
            secret.labels.clear()
            secret.labels.update(labels)
            
            # Update the secret
            update_mask = {"paths": ["labels"]}
            self.client.update_secret(
                request={
                    "secret": secret,
                    "update_mask": update_mask,
                }
            )
            
            logger.info(f"Updated labels for secret: {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating secret labels for {secret_id}: {e}")
            raise
    
    def store_api_keys(self, client_id: str, api_keys: Dict[str, str]) -> Dict[str, str]:
        """
        Store multiple API keys for a client
        
        Args:
            client_id: The client identifier
            api_keys: Dictionary of API keys (provider -> key)
        
        Returns:
            Dictionary of secret IDs (provider -> secret_id)
        """
        secret_ids = {}
        
        for provider, api_key in api_keys.items():
            if api_key:
                secret_id = f"mcp-{client_id}-{provider}-key"
                labels = {
                    "client_id": client_id,
                    "provider": provider,
                    "type": "api_key"
                }
                self.create_secret(secret_id, api_key, labels)
                secret_ids[f"{provider}_api_key_secret_id"] = secret_id
        
        return secret_ids
    
    def get_api_keys(self, client_id: str) -> Dict[str, Optional[str]]:
        """
        Retrieve all API keys for a client
        
        Args:
            client_id: The client identifier
        
        Returns:
            Dictionary of API keys (provider -> key)
        """
        providers = ["klaviyo", "openai", "gemini"]
        api_keys = {}
        
        for provider in providers:
            secret_id = f"mcp-{client_id}-{provider}-key"
            api_keys[provider] = self.get_secret(secret_id)
        
        return api_keys


# Singleton instance
_secret_manager = None

def get_secret_manager() -> SecretManagerService:
    """Get singleton instance of SecretManagerService"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManagerService()
    return _secret_manager