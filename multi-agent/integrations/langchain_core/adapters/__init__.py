"""
Adapters for external service integration.

Provides typed clients and bridge functions for MCP and orchestrator.
"""

from .mcp_client import MCPClient, MCPResponse, MCPError
from .orchestrator_bridge import (
    lc_rag,
    lc_agent,
    check_langchain_available,
    get_langchain_status
)

__all__ = [
    "MCPClient",
    "MCPResponse",
    "MCPError",
    "lc_rag",
    "lc_agent",
    "check_langchain_available",
    "get_langchain_status"
]