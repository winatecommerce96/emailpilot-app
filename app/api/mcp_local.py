"""
MCP Management API endpoints for local development
Provides mock data for testing the MCP Management UI
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(tags=["MCP Management"])

# Mock data for local testing
MOCK_MODELS = [
    {
        "id": "claude-3-opus",
        "display_name": "Claude 3 Opus",
        "provider": "Anthropic",
        "model_name": "claude-3-opus-20240229",
        "max_tokens": 4096,
        "is_active": True
    },
    {
        "id": "claude-3-sonnet",
        "display_name": "Claude 3 Sonnet",
        "provider": "Anthropic",
        "model_name": "claude-3-sonnet-20240229",
        "max_tokens": 4096,
        "is_active": True
    },
    {
        "id": "gpt-4-turbo",
        "display_name": "GPT-4 Turbo",
        "provider": "OpenAI",
        "model_name": "gpt-4-turbo-preview",
        "max_tokens": 4096,
        "is_active": False
    }
]

MOCK_CLIENTS = [
    {
        "id": "klaviyo-client-1",
        "name": "Win at Ecommerce",
        "account_id": "ACCT001",
        "type": "Production",
        "enabled": True,
        "read_only": True,
        "default_model_provider": "claude",
        "has_klaviyo_key": True,
        "has_openai_key": False,
        "has_gemini_key": True,
        "rate_limit_requests_per_minute": 60,
        "rate_limit_tokens_per_day": 1000000,
        "webhook_url": "",
        "total_requests": 1247,
        "total_tokens_used": 45280,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-03-10T08:30:00Z",
        "custom_settings": {}
    },
    {
        "id": "klaviyo-client-2",
        "name": "Test Client",
        "account_id": "ACCT002",
        "type": "Development",
        "enabled": False,
        "read_only": False,
        "default_model_provider": "openai",
        "has_klaviyo_key": True,
        "has_openai_key": True,
        "has_gemini_key": False,
        "rate_limit_requests_per_minute": 30,
        "rate_limit_tokens_per_day": 500000,
        "webhook_url": "https://webhook.example.com/mcp",
        "total_requests": 523,
        "total_tokens_used": 18900,
        "created_at": "2024-02-01T14:30:00Z",
        "updated_at": "2024-03-08T16:45:00Z",
        "custom_settings": {"debug_mode": True}
    }
]

@router.get("/")
async def mcp_root() -> Dict[str, Any]:
    """MCP Management API root endpoint"""
    return {
        "status": "operational",
        "service": "EmailPilot MCP Management API", 
        "version": "2.0.0",
        "features": ["model_management", "client_management", "usage_tracking"],
        "available_endpoints": [
            "GET /api/mcp/models",
            "GET /api/mcp/clients", 
            "GET /api/mcp/health",
            "GET /api/mcp/clients/{client_id}",
            "GET /api/mcp/usage/{client_id}/stats",
            "POST /api/mcp/clients",
            "PUT /api/mcp/clients/{client_id}",
            "DELETE /api/mcp/clients/{client_id}"
        ]
    }

@router.get("/models")
async def get_models() -> List[Dict[str, Any]]:
    """Get all available MCP models"""
    return MOCK_MODELS

@router.get("/clients")
async def get_clients() -> List[Dict[str, Any]]:
    """Get all MCP clients"""
    return MOCK_CLIENTS

@router.get("/health")
async def get_health() -> Dict[str, Any]:
    """Get MCP system health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "details": {
            "models_count": len(MOCK_MODELS),
            "clients_count": len(MOCK_CLIENTS),
            "active_models": sum(1 for m in MOCK_MODELS if m["is_active"])
        }
    }

class ModelUpdate(BaseModel):
    is_active: bool

class MCPExecuteRequest(BaseModel):
    client_id: str
    tool_name: str
    parameters: Dict[str, Any]
    provider: str
    model: str

class ClientUpdateRequest(BaseModel):
    name: str = None
    enabled: bool = None
    read_only: bool = None
    default_model_provider: str = None
    klaviyo_api_key: str = None
    openai_api_key: str = None
    gemini_api_key: str = None
    rate_limit_requests_per_minute: int = None
    rate_limit_tokens_per_day: int = None
    webhook_url: str = None
    custom_settings: Dict[str, Any] = None

@router.patch("/models/{model_id}")
async def update_model(model_id: str, update: ModelUpdate) -> Dict[str, Any]:
    """Update a model's configuration"""
    for model in MOCK_MODELS:
        if model["id"] == model_id:
            model["is_active"] = update.is_active
            return {"status": "success", "model": model}
    raise HTTPException(status_code=404, detail="Model not found")

@router.post("/models/{model_id}/test")
async def test_model(model_id: str) -> Dict[str, Any]:
    """Test a model's connectivity"""
    for model in MOCK_MODELS:
        if model["id"] == model_id:
            return {
                "status": "success",
                "model_id": model_id,
                "response_time_ms": 234,
                "test_result": "Model responded successfully"
            }
    raise HTTPException(status_code=404, detail="Model not found")

@router.get("/clients/{client_id}")
async def get_client_details(client_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific MCP client"""
    for client in MOCK_CLIENTS:
        if client["id"] == client_id:
            return client
    raise HTTPException(status_code=404, detail="Client not found")

@router.put("/clients/{client_id}")
async def update_client(client_id: str, update: ClientUpdateRequest) -> Dict[str, Any]:
    """Update an MCP client's configuration"""
    for client in MOCK_CLIENTS:
        if client["id"] == client_id:
            # Update only provided fields
            update_dict = update.dict(exclude_unset=True)
            
            # Handle API key updates (don't update if empty string provided)
            if "klaviyo_api_key" in update_dict and update_dict["klaviyo_api_key"]:
                client["has_klaviyo_key"] = True
            if "openai_api_key" in update_dict and update_dict["openai_api_key"]:
                client["has_openai_key"] = True
            if "gemini_api_key" in update_dict and update_dict["gemini_api_key"]:
                client["has_gemini_key"] = True
            
            # Remove the actual API keys from the response (security)
            if "klaviyo_api_key" in update_dict:
                del update_dict["klaviyo_api_key"]
            if "openai_api_key" in update_dict:
                del update_dict["openai_api_key"]
            if "gemini_api_key" in update_dict:
                del update_dict["gemini_api_key"]
            
            client.update(update_dict)
            client["updated_at"] = datetime.utcnow().isoformat() + "Z"
            
            return {"status": "success", "client": client}
    raise HTTPException(status_code=404, detail="Client not found")

@router.delete("/clients/{client_id}")
async def delete_client(client_id: str) -> Dict[str, Any]:
    """Delete an MCP client"""
    global MOCK_CLIENTS
    for i, client in enumerate(MOCK_CLIENTS):
        if client["id"] == client_id:
            deleted_client = MOCK_CLIENTS.pop(i)
            return {
                "status": "success", 
                "message": f"Client {deleted_client['name']} deleted successfully"
            }
    raise HTTPException(status_code=404, detail="Client not found")

@router.get("/usage/{client_id}/stats")
async def get_usage_stats(client_id: str, period: str = "weekly") -> Dict[str, Any]:
    """Get usage statistics for a specific client"""
    for client in MOCK_CLIENTS:
        if client["id"] == client_id:
            # Generate mock usage statistics based on period
            base_requests = client["total_requests"]
            base_tokens = client["total_tokens_used"]
            
            if period == "weekly":
                multiplier = 0.2  # 20% of total for this week
            elif period == "monthly":
                multiplier = 0.8  # 80% of total for this month
            else:
                multiplier = 1.0  # All time
            
            period_requests = int(base_requests * multiplier)
            period_tokens = int(base_tokens * multiplier)
            
            return {
                "period": period,
                "client_id": client_id,
                "total_requests": period_requests,
                "total_tokens": period_tokens,
                "total_cost": round(period_tokens * 0.00015, 2),  # Mock cost calculation
                "success_rate": 94.7,
                "average_response_time_ms": 1250,
                "top_tools": [
                    {"tool": "get_campaigns", "count": int(period_requests * 0.4), "percentage": 40.0},
                    {"tool": "get_flows", "count": int(period_requests * 0.25), "percentage": 25.0},
                    {"tool": "get_segments", "count": int(period_requests * 0.2), "percentage": 20.0},
                    {"tool": "get_metrics", "count": int(period_requests * 0.15), "percentage": 15.0}
                ],
                "daily_breakdown": [
                    {"date": "2024-03-04", "requests": int(period_requests * 0.14), "tokens": int(period_tokens * 0.14)},
                    {"date": "2024-03-05", "requests": int(period_requests * 0.16), "tokens": int(period_tokens * 0.16)},
                    {"date": "2024-03-06", "requests": int(period_requests * 0.13), "tokens": int(period_tokens * 0.13)},
                    {"date": "2024-03-07", "requests": int(period_requests * 0.18), "tokens": int(period_tokens * 0.18)},
                    {"date": "2024-03-08", "requests": int(period_requests * 0.15), "tokens": int(period_tokens * 0.15)},
                    {"date": "2024-03-09", "requests": int(period_requests * 0.12), "tokens": int(period_tokens * 0.12)},
                    {"date": "2024-03-10", "requests": int(period_requests * 0.12), "tokens": int(period_tokens * 0.12)}
                ]
            }
    raise HTTPException(status_code=404, detail="Client not found")

@router.post("/clients/{client_id}/test")
async def test_client_connection(client_id: str) -> Dict[str, Any]:
    """Test connection to a specific client's MCP services"""
    for client in MOCK_CLIENTS:
        if client["id"] == client_id:
            return {
                "success": True,
                "client_id": client_id,
                "response_time_ms": 156,
                "response": "MCP connection test successful",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    raise HTTPException(status_code=404, detail="Client not found")

@router.post("/execute")
async def execute_mcp_operation(request: MCPExecuteRequest) -> Dict[str, Any]:
    """Execute an MCP operation/tool for a specific client"""
    # Validate client exists
    client = None
    for c in MOCK_CLIENTS:
        if c["id"] == request.client_id:
            client = c
            break
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not client["enabled"]:
        raise HTTPException(status_code=403, detail="Client is disabled")
    
    # Validate provider/model availability
    provider_key_map = {
        "claude": "has_klaviyo_key",
        "openai": "has_openai_key", 
        "gemini": "has_gemini_key"
    }
    
    if request.provider not in provider_key_map:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")
    
    if not client.get(provider_key_map[request.provider], False):
        raise HTTPException(status_code=400, detail=f"No API key configured for {request.provider}")
    
    # Mock tool execution based on tool name
    tool_responses = {
        "get_campaigns": {
            "campaigns": [
                {"id": "01HXYZ123", "name": "Welcome Series", "status": "active", "type": "regular"},
                {"id": "01HXYZ456", "name": "Black Friday Sale", "status": "draft", "type": "campaign"},
                {"id": "01HXYZ789", "name": "Product Recommendations", "status": "active", "type": "flow"}
            ],
            "total": 3
        },
        "get_flows": {
            "flows": [
                {"id": "01FLOW123", "name": "Abandoned Cart", "status": "live", "trigger_type": "metric"},
                {"id": "01FLOW456", "name": "Welcome Series", "status": "live", "trigger_type": "list"}
            ],
            "total": 2
        },
        "get_segments": {
            "segments": [
                {"id": "01SEG123", "name": "High Value Customers", "count": 1523},
                {"id": "01SEG456", "name": "Recent Buyers", "count": 892}
            ],
            "total": 2
        },
        "get_metrics": {
            "metrics": {
                "total_revenue": 125430.50,
                "total_orders": 2847,
                "average_order_value": 44.06,
                "email_open_rate": 0.247,
                "email_click_rate": 0.031
            }
        }
    }
    
    # Simulate execution time based on tool complexity
    execution_times = {
        "get_campaigns": 1200,
        "get_flows": 800,
        "get_segments": 1500,
        "get_metrics": 2100
    }
    
    if request.tool_name not in tool_responses:
        return {
            "success": False,
            "error": f"Unknown tool: {request.tool_name}",
            "available_tools": list(tool_responses.keys())
        }
    
    # Simulate potential failures for testing
    import random
    if random.random() < 0.05:  # 5% failure rate
        return {
            "success": False,
            "error": "Rate limit exceeded. Please try again later.",
            "retry_after": 60
        }
    
    return {
        "success": True,
        "client_id": request.client_id,
        "tool_name": request.tool_name,
        "provider": request.provider,
        "model": request.model,
        "execution_time_ms": execution_times.get(request.tool_name, 1000),
        "result": tool_responses[request.tool_name],
        "tokens_used": {
            "input": len(str(request.parameters)) * 4,  # Rough token estimation
            "output": len(str(tool_responses[request.tool_name])) * 4
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }