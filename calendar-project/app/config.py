"""
Configuration settings for the Calendar Project FastAPI application.

This module handles environment variables, application settings, and 
service configurations for the interactive campaign calendar.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application Settings
    app_name: str = Field(default="Calendar Project API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(
        default="Interactive Campaign Calendar for EmailPilot",
        env="APP_DESCRIPTION"
    )
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")
    
    # Google Cloud Settings
    google_cloud_project: str = Field(
        default="your-project-id",
        env="GOOGLE_CLOUD_PROJECT"
    )
    google_application_credentials: Optional[str] = Field(
        default=None,
        env="GOOGLE_APPLICATION_CREDENTIALS"
    )
    
    # Firebase/Firestore Settings
    firestore_collection_prefix: str = Field(
        default="calendar",
        env="FIRESTORE_COLLECTION_PREFIX"
    )
    firebase_config: Optional[str] = Field(
        default=None,
        env="FIREBASE_CONFIG"
    )
    
    # Authentication Settings
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # CORS Settings
    cors_origins: list[str] = Field(
        default=["*"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        env="CORS_ALLOW_CREDENTIALS"
    )
    
    # Logging Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Static Files and Templates
    static_directory: str = Field(default="app/static", env="STATIC_DIRECTORY")
    templates_directory: str = Field(
        default="app/templates",
        env="TEMPLATES_DIRECTORY"
    )
    
    # API Settings
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    docs_url: str = Field(default="/docs", env="DOCS_URL")
    redoc_url: str = Field(default="/redoc", env="REDOC_URL")
    openapi_url: str = Field(default="/openapi.json", env="OPENAPI_URL")
    
    # External API Settings
    klaviyo_api_key: Optional[str] = Field(default=None, env="KLAVIYO_API_KEY")
    klaviyo_base_url: str = Field(
        default="https://a.klaviyo.com/api",
        env="KLAVIYO_BASE_URL"
    )
    
    # Google Calendar API Settings
    google_calendar_api_key: Optional[str] = Field(
        default=None,
        env="GOOGLE_CALENDAR_API_KEY"
    )
    google_calendar_id: Optional[str] = Field(
        default=None,
        env="GOOGLE_CALENDAR_ID"
    )
    
    # Email Settings (if needed for notifications)
    smtp_server: Optional[str] = Field(default=None, env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    
    # Cache Settings
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Convert CORS origins to list if it's a string."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins
    
    def get_database_url(self) -> str:
        """Get database URL for SQLAlchemy (if local DB is needed)."""
        return os.getenv("DATABASE_URL", "sqlite:///./calendar.db")
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    def get_secret_key(self) -> str:
        """Get JWT secret key with fallback."""
        if self.is_production() and self.jwt_secret_key == "your-secret-key-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be set in production")
        return self.jwt_secret_key


# Global settings instance
settings = Settings()


# Environment-specific configurations
class DevelopmentConfig(Settings):
    """Development environment configuration."""
    debug: bool = True
    reload: bool = True
    log_level: str = "DEBUG"
    cors_origins: list[str] = ["*"]


class ProductionConfig(Settings):
    """Production environment configuration."""
    debug: bool = False
    reload: bool = False
    log_level: str = "INFO"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate required production settings
        if not self.google_cloud_project or self.google_cloud_project == "your-project-id":
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set in production")
        
        if not self.jwt_secret_key or self.jwt_secret_key == "your-secret-key-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be set in production")


class TestConfig(Settings):
    """Test environment configuration."""
    debug: bool = True
    google_cloud_project: str = "test-project"
    jwt_secret_key: str = "test-secret-key"
    log_level: str = "WARNING"


def get_settings() -> Settings:
    """Get settings based on environment."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionConfig()
    elif environment == "test":
        return TestConfig()
    elif environment == "development":
        return DevelopmentConfig()
    else:
        return Settings()


# Export commonly used settings
__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "DevelopmentConfig",
    "ProductionConfig", 
    "TestConfig"
]