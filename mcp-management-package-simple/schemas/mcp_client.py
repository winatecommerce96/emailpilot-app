"""
Pydantic schemas for MCP client management
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ModelProvider(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"


class MCPClientBase(BaseModel):
    name: str = Field(..., description="Client name")
    account_id: str = Field(..., description="Klaviyo account ID")
    enabled: bool = Field(True, description="Whether the client is enabled")
    read_only: bool = Field(True, description="Whether the client has read-only access")
    default_model_provider: ModelProvider = Field(ModelProvider.CLAUDE, description="Default AI model provider")
    model_settings: Dict[str, Any] = Field(default_factory=dict, description="Model-specific settings")
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }
    rate_limit_requests_per_minute: int = Field(60, ge=1, le=1000, description="Rate limit per minute")
    rate_limit_tokens_per_day: int = Field(1000000, ge=1000, description="Daily token limit")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom settings")


class MCPClientCreate(MCPClientBase):
    klaviyo_api_key: str = Field(..., description="Klaviyo API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API key")
    
    @validator('klaviyo_api_key')
    def validate_klaviyo_key(cls, v):
        if not v.startswith('pk_'):
            raise ValueError("Klaviyo API key must start with 'pk_'")
        return v
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        if v and not v.startswith('sk-'):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return v


class MCPClientUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    read_only: Optional[bool] = None
    default_model_provider: Optional[ModelProvider] = None
    model_settings: Optional[Dict[str, Any]] = None
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }
    rate_limit_requests_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_tokens_per_day: Optional[int] = Field(None, ge=1000)
    webhook_url: Optional[str] = None
    custom_settings: Optional[Dict[str, Any]] = None
    
    # API key updates
    klaviyo_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


class MCPClientResponse(MCPClientBase):
    id: str
    total_requests: int = 0
    total_tokens_used: int = 0
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    # Don't expose secret IDs directly
    has_klaviyo_key: bool = True
    has_openai_key: bool = False
    has_gemini_key: bool = False
    
    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()  # Disable protected namespace warnings
    }


class MCPUsageCreate(BaseModel):
    client_id: str
    model_provider: ModelProvider
    model_name: str
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }
    tool_name: str
    request_tokens: int = 0
    response_tokens: int = 0
    latency_ms: Optional[int] = None
    request_id: str
    status: str = "success"
    error_message: Optional[str] = None


class MCPUsageResponse(BaseModel):
    id: str
    client_id: str
    model_provider: str
    model_name: str
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }
    tool_name: str
    request_tokens: int
    response_tokens: int
    total_tokens: int
    latency_ms: Optional[int]
    estimated_cost: float
    request_id: str
    status: str
    error_message: Optional[str]
    requested_at: datetime
    completed_at: Optional[datetime]
    
    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()  # Disable protected namespace warnings  
    }


class MCPUsageStats(BaseModel):
    client_id: str
    period: str  # daily, weekly, monthly
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_latency_ms: float
    success_rate: float
    top_tools: List[Dict[str, Any]]
    model_breakdown: Dict[str, Dict[str, Any]]
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }


class MCPModelConfigResponse(BaseModel):
    id: str
    provider: str
    model_name: str
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }
    display_name: str
    supports_functions: bool
    supports_vision: bool
    supports_streaming: bool
    max_tokens: int
    context_window: int
    input_cost_per_1k: Optional[float]
    output_cost_per_1k: Optional[float]
    default_temperature: float
    default_max_tokens: int
    enabled: bool
    deprecated: bool
    
    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()  # Disable protected namespace warnings
    }


class MCPTestRequest(BaseModel):
    client_id: str
    model_provider: ModelProvider
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }
    test_query: str = "List available tools"


class MCPTestResponse(BaseModel):
    success: bool
    provider: str
    model_name: str
    
    model_config = {
        "protected_namespaces": ()  # Disable protected namespace warnings
    }
    response: Optional[str]
    error: Optional[str]
    latency_ms: int
    tokens_used: int