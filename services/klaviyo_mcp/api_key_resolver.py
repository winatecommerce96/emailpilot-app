"""
API Key Resolver for Klaviyo MCP Service

Resolves Klaviyo API keys from Firestore client configuration and Secret Manager.
Supports multiple storage patterns for backward compatibility.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from google.cloud import firestore
from google.cloud import secretmanager
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

class APIKeyResolver:
    """Resolves Klaviyo API keys from various sources with Firestore and Secret Manager integration."""
    
    def __init__(self, project_id: str):
        """
        Initialize the API Key Resolver.
        
        Args:
            project_id: Google Cloud Project ID
        """
        self.project_id = project_id
        self.firestore_client = firestore.Client(project=project_id)
        self.secret_client = secretmanager.SecretManagerServiceClient()
        self._cache = {}  # Simple cache for resolved keys
        
    def resolve_api_key(self, client_id: str) -> str:
        """
        Resolve Klaviyo API key for a specific client.
        
        Resolution priority:
        1. Check cache
        2. Load client config from Firestore
        3. Try klaviyo_api_key_secret (Secret Manager reference)
        4. Try convention-based secret name: klaviyo-api-{client_slug}
        5. Try api_key_encrypted (base64 or secret name)
        6. Fallback to klaviyo_api_key field (dev only)
        
        Args:
            client_id: Client document ID or slug
            
        Returns:
            Klaviyo API key
            
        Raises:
            ValueError: If no API key can be resolved
        """
        # Check cache first
        if client_id in self._cache:
            logger.debug(f"Using cached API key for client: {client_id}")
            return self._cache[client_id]
            
        # Load client configuration from Firestore
        client_config = self._get_client_config(client_id)
        if not client_config:
            raise ValueError(f"Client not found: {client_id}")
            
        # Try resolution strategies in order
        api_key = None
        
        # Strategy 1: klaviyo_api_key_secret field (Secret Manager reference)
        secret_ref = client_config.get("klaviyo_api_key_secret")
        if secret_ref:
            api_key = self._resolve_from_secret_manager(secret_ref)
            if api_key:
                logger.info(f"Resolved API key from klaviyo_api_key_secret for client: {client_id}")
                
        # Strategy 2: Convention-based secret name
        if not api_key:
            client_slug = client_config.get("client_slug")
            if client_slug:
                convention_name = f"klaviyo-api-{client_slug}"
                api_key = self._resolve_from_secret_manager(convention_name)
                if api_key:
                    logger.info(f"Resolved API key from convention ({convention_name}) for client: {client_id}")
                    
        # Strategy 3: api_key_encrypted field (base64 or secret name)
        if not api_key:
            encrypted_ref = client_config.get("api_key_encrypted")
            if encrypted_ref:
                # Try as base64 first
                api_key = self._try_base64_decode(encrypted_ref)
                if api_key and api_key.startswith("pk_"):
                    logger.info(f"Resolved API key from base64 for client: {client_id}")
                else:
                    # Try as secret name
                    api_key = self._resolve_from_secret_manager(encrypted_ref)
                    if api_key:
                        logger.info(f"Resolved API key from api_key_encrypted secret for client: {client_id}")
                        
        # Strategy 4: Direct klaviyo_api_key field (development fallback)
        if not api_key:
            api_key = client_config.get("klaviyo_api_key")
            if api_key:
                logger.warning(f"Using plaintext API key for client: {client_id} (development mode)")
                
        if not api_key:
            raise ValueError(f"Unable to resolve Klaviyo API key for client: {client_id}")
            
        # Cache the resolved key
        self._cache[client_id] = api_key.strip()
        return self._cache[client_id]
        
    def clear_cache(self, client_id: Optional[str] = None):
        """
        Clear cached API keys.
        
        Args:
            client_id: Specific client to clear, or None to clear all
        """
        if client_id:
            self._cache.pop(client_id, None)
            logger.info(f"Cleared cached API key for client: {client_id}")
        else:
            self._cache.clear()
            logger.info("Cleared all cached API keys")
            
    def _get_client_config(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Load client configuration from Firestore.
        
        Args:
            client_id: Client document ID or slug
            
        Returns:
            Client configuration dict or None if not found
        """
        try:
            # Try direct document ID first
            doc_ref = self.firestore_client.collection("clients").document(client_id)
            doc = doc_ref.get()
            
            if doc.exists:
                config = doc.to_dict()
                config["_doc_id"] = client_id
                return config
                
            # Try searching by slug
            query = self.firestore_client.collection("clients").where(
                "client_slug", "==", client_id
            ).limit(1)
            
            for doc in query.stream():
                config = doc.to_dict()
                config["_doc_id"] = doc.id
                return config
                
            logger.warning(f"Client not found in Firestore: {client_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading client config from Firestore: {e}")
            return None
            
    def _resolve_from_secret_manager(self, secret_ref: str) -> Optional[str]:
        """
        Resolve a secret from Google Secret Manager.
        
        Args:
            secret_ref: Secret name or full resource path
            
        Returns:
            Secret value or None if not found
        """
        try:
            # Handle full resource path
            if secret_ref.startswith("projects/"):
                name = secret_ref
            else:
                # Build resource path from secret name
                name = f"projects/{self.project_id}/secrets/{secret_ref}/versions/latest"
                
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("utf-8")
            
        except google_exceptions.NotFound:
            logger.debug(f"Secret not found: {secret_ref}")
            return None
        except google_exceptions.PermissionDenied:
            logger.error(f"Permission denied accessing secret: {secret_ref}")
            return None
        except Exception as e:
            logger.error(f"Error accessing secret {secret_ref}: {e}")
            return None
            
    def _try_base64_decode(self, value: str) -> Optional[str]:
        """
        Try to decode a base64 encoded value.
        
        Args:
            value: Potentially base64 encoded string
            
        Returns:
            Decoded value or None if not valid base64
        """
        try:
            decoded = base64.b64decode(value).decode("utf-8")
            # Basic validation - Klaviyo keys start with pk_
            if decoded.startswith("pk_"):
                return decoded
            return None
        except Exception:
            return None
            
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate a Klaviyo API key by making a test request.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        import httpx
        
        try:
            # Test the key with a simple metrics list request
            headers = {
                "Authorization": f"Klaviyo-API-Key {api_key}",
                "accept": "application/json",
                "revision": "2024-06-15"
            }
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://a.klaviyo.com/api/metrics/?page[size]=1",
                    headers=headers
                )
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False