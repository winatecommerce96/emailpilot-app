"""
Refactored Google Secret Manager service.
"""
import os
import json
import logging
from functools import lru_cache
from google.api_core import retry as g_retry
from google.api_core import exceptions as g_ex
from google.cloud import secretmanager_v1

import re

log = logging.getLogger(__name__)

SENSITIVE_RE = r"(?i)(secret|token|password|key|private|credential)"

def mask_sensitive(key: str, value: str) -> str:
    """Mask sensitive values based on key pattern"""
    if re.search(SENSITIVE_RE, key):
        return "••••••••"
    return value

TRANSPORT = os.getenv("SECRET_MANAGER_TRANSPORT", "rest").lower()

class SecretError(Exception):
    """Base exception for secret-related errors."""
    pass

class SecretNotFoundError(SecretError):
    """Raised when a secret is not found."""
    pass

class SecretPermissionError(SecretError):
    """Raised when there are insufficient permissions to access a secret."""
    pass

class SecretManagerService:
    def __init__(self, project_id: str):
        if not project_id:
            raise ValueError("GCP project ID is required.")
        self.project_id = project_id
        self.client = self._get_client()
        self._key_cache = {}  # Cache for API keys

    @lru_cache(maxsize=1)
    def _get_client(self):
        if TRANSPORT not in ("rest", "grpc"):
            raise ValueError(f"Invalid transport: {TRANSPORT}")
        return secretmanager_v1.SecretManagerServiceClient(transport=TRANSPORT)

    def get_secret(self, secret_id: str, version: str = "latest") -> str:
        """Fetches a secret from Google Secret Manager."""
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
        try:
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except g_ex.NotFound:
            raise SecretNotFoundError(f"Secret not found: {name}")
        except g_ex.PermissionDenied:
            raise SecretPermissionError(f"Permission denied for secret: {name}")
        except Exception as e:
            log.error(f"Failed to get secret {secret_id}: {e}")
            raise SecretError(f"Failed to get secret {secret_id}") from e

    def get_secret_json(self, secret_id: str, version: str = "latest") -> dict:
        """Fetches and parses a JSON secret."""
        try:
            secret_str = self.get_secret(secret_id, version)
            return json.loads(secret_str)
        except json.JSONDecodeError as e:
            raise SecretError(f"Failed to decode JSON for secret {secret_id}: {e}") from e

    def list_secrets(self) -> list[str]:
        """Lists all secrets in the project."""
        try:
            secrets = self.client.list_secrets(request={"parent": f"projects/{self.project_id}"})
            return [secret.name.split("/")[-1] for secret in secrets]
        except Exception as e:
            log.error(f"Failed to list secrets: {e}")
            raise SecretError("Failed to list secrets") from e

    def delete_secret(self, secret_id: str):
        """Deletes a secret from Google Secret Manager."""
        name = f"projects/{self.project_id}/secrets/{secret_id}"
        try:
            self.client.delete_secret(request={"name": name})
        except g_ex.NotFound:
            # If the secret is already deleted, that's fine.
            pass
        except g_ex.PermissionDenied:
            raise SecretPermissionError(f"Permission denied for secret: {name}")
        except Exception as e:
            log.error(f"Failed to delete secret {secret_id}: {e}")
            raise SecretError(f"Failed to delete secret {secret_id}") from e

    def create_secret(self, secret_id: str, secret_value: str, labels: dict = None):
        """Creates a new secret or adds a new version to an existing secret."""
        secret_already_exists = False
        
        try:
            # Try to create the secret first
            self.client.create_secret(
                request={
                    "parent": f"projects/{self.project_id}",
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}, "labels": labels or {}},
                }
            )
            log.info(f"Created new secret: {secret_id}")
        except Exception as e:
            # Check if it's an "already exists" error by looking at the error message
            if "already exists" in str(e).lower() or "409" in str(e):
                secret_already_exists = True
                log.info(f"Secret {secret_id} already exists, will add new version")
            else:
                log.error(f"Failed to create secret {secret_id}: {e}")
                raise SecretError(f"Failed to create secret {secret_id}") from e
        
        # Add the secret version (this works for both new and existing secrets)
        try:
            self.client.add_secret_version(
                request={
                    "parent": f"projects/{self.project_id}/secrets/{secret_id}",
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )
            if secret_already_exists:
                log.info(f"Updated existing secret: {secret_id}")
            else:
                log.info(f"Added initial version to new secret: {secret_id}")
        except Exception as e:
            log.error(f"Failed to add version to secret {secret_id}: {e}")
            raise SecretError(f"Failed to add version to secret {secret_id}") from e

    # Convenience alias
    def create_or_update_secret(self, secret_id: str, secret_value: str, labels: dict = None):
        """Create a secret or update by adding a new version (idempotent)."""
        return self.create_secret(secret_id, secret_value, labels=labels or {})

    def list_account_vars(self, prefix: str) -> dict[str, str]:
        """Lists all account-level variables with the configured prefix"""
        all_secrets = self.list_secrets()
        account_vars = {}
        for secret_id in all_secrets:
            if secret_id.startswith(prefix):
                try:
                    account_vars[secret_id] = self.get_secret(secret_id)
                except SecretNotFoundError:
                    # This can happen if the secret is deleted between list and get
                    pass
        return account_vars

    def put_account_var(self, key: str, value: str):
        """Creates or updates an account-level variable in Secret Manager."""
        self.create_secret(key, value, labels={"app": "emailpilot", "type": "account", "managed_by": "admin"})

    # AI Provider API Key Management
    AI_PROVIDER_SECRETS = {
        "OPENAI_API_KEY": "openai-api-key",
        "ANTHROPIC_API_KEY": "emailpilot-claude", 
        "GOOGLE_API_KEY": "gemini-api-key",
        "GOOGLE_GENAI_API_KEY": "gemini-api-key"  # Alias for Google API key
    }

    def get_ai_provider_key(self, key_name: str) -> str:
        """Get an AI provider API key from Secret Manager with fallback to environment variables.
        
        Args:
            key_name: The standard key name (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
            
        Returns:
            The API key if found, None otherwise
            
        Raises:
            SecretError: If there's an issue accessing secrets
        """
        import os
        
        # Check cache first
        cache_key = f"ai_provider_{key_name}"
        if cache_key in self._key_cache:
            log.debug(f"Using cached key for {key_name}")
            return self._key_cache[cache_key]
        
        # Check if we have a mapping for this key
        if key_name not in self.AI_PROVIDER_SECRETS:
            log.warning(f"Unknown AI provider key: {key_name}")
            # Fallback to environment variable
            env_value = os.getenv(key_name)
            if env_value:
                log.info(f"Using environment variable for {key_name}")
                self._key_cache[cache_key] = env_value
                return env_value
            return None
        
        secret_name = self.AI_PROVIDER_SECRETS[key_name]
        
        try:
            # Try to get from Secret Manager
            key_value = self.get_secret(secret_name)
            if key_value:
                log.info(f"Retrieved {key_name} from Secret Manager")
                self._key_cache[cache_key] = key_value
                return key_value
        except SecretNotFoundError:
            log.info(f"Secret {secret_name} not found in Secret Manager for {key_name}")
        except (SecretPermissionError, SecretError) as e:
            log.warning(f"Failed to access {secret_name} in Secret Manager: {e}")
        
        # Fallback to environment variable
        env_value = os.getenv(key_name)
        if env_value:
            log.info(f"Using environment variable fallback for {key_name}")
            self._key_cache[cache_key] = env_value
            return env_value
        
        log.warning(f"No API key found for {key_name} in Secret Manager or environment variables")
        return None

    def set_ai_provider_key(self, key_name: str, key_value: str) -> bool:
        """Set an AI provider API key in Secret Manager.
        
        Args:
            key_name: The standard key name (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
            key_value: The API key value
            
        Returns:
            True if successful, False otherwise
        """
        if key_name not in self.AI_PROVIDER_SECRETS:
            log.error(f"Unknown AI provider key: {key_name}")
            return False
        
        secret_name = self.AI_PROVIDER_SECRETS[key_name]
        
        try:
            self.create_or_update_secret(
                secret_name, 
                key_value, 
                labels={"app": "emailpilot", "type": "ai_provider", "provider": key_name.lower().replace("_api_key", "")}
            )
            
            # Clear cache to force reload
            cache_key = f"ai_provider_{key_name}"
            if cache_key in self._key_cache:
                del self._key_cache[cache_key]
            
            log.info(f"Successfully stored {key_name} in Secret Manager")
            return True
        except SecretError as e:
            log.error(f"Failed to store {key_name} in Secret Manager: {e}")
            return False

    def validate_ai_provider_key(self, key_name: str) -> dict:
        """Validate an AI provider API key format and accessibility.
        
        Args:
            key_name: The standard key name (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
            
        Returns:
            Dict with validation results: {valid: bool, message: str, hint: str}
        """
        try:
            key_value = self.get_ai_provider_key(key_name)
            
            if not key_value:
                return {
                    "valid": False,
                    "message": f"API key {key_name} not found",
                    "hint": f"Add {key_name} to Secret Manager or set as environment variable"
                }
            
            # Basic format validation
            if len(key_value.strip()) < 10:
                return {
                    "valid": False,
                    "message": f"API key {key_name} appears too short",
                    "hint": "API keys should be at least 10 characters long"
                }
            
            # Provider-specific validation
            if key_name == "OPENAI_API_KEY":
                if not key_value.startswith("sk-"):
                    return {
                        "valid": False,
                        "message": "OpenAI API key should start with 'sk-'",
                        "hint": "Check the OpenAI API key format"
                    }
            elif key_name == "ANTHROPIC_API_KEY":
                if not key_value.startswith("sk-ant-"):
                    return {
                        "valid": False,
                        "message": "Anthropic API key should start with 'sk-ant-'",
                        "hint": "Check the Anthropic API key format"
                    }
            elif key_name in ("GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
                if len(key_value.strip()) < 20:
                    return {
                        "valid": False,
                        "message": "Google API key appears too short",
                        "hint": "Google API keys are typically longer than 20 characters"
                    }
            
            return {
                "valid": True,
                "message": f"API key {key_name} format looks valid",
                "hint": "Key format validation passed"
            }
            
        except Exception as e:
            log.error(f"Error validating {key_name}: {e}")
            return {
                "valid": False,
                "message": f"Error validating {key_name}: {str(e)}",
                "hint": "Check Secret Manager access and permissions"
            }
