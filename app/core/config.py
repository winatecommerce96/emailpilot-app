"""
Configuration settings for EmailPilot with Secret Manager integration
"""

import os
import logging
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with Secret Manager integration.
    Prioritizes Secret Manager over environment variables when enabled.
    """
    
    # Secret Manager Configuration (always from env)
    secret_manager_enabled: bool = os.getenv("SECRET_MANAGER_ENABLED", "true").lower() == "true"
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
    
    # Non-sensitive configuration (can stay in env)
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    klaviyo_base_url: str = "https://a.klaviyo.com/api"
    
    # Sensitive configuration (will come from Secret Manager when enabled)
    database_url: str = ""
    secret_key: str = ""
    klaviyo_api_key: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    gemini_api_key: Optional[str] = None
    google_application_credentials: Optional[str] = None
    
    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }
    
    def __init__(self, **kwargs):
        """Initialize settings with Secret Manager integration"""
        super().__init__(**kwargs)
        
        # Load sensitive values from Secret Manager if enabled
        if self.secret_manager_enabled:
            self._load_from_secret_manager()
        else:
            # Fall back to environment variables
            self._load_from_environment()
    
    def _load_from_secret_manager(self):
        """Load sensitive configuration from Google Secret Manager"""
        try:
            from app.services.secret_manager import get_secret_manager
            
            secret_manager = get_secret_manager()
            logger.info("Loading configuration from Secret Manager")
            
            # Map of setting name to secret ID
            secret_mappings = {
                "database_url": "emailpilot-database-url",
                "secret_key": "emailpilot-secret-key",
                "klaviyo_api_key": "emailpilot-klaviyo-api-key",
                "slack_webhook_url": "emailpilot-slack-webhook-url",
                "gemini_api_key": "emailpilot-gemini-api-key",
                "google_application_credentials": "emailpilot-google-credentials"
            }
            
            for setting_name, secret_id in secret_mappings.items():
                try:
                    secret_value = secret_manager.get_secret(secret_id)
                    if secret_value:
                        setattr(self, setting_name, secret_value)
                        logger.debug(f"Loaded {setting_name} from Secret Manager")
                    else:
                        # Fall back to environment variable if secret doesn't exist
                        env_value = os.getenv(setting_name.upper())
                        if env_value:
                            setattr(self, setting_name, env_value)
                            logger.debug(f"Using environment variable for {setting_name} (secret not found)")
                except Exception as e:
                    logger.warning(f"Could not load {setting_name} from Secret Manager: {e}")
                    # Fall back to environment variable
                    env_value = os.getenv(setting_name.upper())
                    if env_value:
                        setattr(self, setting_name, env_value)
            
            # Ensure critical values have defaults if not found
            if not self.database_url:
                self.database_url = os.getenv("DATABASE_URL", "sqlite:///./emailpilot.db")
            if not self.secret_key:
                self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
                
        except ImportError:
            logger.error("Secret Manager service not available, falling back to environment variables")
            self._load_from_environment()
        except Exception as e:
            logger.error(f"Error loading from Secret Manager: {e}")
            self._load_from_environment()
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        logger.info("Loading configuration from environment variables")
        
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./emailpilot.db")
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
        self.klaviyo_api_key = os.getenv("KLAVIYO_API_KEY")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    def get_secret_value(self, key: str) -> Optional[str]:
        """
        Get a secret value either from Secret Manager or environment.
        This method allows dynamic secret retrieval.
        
        Args:
            key: The configuration key to retrieve
            
        Returns:
            The secret value or None if not found
        """
        if hasattr(self, key):
            return getattr(self, key)
        
        # Try to get from Secret Manager if enabled
        if self.secret_manager_enabled:
            try:
                from app.services.secret_manager import get_secret_manager
                secret_manager = get_secret_manager()
                
                # Convert key to secret ID format
                secret_id = f"emailpilot-{key.replace('_', '-')}"
                return secret_manager.get_secret(secret_id)
            except Exception as e:
                logger.warning(f"Could not retrieve {key} from Secret Manager: {e}")
        
        # Fall back to environment variable
        return os.getenv(key.upper())
    
    def update_secret(self, key: str, value: str) -> bool:
        """
        Update a secret in Secret Manager (if enabled) or environment.
        
        Args:
            key: The configuration key to update
            value: The new value
            
        Returns:
            True if successful, False otherwise
        """
        if self.secret_manager_enabled:
            try:
                from app.services.secret_manager import get_secret_manager
                secret_manager = get_secret_manager()
                
                # Convert key to secret ID format
                secret_id = f"emailpilot-{key.replace('_', '-')}"
                
                # Create or update the secret
                secret_manager.create_secret(
                    secret_id=secret_id,
                    secret_value=value,
                    labels={"app": "emailpilot", "type": "config"}
                )
                
                # Update the local value
                setattr(self, key, value)
                logger.info(f"Updated {key} in Secret Manager")
                return True
                
            except Exception as e:
                logger.error(f"Failed to update {key} in Secret Manager: {e}")
                return False
        else:
            # Update environment variable (for current session only)
            os.environ[key.upper()] = value
            setattr(self, key, value)
            return True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create singleton settings instance
settings = get_settings()