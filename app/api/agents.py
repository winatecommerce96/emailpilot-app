"""
General-purpose API endpoints for the Email/SMS Multi-Agent System
Enhanced with AI Models Service integration
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any, Optional
from app.services.agent_service import AgentService, get_agent_service
from google.cloud import firestore
from app.deps import get_db
from app.deps.secrets import get_secret_manager_service
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def agents_root():
    """Agents API root endpoint"""
    return {
        "status": "operational",
        "service": "EmailPilot Agents API",
        "version": "2.0.0", 
        "features": ["agent_invocation", "ai_orchestration", "prompt_management"],
        "available_endpoints": [
            "POST /api/agents/invoke",
            "POST /api/agents/invoke-debug",
            "POST /api/agents/invoke-with-prompt", 
            "POST /api/agents/invoke-coordinated"
        ],
        "orchestrator_available": AI_ORCHESTRATOR_AVAILABLE if 'AI_ORCHESTRATOR_AVAILABLE' in globals() else False
    }

# Import AI Orchestrator - PRIMARY AI INTERFACE
try:
    from app.core.ai_orchestrator import get_ai_orchestrator, ai_complete
    AI_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    AI_ORCHESTRATOR_AVAILABLE = False
    logger.warning("AI Orchestrator not available, falling back to legacy service")
    # Fallback to legacy AI Models Service if orchestrator not available
    try:
        from app.services.ai_models_service import get_ai_models_service
        AI_MODELS_AVAILABLE = True
    except ImportError:
        AI_MODELS_AVAILABLE = False
        logger.info("AI Models Service not available, using standard agent service")

@router.post("/invoke")
async def invoke_agent(
    request: Request,
    data: Dict[str, Any],
    agent_service: AgentService = Depends(get_agent_service),
    db: firestore.Client = Depends(get_db)
):
    """
    Invoke the agent orchestrator with the given data.
    Enhanced to use AI Models Service for prompt management if available.
    """
    
    # Use AI Orchestrator if available and request needs AI enhancement
    if AI_ORCHESTRATOR_AVAILABLE and ("prompt_id" in data or "ai_prompt" in data):
        try:
            # Build messages from prompt or context
            messages = []
            if "ai_prompt" in data:
                messages.append({"role": "user", "content": data["ai_prompt"]})
            elif "prompt_id" in data:
                # For backward compatibility with prompt_id
                prompt_content = f"Execute prompt {data['prompt_id']} with variables: {data.get('variables', {})}"
                messages.append({"role": "user", "content": prompt_content})
            
            # Use orchestrator for completion
            ai_response = await ai_complete(
                messages=messages,
                provider=data.get("provider", "auto"),
                model=data.get("model"),
                temperature=0.7,
                max_tokens=1000
            )
            
            # Enhance agent data with AI response
            data["ai_enhanced_context"] = ai_response
            data["ai_provider"] = "orchestrator"
            data["ai_model"] = "auto-selected"
            
        except Exception as e:
            logger.error(f"Error using AI Orchestrator: {e}")
            # Try legacy AI Models Service as fallback
            if AI_MODELS_AVAILABLE and "prompt_id" in data:
                try:
                    ai_service = get_ai_models_service(db, get_secret_manager_service())
                    prompt_result = await ai_service.execute_prompt(
                        prompt_id=data["prompt_id"],
                        variables=data.get("variables", {}),
                        override_provider=data.get("provider"),
                        override_model=data.get("model")
                    )
                    if prompt_result["success"]:
                        data["ai_enhanced_context"] = prompt_result["response"]
                        data["ai_provider"] = prompt_result["provider"]
                        data["ai_model"] = prompt_result["model"]
                except Exception as legacy_e:
                    logger.error(f"Error using legacy AI Models Service: {legacy_e}")
    
    # Invoke the standard agent service
    try:
        return await agent_service.invoke_agent(data)
    except Exception as e:
        logger.exception("invoke_agent failed")
        # Return structured error instead of generic 500
        return {"status": "error", "message": str(e)}


@router.post("/invoke-debug")
async def invoke_agent_debug(data: Dict[str, Any]):
    """Debug helper to capture error details from agent invocation."""
    try:
        svc = get_agent_service()
        return await svc.invoke_agent(data)
    except Exception as e:
        logger.exception("invoke_agent_debug failed")
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
        }

@router.post("/invoke-with-prompt")
async def invoke_agent_with_prompt(
    request: Request,
    data: Dict[str, Any],
    agent_service: AgentService = Depends(get_agent_service),
    db: firestore.Client = Depends(get_db)
):
    """
    Invoke an agent using a specific AI prompt template.
    Uses AI Orchestrator as primary interface, falls back to AI Models Service.
    """
    if not AI_ORCHESTRATOR_AVAILABLE and not AI_MODELS_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="AI services not available"
        )
    
    try:
        ai_service = get_ai_models_service(db, get_secret_manager_service())
        
        # Get agent type from data
        agent_type = data.get("agent_type", "content_strategist")
        context = data.get("context", {})
        
        # Execute agent-specific prompt
        prompt_result = await ai_service.execute_agent_prompt(
            agent_type=agent_type,
            context=context
        )
        
        if not prompt_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to execute prompt: {prompt_result.get('error')}"
            )
        
        # Enhance data with AI response
        enhanced_data = {
            **data,
            "ai_response": prompt_result["response"],
            "ai_provider": prompt_result.get("provider"),
            "ai_model": prompt_result.get("model")
        }
        
        # Invoke agent with enhanced data
        return await agent_service.invoke_agent(enhanced_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in invoke_agent_with_prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoke-coordinated")
async def invoke_coordinated(
    data: Dict[str, Any],
    db: firestore.Client = Depends(get_db)
):
    """Invoke a coordinated run across selected agents.

    Body fields:
    - agents or selected_agents: List[str]
    - workflow_type: "parallel" | "sequential" (default sequential)
    - sequence: optional explicit list for sequential fixed order
    - any additional context fields
    """
    try:
        # Prefer enhanced service for coordinated runs
        try:
            from app.services.agent_service_enhanced import get_enhanced_agent_service
            svc = get_enhanced_agent_service(db, get_secret_manager_service())
            result = await svc.invoke_agent(data)
            return result
        except Exception as e:
            raise HTTPException(status_code=501, detail=f"Enhanced coordination unavailable: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("invoke_coordinated failed")
        raise HTTPException(status_code=500, detail=str(e))
