"""
Configuration settings for EmailPilot
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./emailpilot.db")
    
    # Google Cloud
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-prod")
    google_application_credentials: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Secret Manager
    secret_manager_enabled: bool = os.getenv("SECRET_MANAGER_ENABLED", "false").lower() == "true"
    
    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Klaviyo
    klaviyo_base_url: str = "https://a.klaviyo.com/api"
    
    # Slack
    slack_webhook_url: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    
    # Gemini AI
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    class Config:
        env_file = ".env"

settings = Settings()