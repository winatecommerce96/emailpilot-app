"""
MCP Management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.mcp_client import MCPClient, MCPUsage, MCPModelConfig
from app.schemas.mcp_client import (
    MCPClientCreate,
    MCPClientUpdate,
    MCPClientResponse,
    MCPUsageResponse,
    MCPUsageStats,
    MCPModelConfigResponse,
    MCPTestRequest,
    MCPTestResponse,
    ModelProvider
)
from app.services.secret_manager import get_secret_manager
from app.services.mcp_service import get_mcp_service
import logging
from sqlalchemy import func, and_
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/mcp",
    tags=["MCP Management"]
)


@router.get("/clients", response_model=List[MCPClientResponse])
async def list_mcp_clients(
    skip: int = 0,
    limit: int = 100,
    enabled_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all MCP clients"""
    query = db.query(MCPClient)
    
    if enabled_only:
        query = query.filter(MCPClient.enabled == True)
    
    clients = query.offset(skip).limit(limit).all()
    
    # Convert to response model with has_key flags
    responses = []
    secret_manager = get_secret_manager()
    
    for client in clients:
        api_keys = secret_manager.get_api_keys(client.id)
        response = MCPClientResponse(
            **client.__dict__,
            has_klaviyo_key=bool(api_keys.get("klaviyo")),
            has_openai_key=bool(api_keys.get("openai")),
            has_gemini_key=bool(api_keys.get("gemini"))
        )
        responses.append(response)
    
    return responses


@router.get("/clients/{client_id}", response_model=MCPClientResponse)
async def get_mcp_client(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific MCP client"""
    client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check API key existence
    secret_manager = get_secret_manager()
    api_keys = secret_manager.get_api_keys(client_id)
    
    return MCPClientResponse(
        **client.__dict__,
        has_klaviyo_key=bool(api_keys.get("klaviyo")),
        has_openai_key=bool(api_keys.get("openai")),
        has_gemini_key=bool(api_keys.get("gemini"))
    )


@router.post("/clients", response_model=MCPClientResponse)
async def create_mcp_client(
    client_data: MCPClientCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new MCP client"""
    # Check if client already exists
    existing = db.query(MCPClient).filter(
        (MCPClient.account_id == client_data.account_id) |
        (MCPClient.name == client_data.name)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Client with this account ID or name already exists"
        )
    
    # Store API keys in Secret Manager
    secret_manager = get_secret_manager()
    api_keys = {
        "klaviyo": client_data.klaviyo_api_key,
        "openai": client_data.openai_api_key,
        "gemini": client_data.gemini_api_key
    }
    
    # Create client
    client = MCPClient(
        name=client_data.name,
        account_id=client_data.account_id,
        enabled=client_data.enabled,
        read_only=client_data.read_only,
        default_model_provider=client_data.default_model_provider,
        model_settings=client_data.model_settings,
        rate_limit_requests_per_minute=client_data.rate_limit_requests_per_minute,
        rate_limit_tokens_per_day=client_data.rate_limit_tokens_per_day,
        webhook_url=client_data.webhook_url,
        custom_settings=client_data.custom_settings,
        created_by=current_user.get("username", "admin")
    )
    
    db.add(client)
    db.flush()  # Get the ID
    
    # Store secrets and update client with secret IDs
    secret_ids = secret_manager.store_api_keys(client.id, api_keys)
    for key, value in secret_ids.items():
        setattr(client, key, value)
    
    db.commit()
    db.refresh(client)
    
    return MCPClientResponse(
        **client.__dict__,
        has_klaviyo_key=bool(api_keys.get("klaviyo")),
        has_openai_key=bool(api_keys.get("openai")),
        has_gemini_key=bool(api_keys.get("gemini"))
    )


@router.put("/clients/{client_id}", response_model=MCPClientResponse)
async def update_mcp_client(
    client_id: str,
    client_data: MCPClientUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an MCP client"""
    client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Update basic fields
    update_data = client_data.dict(exclude_unset=True)
    api_key_updates = {}
    
    # Extract API key updates
    for key in ["klaviyo_api_key", "openai_api_key", "gemini_api_key"]:
        if key in update_data:
            provider = key.replace("_api_key", "")
            api_key_updates[provider] = update_data.pop(key)
    
    # Update client fields
    for field, value in update_data.items():
        setattr(client, field, value)
    
    # Update API keys if provided
    if api_key_updates:
        secret_manager = get_secret_manager()
        secret_ids = secret_manager.store_api_keys(client_id, api_key_updates)
        for key, value in secret_ids.items():
            setattr(client, key, value)
    
    client.updated_at = datetime.now()
    db.commit()
    db.refresh(client)
    
    # Get current API key status
    secret_manager = get_secret_manager()
    api_keys = secret_manager.get_api_keys(client_id)
    
    return MCPClientResponse(
        **client.__dict__,
        has_klaviyo_key=bool(api_keys.get("klaviyo")),
        has_openai_key=bool(api_keys.get("openai")),
        has_gemini_key=bool(api_keys.get("gemini"))
    )


@router.delete("/clients/{client_id}")
async def delete_mcp_client(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an MCP client"""
    client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Delete API keys from Secret Manager
    secret_manager = get_secret_manager()
    for provider in ["klaviyo", "openai", "gemini"]:
        secret_id = f"mcp-{client_id}-{provider}-key"
        secret_manager.delete_secret(secret_id)
    
    # Delete usage records
    db.query(MCPUsage).filter(MCPUsage.client_id == client_id).delete()
    
    # Delete client
    db.delete(client)
    db.commit()
    
    return {"message": "Client deleted successfully"}


@router.post("/clients/{client_id}/test", response_model=MCPTestResponse)
async def test_mcp_connection(
    client_id: str,
    test_request: MCPTestRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test MCP connection for a specific provider"""
    client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    mcp_service = get_mcp_service()
    
    try:
        start_time = datetime.now()
        
        # Test the connection
        result = await mcp_service.test_connection(client_id, test_request.model_provider)
        
        # Execute a test query if connection successful
        if result["success"]:
            tool_result = await mcp_service.execute_tool(
                client_id=client_id,
                tool_name="get_campaigns",
                parameters={"limit": 1},
                provider=test_request.model_provider
            )
            
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return MCPTestResponse(
                success=True,
                provider=test_request.model_provider,
                model_name=result.get("model", "default"),
                response=f"Successfully connected. Available tools: {len(result.get('available_tools', []))}",
                latency_ms=latency_ms,
                tokens_used=tool_result.get("request_tokens", 0) + tool_result.get("response_tokens", 0)
            )
        else:
            return MCPTestResponse(
                success=False,
                provider=test_request.model_provider,
                model_name="",
                error=result.get("error", "Connection failed"),
                latency_ms=0,
                tokens_used=0
            )
            
    except Exception as e:
        logger.error(f"Error testing MCP connection: {e}")
        return MCPTestResponse(
            success=False,
            provider=test_request.model_provider,
            model_name="",
            error=str(e),
            latency_ms=0,
            tokens_used=0
        )


@router.post("/execute")
async def execute_mcp_tool(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute an MCP tool"""
    client_id = request.get("client_id")
    tool_name = request.get("tool_name")
    parameters = request.get("parameters", {})
    provider = request.get("provider")
    model = request.get("model")
    
    if not client_id or not tool_name:
        raise HTTPException(
            status_code=400,
            detail="client_id and tool_name are required"
        )
    
    # Check if client exists and is enabled
    client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not client.enabled:
        raise HTTPException(status_code=403, detail="Client is disabled")
    
    # Check rate limiting
    if not await _check_rate_limit(client, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    # Execute tool
    mcp_service = get_mcp_service()
    
    try:
        result = await mcp_service.execute_tool(
            client_id=client_id,
            tool_name=tool_name,
            parameters=parameters,
            provider=provider or client.default_model_provider,
            model=model
        )
        
        return {
            "success": True,
            "result": result.get("result"),
            "tokens_used": result.get("request_tokens", 0) + result.get("response_tokens", 0),
            "provider": provider or client.default_model_provider,
            "model": model
        }
        
    except Exception as e:
        logger.error(f"Error executing MCP tool: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing tool: {str(e)}"
        )


@router.get("/usage/{client_id}", response_model=List[MCPUsageResponse])
async def get_client_usage(
    client_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage history for a client"""
    query = db.query(MCPUsage).filter(MCPUsage.client_id == client_id)
    
    if start_date:
        query = query.filter(MCPUsage.requested_at >= start_date)
    
    if end_date:
        query = query.filter(MCPUsage.requested_at <= end_date)
    
    usage_records = query.order_by(MCPUsage.requested_at.desc()).limit(limit).all()
    
    return [MCPUsageResponse.from_orm(record) for record in usage_records]


@router.get("/usage/{client_id}/stats", response_model=MCPUsageStats)
async def get_client_usage_stats(
    client_id: str,
    period: str = "daily",  # daily, weekly, monthly
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage statistics for a client"""
    # Determine date range based on period
    end_date = datetime.now()
    if period == "daily":
        start_date = end_date - timedelta(days=1)
    elif period == "weekly":
        start_date = end_date - timedelta(weeks=1)
    elif period == "monthly":
        start_date = end_date - timedelta(days=30)
    else:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Get usage records
    usage_records = db.query(MCPUsage).filter(
        and_(
            MCPUsage.client_id == client_id,
            MCPUsage.requested_at >= start_date,
            MCPUsage.requested_at <= end_date
        )
    ).all()
    
    if not usage_records:
        return MCPUsageStats(
            client_id=client_id,
            period=period,
            total_requests=0,
            total_tokens=0,
            total_cost=0,
            avg_latency_ms=0,
            success_rate=0,
            top_tools=[],
            model_breakdown={}
        )
    
    # Calculate statistics
    total_requests = len(usage_records)
    total_tokens = sum(r.total_tokens for r in usage_records)
    total_cost = sum(r.estimated_cost for r in usage_records)
    avg_latency = sum(r.latency_ms or 0 for r in usage_records) / len(usage_records)
    success_count = sum(1 for r in usage_records if r.status == "success")
    success_rate = (success_count / total_requests) * 100
    
    # Tool usage breakdown
    tool_counts = {}
    for record in usage_records:
        tool_counts[record.tool_name] = tool_counts.get(record.tool_name, 0) + 1
    
    top_tools = [
        {"tool": tool, "count": count, "percentage": (count / total_requests) * 100}
        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Model breakdown
    model_breakdown = {}
    for record in usage_records:
        key = f"{record.model_provider}:{record.model_name}"
        if key not in model_breakdown:
            model_breakdown[key] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0,
                "avg_latency_ms": 0
            }
        
        model_breakdown[key]["requests"] += 1
        model_breakdown[key]["tokens"] += record.total_tokens
        model_breakdown[key]["cost"] += record.estimated_cost
        model_breakdown[key]["avg_latency_ms"] += (record.latency_ms or 0)
    
    # Calculate averages
    for key in model_breakdown:
        if model_breakdown[key]["requests"] > 0:
            model_breakdown[key]["avg_latency_ms"] /= model_breakdown[key]["requests"]
    
    return MCPUsageStats(
        client_id=client_id,
        period=period,
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_cost=total_cost,
        avg_latency_ms=avg_latency,
        success_rate=success_rate,
        top_tools=top_tools,
        model_breakdown=model_breakdown
    )


@router.get("/models", response_model=List[MCPModelConfigResponse])
async def list_available_models(
    provider: Optional[ModelProvider] = None,
    enabled_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List available AI models"""
    query = db.query(MCPModelConfig)
    
    if provider:
        query = query.filter(MCPModelConfig.provider == provider)
    
    if enabled_only:
        query = query.filter(MCPModelConfig.enabled == True)
    
    models = query.all()
    
    # If no models in DB, return default configurations
    if not models:
        mcp_service = get_mcp_service()
        default_models = []
        
        for provider_name, provider_config in mcp_service.model_configs.items():
            for model_key, model_info in provider_config.get("models", {}).items():
                default_models.append(MCPModelConfigResponse(
                    id=f"{provider_name}:{model_key}",
                    provider=provider_name,
                    model_name=model_key,
                    display_name=model_info["display_name"],
                    supports_functions=True,
                    supports_vision="vision" in model_key.lower(),
                    supports_streaming=True,
                    max_tokens=model_info["max_tokens"],
                    context_window=model_info["context_window"],
                    input_cost_per_1k=model_info.get("input_cost_per_1k"),
                    output_cost_per_1k=model_info.get("output_cost_per_1k"),
                    default_temperature=0.7,
                    default_max_tokens=2048,
                    enabled=True,
                    deprecated=False
                ))
        
        return default_models
    
    return [MCPModelConfigResponse.from_orm(model) for model in models]


async def _check_rate_limit(client: MCPClient, db: Session) -> bool:
    """Check if client has exceeded rate limits"""
    # Check per-minute rate limit
    one_minute_ago = datetime.now() - timedelta(minutes=1)
    recent_requests = db.query(func.count(MCPUsage.id)).filter(
        and_(
            MCPUsage.client_id == client.id,
            MCPUsage.requested_at >= one_minute_ago
        )
    ).scalar()
    
    if recent_requests >= client.rate_limit_requests_per_minute:
        return False
    
    # Check daily token limit
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_tokens = db.query(func.sum(MCPUsage.total_tokens)).filter(
        and_(
            MCPUsage.client_id == client.id,
            MCPUsage.requested_at >= today_start
        )
    ).scalar() or 0
    
    if today_tokens >= client.rate_limit_tokens_per_day:
        return False
    
    return True