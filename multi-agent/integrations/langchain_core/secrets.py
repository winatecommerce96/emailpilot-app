"""
Secret Manager integration for API keys.

Fetches API keys from Google Secret Manager instead of environment variables.
"""

import logging
import os
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=10)
def get_secret(secret_name: str, project_id: Optional[str] = None) -> Optional[str]:
    """
    Fetch a secret from Google Secret Manager.
    
    Args:
        secret_name: Name of the secret
        project_id: GCP project ID (uses GOOGLE_CLOUD_PROJECT if not provided)
    
    Returns:
        Secret value or None if not found
    """
    try:
        # Use subprocess to call gcloud directly - more reliable than REST transport
        import subprocess
        
        if not project_id:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        
        # Call gcloud directly
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest", 
             f"--secret={secret_name}", f"--project={project_id}"],
            capture_output=True,
            text=True,
            timeout=5  # 5 second timeout
        )
        
        if result.returncode == 0:
            secret_value = result.stdout.strip()
            logger.info(f"Successfully fetched secret: {secret_name}")
            return secret_value
        else:
            logger.warning(f"Failed to fetch secret {secret_name}: {result.stderr}")
            return None
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout fetching secret {secret_name}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch secret {secret_name}: {e}")
        return None


def get_api_key(provider: str) -> Optional[str]:
    """
    Get API key for a specific provider from Secret Manager.
    
    Args:
        provider: Provider name (openai, anthropic, gemini)
    
    Returns:
        API key or None if not found
    """
    # Check if we should use Secret Manager
    use_secret_manager = os.getenv("USE_SECRET_MANAGER", "true").lower() == "true"
    
    if not use_secret_manager:
        # Fall back to environment variables
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif provider in ["gemini", "google"]:
            return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        return None
    
    # Get secret names from environment or use defaults
    secret_names = {
        "openai": os.getenv("OPENAI_SECRET_NAME", "openai-api-key"),
        "anthropic": os.getenv("ANTHROPIC_SECRET_NAME", "emailpilot-claude"),
        "gemini": os.getenv("GEMINI_SECRET_NAME", "emailpilot-gemini-api-key"),
        "google": os.getenv("GEMINI_SECRET_NAME", "emailpilot-gemini-api-key")
    }
    
    secret_name = secret_names.get(provider)
    if not secret_name:
        logger.warning(f"Unknown provider: {provider}")
        return None
    
    return get_secret(secret_name)


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from Secret Manager."""
    return get_api_key("openai")


def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key from Secret Manager."""
    return get_api_key("anthropic")


def get_google_api_key() -> Optional[str]:
    """Get Google/Gemini API key from Secret Manager."""
    return get_api_key("gemini")


def clear_cache():
    """Clear the secret cache (useful for key rotation)."""
    get_secret.cache_clear()
    logger.info("Secret cache cleared")