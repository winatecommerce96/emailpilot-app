"""
Refactored configuration settings for EmailPilot.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    google_cloud_project: str = Field(..., env="GOOGLE_CLOUD_PROJECT")
    environment: str = Field("production", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    secret_key: str
    app_base_url: str = Field("http://localhost:8000", env="APP_BASE_URL")
    slack_webhook_url: str | None = None
    gemini_api_key: str | None = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200  # 30 days
    klaviyo_base_url: str = "https://a.klaviyo.com/api"
    secret_manager_enabled: bool = Field(True, env="SECRET_MANAGER_ENABLED")
    secret_manager_prefix: str = Field("EMAILPILOT_", env="SECRET_MANAGER_PREFIX")

    # Asana OAuth
    asana_client_id: str | None = None
    asana_client_secret: str | None = None
    asana_redirect_uri: str = "http://localhost:8000/api/integrations/asana/callback"

    # Klaviyo OAuth
    klaviyo_oauth_client_id: str | None = None
    klaviyo_oauth_client_secret: str | None = None
    klaviyo_oauth_redirect_uri: str = "http://localhost:8000/api/integrations/klaviyo/oauth/callback"
    klaviyo_oauth_scopes: str = "accounts:read,campaigns:read,flows:read,lists:read,metrics:read,profiles:read,segments:read"
    
    # Legacy Klaviyo OAuth (for backward compatibility)
    klaviyo_client_id: str | None = None
    klaviyo_client_secret: str | None = None
    klaviyo_redirect_uri: str = "http://localhost:8000/api/integrations/klaviyo/callback"

    # Google OAuth
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    class Config:
        env_file = ".env"
        extra = "ignore"

def get_settings() -> Settings:
    from app.services.secrets import SecretManagerService, SecretNotFoundError

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT environment variable not set.")

    secret_manager = SecretManagerService(project_id=project_id)

    try:
        secret_key = secret_manager.get_secret("emailpilot-secret-key")
    except SecretNotFoundError:
        secret_key = "development-secret-key-replace-in-production"

    try:
        slack_webhook_url = secret_manager.get_secret("emailpilot-slack-webhook-url")
    except SecretNotFoundError:
        slack_webhook_url = None

    try:
        gemini_api_key = secret_manager.get_secret("emailpilot-gemini-api-key")
    except SecretNotFoundError:
        gemini_api_key = None

    try:
        asana_client_id = secret_manager.get_secret("asana-client-id")
    except SecretNotFoundError:
        asana_client_id = None
    
    try:
        asana_client_secret = secret_manager.get_secret("asana-client-secret")
    except SecretNotFoundError:
        asana_client_secret = None

    try:
        klaviyo_client_id = secret_manager.get_secret("klaviyo-client-id")
    except SecretNotFoundError:
        klaviyo_client_id = None

    try:
        klaviyo_client_secret = secret_manager.get_secret("klaviyo-client-secret")
    except SecretNotFoundError:
        klaviyo_client_secret = None

    # Load Klaviyo OAuth credentials (try both naming conventions)
    try:
        klaviyo_oauth_client_id = secret_manager.get_secret("klaviyo-oauth-client-id")
    except SecretNotFoundError:
        # Fall back to the non-OAuth version if OAuth-specific doesn't exist
        klaviyo_oauth_client_id = klaviyo_client_id

    try:
        klaviyo_oauth_client_secret = secret_manager.get_secret("klaviyo-oauth-client-secret")
    except SecretNotFoundError:
        # Fall back to the non-OAuth version if OAuth-specific doesn't exist
        klaviyo_oauth_client_secret = klaviyo_client_secret

    try:
        google_oauth_client_id = secret_manager.get_secret("google-oauth-client-id")
    except SecretNotFoundError:
        google_oauth_client_id = None
    
    try:
        google_oauth_client_secret = secret_manager.get_secret("google-oauth-client-secret")
    except SecretNotFoundError:
        google_oauth_client_secret = None

    try:
        google_oauth_redirect_uri = secret_manager.get_secret("google-oauth-redirect-uri")
    except SecretNotFoundError:
        google_oauth_redirect_uri = "http://localhost:8000/api/auth/google/callback"


    return Settings(
        google_cloud_project=project_id,
        secret_key=secret_key,
        slack_webhook_url=slack_webhook_url,
        gemini_api_key=gemini_api_key,
        asana_client_id=asana_client_id,
        asana_client_secret=asana_client_secret,
        klaviyo_client_id=klaviyo_client_id,
        klaviyo_client_secret=klaviyo_client_secret,
        klaviyo_oauth_client_id=klaviyo_oauth_client_id,
        klaviyo_oauth_client_secret=klaviyo_oauth_client_secret,
        google_oauth_client_id=google_oauth_client_id,
        google_oauth_client_secret=google_oauth_client_secret,
        google_oauth_redirect_uri=google_oauth_redirect_uri,
    )
