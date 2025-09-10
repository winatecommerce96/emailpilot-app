"""
MCP Management API

API endpoints for registering, managing, and querying MCP tools with AI capabilities.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from app.deps import get_db
from app.services.universal_mcp_registry import UniversalMCPRegistry
from app.services.llm_selector import LLMSelector, OptimizationMode
from google.cloud import firestore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp", tags=["MCP Management"])


# Request/Response Models
class MCPConfig(BaseModel):
    """Configuration for a new MCP tool"""
    name: str = Field(..., description="Name of the MCP tool")
    description: Optional[str] = Field(None, description="Description of the tool")
    base_url: Optional[str] = Field(None, description="Base URL for the API")
    auth_type: str = Field("api_key", description="Authentication type")
    service_type: Optional[str] = Field(None, description="Type of service (marketing, financial, etc.)")
    endpoints: Optional[List[Dict[str, Any]]] = Field(None, description="Known endpoints")
    example_queries: Optional[List[str]] = Field(None, description="Example queries")


class QueryRequest(BaseModel):
    """Request for querying an MCP"""
    query: str = Field(..., description="Natural language query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    optimization: str = Field("balanced", description="Optimization mode")


class PromptUpdate(BaseModel):
    """Update request for agent prompts"""
    system_prompt: str = Field(..., description="New system prompt")
    examples: Optional[List[str]] = Field(None, description="Example queries")


class MCPTestRequest(BaseModel):
    """Request for testing MCP queries"""
    mcp_id: str = Field(..., description="MCP identifier")
    query: str = Field(..., description="Test query")
    use_cache: bool = Field(True, description="Use cached responses if available")


# Singleton instance of the registry
_registry_instance: Optional[UniversalMCPRegistry] = None

# Dependency injection
async def get_mcp_registry(db: firestore.Client = Depends(get_db)) -> UniversalMCPRegistry:
    """Get MCP registry instance (singleton pattern)"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = UniversalMCPRegistry(db)
    return _registry_instance


async def get_llm_selector() -> LLMSelector:
    """Get LLM selector instance"""
    return LLMSelector()


# Endpoints
@router.post("/register")
async def register_mcp(
    config: MCPConfig,
    background_tasks: BackgroundTasks,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> Dict[str, Any]:
    """
    Register a new MCP tool with automatic AI wrapper and agent generation
    """
    try:
        # Add ID if not present
        mcp_dict = config.dict()
        if 'id' not in mcp_dict:
            mcp_dict['id'] = config.name.lower().replace(' ', '_')
        
        # Register MCP
        result = await registry.register_new_mcp(mcp_dict)
        
        # Log registration in background
        background_tasks.add_task(
            log_mcp_registration,
            mcp_dict['id'],
            config.name
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to register MCP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_mcps(
    status: Optional[str] = None,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> List[Dict[str, Any]]:
    """
    List all registered MCP tools
    """
    try:
        mcps = await registry.list_mcps(status)
        return mcps
    except Exception as e:
        logger.error(f"Failed to list MCPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mcp_id}")
async def get_mcp(
    mcp_id: str,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> Dict[str, Any]:
    """
    Get details of a specific MCP tool
    """
    try:
        mcp = await registry.get_mcp(mcp_id)
        if not mcp:
            raise HTTPException(status_code=404, detail=f"MCP {mcp_id} not found")
        return mcp
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP {mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mcp_id}/tools")
async def get_mcp_tools(
    mcp_id: str,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> List[Dict[str, Any]]:
    """
    Get all tools for a specific MCP
    """
    try:
        tools = await registry.get_mcp_tools(mcp_id)
        return tools
    except Exception as e:
        logger.error(f"Failed to get tools for MCP {mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{mcp_id}/query")
async def query_mcp(
    mcp_id: str,
    request: QueryRequest,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry),
    llm_selector: LLMSelector = Depends(get_llm_selector)
) -> Dict[str, Any]:
    """
    Query an MCP using its AI wrapper with natural language
    """
    try:
        # Get MCP configuration
        mcp = await registry.get_mcp(mcp_id)
        if not mcp:
            raise HTTPException(status_code=404, detail=f"MCP {mcp_id} not found")
        
        # Get wrapper
        wrapper = await get_mcp_wrapper(mcp_id, registry)
        
        # Select LLM based on optimization
        optimization = OptimizationMode(request.optimization.lower())
        llm_model = llm_selector.select_for_mcp(mcp_id)
        
        # Process query
        start_time = datetime.now()
        result = await wrapper.process_query(request.query, request.context)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Update metrics
        await registry.update_mcp_metrics(mcp_id, {
            'total_queries': firestore.Increment(1),
            'last_query': datetime.now()
        })
        
        return {
            'success': result.get('success', False),
            'data': result.get('data'),
            'mcp_id': mcp_id,
            'llm_model': llm_model,
            'processing_time_ms': processing_time,
            'query': request.query
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query MCP {mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{mcp_id}/invoke")
async def invoke_mcp_tool(
    mcp_id: str,
    tool_name: str,
    params: Dict[str, Any],
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> Dict[str, Any]:
    """
    Directly invoke a specific tool of an MCP
    """
    try:
        # Get wrapper
        wrapper = await get_mcp_wrapper(mcp_id, registry)
        
        # Invoke tool
        result = await wrapper.invoke_tool(tool_name, params)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to invoke tool {tool_name} for MCP {mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mcp_id}/agent")
async def get_mcp_agent(
    mcp_id: str,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> Dict[str, Any]:
    """
    Get the LangChain agent for an MCP
    """
    try:
        mcp = await registry.get_mcp(mcp_id)
        if not mcp:
            raise HTTPException(status_code=404, detail=f"MCP {mcp_id} not found")
        
        agent_info = mcp.get('agent', {})
        
        return {
            'mcp_id': mcp_id,
            'agent_name': agent_info.get('name'),
            'description': agent_info.get('description'),
            'llm_model': agent_info.get('llm_model'),
            'status': 'active'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent for MCP {mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{mcp_id}/prompts")
async def update_mcp_prompts(
    mcp_id: str,
    prompts: PromptUpdate,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> Dict[str, str]:
    """
    Update the prompts for an MCP's agent
    """
    try:
        # Get agent factory
        from app.services.universal_mcp_registry import MCPAgentFactory
        llm_selector = LLMSelector()
        agent_factory = MCPAgentFactory(llm_selector)
        
        # Update prompts
        await agent_factory.update_agent_prompt(mcp_id, prompts.system_prompt)
        
        # Update in Firestore
        await registry.db.collection('mcp_registry').document(mcp_id).update({
            'agent.system_prompt': prompts.system_prompt,
            'agent.examples': prompts.examples or [],
            'updated_at': datetime.now()
        })
        
        return {'status': 'updated', 'mcp_id': mcp_id}
        
    except Exception as e:
        logger.error(f"Failed to update prompts for MCP {mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{mcp_id}/test")
async def test_mcp_query(
    test_request: MCPTestRequest,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> Dict[str, Any]:
    """
    Test a query against an MCP with detailed debugging info
    """
    try:
        wrapper = await get_mcp_wrapper(test_request.mcp_id, registry)
        
        # Process with detailed logging
        result = await wrapper.process_query(test_request.query, {'debug': True})
        
        return {
            'mcp_id': test_request.mcp_id,
            'query': test_request.query,
            'success': result.get('success'),
            'result': result.get('data'),
            'debug_info': {
                'intent': result.get('intent'),
                'tools_tried': result.get('tools_tried', []),
                'errors': result.get('errors', [])
            }
        }
        
    except Exception as e:
        logger.error(f"Test query failed for MCP {test_request.mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{mcp_id}")
async def deactivate_mcp(
    mcp_id: str,
    registry: UniversalMCPRegistry = Depends(get_mcp_registry)
) -> Dict[str, str]:
    """
    Deactivate an MCP tool
    """
    try:
        await registry.deactivate_mcp(mcp_id)
        return {'status': 'deactivated', 'mcp_id': mcp_id}
    except Exception as e:
        logger.error(f"Failed to deactivate MCP {mcp_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm/models")
async def list_llm_models(
    provider: Optional[str] = None,
    llm_selector: LLMSelector = Depends(get_llm_selector)
) -> List[str]:
    """
    List available LLM models
    """
    return llm_selector.list_models(provider)


@router.get("/llm/recommend")
async def recommend_llm(
    task: str = "query_analysis",
    optimization: str = "balanced",
    llm_selector: LLMSelector = Depends(get_llm_selector)
) -> Dict[str, Any]:
    """
    Get LLM recommendation for a task
    """
    opt_mode = OptimizationMode(optimization.lower())
    model = llm_selector.select_for_task(task, opt_mode)
    model_info = llm_selector.get_model_info(model)
    
    return {
        'recommended_model': model,
        'task': task,
        'optimization': optimization,
        'model_info': model_info
    }


# Helper functions
async def get_mcp_wrapper(mcp_id: str, registry: UniversalMCPRegistry):
    """Get or create wrapper for MCP"""
    # In production, this would retrieve the actual wrapper instance
    # For now, we'll create a mock wrapper
    from app.services.universal_mcp_registry import AIWrapperGenerator
    llm_selector = LLMSelector()
    generator = AIWrapperGenerator(llm_selector)
    
    mcp = await registry.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail=f"MCP {mcp_id} not found")
    
    wrapper = await generator.generate_wrapper(mcp['config'])
    return wrapper


async def log_mcp_registration(mcp_id: str, name: str):
    """Log MCP registration for analytics"""
    logger.info(f"MCP registered: {mcp_id} ({name})")