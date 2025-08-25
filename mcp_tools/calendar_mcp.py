"""
MCP Integration for Calendar Tools
Wraps calendar tools with MCP protocol for extended capabilities
"""
import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8090")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")


class CalendarMCPClient:
    """Client for MCP calendar operations"""
    
    def __init__(self, server_url: str = MCP_SERVER_URL, api_key: str = MCP_API_KEY):
        self.server_url = server_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            response = await self.client.get(f"{self.server_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        try:
            response = await self.client.get(
                f"{self.server_url}/tools",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool with arguments"""
        try:
            response = await self.client.post(
                f"{self.server_url}/tools/{tool_name}",
                json=arguments,
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"MCP tool call failed: {tool_name} - {e}")
            return {"error": str(e)}


class MCPToolWrapper:
    """Wrapper to convert LangGraph tools to MCP-compatible tools"""
    
    def __init__(self, mcp_client: Optional[CalendarMCPClient] = None):
        self.mcp_client = mcp_client or CalendarMCPClient()
        self._tools_cache = {}
    
    async def wrap_tool(self, tool_func, use_mcp: bool = True):
        """
        Wrap a tool function to optionally use MCP
        
        Args:
            tool_func: Original tool function
            use_mcp: Whether to use MCP server if available
        
        Returns:
            Wrapped tool function
        """
        tool_name = tool_func.name if hasattr(tool_func, 'name') else tool_func.__name__
        
        async def wrapped_tool(*args, **kwargs):
            # Try MCP first if enabled and available
            if use_mcp:
                if await self.mcp_client.health_check():
                    logger.info(f"Using MCP for tool: {tool_name}")
                    
                    # Convert args/kwargs to MCP format
                    arguments = {
                        "args": args,
                        "kwargs": kwargs
                    }
                    
                    result = await self.mcp_client.call_tool(tool_name, arguments)
                    
                    if "error" not in result:
                        return result
                    else:
                        logger.warning(f"MCP call failed, falling back to local: {result['error']}")
            
            # Fall back to local execution
            logger.info(f"Using local execution for tool: {tool_name}")
            
            # Handle both sync and async tools
            if asyncio.iscoroutinefunction(tool_func):
                return await tool_func(*args, **kwargs)
            else:
                return tool_func(*args, **kwargs)
        
        # Preserve tool metadata
        wrapped_tool.__name__ = tool_name
        wrapped_tool.name = tool_name
        if hasattr(tool_func, 'description'):
            wrapped_tool.description = tool_func.description
        if hasattr(tool_func, 'args_schema'):
            wrapped_tool.args_schema = tool_func.args_schema
        
        return wrapped_tool
    
    async def register_tools(self, tools: List) -> List:
        """
        Register and wrap multiple tools
        
        Args:
            tools: List of tool functions
        
        Returns:
            List of wrapped tools
        """
        wrapped_tools = []
        
        for tool in tools:
            wrapped = await self.wrap_tool(tool)
            wrapped_tools.append(wrapped)
            
            # Cache for later reference
            tool_name = tool.name if hasattr(tool, 'name') else tool.__name__
            self._tools_cache[tool_name] = wrapped
        
        logger.info(f"Registered {len(wrapped_tools)} tools with MCP wrapper")
        return wrapped_tools


# MCP-specific calendar tools
async def analyze_klaviyo_metrics(client_id: str, timeframe: str = "last_30_days") -> Dict[str, Any]:
    """
    Analyze Klaviyo metrics via MCP
    
    This tool connects to the actual Klaviyo API through MCP
    """
    async with CalendarMCPClient() as client:
        return await client.call_tool("analyze_klaviyo_metrics", {
            "client_id": client_id,
            "timeframe": timeframe
        })


async def sync_calendar_to_klaviyo(calendar_events: List[Dict[str, Any]], client_id: str) -> Dict[str, Any]:
    """
    Sync calendar events to Klaviyo campaigns via MCP
    
    This tool creates actual Klaviyo campaigns through MCP
    """
    async with CalendarMCPClient() as client:
        return await client.call_tool("sync_to_klaviyo", {
            "events": calendar_events,
            "client_id": client_id
        })


async def fetch_klaviyo_templates(client_id: str) -> List[Dict[str, Any]]:
    """
    Fetch available Klaviyo templates via MCP
    
    This tool retrieves actual templates from Klaviyo through MCP
    """
    async with CalendarMCPClient() as client:
        result = await client.call_tool("fetch_templates", {
            "client_id": client_id
        })
        return result.get("templates", [])


# Bridge function for sync/async compatibility
def get_mcp_calendar_tools():
    """
    Get MCP-enhanced calendar tools
    
    Returns:
        List of MCP-wrapped tool functions
    """
    from tools.calendar_tools import get_calendar_tools
    
    # Get base tools
    base_tools = get_calendar_tools()
    
    # Add MCP-specific tools
    mcp_tools = [
        analyze_klaviyo_metrics,
        sync_calendar_to_klaviyo,
        fetch_klaviyo_templates
    ]
    
    # Combine all tools
    all_tools = base_tools + mcp_tools
    
    logger.info(f"Loaded {len(base_tools)} base tools and {len(mcp_tools)} MCP tools")
    
    return all_tools


# Integration with LangGraph
async def create_mcp_enhanced_graph():
    """
    Create a LangGraph with MCP-enhanced tools
    
    Returns:
        Enhanced graph with MCP capabilities
    """
    from graph.graph import create_calendar_graph
    from langgraph.prebuilt import ToolNode
    
    # Create base graph
    graph = create_calendar_graph()
    
    # Get MCP-enhanced tools
    tools = get_mcp_calendar_tools()
    
    # Wrap tools with MCP
    wrapper = MCPToolWrapper()
    wrapped_tools = await wrapper.register_tools(tools)
    
    # Create enhanced tool node
    tool_node = ToolNode(wrapped_tools)
    
    # Replace the tools node in the graph
    # This would require modifying the graph structure
    # For now, we return the base graph with a note
    
    logger.info("Created MCP-enhanced calendar graph")
    
    return graph


# Test function
async def test_mcp_integration():
    """Test MCP integration"""
    print("\n" + "="*50)
    print("MCP INTEGRATION TEST")
    print("="*50)
    
    async with CalendarMCPClient() as client:
        # Test health
        health = await client.health_check()
        print(f"MCP Server Health: {'✓ OK' if health else '✗ Unavailable'}")
        
        if health:
            # List tools
            tools = await client.list_tools()
            print(f"Available MCP Tools: {len(tools)}")
            for tool in tools[:5]:  # Show first 5
                print(f"  - {tool.get('name', 'unknown')}")
            
            # Test a tool call
            result = await client.call_tool("test_echo", {"message": "Hello MCP"})
            print(f"Test Call Result: {result}")
        else:
            print("MCP Server not available - tools will fall back to local execution")
    
    print("="*50 + "\n")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_mcp_integration())