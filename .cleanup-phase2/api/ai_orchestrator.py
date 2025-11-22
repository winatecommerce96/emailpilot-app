"""
AI Orchestrator API Routes
==========================

FastAPI routes for the centralized AI Orchestrator.
All AI requests should go through these endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging

from app.core.ai_orchestrator import (
    get_ai_orchestrator,
    Provider,
    ModelTier,
    CompletionRequest,
    CompletionResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI Orchestrator"])


class OrchestratorRequest(BaseModel):
    """Request model for AI completions"""
    messages: List[Dict[str, str]] = Field(..., description="List of message objects")
    provider: str = Field("auto", description="Provider: openai, claude, gemini, or auto")
    model: Optional[str] = Field(None, description="Specific model to use")
    model_tier: str = Field("auto", description="Model tier: flagship, standard, fast, or auto")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(1000, ge=1, le=32000, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Enable streaming response")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class OrchestratorResponse(BaseModel):
    """Response model for AI completions"""
    success: bool
    content: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None  # Changed from Dict[str, int] to Dict[str, Any] to handle provider_raw
    warnings: Optional[List[str]] = None
    cached: bool = False
    error: Optional[str] = None


@router.post("/complete", response_model=OrchestratorResponse)
async def complete(request: OrchestratorRequest):
    """
    Main completion endpoint - handles all AI requests
    
    This is the primary endpoint for AI completions in EmailPilot.
    It automatically handles provider selection, fallbacks, and retries.
    """
    try:
        orchestrator = get_ai_orchestrator()
        
        # Convert request to orchestrator format
        completion_request = {
            "messages": request.messages,
            "provider": request.provider,
            "model": request.model,
            "model_tier": request.model_tier,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
            "metadata": request.metadata
        }
        
        # Execute completion
        response = await orchestrator.complete(completion_request)
        
        return OrchestratorResponse(
            success=True,
            content=response.content,
            provider=response.provider,
            model=response.model,
            usage=response.usage,
            warnings=response.warnings,
            cached=response.cached
        )
        
    except Exception as e:
        logger.error(f"Orchestrator completion failed: {e}")
        return OrchestratorResponse(
            success=False,
            error=str(e)
        )


@router.post("/stream")
async def stream_completion(request: OrchestratorRequest):
    """
    Streaming completion endpoint
    
    Returns responses as they are generated (SSE format).
    """
    try:
        orchestrator = get_ai_orchestrator()
        
        # Import streaming response
        from fastapi.responses import StreamingResponse
        import json
        
        async def generate():
            async for chunk in orchestrator.stream(request.dict()):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(provider: Optional[str] = None):
    """
    List available models
    
    Args:
        provider: Optional provider filter (openai, claude, gemini)
    """
    try:
        orchestrator = get_ai_orchestrator()
        models = await orchestrator.list_models(provider)
        return {
            "success": True,
            "models": models
        }
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/models/refresh")
async def refresh_models():
    """Refresh the model catalog"""
    try:
        orchestrator = get_ai_orchestrator()
        result = await orchestrator.refresh_models()
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to refresh models: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/stats")
async def get_usage_stats():
    """Get usage statistics"""
    try:
        orchestrator = get_ai_orchestrator()
        stats = await orchestrator.get_usage_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/cache/clear")
async def clear_cache():
    """Clear the response cache"""
    try:
        orchestrator = get_ai_orchestrator()
        orchestrator.clear_cache()
        return {
            "success": True,
            "message": "Cache cleared"
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health")
async def health_check():
    """Check orchestrator health"""
    try:
        orchestrator = get_ai_orchestrator()
        models = await orchestrator.list_models()
        
        # Check if we have at least one provider working
        has_working_provider = any(
            len(provider_models) > 0 
            for provider_models in models.values()
        )
        
        return {
            "status": "healthy" if has_working_provider else "degraded",
            "providers": {
                provider: len(provider_models) 
                for provider, provider_models in models.items()
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }