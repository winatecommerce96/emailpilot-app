"""
Hub Dashboard API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import os
from datetime import datetime

router = APIRouter(prefix="/api/hub", tags=["Hub Dashboard"])

@router.get("/status")
async def get_service_status() -> Dict[str, Any]:
    """Check service availability"""
    return {
        "studio": {
            "available": check_studio_health(),
            "version": "1.0.0"
        },
        "langsmith": {
            "connected": check_langsmith_connection(),
            "project": os.getenv("LANGSMITH_PROJECT", "unknown")
        },
        "editor": {
            "available": True
        }
    }

@router.get("/recent-runs")
async def get_recent_runs(limit: int = 10, graph: str = None) -> List[Dict[str, Any]]:
    """List recent workflow runs"""
    # TODO: Implement actual run fetching
    return [
        {
            "run_id": f"run_{datetime.now().strftime('%Y%m%d')}_{i:03d}",
            "graph": graph or "emailpilot_calendar",
            "status": "success" if i % 3 != 2 else "failed",
            "created_at": datetime.now().isoformat(),
            "smith_run_url": f"https://smith.langchain.com/runs/{i}"
        }
        for i in range(limit)
    ]

@router.post("/context")
async def save_run_context(context: Dict[str, Any]) -> Dict[str, bool]:
    """Save run context"""
    # TODO: Implement context storage
    return {"saved": True}

def check_studio_health() -> bool:
    """Check if Studio is available"""
    # TODO: Implement actual health check
    studio_root = os.getenv("STUDIO_ROOT", "")
    return bool(studio_root)

def check_langsmith_connection() -> bool:
    """Check LangSmith connectivity"""
    try:
        from langsmith import Client
        client = Client()
        # Simple connectivity check
        list(client.list_projects())
        return True
    except:
        return False
