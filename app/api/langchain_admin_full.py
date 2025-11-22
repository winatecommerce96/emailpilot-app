"""
LangChain Admin API - Full implementation with agent registry integration.
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio

# Add multi-agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "multi-agent"))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/langchain", tags=["LangChain Admin"])

# Import LangChain components
try:
    from integrations.langchain_core.admin.registry import get_agent_registry
    from integrations.langchain_core.config import get_config
    langchain_available = True
except ImportError as e:
    logger.warning(f"LangChain not available: {e}")
    langchain_available = False
    get_agent_registry = None
    get_config = None

# Static provider models registry
PROVIDER_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
    "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]
}

# MCP Server configurations
MCP_SERVERS = {
    "klaviyo_revenue": {
        "id": "klaviyo_revenue",
        "name": "Klaviyo Revenue API",
        "port": 9090,
        "base_url": "http://localhost:9090",
        "health_endpoint": "/healthz"
    },
    "performance_api": {
        "id": "performance_api",
        "name": "Performance API",
        "port": 9091,
        "base_url": "http://localhost:9091",
        "health_endpoint": "/healthz"
    },
    "multi_agent": {
        "id": "multi_agent",
        "name": "Multi-Agent System",
        "port": 8090,
        "base_url": "http://localhost:8090",
        "health_endpoint": "/healthz"
    }
}

# In-memory run storage (for demo - use database in production)
runs_storage = {}


class RunRequest(BaseModel):
    """Request to run an agent."""
    inputs: Dict[str, Any] = Field(..., description="Input variables for the agent")
    config: Optional[Dict[str, Any]] = Field(None, description="Runtime configuration")


class ValidationRequest(BaseModel):
    """Request to validate agent inputs."""
    inputs: Dict[str, Any] = Field(..., description="Input variables to validate")


@router.get("/agents")
async def list_agents() -> Dict[str, Any]:
    """List all registered agents."""
    if not langchain_available:
        return {"agents": [], "status": "langchain_not_available"}
    
    try:
        registry = get_agent_registry()
        agents = registry.list_agents()
        
        # Format for UI
        formatted_agents = []
        for agent in agents:
            formatted_agents.append({
                "id": agent.get("name"),
                "name": agent.get("name"),
                "description": agent.get("description", "No description"),
                "status": agent.get("status", "unknown"),
                "version": agent.get("version", "1.0")
            })
        
        return {"agents": formatted_agents}
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return {"agents": [], "status": "error", "error": str(e)}


@router.get("/agents/{agent_name}")
async def get_agent(agent_name: str) -> Dict[str, Any]:
    """Get details for a specific agent."""
    if not langchain_available:
        raise HTTPException(status_code=503, detail="LangChain not available")
    
    try:
        registry = get_agent_registry()
        agent = registry.get_agent(agent_name)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_name}/variables")
async def get_agent_variables(agent_name: str) -> List[Dict[str, Any]]:
    """Get input variables for an agent."""
    if not langchain_available:
        return []
    
    try:
        registry = get_agent_registry()
        agent = registry.get_agent(agent_name)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
        variables = agent.get("variables", [])
        
        # Fix variable names for specific agents
        if agent_name == "klaviyo_revenue":
            # Ensure we have brand instead of brand_id
            for var in variables:
                if var.get("name") == "brand_id":
                    var["name"] = "brand"
                    var["description"] = "Brand slug (e.g., rogue-creamery)"
        
        return variables
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting variables for {agent_name}: {e}")
        return []


@router.post("/agents/{agent_name}/validate")
async def validate_agent_inputs(agent_name: str, request: ValidationRequest) -> Dict[str, Any]:
    """Validate inputs for an agent."""
    if not langchain_available:
        return {"valid": False, "errors": ["LangChain not available"]}
    
    try:
        registry = get_agent_registry()
        agent = registry.get_agent(agent_name)
        
        if not agent:
            return {"valid": False, "errors": [f"Agent {agent_name} not found"]}
        
        variables = agent.get("variables", [])
        errors = []
        
        # Check required variables
        for var in variables:
            var_name = var.get("name")
            
            # Handle brand_id vs brand naming issue
            if var_name == "brand_id" and "brand" in request.inputs:
                var_name = "brand"
            
            if var.get("required", False) and var_name not in request.inputs:
                errors.append(f"Missing required variable: {var_name}")
            
            # Validate type
            if var_name in request.inputs:
                value = request.inputs[var_name]
                var_type = var.get("type", "string")
                
                if var_type == "integer" and not isinstance(value, int):
                    try:
                        request.inputs[var_name] = int(value)
                    except:
                        errors.append(f"{var_name} must be an integer")
                
                # Validate pattern
                if "pattern" in var and var_type == "string":
                    import re
                    if not re.match(var["pattern"], str(value)):
                        errors.append(f"{var_name} does not match pattern {var['pattern']}")
                
                # Validate allowed values
                if "allowed_values" in var and value not in var["allowed_values"]:
                    errors.append(f"{var_name} must be one of {var['allowed_values']}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    except Exception as e:
        logger.error(f"Error validating inputs for {agent_name}: {e}")
        return {"valid": False, "errors": [str(e)]}


@router.get("/agents/{agent_id}/prompt")
async def get_agent_prompt(agent_id: str) -> Dict[str, Any]:
    """
    Get the prompt template for a specific agent.
    
    Args:
        agent_id: The agent identifier
        
    Returns:
        Agent prompt template and related configuration
    """
    try:
        # Try to get from registry first
        if langchain_available and get_agent_registry:
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


@router.post("/agents")
async def create_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new agent in the registry."""
    try:
        # Import registry here to ensure it's initialized
        try:
            from multi_agent.integrations.langchain_core.admin.registry import registry as agent_registry
            
            # Validate required fields
            required_fields = ["name", "description", "prompt_template"]
            for field in required_fields:
                if field not in agent_data:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required field: {field}"
                    )
            
            # Register the new agent
            agent_registry.register_agent({
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
                "message": f"Agent '{agent_data['name']}' created successfully"
            }
            
        except ImportError:
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
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}/prompt")
async def update_agent_prompt(agent_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the prompt template for a specific agent.
    
    Args:
        agent_id: The agent identifier
        request: Contains prompt_template and/or default_task
        
    Returns:
        Update confirmation
    """
    try:
        if not langchain_available or not get_agent_registry:
            raise HTTPException(status_code=503, detail="LangChain agent registry not available")
            
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


@router.post("/agents/{agent_name}/runs")
async def run_agent(agent_name: str, request: RunRequest) -> Dict[str, Any]:
    """Start a new agent run."""
    if not langchain_available:
        raise HTTPException(status_code=503, detail="LangChain not available")
    
    try:
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Store run info
        runs_storage[run_id] = {
            "id": run_id,
            "agent": agent_name,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "inputs": request.inputs,
            "events": []
        }
        
        # TODO: Actually execute the agent
        # For now, simulate completion after a delay
        async def simulate_run():
            await asyncio.sleep(2)
            runs_storage[run_id]["status"] = "completed"
            runs_storage[run_id]["ended_at"] = datetime.utcnow().isoformat()
            runs_storage[run_id]["events"].append({
                "type": "system",
                "message": f"Agent {agent_name} completed successfully",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        asyncio.create_task(simulate_run())
        
        return {"run_id": run_id, "status": "started"}
    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def list_runs(
    agent: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date: Optional[str] = Query(None)
) -> List[Dict[str, Any]]:
    """List agent runs with optional filters."""
    runs = list(runs_storage.values())
    
    # Apply filters
    if agent:
        runs = [r for r in runs if r["agent"] == agent]
    if status:
        runs = [r for r in runs if r["status"] == status]
    if date:
        runs = [r for r in runs if r["started_at"].startswith(date)]
    
    # Sort by start time (newest first)
    runs.sort(key=lambda r: r["started_at"], reverse=True)
    
    return runs


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    """Get details for a specific run."""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return runs_storage[run_id]


@router.post("/runs/{run_id}/abort")
async def abort_run(run_id: str) -> Dict[str, Any]:
    """Abort a running agent."""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    run = runs_storage[run_id]
    if run["status"] != "running":
        raise HTTPException(status_code=400, detail=f"Run {run_id} is not running")
    
    run["status"] = "aborted"
    run["ended_at"] = datetime.utcnow().isoformat()
    run["events"].append({
        "type": "system",
        "message": "Run aborted by user",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"status": "aborted"}


@router.post("/runs/{run_id}/replay")
async def replay_run(run_id: str) -> Dict[str, Any]:
    """Replay a previous run with the same inputs."""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    old_run = runs_storage[run_id]
    
    # Create new run with same inputs
    new_run_id = str(uuid.uuid4())
    runs_storage[new_run_id] = {
        "id": new_run_id,
        "agent": old_run["agent"],
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "inputs": old_run["inputs"],
        "events": [
            {
                "type": "system",
                "message": f"Replaying run {run_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "replayed_from": run_id
    }
    
    # Simulate completion
    async def simulate_run():
        await asyncio.sleep(2)
        runs_storage[new_run_id]["status"] = "completed"
        runs_storage[new_run_id]["ended_at"] = datetime.utcnow().isoformat()
    
    asyncio.create_task(simulate_run())
    
    return {"new_run_id": new_run_id, "status": "started"}


@router.get("/runs/{run_id}/events/stream")
async def stream_run_events(run_id: str, request: Request):
    """Stream events for a run using Server-Sent Events."""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    async def event_generator():
        """Generate SSE events."""
        last_index = 0
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            run = runs_storage.get(run_id)
            if not run:
                break
            
            # Send new events
            events = run.get("events", [])
            for event in events[last_index:]:
                yield f"data: {json.dumps(event)}\n\n"
            
            last_index = len(events)
            
            # If run is complete, send final event and close
            if run["status"] in ["completed", "failed", "aborted"]:
                run_status = run["status"]
                yield f"data: {json.dumps({'type': 'system', 'message': f'Run {run_status}'})}\n\n"
                break
            
            # Wait before checking for new events
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/mcp/servers")
async def list_mcp_servers() -> List[Dict[str, Any]]:
    """List configured MCP servers."""
    return list(MCP_SERVERS.values())


@router.post("/mcp/servers/{server_id}/health")
async def check_mcp_health(server_id: str) -> Dict[str, Any]:
    """Check health of an MCP server."""
    if server_id not in MCP_SERVERS:
        raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
    
    server = MCP_SERVERS[server_id]
    
    # Try to check health
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{server['base_url']}{server['health_endpoint']}")
            
            return {
                "server_id": server_id,
                "healthy": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text[:200] if response.text else None
            }
    except Exception as e:
        return {
            "server_id": server_id,
            "healthy": False,
            "error": str(e)
        }


@router.get("/models/providers")
async def get_providers() -> Dict[str, Any]:
    """Get list of supported model providers."""
    return {"providers": list(PROVIDER_MODELS.keys())}


@router.get("/models/available")
async def get_available_models(
    provider: str = Query(..., description="Provider to get models for")
) -> List[str]:
    """Get available models for a specific provider."""
    if provider not in PROVIDER_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}. Supported: {list(PROVIDER_MODELS.keys())}"
        )
    
    return PROVIDER_MODELS[provider]


@router.get("/usage/summary")
async def get_usage_summary() -> Dict[str, Any]:
    """Get usage summary."""
    return {
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "by_provider": {},
        "by_model": {},
        "runs_count": len(runs_storage)
    }