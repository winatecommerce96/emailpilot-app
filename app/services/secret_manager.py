"""
Google Secret Manager service with strict remote-only access.
No local fallbacks - fails fast with actionable errors.
Supports project-aware secret loading and JSON secrets.
"""
import os
import json
import logging
from functools import lru_cache
from google.api_core import retry as g_retry
from google.api_core import exceptions as g_ex
from google.cloud import secretmanager_v1

log = logging.getLogger(__name__)

# Allow choosing transport; default to REST in dev to dodge SRV DNS
TRANSPORT = os.getenv("SECRET_MANAGER_TRANSPORT", "rest").lower()

class SecretLoadError(RuntimeError):
    """Raised when secret loading fails - no fallback allowed"""
    pass

@lru_cache(maxsize=1)
def _client():
    """Create Secret Manager client with configurable transport"""
    if TRANSPORT not in ("rest", "grpc"):
        raise SecretLoadError(f"Invalid transport: {TRANSPORT}")
    return secretmanager_v1.SecretManagerServiceClient(transport=TRANSPORT)


def get_secret_strict(project_id: str, secret_id: str, *, timeout: float = 10.0, max_attempts: int = 3) -> str:
    """
    Fetch secret (latest version) or raise SecretLoadError. No local fallback.
    
    Args:
        project_id: GCP project ID where secret is stored
        secret_id: The secret identifier (e.g., "emailpilot-secret-key")
        timeout: Timeout per attempt in seconds
        max_attempts: Number of retry attempts
        
    Returns:
        The secret value as a string
        
    Raises:
        SecretLoadError: If secret cannot be loaded (no fallback)
    """
    if not project_id:
        raise SecretLoadError("Project ID is required.")
    
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    
    # Retry transient failures but still fail fast
    retry = g_retry.Retry(
        predicate=g_retry.if_exception_type(
            g_ex.ServiceUnavailable, 
            g_ex.DeadlineExceeded, 
            g_ex.InternalServerError
        ),
        deadline=timeout * max_attempts
    )
    
    try:
        resp = retry(_client().access_secret_version)(request={"name": name}, timeout=timeout)
        return resp.payload.data.decode("utf-8")
    except Exception as e:
        msg = f"Failed to load Secret '{secret_id}' from project '{project_id}': {e}"
        log.error(msg)
        raise SecretLoadError(msg) from e


def get_secret_json_strict(project_id: str, secret_id: str, **kwargs) -> dict:
    """Fetch a JSON secret and parse it."""
    return json.loads(get_secret_strict(project_id, secret_id, **kwargs))


# Compatibility layer for existing admin code
class SecretManagerService:
    """Compatibility wrapper for the old service class API"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
    
    def get_secret(self, secret_id: str) -> str | None:
        """Get secret with fallback to None (old API compatibility)"""
        try:
            return get_secret_strict(self.project_id, secret_id)
        except SecretLoadError:
            return None
    
    def create_or_update_secret(self, secret_id: str, secret_value: str, labels: dict = None):
        """Create or update a secret in Secret Manager"""
        client = _client()
        parent = f"projects/{self.project_id}"
        secret_path = f"{parent}/secrets/{secret_id}"
        
        # Check if secret exists
        try:
            client.get_secret(request={"name": secret_path})
            secret_exists = True
        except Exception:
            secret_exists = False
        
        # Create secret if it doesn't exist
        if not secret_exists:
            try:
                secret = {
                    "replication": {"automatic": {}}
                }
                if labels:
                    secret["labels"] = labels
                    
                client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": secret
                    }
                )
            except Exception as e:
                log.error(f"Failed to create secret {secret_id}: {e}")
                raise
        
        # Add new version
        try:
            client.add_secret_version(
                request={
                    "parent": secret_path,
                    "payload": {"data": secret_value.encode("utf-8")}
                }
            )
        except Exception as e:
            log.error(f"Failed to add secret version for {secret_id}: {e}")
            raise
    
    def create_secret(self, secret_id: str, secret_value: str, **kwargs):
        """Create or update a secret (backward compatibility)"""
        return self.create_or_update_secret(secret_id, secret_value, kwargs.get("labels"))
    
    def list_secrets(self, filter_str: str = None):
        """List secrets in the project"""
        client = _client()
        parent = f"projects/{self.project_id}"
        
        try:
            request = {"parent": parent}
            if filter_str:
                request["filter"] = filter_str
            
            response = client.list_secrets(request=request)
            return [secret.name.split("/")[-1] for secret in response]
        except Exception as e:
            log.error(f"Failed to list secrets: {e}")
            return []


_secret_manager = None

def get_secret_manager() -> SecretManagerService:
    """Get singleton instance of SecretManagerService (compatibility)"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManagerService()
    return _secret_manager


# Enhanced SecretManagerService for account-level variables
import re
SENSITIVE_RE = r"(?i)(secret|token|password|key|private|credential)"

class EnhancedSecretManagerService:
    """Enhanced Secret Manager service supporting multiple providers and account-level variables"""
    
    def __init__(self):
        from app.core.config import get_settings
        self.settings = get_settings()
        self.provider = self.settings.secret_manager_provider
        self.project_id = self.settings.secret_manager_project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.prefix = self.settings.secret_manager_prefix
    
    def list_account_vars(self) -> dict[str, str]:
        """List all account-level variables with the configured prefix"""
        if not self.settings.secret_manager_enabled or self.provider == "local":
            # Fallback to process env filtered by prefix
            return {k: v for k, v in os.environ.items() if k.startswith(self.prefix)}
        
        if self.provider == "gcp":
            return self._list_gcp()
        
        # Other providers would go here (aws, azure)
        return {}
    
    def get_account_var(self, key: str) -> str | None:
        """Get a specific account-level variable"""
        if not key.startswith(self.prefix):
            return None
            
        if not self.settings.secret_manager_enabled or self.provider == "local":
            return os.environ.get(key)
        
        if self.provider == "gcp":
            return self._get_gcp(key)
        
        return None
    
    def put_account_var(self, key: str, value: str) -> None:
        """Set an account-level variable"""
        if not key.startswith(self.prefix):
            raise ValueError(f"Key must start with prefix {self.prefix}")
        
        if not self.settings.secret_manager_enabled or self.provider == "local":
            os.environ[key] = value  # dev-only; not persisted
            return
        
        if self.provider == "gcp":
            self._put_gcp(key, value)
    
    def _list_gcp(self) -> dict[str, str]:
        """List GCP secrets with prefix"""
        result = {}
        try:
            client = _client()
            parent = f"projects/{self.project_id}"
            
            # List all secrets
            response = client.list_secrets(request={"parent": parent})
            
            for secret in response:
                name = secret.name.split("/")[-1]
                if not name.startswith(self.prefix):
                    continue
                
                # Get latest version
                try:
                    ver_path = f"{secret.name}/versions/latest"
                    payload = client.access_secret_version(
                        request={"name": ver_path}
                    ).payload.data.decode("utf-8")
                    result[name] = payload
                except Exception as e:
                    log.warning(f"Could not read secret {name}: {e}")
                    result[name] = ""
            
        except Exception as e:
            log.error(f"Failed to list GCP secrets: {e}")
        
        return result
    
    def _get_gcp(self, key: str) -> str | None:
        """Get a specific GCP secret"""
        try:
            return get_secret_strict(self.project_id, key)
        except Exception:
            return None
    
    def _put_gcp(self, key: str, value: str) -> None:
        """Create or update a GCP secret"""
        sm = SecretManagerService(self.project_id)
        sm.create_or_update_secret(
            secret_id=key,
            secret_value=value,
            labels={"app": "emailpilot", "type": "account", "managed_by": "admin"}
        )
    
    @staticmethod
    def mask_sensitive(key: str, value: str) -> str:
        """Mask sensitive values based on key pattern"""
        if re.search(SENSITIVE_RE, key):
            return "••••••••"
        return value