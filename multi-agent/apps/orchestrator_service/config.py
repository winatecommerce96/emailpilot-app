"""
Configuration management for multi-agent orchestration.
Reads from environment variables and provides centralized config.
"""

import os
from typing import Optional, Dict, Any, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, AnyUrl
from functools import lru_cache


class AppConfig(BaseSettings):
    """Main application configuration with all expected fields."""
    
    # Core GCP
    google_cloud_project: str = Field(
        default="emailpilot-438321",
        alias="GOOGLE_CLOUD_PROJECT"
    )
    
    # Application metadata
    app_name: str = Field(
        default="multi-agent-orchestrator",
        alias="APP_NAME"
    )
    app_version: str = Field(
        default="1.0.0",
        alias="APP_VERSION"
    )
    environment: str = Field(
        default="development",
        alias="ENVIRONMENT"
    )
    
    # LLM routing
    primary_provider: Literal["openai", "anthropic", "gemini"] = Field(
        default="openai",
        alias="PRIMARY_PROVIDER"
    )
    primary_model: str = Field(
        default="gpt-4-turbo-preview",
        alias="PRIMARY_MODEL"
    )
    secondary_provider: Optional[Literal["openai", "anthropic", "gemini"]] = Field(
        default="anthropic",
        alias="SECONDARY_PROVIDER"
    )
    secondary_model: Optional[str] = Field(
        default="claude-3-sonnet-20240229",
        alias="SECONDARY_MODEL"
    )
    marketing_provider: Optional[Literal["openai", "anthropic", "gemini"]] = Field(
        default="gemini",
        alias="MARKETING_PROVIDER"
    )
    marketing_model: Optional[str] = Field(
        default="gemini-2.0-flash",
        alias="MARKETING_MODEL"
    )
    
    # Service endpoints - using str instead of AnyUrl for flexibility
    emailpilot_base_url: str = Field(
        default="http://localhost:8000",
        alias="EMAILPILOT_BASE_URL"
    )
    klaviyo_mcp_url: str = Field(
        default="http://localhost:9090",
        alias="KLAVIYO_MCP_URL"
    )
    
    # Feature flags / limits
    auto_approve_in_dev: bool = Field(
        default=False,
        alias="AUTO_APPROVE_IN_DEV"
    )
    max_revision_loops: int = Field(
        default=3,
        alias="MAX_REVISION_LOOPS"
    )
    enable_tracing: bool = Field(
        default=False,
        alias="ENABLE_TRACING"
    )
    
    # Server configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8100, alias="PORT")
    workers: int = Field(default=1, alias="WORKERS")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # allow lowercase/uppercase envs
        extra="ignore",         # ignore unknown keys instead of raising
    )


class ModelConfig(BaseSettings):
    """Model provider configuration."""
    
    # Primary models
    primary_provider: str = Field(
        default="openai",
        alias="PRIMARY_PROVIDER"
    )
    primary_model: str = Field(
        default="gpt-4-turbo-preview",
        alias="PRIMARY_MODEL"
    )
    
    # Fallback models
    secondary_provider: str = Field(
        default="anthropic",
        alias="SECONDARY_PROVIDER"
    )
    secondary_model: str = Field(
        default="claude-3-sonnet-20240229",
        alias="SECONDARY_MODEL"
    )
    
    # Marketing-optimized model (bypasses safety filters)
    marketing_provider: str = Field(
        default="gemini",
        alias="MARKETING_PROVIDER"
    )
    marketing_model: str = Field(
        default="gemini-2.0-flash",
        alias="MARKETING_MODEL"
    )
    
    # API Keys (will be loaded from Secret Manager in production)
    openai_api_key: Optional[str] = Field(
        default=None,
        alias="OPENAI_API_KEY"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        alias="ANTHROPIC_API_KEY"
    )
    google_api_key: Optional[str] = Field(
        default=None,
        alias="GOOGLE_API_KEY"
    )
    
    # Model parameters
    default_temperature: float = Field(
        default=0.7,
        alias="DEFAULT_TEMPERATURE"
    )
    default_max_tokens: int = Field(
        default=2000,
        alias="DEFAULT_MAX_TOKENS"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class ServiceEndpoints(BaseSettings):
    """External service endpoints."""
    
    # EmailPilot API
    emailpilot_base_url: str = Field(
        default="http://localhost:8000",
        alias="EMAILPILOT_BASE_URL"
    )
    
    # MCP Services
    klaviyo_mcp_url: str = Field(
        default="http://localhost:9090",
        alias="KLAVIYO_MCP_URL"
    )
    
    firestore_mcp_url: str = Field(
        default="http://localhost:9091",
        alias="FIRESTORE_MCP_URL"
    )
    
    openapi_mcp_url: str = Field(
        default="http://localhost:9092",
        alias="OPENAPI_MCP_URL"
    )
    
    # Analytics
    bigquery_project: Optional[str] = Field(
        default=None,
        alias="BIGQUERY_PROJECT"
    )
    bigquery_dataset: Optional[str] = Field(
        default=None,
        alias="BIGQUERY_DATASET"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class StorageConfig(BaseSettings):
    """Storage configuration."""
    
    # Google Cloud Project
    gcp_project: str = Field(
        default="emailpilot-438321",
        alias="GOOGLE_CLOUD_PROJECT"
    )
    
    # Firestore transport configuration
    firestore_transport: Literal["grpc", "rest", "auto"] = Field(
        default="auto",
        alias="FIRESTORE_TRANSPORT_MODE",
        description="Transport protocol for Firestore: grpc, rest, or auto (auto-detect)"
    )
    
    firestore_timeout_seconds: int = Field(
        default=60,
        alias="FIRESTORE_TIMEOUT_SECONDS",
        description="Timeout for Firestore operations"
    )
    
    firestore_enable_diagnostics: bool = Field(
        default=True,
        alias="FIRESTORE_ENABLE_DIAGNOSTICS",
        description="Run connectivity diagnostics on startup"
    )
    
    # Firestore collections (namespaced for multi-agent)
    artifacts_collection: str = Field(
        default="ma_artifacts",
        alias="MA_ARTIFACTS_COLLECTION"
    )
    
    approvals_collection: str = Field(
        default="ma_approvals",
        alias="MA_APPROVALS_COLLECTION"
    )
    
    runs_collection: str = Field(
        default="ma_runs",
        alias="MA_RUNS_COLLECTION"
    )
    
    # Secret Manager
    use_secret_manager: bool = Field(
        default=True,
        alias="USE_SECRET_MANAGER"
    )
    secret_prefix: str = Field(
        default="ma-",
        alias="SECRET_PREFIX"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class OrchestrationConfig(BaseSettings):
    """Orchestration behavior configuration."""
    
    # Retry configuration
    max_retries: int = Field(
        default=3,
        alias="MAX_RETRIES"
    )
    retry_delay_seconds: int = Field(
        default=5,
        alias="RETRY_DELAY_SECONDS"
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        alias="RETRY_BACKOFF_FACTOR"
    )
    
    # Timeout configuration
    node_timeout_seconds: int = Field(
        default=300,
        alias="NODE_TIMEOUT_SECONDS"
    )
    approval_timeout_hours: int = Field(
        default=24,
        alias="APPROVAL_TIMEOUT_HOURS"
    )
    
    # Graph configuration
    max_revision_loops: int = Field(
        default=3,
        alias="MAX_REVISION_LOOPS"
    )
    enable_human_approval: bool = Field(
        default=True,
        alias="ENABLE_HUMAN_APPROVAL"
    )
    auto_approve_in_dev: bool = Field(
        default=False,
        alias="AUTO_APPROVE_IN_DEV"
    )
    
    # Caching
    enable_caching: bool = Field(
        default=True,
        alias="ENABLE_CACHING"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        alias="CACHE_TTL_SECONDS"
    )
    
    # Observability
    enable_tracing: bool = Field(
        default=True,
        alias="ENABLE_TRACING"
    )
    trace_endpoint: str = Field(
        default="http://localhost:4318",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class Settings:
    """Aggregated settings container."""
    
    def __init__(self):
        # AppConfig now contains all the fields that were causing issues
        self.app = AppConfig()
        self.models = ModelConfig()
        self.services = ServiceEndpoints()
        self.storage = StorageConfig()
        self.orchestration = OrchestrationConfig()
        
    def to_dict(self) -> Dict[str, Any]:
        """Export all settings as dictionary."""
        return {
            "app": self.app.model_dump(),
            "models": self.models.model_dump(exclude={"openai_api_key", "anthropic_api_key", "google_api_key"}),
            "services": self.services.model_dump(),
            "storage": self.storage.model_dump(),
            "orchestration": self.orchestration.model_dump(),
        }
    
    def get_model_config(self, purpose: str = "general") -> Dict[str, str]:
        """Get model configuration for specific purpose."""
        if purpose == "marketing":
            return {
                "provider": self.models.marketing_provider,
                "model": self.models.marketing_model,
            }
        elif purpose == "analysis":
            return {
                "provider": self.models.primary_provider,
                "model": self.models.primary_model,
            }
        else:
            return {
                "provider": self.models.primary_provider,
                "model": self.models.primary_model,
                "fallback_provider": self.models.secondary_provider,
                "fallback_model": self.models.secondary_model,
            }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export commonly used settings
settings = get_settings()