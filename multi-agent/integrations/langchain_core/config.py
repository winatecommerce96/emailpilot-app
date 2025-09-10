"""
Configuration module for LangChain Core integration.

Uses pydantic-settings v2 for type-safe configuration management.
No global environment mutations - all config is encapsulated.
"""

from typing import Literal, Optional, Dict, Any
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LangChainConfig(BaseSettings):
    """
    LangChain Core configuration with sensible defaults.
    
    All values can be overridden via environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Provider Configuration
    lc_provider: Literal["openai", "anthropic", "gemini"] = Field(
        default="openai",
        description="Primary LLM provider"
    )
    
    lc_model: str = Field(
        default="gpt-4o-mini",
        description="Model identifier for the selected provider"
    )
    
    lc_temperature: float = Field(
        default=0.0,
        description="LLM temperature for consistency",
        ge=0.0,
        le=2.0
    )
    
    lc_max_tokens: int = Field(
        default=2000,
        description="Maximum tokens for LLM responses",
        gt=0
    )
    
    # Embeddings Configuration
    embeddings_provider: Literal["openai", "vertex", "local"] = Field(
        default="openai",
        description="Embeddings provider"
    )
    
    embeddings_model: str = Field(
        default="text-embedding-3-large",
        description="Embeddings model identifier"
    )
    
    # Vector Store Configuration
    vectorstore: Literal["faiss", "chroma"] = Field(
        default="faiss",
        description="Vector store backend"
    )
    
    vectorstore_path: Path = Field(
        default=Path(__file__).parent / ".faiss",
        description="Path for persisted vector store"
    )
    
    # MCP Integration
    mcp_base_url: str = Field(
        default="http://localhost:8090/api/mcp",
        description="Base URL for MCP gateway"
    )
    
    klaviyo_mcp_url: str = Field(
        default="http://localhost:8000/api/mcp/gateway",
        description="Klaviyo MCP Gateway endpoint (routes to Enhanced MCP)"
    )
    
    mcp_timeout_seconds: int = Field(
        default=30,
        description="Timeout for MCP calls",
        gt=0
    )
    
    # Firestore Configuration
    firestore_project: Optional[str] = Field(
        default="emailpilot-438321",
        alias="GOOGLE_CLOUD_PROJECT",
        description="Google Cloud project for Firestore"
    )
    
    firestore_emulator: Optional[str] = Field(
        default=None,
        alias="FIRESTORE_EMULATOR_HOST",
        description="Firestore emulator host if using emulator"
    )
    
    # Agent Configuration
    agent_budget_steps: int = Field(
        default=15,
        description="Maximum steps for agent execution",
        gt=0
    )
    
    agent_timeout_s: int = Field(
        default=60,
        description="Agent execution timeout in seconds",
        gt=0
    )
    
    agent_enable_caching: bool = Field(
        default=True,
        description="Enable in-process caching for agent tools"
    )
    
    # RAG Configuration
    rag_chunk_size: int = Field(
        default=1000,
        description="Chunk size for document splitting",
        gt=0
    )
    
    rag_chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks",
        ge=0
    )
    
    rag_k_documents: int = Field(
        default=5,
        description="Number of documents to retrieve",
        gt=0
    )
    
    # Observability
    enable_tracing: bool = Field(
        default=False,
        description="Enable LangSmith/OpenTelemetry tracing"
    )
    
    langsmith_api_key: Optional[str] = Field(
        default=None,
        alias="LANGCHAIN_API_KEY",
        description="LangSmith API key for tracing"
    )
    
    langsmith_project: str = Field(
        default="emailpilot-langchain",
        alias="LANGCHAIN_PROJECT",
        description="LangSmith project name"
    )
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Secret Manager Configuration
    use_secret_manager: bool = Field(
        default=True,
        alias="USE_SECRET_MANAGER",
        description="Use Google Secret Manager for API keys"
    )
    
    openai_secret_name: str = Field(
        default="openai-api-key",
        alias="OPENAI_SECRET_NAME",
        description="Secret Manager name for OpenAI API key"
    )
    
    anthropic_secret_name: str = Field(
        default="emailpilot-claude",
        alias="ANTHROPIC_SECRET_NAME",
        description="Secret Manager name for Anthropic API key"
    )
    
    gemini_secret_name: str = Field(
        default="emailpilot-gemini-api-key",
        alias="GEMINI_SECRET_NAME",
        description="Secret Manager name for Gemini API key"
    )
    
    # Cached API keys (populated from Secret Manager)
    _openai_api_key: Optional[str] = None
    _anthropic_api_key: Optional[str] = None
    _google_api_key: Optional[str] = None
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from Secret Manager."""
        if self._openai_api_key is None and self.use_secret_manager:
            from .secrets import get_openai_api_key
            self._openai_api_key = get_openai_api_key()
        return self._openai_api_key
    
    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from Secret Manager."""
        if self._anthropic_api_key is None and self.use_secret_manager:
            from .secrets import get_anthropic_api_key
            self._anthropic_api_key = get_anthropic_api_key()
        return self._anthropic_api_key
    
    @property
    def google_api_key(self) -> Optional[str]:
        """Get Google API key from Secret Manager."""
        if self._google_api_key is None and self.use_secret_manager:
            from .secrets import get_google_api_key
            self._google_api_key = get_google_api_key()
        return self._google_api_key
    
    @field_validator("vectorstore_path")
    @classmethod
    def ensure_path(cls, v: Path) -> Path:
        """Ensure vector store path is absolute."""
        if not v.is_absolute():
            v = Path(__file__).parent / v
        return v
    
    @field_validator("lc_model")
    @classmethod
    def validate_model(cls, v: str, info) -> str:
        """Validate model matches provider."""
        provider = info.data.get("lc_provider")
        
        # Map common models to provider-specific names
        model_map = {
            "openai": {
                "gpt-4o-mini": "gpt-4o-mini",
                "gpt-4": "gpt-4-turbo-preview",
                "gpt-3.5": "gpt-3.5-turbo"
            },
            "anthropic": {
                "gpt-4o-mini": "claude-3-haiku-20240307",
                "claude-3-haiku": "claude-3-haiku-20240307",
                "claude-3-sonnet": "claude-3-sonnet-20240229"
            },
            "gemini": {
                "gpt-4o-mini": "gemini-1.5-flash",
                "gemini-flash": "gemini-1.5-flash",
                "gemini-pro": "gemini-1.5-pro"
            }
        }
        
        if provider in model_map and v in model_map[provider]:
            return model_map[provider][v]
        
        return v
    
    def model_banner(self) -> str:
        """Generate a banner string for logging."""
        import importlib.metadata as m
        
        try:
            lg_version = m.version("langgraph")
        except:
            lg_version = "unknown"
        
        try:
            lc_version = m.version("langchain")
        except:
            lc_version = "unknown"
        
        return (
            f"[lc] provider={self.lc_provider} model={self.lc_model} "
            f"embedder={self.embeddings_model} vs={self.vectorstore} "
            f"langchain={lc_version} langgraph={lg_version}"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary (redacting secrets)."""
        data = self.model_dump(exclude={'_openai_api_key', '_anthropic_api_key', '_google_api_key'})
        
        # Don't include API keys in output
        sensitive_fields = [
            "openai_api_key",
            "anthropic_api_key", 
            "google_api_key",
            "langsmith_api_key"
        ]
        
        for field in sensitive_fields:
            if field in data:
                data[field] = "***FROM_SECRET_MANAGER***" if self.use_secret_manager else "***REDACTED***"
        
        return data


# Singleton instance
_config: Optional[LangChainConfig] = None


def get_config(reload: bool = False) -> LangChainConfig:
    """
    Get configuration singleton.
    
    Args:
        reload: Force reload of configuration
    
    Returns:
        LangChainConfig instance
    """
    global _config
    
    if _config is None or reload:
        _config = LangChainConfig()
    
    return _config