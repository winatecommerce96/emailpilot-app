"""
Direct Klaviyo API Integration for MCP Chat
Bypasses MCP wrapper and directly calls Klaviyo API service for real data
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional, List
import logging
import httpx
from app.utils.klaviyo_api import ensure_klaviyo_api_available, get_base_url
from app.deps.firestore import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp/direct", tags=["MCP Direct"])

# Tool definitions based on actual Klaviyo API endpoints
KLAVIYO_TOOLS = [
    {
        "name": "GET /clients/{client_id}/revenue/last7",
        "description": "Get last 7-day email-attributed revenue for a client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client identifier"},
                "timeframe_key": {
                    "type": "string",
                    "enum": ["last_7_days", "last_30_days", "last_90_days", "yesterday", "last_24_hours"],
                    "description": "Time period for revenue data"
                },
                "metric_name": {
                    "type": "string",
                    "description": "Metric name (default 'Placed Order')"
                }
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "GET /clients/{client_id}/weekly/metrics",
        "description": "Weekly metrics bundle for client (campaign/flow split + orders)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client identifier"}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "GET /clients/{client_id}/weekly/full",
        "description": "Full weekly metrics including engagement rates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client identifier"}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "GET /clients/by-slug/{slug}/revenue/last7",
        "description": "Get revenue by client slug instead of ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Client slug"},
                "timeframe_key": {
                    "type": "string",
                    "enum": ["last_7_days", "last_30_days", "last_90_days"],
                    "description": "Time period"
                }
            },
            "required": ["slug"]
        }
    }
]

async def get_client_api_key(client_id: str) -> Optional[str]:
    """Get Klaviyo API key for a client from Firestore"""
    try:
        db = get_db()
        client_doc = db.collection('clients').document(client_id).get()
        if client_doc.exists:
            data = client_doc.to_dict()
            # Try various possible field names
            return (data.get('klaviyo_private_api_key') or 
                   data.get('klaviyo_api_key') or
                   data.get('private_api_key'))
    except Exception as e:
        logger.error(f"Failed to get API key for client {client_id}: {e}")
    return None

@router.get("/tools")
async def list_direct_tools() -> Dict[str, Any]:
    """List available Klaviyo API tools"""
    logger.info("Returning direct Klaviyo API tools")
    
    # Check if Klaviyo API service is available
    try:
        await ensure_klaviyo_api_available()
        base = get_base_url()
        
        # Test health endpoint
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{base}/healthz")
            if r.status_code == 200:
                return {
                    "result": {"tools": KLAVIYO_TOOLS},
                    "service": "klaviyo_api",
                    "status": "available",
                    "base_url": base
                }
    except Exception as e:
        logger.warning(f"Klaviyo API service check failed: {e}")
    
    return {
        "result": {"tools": KLAVIYO_TOOLS},
        "service": "klaviyo_api",
        "status": "starting",
        "message": "Klaviyo API service is starting up..."
    }

@router.post("/chat")
async def direct_chat(
    prompt: Optional[str] = Body(default=None),
    tool_name: Optional[str] = Body(default=None),
    arguments: Dict[str, Any] = Body(default_factory=dict)
) -> Dict[str, Any]:
    """Execute Klaviyo API tools directly"""
    
    # Ensure Klaviyo API is available
    await ensure_klaviyo_api_available()
    base = get_base_url()
    
    if not tool_name:
        # Return available tools
        tools = await list_direct_tools()
        return {
            "message": "Specify tool_name to execute. Available tools:",
            "tools": tools["result"]["tools"],
            "hint": "Use tool_name and arguments to execute"
        }
    
    # Parse tool name to extract endpoint
    if tool_name.startswith("GET "):
        method = "GET"
        endpoint = tool_name[4:]
    elif tool_name.startswith("POST "):
        method = "POST"
        endpoint = tool_name[5:]
    else:
        return {
            "error": f"Invalid tool format: {tool_name}",
            "hint": "Tool name should start with GET or POST"
        }
    
    # Replace path parameters
    for param, value in arguments.items():
        placeholder = f"{{{param}}}"
        if placeholder in endpoint:
            endpoint = endpoint.replace(placeholder, str(value))
            # Remove from arguments since it's now in the path
            arguments = {k: v for k, v in arguments.items() if k != param}
    
    # Make the actual API call
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            url = f"{base}{endpoint}"
            logger.info(f"Calling Klaviyo API: {method} {url}")
            
            if method == "GET":
                response = await client.get(url, params=arguments)
            else:
                response = await client.post(url, json=arguments)
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "result": data,
                "source": "klaviyo_api",
                "endpoint": endpoint,
                "status": "success"
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Klaviyo API returned error: {e.response.status_code} - {e.response.text}")
        return {
            "error": f"API error: {e.response.status_code}",
            "detail": e.response.text,
            "endpoint": endpoint
        }
    except Exception as e:
        logger.error(f"Failed to call Klaviyo API: {e}")
        return {
            "error": "Failed to call Klaviyo API",
            "detail": str(e),
            "endpoint": endpoint
        }

@router.get("/status")
async def direct_status() -> Dict[str, Any]:
    """Check direct Klaviyo API status"""
    try:
        await ensure_klaviyo_api_available()
        base = get_base_url()
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{base}/healthz")
            if r.status_code == 200:
                health = r.json()
                return {
                    "status": "available",
                    "mode": "direct",
                    "service": "klaviyo_api",
                    "base_url": base,
                    "health": health,
                    "tools_count": len(KLAVIYO_TOOLS)
                }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
    
    return {
        "status": "unavailable",
        "mode": "direct",
        "error": "Klaviyo API service not responding"
    }

@router.get("/clients")
async def list_clients() -> Dict[str, Any]:
    """List available clients from Firestore"""
    try:
        db = get_db()
        clients = []
        
        for doc in db.collection('clients').stream():
            data = doc.to_dict()
            # Check if client has Klaviyo API key
            has_key = bool(
                data.get('klaviyo_private_api_key') or 
                data.get('klaviyo_api_key') or
                data.get('private_api_key')
            )
            
            clients.append({
                "id": doc.id,
                "name": data.get('name', doc.id),
                "slug": data.get('slug', ''),
                "has_api_key": has_key
            })
        
        return {
            "clients": clients,
            "count": len(clients)
        }
    except Exception as e:
        logger.error(f"Failed to list clients: {e}")
        return {
            "error": "Failed to list clients",
            "detail": str(e)
        }