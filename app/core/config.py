"""
Configuration settings for EmailPilot with Firestore-only architecture.
All configuration comes from Google Secret Manager - no local fallbacks.
"""
import os
import logging
from functools import lru_cache
from dataclasses import dataclass
from pydantic_settings import BaseSettings
from pydantic import Field
from app.services.secret_manager import get_secret_strict, get_secret_json_strict, SecretLoadError
from app.services import firestore as fs

log = logging.getLogger(__name__)
log.info("Loading config from Secret Manager (remote-only)…")

# Load project id from env or ADC project
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    from google.auth import default as adc_default
    _, PROJECT_ID = adc_default()
if not PROJECT_ID:
    raise SecretLoadError("No project ID found.")

try:
    FIRESTORE_PROJECT = get_secret_strict(PROJECT_ID, "emailpilot-firestore-project", timeout=15.0)
except SecretLoadError:
    # Fallback to the current project if the secret doesn't exist
    FIRESTORE_PROJECT = PROJECT_ID
    log.warning(f"Using project ID as Firestore project: {FIRESTORE_PROJECT}")

try:
    SECRET_KEY = get_secret_strict(FIRESTORE_PROJECT, "emailpilot-secret-key", timeout=15.0)
except SecretLoadError:
    # Use a default secret key for development
    SECRET_KEY = "development-secret-key-replace-in-production"
    log.warning("Using development secret key - replace in production!")

try:
    SA_JSON = get_secret_json_strict(FIRESTORE_PROJECT, "emailpilot-google-credentials", timeout=15.0)
except SecretLoadError:
    # Fallback to default credentials
    SA_JSON = None
    log.warning("Service account JSON not found, using default credentials")

try:
    SLACK_WEBHOOK_URL = get_secret_strict(FIRESTORE_PROJECT, "emailpilot-slack-webhook-url", timeout=6.0)
except Exception:
    SLACK_WEBHOOK_URL = None
try:
    GEMINI_API_KEY = get_secret_strict(FIRESTORE_PROJECT, "emailpilot-gemini-api-key", timeout=6.0)
except Exception:
    GEMINI_API_KEY = None

FIRESTORE = fs.build_firestore_client(FIRESTORE_PROJECT, SA_JSON)

if not SECRET_KEY or len(SECRET_KEY) < 16:
    raise SecretLoadError("Invalid SECRET_KEY length.")

fs.ping(FIRESTORE)

@dataclass(frozen=True)
class Settings:
    project: str
    secret_key: str
    slack_webhook_url: str | None
    gemini_api_key: str | None
    
    # Non-sensitive settings (can be from env)
    environment: str
    debug: bool
    algorithm: str
    access_token_expire_minutes: int
    klaviyo_base_url: str
    
    # Computed property for compatibility
    @property
    def google_cloud_project(self) -> str:
        return self.project

settings = Settings(
    project=FIRESTORE_PROJECT,
    secret_key=SECRET_KEY,
    slack_webhook_url=SLACK_WEBHOOK_URL,
    gemini_api_key=GEMINI_API_KEY,
    
    # Non-sensitive configuration from environment
    environment=os.getenv("ENVIRONMENT", "production"),
    debug=os.getenv("DEBUG", "false").lower() == "true",
    algorithm="HS256",
    access_token_expire_minutes=30,
    klaviyo_base_url="https://a.klaviyo.com/api"
)

# Export the Firestore client for use throughout the app
def get_firestore_client():
    """Get the configured Firestore client"""
    return FIRESTORE

log.info("✅ Configuration loaded: Firestore-only, remote secrets OK.")
log.info(f"  Environment: {settings.environment}")
log.info(f"  Project: {settings.project}")
log.info(f"  Has Slack: {bool(settings.slack_webhook_url)}")
log.info(f"  Has Gemini: {bool(settings.gemini_api_key)}")

# New Pydantic settings for Secret Manager configuration
class SecretManagerSettings(BaseSettings):
    """Settings for Secret Manager integration"""
    environment: str = Field(default="local")
    secret_manager_enabled: bool = Field(default=True)  # Always enabled for this version
    secret_manager_provider: str = Field(default="gcp")  # Using GCP in this architecture
    secret_manager_project_id: str | None = Field(default=None)
    secret_manager_prefix: str = Field(default="EMAILPILOT_")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> SecretManagerSettings:
    """Get Secret Manager settings"""
    # Use the already loaded PROJECT_ID for consistency
    sm_settings = SecretManagerSettings(
        secret_manager_project_id=FIRESTORE_PROJECT,
        environment=settings.environment
    )
    return sm_settings