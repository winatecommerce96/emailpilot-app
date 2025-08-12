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
        "type": "Production",
        "created_at": "2024-01-15T10:00:00Z"
    },
    {
        "id": "klaviyo-client-2",
        "name": "Test Client",
        "type": "Development",
        "created_at": "2024-02-01T14:30:00Z"
    }
]

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