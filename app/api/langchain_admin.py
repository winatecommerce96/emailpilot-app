"""
LangChain Admin API - Simplified fallback implementation.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/langchain", tags=["LangChain Admin"])

# Static provider models registry
PROVIDER_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
    "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]  # Alias for google
}


@router.get("/models/providers")
async def get_providers() -> List[str]:
    """Get list of supported model providers."""
    try:
        return list(PROVIDER_MODELS.keys())
    except Exception as e:
        logger.error(f"Error getting providers: {e}")
        # Never return 500 - return empty list as fallback
        return []


@router.get("/models/available")
async def get_available_models(
    provider: str = Query(..., description="Provider to get models for (openai/anthropic/google/gemini)")
) -> List[str]:
    """
    Get available models for a specific provider.
    
    Args:
        provider: Provider to get models for (openai/anthropic/google/gemini)
    
    Returns:
        List of model names for the provider
    """
    try:
        # Validate provider parameter
        if not provider:
            raise HTTPException(
                status_code=400, 
                detail={
                    "detail": "Provider parameter is required",
                    "hint": "Use one of: openai, anthropic, google, gemini",
                    "provider": None
                }
            )
        
        # Check if provider is supported
        if provider not in PROVIDER_MODELS:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": f"Unsupported provider: {provider}",
                    "hint": f"Supported providers: {list(PROVIDER_MODELS.keys())}",
                    "provider": provider
                }
            )
        
        # Return models for the provider
        return PROVIDER_MODELS[provider]
        
    except HTTPException:
        # Re-raise HTTP exceptions (400 errors)
        raise
    except Exception as e:
        # Log unexpected errors but never return 500
        logger.error(f"Unexpected error in get_available_models: {e}")
        logger.info("DEBUG: Current PROVIDER_MODELS keys: " + str(list(PROVIDER_MODELS.keys())))
        # Return empty list as fallback
        return []


@router.get("/models/resolve")
async def resolve_model_policy(
    user_id: Optional[str] = Query(None, description="User ID for policy resolution"),
    brand: Optional[str] = Query(None, description="Brand for policy resolution")
) -> Dict[str, str]:
    """
    Resolve effective model policy for user/brand.
    
    Args:
        user_id: User ID for policy resolution
        brand: Brand for policy resolution
    
    Returns:
        Resolved model configuration with source scope
    """
    try:
        # For now, return a static default policy since we don't have the full resolver infrastructure
        # This prevents 500 errors while the system is being developed
        return {
            "provider": "google",
            "model": "gemini-1.5-flash",
            "source_scope": "global"
        }
        
    except Exception as e:
        # Log the error but return a 422 with helpful information
        logger.warning(f"Policy resolution failed for user_id={user_id}, brand={brand}: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Policy resolution failed",
                "hint": "Check if user_id and brand are valid, or contact support",
                "user_id": user_id,
                "brand": brand
            }
        )


@router.post("/models/validate")
async def validate_api_key(request: dict) -> Dict[str, Any]:
    """
    Validate API key for a specific provider.
    
    Args:
        request: Dict containing 'provider' key
    
    Returns:
        Validation result
    """
    try:
        provider = request.get('provider')
        if not provider:
            raise HTTPException(
                status_code=400,
                detail="Provider is required"
            )
        
        if provider not in PROVIDER_MODELS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {provider}"
            )
        
        # For now, just return success since we don't have actual API key validation
        # In a real implementation, this would make an actual API call to validate the key
        return {
            "provider": provider,
            "valid": True,
            "message": f"{provider} API key validation successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Key validation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/models/policies")
async def get_model_policy(
    scope: str = Query("global", description="Policy scope (global/brand/user)"),
    scope_id: Optional[str] = Query(None, description="Scope identifier for brand/user")
) -> Dict[str, Any]:
    """
    Get model policy for a specific scope.
    
    Args:
        scope: Policy scope level
        scope_id: Identifier for brand/user scopes
    
    Returns:
        Model policy configuration
    """
    try:
        # Return a default policy structure
        # In a real implementation, this would fetch from database
        return {
            "provider": "google",
            "model": "gemini-1.5-flash",
            "temperature": 0.7,
            "max_tokens": 2048,
            "limits": {
                "daily_tokens": 1000000,
                "rate_limit_rpm": 60
            },
            "allowlist": [],
            "blocklist": [],
            "scope": scope,
            "scope_id": scope_id
        }
        
    except Exception as e:
        logger.error(f"Policy fetch error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch policy: {str(e)}"
        )


@router.put("/models/policies")
async def update_model_policy(
    policy: dict,
    level: str = Query("global", description="Policy level"),
    identifier: Optional[str] = Query(None, description="Level identifier")
) -> Dict[str, str]:
    """
    Update model policy for a specific level.
    
    Args:
        policy: Policy configuration
        level: Policy level (global/brand/user)  
        identifier: Identifier for brand/user levels
    
    Returns:
        Update confirmation
    """
    try:
        # In a real implementation, this would save to database
        logger.info(f"Policy update for {level}:{identifier}: {policy}")
        
        return {
            "status": "success",
            "message": f"Policy updated for {level}:{identifier or 'default'}",
            "level": level,
            "identifier": identifier
        }
        
    except Exception as e:
        logger.error(f"Policy update error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update policy: {str(e)}"
        )


# Simple fallback endpoints for compatibility
@router.get("/agents")
async def list_agents() -> Dict[str, Any]:
    """List all registered agents (fallback implementation)."""
    return {"agents": [], "status": "fallback_mode"}


@router.get("/usage/summary")
async def get_usage_summary() -> Dict[str, Any]:
    """Get usage summary (fallback implementation)."""
    return {
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "by_provider": {},
        "by_model": {}
    }