"""
Configuration management for LangChain Lab using pydantic-settings v2.

All configuration is loaded from environment variables or .env file,
with sensible defaults for local development.
"""

import os
from typing import Literal, Optional
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class LangChainConfig(BaseSettings):
    """Configuration for LangChain Lab components."""
    
    # LLM Configuration
    lc_provider: Literal["openai", "anthropic", "gemini"] = Field(
        default="openai",
        description="LLM provider for chains and agents"
    )
    
    lc_model: str = Field(
        default="gpt-4o-mini",
        description="Model name (e.g., gpt-4o-mini, claude-3-sonnet-20240229, gemini-2.0-flash)"
    )
    
    # Embeddings Configuration
    embeddings_provider: Literal["openai", "vertex", "sentence-transformers"] = Field(
        default="openai",
        description="Provider for text embeddings"
    )
    
    embeddings_model: str = Field(
        default="text-embedding-3-small",
        description="Embeddings model (e.g., text-embedding-3-small, text-embedding-3-large)"
    )
    
    # Vector Store Configuration
    vectorstore: Literal["faiss", "chroma"] = Field(
        default="faiss",
        description="Vector store backend for RAG"
    )
    
    vectorstore_path: Path = Field(
        default=Path("multi-agent/langchain_lab/.faiss"),
        description="Path to persist vector store"
    )
    
    # External Services
    firestore_project: Optional[str] = Field(
        default=None,
        description="Google Cloud project for Firestore (defaults to GOOGLE_CLOUD_PROJECT)"
    )
    
    readonly_klaviyo_base_url: str = Field(
        default="http://localhost:9090",
        description="Base URL for read-only Klaviyo stub/proxy"
    )
    
    # Observability
    enable_tracing: bool = Field(
        default=False,
        description="Enable LangSmith/OpenTelemetry tracing"
    )
    
    langchain_tracing_v2: Optional[str] = Field(
        default=None,
        description="LangChain tracing endpoint"
    )
    
    langchain_api_key: Optional[str] = Field(
        default=None,
        description="LangChain/LangSmith API key for tracing"
    )
    
    # API Keys (loaded from environment)
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    
    google_api_key: Optional[str] = Field(
        default=None,
        description="Google AI API key for Gemini"
    )
    
    vertex_project: Optional[str] = Field(
        default=None,
        description="Google Cloud project for Vertex AI"
    )
    
    # Agent Configuration
    agent_max_iterations: int = Field(
        default=10,
        description="Maximum iterations for agent execution"
    )
    
    agent_timeout_seconds: int = Field(
        default=30,
        description="Timeout for agent execution"
    )
    
    tool_call_budget: int = Field(
        default=15,
        description="Maximum number of tool calls per agent run"
    )
    
    # RAG Configuration
    rag_chunk_size: int = Field(
        default=1000,
        description="Size of text chunks for RAG"
    )
    
    rag_chunk_overlap: int = Field(
        default=200,
        description="Overlap between text chunks"
    )
    
    rag_k_documents: int = Field(
        default=5,
        description="Number of documents to retrieve"
    )
    
    # Data Paths
    seed_docs_path: Path = Field(
        default=Path("multi-agent/langchain_lab/data/seed_docs"),
        description="Path to seed documents for RAG"
    )
    
    artifacts_path: Path = Field(
        default=Path("multi-agent/langchain_lab/artifacts"),
        description="Path to store output artifacts"
    )
    
    @field_validator("firestore_project")
    @classmethod
    def resolve_firestore_project(cls, v: Optional[str]) -> str:
        """Resolve Firestore project from environment if not provided."""
        if v is None:
            v = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        return v
    
    @field_validator("vectorstore_path", "seed_docs_path", "artifacts_path")
    @classmethod
    def resolve_paths(cls, v: Path) -> Path:
        """Ensure paths are absolute."""
        if not v.is_absolute():
            # Resolve relative to emailpilot-app root
            base_path = Path("/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app")
            v = base_path / v
        return v
    
    @field_validator("enable_tracing")
    @classmethod
    def configure_tracing(cls, v: bool, values) -> bool:
        """Configure tracing environment if enabled."""
        if v:
            # Set tracing environment variables if not already set
            if not os.getenv("LANGCHAIN_TRACING_V2"):
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="",  # No prefix, use exact field names
    )
    
    def model_banner(self) -> str:
        """Return a banner string with current configuration."""
        return (
            f"[lc] provider={self.lc_provider} model={self.lc_model} "
            f"embedder={self.embeddings_model} vs={self.vectorstore}"
        )
    
    def validate_api_keys(self) -> list[str]:
        """Validate that required API keys are present."""
        missing = []
        
        if self.lc_provider == "openai" and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        elif self.lc_provider == "anthropic" and not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        elif self.lc_provider == "gemini" and not self.google_api_key:
            missing.append("GOOGLE_API_KEY")
        
        if self.embeddings_provider == "openai" and not self.openai_api_key:
            missing.append("OPENAI_API_KEY (for embeddings)")
        elif self.embeddings_provider == "vertex" and not self.vertex_project:
            missing.append("VERTEX_PROJECT")
        
        return missing


@lru_cache(maxsize=1)
def get_config() -> LangChainConfig:
    """Get cached configuration instance."""
    config = LangChainConfig()
    
    # Log configuration banner on first load
    import logging
    logger = logging.getLogger(__name__)
    logger.info(config.model_banner())
    
    # Validate API keys
    missing_keys = config.validate_api_keys()
    if missing_keys:
        logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
    
    return config