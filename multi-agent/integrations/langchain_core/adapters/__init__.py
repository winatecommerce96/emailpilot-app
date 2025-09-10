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
# Try to import Enhanced MCP adapter
try:
    from .enhanced_mcp_adapter import (
        EnhancedMCPAdapter,
        get_enhanced_mcp_adapter,
        get_enhanced_tools_for_agent,
        ENHANCED_MCP_TOOL_MAPPING
    )
    ENHANCED_MCP_AVAILABLE = True
except ImportError:
    ENHANCED_MCP_AVAILABLE = False

__all__ = [
    "MCPClient",
    "MCPResponse",
    "MCPError",
    "lc_rag",
    "lc_agent",
    "check_langchain_available",
    "get_langchain_status"
]

# Add Enhanced MCP exports if available
if ENHANCED_MCP_AVAILABLE:
    __all__.extend([
        "EnhancedMCPAdapter",
        "get_enhanced_mcp_adapter",
        "get_enhanced_tools_for_agent",
        "ENHANCED_MCP_TOOL_MAPPING"
    ])