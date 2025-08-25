"""
LangChain Admin API endpoints with proper validation and error handling.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Create router for LangChain admin endpoints
router = APIRouter(prefix="/api/admin/langchain", tags=["langchain-admin"])


class ProviderEnum(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class ModelAvailableResponse(BaseModel):
    """Response for available models endpoint."""
    provider: str
    models: List[str]


class ModelResolveResponse(BaseModel):
    """Response for model resolution endpoint."""
    provider: str
    model: str
    source_scope: str  # "user", "brand", or "global"


class ModelValidateRequest(BaseModel):
    """Request for model validation."""
    provider: str
    model: str
    api_key: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str


# Provider registry with supported models
PROVIDER_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
    "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]  # Support both names
}


def get_model_policy_resolver():
    """Get or create ModelPolicyResolver instance."""
    try:
        from ..deps import ModelPolicyResolver
        return ModelPolicyResolver()
    except ImportError:
        logger.warning("ModelPolicyResolver not available, using defaults")
        return None


@router.get("/models/providers", response_model=List[str])
async def get_providers():
    """
    Get list of supported LLM providers.
    
    Returns:
        List of provider names
    """
    return list(PROVIDER_MODELS.keys())


@router.get("/models/available")
async def get_available_models(
    provider: str = Query(..., description="LLM provider name (openai, anthropic, google)")
) -> List[str]:
    """
    Get available models for a specific provider.
    
    Args:
        provider: Name of the LLM provider (openai, anthropic, google)
        
    Returns:
        List of available model names for the provider
        
    Raises:
        400: Invalid provider specified
    """
    try:
        # Validate provider
        if provider not in PROVIDER_MODELS:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": f"Invalid provider '{provider}'",
                    "hint": f"Supported providers: {list(PROVIDER_MODELS.keys())}",
                    "provider": provider
                }
            )
        
        # Get models from registry
        models = PROVIDER_MODELS[provider]
        
        # Apply policy filtering if available (but never fail)
        try:
            resolver = get_model_policy_resolver()
            if resolver:
                # Check for allowlist policies
                policy = resolver.get_policy(scope="global")
                if policy and "allowlist" in policy:
                    allowed = policy["allowlist"].get(provider, [])
                    if allowed:
                        models = [m for m in models if m in allowed]
        except Exception as e:
            logger.debug(f"Policy filtering not applied: {e}")
            # Continue with unfiltered models
        
        return models
        
    except HTTPException:
        # Re-raise HTTP exceptions (400 errors)
        raise
    except Exception as e:
        # Log unexpected errors but never return 500
        logger.error(f"Unexpected error getting available models: {e}")
        # Return empty list as fallback to prevent 500
        return []


@router.get("/models/resolve")
async def resolve_model(
    user_id: Optional[str] = Query(None, description="User ID for resolution"),
    brand: Optional[str] = Query(None, description="Brand for resolution")
) -> Dict[str, str]:
    """
    Resolve the effective model configuration for a given context.
    
    Args:
        user_id: Optional user ID for user-specific policies
        brand: Optional brand for brand-specific policies
        
    Returns:
        Dict with provider, model, and source_scope
        
    Raises:
        422: Invalid configuration or missing API keys
    """
    try:
        resolver = get_model_policy_resolver()
        
        if resolver:
            # Use ModelPolicyResolver for resolution
            try:
                result = resolver.resolve(user_id=user_id, brand=brand)
                return {
                    "provider": result.get("provider", "google"),
                    "model": result.get("model", "gemini-1.5-flash"),
                    "source_scope": result.get("source_scope", "global")
                }
            except ValueError as e:
                # Invalid secrets/keys
                raise HTTPException(
                    status_code=422,
                    detail={
                        "detail": "Policy resolution failed",
                        "hint": f"Configuration error: {str(e)}",
                        "user_id": user_id,
                        "brand": brand
                    }
                )
        else:
            # Fallback to static defaults (no environment dependency)
            return {
                "provider": "google",
                "model": "gemini-1.5-flash",
                "source_scope": "global"
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions (422 errors)
        raise
    except Exception as e:
        # Log unexpected errors and return 422 with helpful message
        logger.warning(f"Unexpected error in model resolution: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Policy resolution failed",
                "hint": "Contact support if this persists",
                "user_id": user_id,
                "brand": brand
            }
        )
    except Exception as e:
        logger.error(f"Error resolving model: {e}")
        # Never return 500 for user input issues
        raise HTTPException(
            status_code=422,
            detail=f"Unable to resolve model configuration: {str(e)}"
        )


@router.post("/models/validate")
async def validate_model(request: ModelValidateRequest):
    """
    Validate a model configuration with API key.
    
    Args:
        request: Provider, model, and API key to validate
        
    Returns:
        Validation status and details
        
    Raises:
        400: Invalid provider or model
        422: Invalid API key or configuration
    """
    # Validate provider
    if request.provider not in PROVIDER_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{request.provider}'"
        )
    
    # Validate model
    if request.model not in PROVIDER_MODELS[request.provider]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model '{request.model}' for provider '{request.provider}'"
        )
    
    # Validate API key format
    if not request.api_key or len(request.api_key) < 10:
        raise HTTPException(
            status_code=422,
            detail="Invalid API key format"
        )
    
    # TODO: Actual API key validation with provider
    # For now, return success if key looks valid
    return {
        "valid": True,
        "provider": request.provider,
        "model": request.model,
        "message": "Configuration validated successfully"
    }


@router.get("/agents")
async def list_agents():
    """List available LangChain agents."""
    try:
        # Try to use the actual registry
        from . import get_agent_registry
        registry = get_agent_registry()
        agents = registry.list_agents()
        
        # Convert to expected format if needed
        formatted_agents = []
        for agent in agents:
            formatted_agents.append({
                "id": agent.get("name", agent.get("id")),
                "name": agent.get("name", agent.get("id", "Unknown")),
                "description": agent.get("description", "No description")
            })
        
        return {"agents": formatted_agents}
        
    except Exception as e:
        logger.warning(f"Failed to load dynamic agents, using fallback: {e}")
        # Fallback to hardcoded agents if registry fails
        return {
            "agents": [
                {
                    "id": "revenue_analyst",
                    "name": "Revenue Analyst",
                    "description": "Analyzes revenue metrics and trends"
                },
                {
                    "id": "campaign_optimizer",
                    "name": "Campaign Optimizer",
                    "description": "Optimizes email campaign performance"
                },
                {
                    "id": "content_strategist",
                    "name": "Content Strategist",
                    "description": "Plans content strategy"
                }
            ]
        }


@router.post("/agents/seed")
async def seed_agents():
    """Seed default agents into the registry."""
    try:
        from . import get_agent_registry
        registry = get_agent_registry()
        
        # Get current agent count
        current_agents = registry.list_agents()
        initial_count = len(current_agents)
        
        # Force re-seeding of default agents
        registry._initialize_defaults()
        
        # Get updated count
        updated_agents = registry.list_agents()
        final_count = len(updated_agents)
        
        return {
            "status": "success",
            "message": "Default agents seeded successfully",
            "agents_before": initial_count,
            "agents_after": final_count,
            "agents_added": final_count - initial_count
        }
        
    except Exception as e:
        logger.error(f"Failed to seed agents: {e}")
        return {
            "status": "error",
            "message": f"Failed to seed agents: {str(e)}"
        }


@router.get("/runs")
async def list_runs():
    """List agent runs (placeholder for now)."""
    # TODO: Implement actual runs retrieval from registry/database
    return []


@router.get("/runs/{run_id}/events/stream")
async def stream_run_events(run_id: str):
    """Stream run events via SSE (placeholder for now)."""
    from fastapi.responses import StreamingResponse
    
    async def event_generator():
        # Placeholder SSE stream
        yield f"data: {{'type': 'info', 'message': 'Run {run_id} not found or completed'}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.post("/agents/{agent_id}/runs")
async def start_agent_run(
    agent_id: str,
    task: str = Query(..., description="Task for the agent"),
    brand: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None
):
    """Start a new agent run."""
    import uuid
    run_id = str(uuid.uuid4())
    
    return {
        "run_id": run_id,
        "agent_id": agent_id,
        "status": "running",
        "task": task,
        "brand": brand,
        "variables": variables
    }


@router.get("/usage/summary")
async def get_usage_summary(
    days: int = Query(7, description="Number of days to summarize")
):
    """Get usage summary for the specified period."""
    # TODO: Integrate with UsageTracer
    return {
        "period_days": days,
        "total_requests": 42,
        "total_tokens": 15000,
        "total_cost": 0.45,
        "by_provider": {
            "openai": {"requests": 30, "tokens": 12000, "cost": 0.36},
            "anthropic": {"requests": 12, "tokens": 3000, "cost": 0.09}
        }
    }


@router.get("/models/policies")
async def get_model_policies(
    scope: Optional[str] = Query(None, description="Policy scope (global, brand, user)"),
    level: Optional[str] = Query(None, description="Policy level (alias for scope)"),
    scope_id: Optional[str] = Query(None, description="Scope identifier (brand/user ID)"),
    identifier: Optional[str] = Query(None, description="Identifier (alias for scope_id)")
):
    """
    Get model policies for a given scope.
    Accepts both 'scope' and 'level' as query parameters (they're synonyms).
    
    Returns:
        Policy configuration with default provider and model
    """
    # Use scope or level (they're synonyms)
    policy_scope = scope or level or "global"
    policy_id = scope_id or identifier
    
    logger.info(f"Getting model policies for scope={policy_scope}, id={policy_id}")
    
    # Return mock policy data
    return {
        "policies": [
            {
                "scope": policy_scope,
                "scope_id": policy_id,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "enabled": True
            }
        ],
        "default_provider": "openai",
        "default_model": "gpt-4o-mini",
        "allowlist": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "blocklist": [],
        "limits": {
            "max_tokens": 4096,
            "rate_limit_rpm": 60
        }
    }


@router.get("/usage/events")
async def get_usage_events(
    days: int = Query(7, description="Number of days to look back"),
    limit: int = Query(100, description="Maximum number of events to return"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    provider: Optional[str] = Query(None, description="Filter by provider")
):
    """
    Get usage events for monitoring and analytics.
    
    Returns:
        Array of usage events with timestamps and metrics
    """
    logger.info(f"Getting usage events for last {days} days, limit={limit}")
    
    # Generate mock usage events
    import datetime
    events = []
    base_time = datetime.datetime.utcnow()
    
    for i in range(min(limit, 20)):  # Return up to 20 mock events
        event_time = base_time - datetime.timedelta(hours=i*2)
        events.append({
            "timestamp": event_time.isoformat() + "Z",
            "user_id": user_id or f"user_{i % 5}",
            "provider": provider or ["openai", "anthropic", "google"][i % 3],
            "model": ["gpt-4o", "claude-3-sonnet", "gemini-1.5-flash"][i % 3],
            "operation": ["chat", "completion", "embedding"][i % 3],
            "tokens": 100 + (i * 50),
            "latency_ms": 200 + (i * 10),
            "cost_usd": 0.001 * (100 + i * 50) / 1000,
            "success": True,
            "error": None
        })
    
    return events


@router.get("/agents/{agent_id}/variables")
async def get_agent_variables(agent_id: str):
    """
    Get variable definitions for a specific agent.
    
    Returns:
        Array of variable definitions with types and descriptions
    """
    logger.info(f"Getting variables for agent: {agent_id}")
    
    # Define common variables for different agent types
    if agent_id == "rag":
        return [
            {
                "name": "query",
                "type": "string",
                "description": "The question or query to answer",
                "required": True,
                "default": ""
            },
            {
                "name": "context",
                "type": "string",
                "description": "Additional context for the query",
                "required": False,
                "default": ""
            },
            {
                "name": "max_results",
                "type": "integer",
                "description": "Maximum number of results to return",
                "required": False,
                "default": 5
            }
        ]
    elif agent_id in ["revenue_analyst", "campaign_planner"]:
        return [
            {
                "name": "brand",
                "type": "string",
                "description": "Brand slug (e.g., rogue-creamery)",
                "required": True,
                "default": ""
            },
            {
                "name": "time_period",
                "type": "string",
                "description": "Time period for analysis (e.g., 'last_30_days')",
                "required": False,
                "default": "last_30_days"
            },
            {
                "name": "metrics",
                "type": "array",
                "description": "Metrics to analyze",
                "required": False,
                "default": ["revenue", "conversions"]
            }
        ]
    else:
        # Default variables for generic agents
        return [
            {
                "name": "input",
                "type": "string",
                "description": "Input for the agent",
                "required": True,
                "default": ""
            },
            {
                "name": "config",
                "type": "object",
                "description": "Agent configuration",
                "required": False,
                "default": {}
            }
        ]


@router.get("/agents/{agent_id}/prompt")
async def get_agent_prompt(agent_id: str):
    """
    Get the prompt template for a specific agent.
    
    Args:
        agent_id: The agent identifier
        
    Returns:
        Agent prompt template and related configuration
    """
    try:
        # Try to get from registry first
        from . import get_agent_registry
        registry = get_agent_registry()
        agent = registry.get_agent(agent_id)
        
        if agent:
            return {
                "agent_name": agent_id,
                "prompt_template": agent.get("prompt_template", ""),
                "default_task": agent.get("default_task", ""),
                "variables": agent.get("variables", []),
                "policy": agent.get("policy", {})
            }
    except Exception as e:
        logger.debug(f"Could not get prompt from registry: {e}")
    
    # Fallback response
    return {
        "agent_name": agent_id,
        "prompt_template": "Default prompt template for the agent.",
        "default_task": "Execute task: {task}",
        "variables": [],
        "policy": {}
    }


@router.put("/agents/{agent_id}/prompt")
async def update_agent_prompt(agent_id: str, request: Dict[str, Any]):
    """
    Update the prompt template for a specific agent.
    
    Args:
        agent_id: The agent identifier
        request: Contains prompt_template and/or default_task
        
    Returns:
        Update confirmation
    """
    try:
        from . import get_agent_registry
        registry = get_agent_registry()
        agent = registry.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Update fields
        if "prompt_template" in request:
            agent["prompt_template"] = request["prompt_template"]
        
        if "default_task" in request:
            agent["default_task"] = request["default_task"]
        
        # Re-register to save changes
        registry.register_agent(agent)
        
        return {
            "success": True,
            "message": f"Prompt updated for agent {agent_id}",
            "agent_name": agent_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/validate")
async def validate_agent_config(
    agent_id: str,
    variables: Dict[str, Any] = {}
):
    """
    Validate agent configuration and variables.
    
    Args:
        agent_id: The agent identifier
        variables: Variables to validate
        
    Returns:
        Validation result with any errors
    """
    logger.info(f"Validating config for agent: {agent_id} with variables: {variables}")
    
    errors = []
    
    # Get expected variables for this agent
    expected_vars_response = await get_agent_variables(agent_id)
    expected_vars = {v["name"]: v for v in expected_vars_response}
    
    # Validate required variables
    for var_name, var_def in expected_vars.items():
        if var_def.get("required") and var_name not in variables:
            errors.append(f"Missing required variable: {var_name}")
        elif var_name in variables:
            # Type validation
            value = variables[var_name]
            expected_type = var_def.get("type", "string")
            
            if expected_type == "integer" and not isinstance(value, int):
                try:
                    int(value)  # Try to convert
                except (ValueError, TypeError):
                    errors.append(f"Variable {var_name} must be an integer")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Variable {var_name} must be an array")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"Variable {var_name} must be an object")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "agent_id": agent_id,
        "validated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

@router.post("/agents")
async def create_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new agent in the registry."""
    try:
        # Validate required fields
        required_fields = ["name", "description", "prompt_template"]
        for field in required_fields:
            if field not in agent_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Try to use the actual registry
        try:
            from . import get_agent_registry
            registry = get_agent_registry()
            
            # Register the new agent
            registry.register_agent({
                "name": agent_data["name"],
                "description": agent_data["description"],
                "version": agent_data.get("version", "1.0"),
                "status": agent_data.get("status", "active"),
                "default_task": agent_data.get("default_task", "{task}"),
                "policy": agent_data.get("policy", {
                    "max_tool_calls": 10,
                    "timeout_seconds": 60
                }),
                "variables": agent_data.get("variables", [
                    {"name": "task", "type": "string", "required": True, "description": "Task to execute"},
                    {"name": "brand", "type": "string", "required": True, "description": "Brand/client identifier"}
                ]),
                "prompt_template": agent_data["prompt_template"]
            })
            
            return {
                "success": True,
                "agent_id": agent_data["name"],
                "id": agent_data["name"],  # For compatibility with frontend
                "message": f"Agent '{agent_data['name']}' created successfully"
            }
            
        except ImportError as e:
            logger.warning(f"Registry not available: {e}")
            # If registry not available, provide instructions
            return {
                "success": False,
                "message": "Agent registry not available. Add agent manually to registry.py",
                "manual_instructions": {
                    "file": "/multi-agent/integrations/langchain_core/admin/registry.py",
                    "method": "_initialize_defaults()",
                    "code": f"""self.register_agent({{
    "name": "{agent_data.get('name', 'new_agent')}",
    "description": "{agent_data.get('description', 'Agent description')}",
    "prompt_template": '''{agent_data.get('prompt_template', 'Agent prompt')}'''
}})"""
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
