"""
MCP Client Model for managing MCP configurations and API keys
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text, Integer, Float
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class MCPClient(Base):
    """Model for MCP client configurations"""
    __tablename__ = "mcp_clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    account_id = Column(String, nullable=False, unique=True)  # Klaviyo account ID
    
    # Encrypted API keys stored in Secret Manager
    klaviyo_api_key_secret_id = Column(String, nullable=False)  # Reference to Secret Manager
    openai_api_key_secret_id = Column(String)  # Optional OpenAI key
    gemini_api_key_secret_id = Column(String)  # Optional Gemini key
    
    # Configuration
    enabled = Column(Boolean, default=True)
    read_only = Column(Boolean, default=True)
    
    # Model preferences
    default_model_provider = Column(String, default="claude")  # claude, openai, gemini
    model_settings = Column(JSON, default={})  # Model-specific settings
    
    # Rate limiting
    rate_limit_requests_per_minute = Column(Integer, default=60)
    rate_limit_tokens_per_day = Column(Integer, default=1000000)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String)
    
    # Additional settings
    webhook_url = Column(String)  # Optional webhook for notifications
    custom_settings = Column(JSON, default={})  # Flexible settings storage


class MCPUsage(Base):
    """Model for tracking MCP usage and analytics"""
    __tablename__ = "mcp_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, nullable=False)
    
    # Request details
    model_provider = Column(String, nullable=False)  # claude, openai, gemini
    model_name = Column(String, nullable=False)  # gpt-4, claude-3, gemini-pro, etc.
    tool_name = Column(String, nullable=False)  # MCP tool used
    
    # Usage metrics
    request_tokens = Column(Integer, default=0)
    response_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer)  # Response time in milliseconds
    
    # Cost tracking
    estimated_cost = Column(Float, default=0.0)  # In USD
    
    # Request metadata
    request_id = Column(String, unique=True)
    status = Column(String)  # success, error, rate_limited
    error_message = Column(Text)
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class MCPModelConfig(Base):
    """Model for managing AI model configurations"""
    __tablename__ = "mcp_model_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String, nullable=False)  # claude, openai, gemini
    model_name = Column(String, nullable=False)  # gpt-4, claude-3, gemini-pro
    display_name = Column(String, nullable=False)
    
    # Model capabilities
    supports_functions = Column(Boolean, default=True)
    supports_vision = Column(Boolean, default=False)
    supports_streaming = Column(Boolean, default=True)
    
    # Limits and pricing
    max_tokens = Column(Integer, default=4096)
    context_window = Column(Integer, default=100000)
    input_cost_per_1k = Column(Float)  # USD per 1k tokens
    output_cost_per_1k = Column(Float)  # USD per 1k tokens
    
    # Configuration
    default_temperature = Column(Float, default=0.7)
    default_max_tokens = Column(Integer, default=2048)
    endpoint_url = Column(String)  # API endpoint
    
    # Status
    enabled = Column(Boolean, default=True)
    deprecated = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())