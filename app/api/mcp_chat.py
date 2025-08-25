"""
Simple MCP Chat/Proxy endpoints for Klaviyo API MCP

Exposes:
- GET /api/mcp/tools -> lists tools from OpenAPI MCP
- POST /api/mcp/chat -> routes a tool call to MCP based on provided name/arguments
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional
import logging
import httpx

from app.utils.klaviyo_api import ensure_klaviyo_api_available, get_base_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp", tags=["MCP Chat"])


@router.get("/tools")
async def list_mcp_tools(kind: str = "openapi_revenue", use_direct: bool = True) -> Dict[str, Any]:
    """List available tools from the OpenAPI MCP server (revenue/klaviyo)."""
    
    # Try direct integration first
    if use_direct:
        try:
            from .mcp_chat_direct import list_direct_tools
            result = await list_direct_tools()
            if result.get("status") in ["available", "starting"]:
                return result
        except Exception as e:
            logger.warning(f"Direct integration failed: {e}")
    
    # Try MCP wrapper
    await ensure_klaviyo_api_available()
    base = get_base_url()
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            # Initialize if needed
            await c.post(f"{base}/admin/mcp/start", json={"kind": kind})
            # Call tools/list via generic MCP call shim
            req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            r = await c.post(f"{base}/admin/mcp/call", json={"kind": kind, "request": req})
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.warning(f"MCP tools unavailable, using fallback: {e}")
        # Use fallback tools when MCP wrapper is not available
        from .mcp_chat_fallback import MOCK_TOOLS
        return {
            "result": {"tools": MOCK_TOOLS},
            "fallback": True,
            "message": "Using fallback tools. MCP wrapper not available."
        }


@router.post("/chat")
async def mcp_chat(
    prompt: Optional[str] = Body(default=None),
    tool_name: Optional[str] = Body(default=None),
    arguments: Dict[str, Any] = Body(default_factory=dict),
    prefer: Optional[str] = Body(default=None, description="openapi_revenue | performance_openapi | firebase"),
    use_direct: bool = Body(default=True, description="Use direct Klaviyo API integration"),
) -> Dict[str, Any]:
    """Simple chat-like tool invoker.

    If tool_name is provided, calls that tool via /admin/mcp/tools/smart_call.
    If only prompt is provided, returns a helpful message with available tools.
    """
    
    # Try direct integration first
    if use_direct and tool_name:
        try:
            from .mcp_chat_direct import direct_chat
            result = await direct_chat(prompt=prompt, tool_name=tool_name, arguments=arguments)
            if result.get("status") == "success" or "result" in result:
                return result
        except Exception as e:
            logger.warning(f"Direct integration failed, falling back: {e}")
    
    # Fall back to MCP wrapper
    await ensure_klaviyo_api_available()
    base = get_base_url()
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            # If no explicit tool, hint tools list
            if not tool_name:
                tools = await list_mcp_tools()
                return {
                    "message": "Provide tool_name to execute. See tools list.",
                    "prompt_echo": prompt,
                    "tools": tools,
                }
            # Execute tool via smart router
            payload = {"name": tool_name, "arguments": arguments}
            if prefer:
                payload["prefer"] = prefer
            r = await c.post(f"{base}/admin/mcp/tools/smart_call", json=payload)
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP chat call failed: {e}")
        raise HTTPException(status_code=500, detail="MCP chat call failed")

