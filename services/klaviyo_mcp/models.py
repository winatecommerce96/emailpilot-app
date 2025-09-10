"""
Pydantic models for Klaviyo MCP Service
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class ToolCallRequest(BaseModel):
    """Request model for MCP tool calls."""
    client_id: str = Field(..., description="Client ID or slug")
    tool_name: str = Field(..., description="Name of the MCP tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """Response model for MCP tool calls."""
    success: bool = Field(..., description="Whether the tool call succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Tool response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    client_id: str = Field(..., description="Client ID")
    tool_name: str = Field(..., description="Tool name that was called")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")


class ClientStatus(BaseModel):
    """Status of a single MCP client instance."""
    client_id: str
    port: int
    is_alive: bool
    created_at: float
    last_used: float
    idle_seconds: float


class ServiceStatus(BaseModel):
    """Overall service status."""
    total_instances: int
    max_clients: int
    idle_timeout: int
    instances: List[ClientStatus]


class ToolInfo(BaseModel):
    """Information about an MCP tool."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="Tool input schema")
    category: Optional[str] = Field(None, description="Tool category")


class ToolRegistry(BaseModel):
    """Registry of available MCP tools."""
    tools: List[ToolInfo]
    total_count: int
    categories: List[str]


class CampaignMetricsRequest(BaseModel):
    """Request for campaign metrics."""
    client_id: str = Field(..., description="Client ID or slug")
    campaign_id: str = Field(..., description="Campaign ID")
    metrics: Optional[List[str]] = Field(
        None,
        description="Specific metrics to retrieve",
        example=["open_rate", "click_rate", "delivered", "bounce_rate"]
    )
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    conversion_metric_id: Optional[str] = Field(None, description="ID of conversion metric")


class MetricAggregateRequest(BaseModel):
    """Request for metric aggregates."""
    client_id: str = Field(..., description="Client ID or slug")
    metric_id: str = Field(..., description="Metric ID")
    measurement: str = Field("count", description="Measurement type (count, sum, unique)")
    group_by: Optional[List[str]] = Field(None, description="Dimensions to group by")
    timeframe: Optional[str] = Field("last_30_days", description="Timeframe key")
    start_date: Optional[str] = Field(None, description="Custom start date")
    end_date: Optional[str] = Field(None, description="Custom end date")


class APIKeyValidationRequest(BaseModel):
    """Request to validate an API key."""
    client_id: str = Field(..., description="Client ID or slug")
    refresh_cache: bool = Field(False, description="Force refresh cached key")


class APIKeyValidationResponse(BaseModel):
    """Response from API key validation."""
    client_id: str
    is_valid: bool
    error: Optional[str] = None
    key_source: Optional[str] = Field(None, description="Where the key was resolved from")


class ClientConfiguration(BaseModel):
    """Client configuration from Firestore."""
    client_id: str
    client_name: str
    client_slug: Optional[str] = None
    klaviyo_api_key_secret: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    klaviyo_api_key: Optional[str] = None
    placed_order_metric_id: Optional[str] = None
    timezone: str = "UTC"
    currency: str = "USD"