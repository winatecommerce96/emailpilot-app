"""
MCP Chat with Fallback Support
Provides mock tools when MCP wrapper is unavailable
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp/fallback", tags=["MCP Fallback"])

# Mock tools based on Klaviyo API OpenAPI spec
MOCK_TOOLS = [
    {
        "name": "GET /clients/{client_id}/revenue/last7",
        "description": "Get last 7-day email-attributed revenue for a client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client identifier"},
                "timeframe_key": {
                    "type": "string",
                    "enum": ["last_7_days", "last_30_days", "last_90_days"],
                    "description": "Time period for revenue data"
                }
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "GET /clients/{client_id}/campaigns",
        "description": "List campaigns for a client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client identifier"},
                "limit": {"type": "integer", "description": "Number of campaigns to return"}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "GET /clients/{client_id}/flows",
        "description": "List flows for a client",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client identifier"}
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "POST /reports/weekly",
        "description": "Generate weekly revenue report",
        "inputSchema": {
            "type": "object",
            "properties": {
                "preview": {"type": "boolean", "description": "Preview mode (don't send to Slack)"}
            }
        }
    },
    {
        "name": "POST /reports/monthly",
        "description": "Generate monthly revenue report",
        "inputSchema": {
            "type": "object",
            "properties": {
                "month": {"type": "integer", "description": "Month (1-12)"},
                "year": {"type": "integer", "description": "Year"}
            }
        }
    }
]

@router.get("/tools")
async def list_fallback_tools() -> Dict[str, Any]:
    """Return mock tools for testing when MCP wrapper is unavailable"""
    logger.info("Returning fallback/mock MCP tools")
    
    return {
        "result": {
            "tools": MOCK_TOOLS
        },
        "fallback": True,
        "message": "Using fallback tools. MCP wrapper not available."
    }

@router.post("/chat")
async def fallback_chat(
    prompt: Optional[str] = Body(default=None),
    tool_name: Optional[str] = Body(default=None),
    arguments: Dict[str, Any] = Body(default_factory=dict)
) -> Dict[str, Any]:
    """Fallback chat handler with mock responses"""
    
    if not tool_name:
        # Return available tools
        return {
            "message": "Available tools (fallback mode):",
            "tools": [tool["name"] for tool in MOCK_TOOLS],
            "fallback": True,
            "hint": "Specify tool_name to execute a tool"
        }
    
    # Find the tool
    tool = next((t for t in MOCK_TOOLS if t["name"] == tool_name), None)
    
    if not tool:
        return {
            "error": f"Tool '{tool_name}' not found",
            "available_tools": [t["name"] for t in MOCK_TOOLS],
            "fallback": True
        }
    
    # Generate mock response based on tool
    if "revenue" in tool_name:
        return {
            "result": {
                "revenue": {
                    "total": 12345.67,
                    "currency": "USD",
                    "period": arguments.get("timeframe_key", "last_7_days"),
                    "client_id": arguments.get("client_id", "unknown")
                },
                "mock": True
            },
            "fallback": True
        }
    elif "campaigns" in tool_name:
        return {
            "result": {
                "campaigns": [
                    {
                        "id": "camp_001",
                        "name": "Summer Sale 2025",
                        "sent": 5000,
                        "opens": 1500,
                        "clicks": 300,
                        "revenue": 4567.89
                    },
                    {
                        "id": "camp_002",
                        "name": "Welcome Series",
                        "sent": 2000,
                        "opens": 800,
                        "clicks": 150,
                        "revenue": 2345.67
                    }
                ],
                "mock": True
            },
            "fallback": True
        }
    elif "flows" in tool_name:
        return {
            "result": {
                "flows": [
                    {
                        "id": "flow_001",
                        "name": "Abandoned Cart",
                        "active": True,
                        "triggered": 150,
                        "revenue": 3456.78
                    }
                ],
                "mock": True
            },
            "fallback": True
        }
    elif "reports" in tool_name:
        return {
            "result": {
                "report": {
                    "type": "weekly" if "weekly" in tool_name else "monthly",
                    "generated_at": "2025-08-21T10:00:00Z",
                    "summary": "Report generated successfully (mock)",
                    "total_revenue": 45678.90
                },
                "mock": True
            },
            "fallback": True
        }
    else:
        return {
            "result": {"message": "Tool executed (mock)", "mock": True},
            "fallback": True
        }

@router.get("/status")
async def fallback_status() -> Dict[str, Any]:
    """Check fallback MCP status"""
    return {
        "status": "available",
        "mode": "fallback",
        "tools_count": len(MOCK_TOOLS),
        "message": "Fallback MCP is available for testing"
    }