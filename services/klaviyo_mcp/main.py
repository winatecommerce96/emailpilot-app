"""
Klaviyo MCP Service - FastAPI wrapper for Klaviyo MCP Server Enhanced

This service provides a Python API interface to the Node.js Klaviyo MCP Server,
with multi-client support and Firestore/Secret Manager integration.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .api_key_resolver import APIKeyResolver
from .client_manager import MCPClientManager
from .models import (
    ToolCallRequest,
    ToolCallResponse,
    ServiceStatus,
    ToolRegistry,
    ToolInfo,
    CampaignMetricsRequest,
    MetricAggregateRequest,
    APIKeyValidationRequest,
    APIKeyValidationResponse,
)
from .tools import MCPToolRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set")

MCP_SERVER_PATH = os.environ.get(
    "KLAVIYO_MCP_ENHANCED_PATH",
    "services/klaviyo_mcp_enhanced"
)
MCP_BASE_PORT = int(os.environ.get("KLAVIYO_MCP_BASE_PORT", "10000"))
MCP_MAX_CLIENTS = int(os.environ.get("KLAVIYO_MCP_MAX_CLIENTS", "10"))
MCP_IDLE_TIMEOUT = int(os.environ.get("KLAVIYO_MCP_IDLE_TIMEOUT", "3600"))

# Global instances
api_key_resolver: Optional[APIKeyResolver] = None
client_manager: Optional[MCPClientManager] = None
tool_registry: Optional[MCPToolRegistry] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global api_key_resolver, client_manager, tool_registry
    
    # Startup
    logger.info("Starting Klaviyo MCP Service")
    api_key_resolver = APIKeyResolver(PROJECT_ID)
    client_manager = MCPClientManager(
        mcp_server_path=MCP_SERVER_PATH,
        base_port=MCP_BASE_PORT,
        max_clients=MCP_MAX_CLIENTS,
        idle_timeout=MCP_IDLE_TIMEOUT
    )
    tool_registry = MCPToolRegistry()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Klaviyo MCP Service")
    if client_manager:
        client_manager.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Klaviyo MCP Service",
    description="Python wrapper for Klaviyo MCP Server Enhanced with multi-client support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injectors
def get_api_key_resolver() -> APIKeyResolver:
    """Get the API key resolver instance."""
    if not api_key_resolver:
        raise RuntimeError("API key resolver not initialized")
    return api_key_resolver


def get_client_manager() -> MCPClientManager:
    """Get the client manager instance."""
    if not client_manager:
        raise RuntimeError("Client manager not initialized")
    return client_manager


def get_tool_registry() -> MCPToolRegistry:
    """Get the tool registry instance."""
    if not tool_registry:
        raise RuntimeError("Tool registry not initialized")
    return tool_registry


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "klaviyo-mcp",
        "project_id": PROJECT_ID,
        "timestamp": time.time()
    }


# Service status
@app.get("/status", response_model=ServiceStatus)
async def get_service_status(
    manager: MCPClientManager = Depends(get_client_manager)
):
    """Get service status including all client instances."""
    return manager.get_status()


# Tool registry
@app.get("/tools", response_model=ToolRegistry)
async def list_tools(
    registry: MCPToolRegistry = Depends(get_tool_registry),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """List available MCP tools."""
    tools = registry.get_tools(category=category)
    return ToolRegistry(
        tools=tools,
        total_count=len(tools),
        categories=registry.get_categories()
    )


# Generic tool call
@app.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(
    request: ToolCallRequest,
    background_tasks: BackgroundTasks,
    resolver: APIKeyResolver = Depends(get_api_key_resolver),
    manager: MCPClientManager = Depends(get_client_manager),
    registry: MCPToolRegistry = Depends(get_tool_registry)
):
    """
    Call any MCP tool for a specific client.
    
    This endpoint:
    1. Resolves the client's API key from Firestore/Secret Manager
    2. Gets or creates an MCP server instance for the client
    3. Calls the specified tool with the provided arguments
    4. Returns the tool response
    """
    start_time = time.time()
    
    try:
        # Resolve API key
        api_key = resolver.resolve_api_key(request.client_id)
        
        # Get or create client instance
        instance = manager.get_or_create_client(request.client_id, api_key)
        
        # Call the tool
        result = await manager.call_tool_async(
            request.client_id,
            request.tool_name,
            request.arguments
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return ToolCallResponse(
            success=True,
            data=result,
            client_id=request.client_id,
            tool_name=request.tool_name,
            execution_time_ms=execution_time_ms
        )
        
    except ValueError as e:
        # Client not found or API key resolution failed
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # MCP server or tool call failed
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error calling tool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Campaign metrics endpoint
@app.post("/campaigns/metrics")
async def get_campaign_metrics(
    request: CampaignMetricsRequest,
    resolver: APIKeyResolver = Depends(get_api_key_resolver),
    manager: MCPClientManager = Depends(get_client_manager)
):
    """Get campaign performance metrics for a specific campaign."""
    tool_request = ToolCallRequest(
        client_id=request.client_id,
        tool_name="get_campaign_metrics",
        arguments={
            "id": request.campaign_id,
            "metrics": request.metrics,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "conversion_metric_id": request.conversion_metric_id
        }
    )
    
    return await call_tool(
        tool_request,
        BackgroundTasks(),
        resolver,
        manager,
        get_tool_registry()
    )


# Metric aggregates endpoint
@app.post("/metrics/aggregates")
async def query_metric_aggregates(
    request: MetricAggregateRequest,
    resolver: APIKeyResolver = Depends(get_api_key_resolver),
    manager: MCPClientManager = Depends(get_client_manager)
):
    """Query aggregated metric data for custom analytics."""
    tool_request = ToolCallRequest(
        client_id=request.client_id,
        tool_name="query_metric_aggregates",
        arguments={
            "metric_id": request.metric_id,
            "measurement": request.measurement,
            "group_by": request.group_by,
            "timeframe": request.timeframe,
            "start_date": request.start_date,
            "end_date": request.end_date
        }
    )
    
    return await call_tool(
        tool_request,
        BackgroundTasks(),
        resolver,
        manager,
        get_tool_registry()
    )


# API key validation
@app.post("/clients/validate-key", response_model=APIKeyValidationResponse)
async def validate_api_key(
    request: APIKeyValidationRequest,
    resolver: APIKeyResolver = Depends(get_api_key_resolver)
):
    """Validate a client's Klaviyo API key."""
    try:
        # Clear cache if requested
        if request.refresh_cache:
            resolver.clear_cache(request.client_id)
            
        # Resolve the API key
        api_key = resolver.resolve_api_key(request.client_id)
        
        # Validate the key
        is_valid = resolver.validate_api_key(api_key)
        
        return APIKeyValidationResponse(
            client_id=request.client_id,
            is_valid=is_valid,
            key_source="resolved_from_config"
        )
        
    except ValueError as e:
        return APIKeyValidationResponse(
            client_id=request.client_id,
            is_valid=False,
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        return APIKeyValidationResponse(
            client_id=request.client_id,
            is_valid=False,
            error="Validation failed"
        )


# Cache management
@app.post("/cache/clear")
async def clear_cache(
    client_id: Optional[str] = Query(None, description="Clear cache for specific client"),
    resolver: APIKeyResolver = Depends(get_api_key_resolver)
):
    """Clear API key cache."""
    resolver.clear_cache(client_id)
    return {
        "success": True,
        "message": f"Cache cleared for {'client ' + client_id if client_id else 'all clients'}"
    }


# Client instance management
@app.post("/clients/{client_id}/restart")
async def restart_client_instance(
    client_id: str,
    resolver: APIKeyResolver = Depends(get_api_key_resolver),
    manager: MCPClientManager = Depends(get_client_manager)
):
    """Restart an MCP server instance for a specific client."""
    try:
        # Stop existing instance if any
        with manager.lock:
            if client_id in manager.instances:
                manager._stop_instance(client_id)
                
        # Resolve API key and create new instance
        api_key = resolver.resolve_api_key(client_id)
        instance = manager.get_or_create_client(client_id, api_key)
        
        return {
            "success": True,
            "client_id": client_id,
            "port": instance.port,
            "message": "Instance restarted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error restarting instance for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("KLAVIYO_MCP_PORT", "9092")),
        reload=os.environ.get("ENVIRONMENT") == "development"
    )