"""
Enhanced MCP Adapter for LangChain Tools
Non-destructive adapter that maps Enhanced MCP tools to LangChain-friendly names
Preserves existing functionality while adding new capabilities
"""

import json
import logging
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import httpx
from langchain.tools import Tool
from langchain.tools.base import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Tool mapping from LangChain names to Enhanced MCP methods
ENHANCED_MCP_TOOL_MAPPING = {
    # Campaign tools
    'klaviyo_campaigns': 'campaigns.list',
    'klaviyo_campaigns_get': 'campaigns.get',
    'klaviyo_campaign_metrics': 'campaigns.get_metrics',
    
    # Metric tools
    'klaviyo_metrics': 'metrics.list',
    'klaviyo_metrics_get': 'metrics.get',
    'klaviyo_metrics_aggregate': 'metrics.aggregate',
    'klaviyo_metrics_timeline': 'metrics.timeline',
    
    # Segment tools
    'klaviyo_segments': 'segments.list',
    'klaviyo_segments_get': 'segments.get',
    'klaviyo_segments_profiles': 'segments.get_profiles',
    
    # List tools
    'klaviyo_lists': 'lists.list',
    'klaviyo_lists_get': 'lists.get',
    'klaviyo_lists_profiles': 'lists.get_profiles',
    
    # Flow tools
    'klaviyo_flows': 'flows.list',
    'klaviyo_flows_get': 'flows.get',
    'klaviyo_flows_metrics': 'flows.get_metrics',
    
    # Profile tools
    'klaviyo_profiles_get': 'profiles.get',
    'klaviyo_profiles_create': 'profiles.create',
    'klaviyo_profiles_update': 'profiles.update',
    
    # Template tools
    'klaviyo_templates': 'templates.list',
    'klaviyo_templates_get': 'templates.get',
    
    # Event tools
    'klaviyo_events_create': 'events.create',
    'klaviyo_events_get': 'events.get',
    
    # Reporting tools
    'klaviyo_reporting_revenue': 'reporting.revenue',
    'klaviyo_reporting_performance': 'reporting.performance',
    'klaviyo_reporting_attribution': 'reporting.attribution'
}

class EnhancedMCPAdapter:
    """Adapter to connect Enhanced MCP with LangChain agents"""
    
    def __init__(self, 
                 gateway_url: str = "http://localhost:8000/api/mcp/gateway",
                 enhanced_mcp_url: str = "http://localhost:9095",
                 timeout: float = 30.0):
        """
        Initialize Enhanced MCP Adapter
        
        Args:
            gateway_url: MCP Gateway URL
            enhanced_mcp_url: Direct Enhanced MCP URL (for health checks)
            timeout: Request timeout in seconds
        """
        self.gateway_url = gateway_url
        self.enhanced_mcp_url = enhanced_mcp_url
        self.timeout = timeout
        self._client = None
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        logger.info(f"Enhanced MCP Adapter initialized with gateway: {gateway_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def check_health(self) -> Dict[str, Any]:
        """Check health of Enhanced MCP and Gateway"""
        health = {
            "adapter": "healthy",
            "gateway": "unknown",
            "enhanced_mcp": "unknown",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Check Gateway
            client = await self._get_client()
            response = await client.get(f"{self.gateway_url}/status")
            if response.status_code == 200:
                health["gateway"] = "healthy"
            
            # Check Enhanced MCP
            response = await client.get(f"{self.enhanced_mcp_url}/health")
            if response.status_code == 200:
                health["enhanced_mcp"] = "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        return health
    
    async def call_mcp_tool(self, 
                           tool_name: str, 
                           client_id: str,
                           arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call an Enhanced MCP tool through the Gateway
        
        Args:
            tool_name: Enhanced MCP tool name (e.g., 'campaigns.list')
            client_id: Klaviyo client ID
            arguments: Tool arguments
        
        Returns:
            Tool response data
        """
        arguments = arguments or {}
        
        # Check cache
        cache_key = f"{client_id}:{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                logger.debug(f"Cache hit for {tool_name}")
                return cached_data
        
        # Make request
        payload = {
            "client_id": client_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "use_enhanced": True
        }
        
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.gateway_url}/invoke",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Cache successful responses
                    self._cache[cache_key] = (data.get("data"), datetime.now())
                    return data.get("data")
                else:
                    raise Exception(f"MCP tool failed: {data.get('error')}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            raise
    
    def create_langchain_tool(self, 
                             langchain_name: str,
                             mcp_method: str,
                             description: str = None) -> Tool:
        """
        Create a LangChain tool that wraps an Enhanced MCP method
        
        Args:
            langchain_name: LangChain-friendly tool name
            mcp_method: Enhanced MCP method name
            description: Tool description
        
        Returns:
            LangChain Tool instance
        """
        description = description or f"Access Klaviyo data via {mcp_method}"
        
        def tool_func(query: str = "", client_id: str = None, **kwargs) -> str:
            """Synchronous wrapper for async MCP call"""
            # Try to extract client_id from query or kwargs
            if not client_id:
                # Look for client_id in various places
                client_id = kwargs.get('brand_id') or kwargs.get('client') or 'default'
            
            # Run async function in sync context properly
            try:
                # Check if we're in an async context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're already in an async loop, use run_coroutine_threadsafe
                    import concurrent.futures
                    import threading
                    
                    # Create a new event loop in a thread
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                self.call_mcp_tool(mcp_method, client_id, kwargs)
                            )
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_in_thread)
                        result = future.result(timeout=30)
                else:
                    # No running loop, we can use run_until_complete
                    result = loop.run_until_complete(
                        self.call_mcp_tool(mcp_method, client_id, kwargs)
                    )
            except RuntimeError:
                # No event loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.call_mcp_tool(mcp_method, client_id, kwargs)
                    )
                finally:
                    # Don't close the loop if it's the main thread loop
                    pass
            
            return json.dumps(result, indent=2)
        
        return Tool(
            name=langchain_name,
            description=description,
            func=tool_func
        )
    
    def get_all_enhanced_tools(self, default_client_id: str = None) -> List[Tool]:
        """
        Get all Enhanced MCP tools as LangChain tools
        
        Args:
            default_client_id: Default client ID if not specified in tool call
        
        Returns:
            List of LangChain Tool instances
        """
        tools = []
        
        # Tool descriptions
        descriptions = {
            'klaviyo_campaigns': "List all email campaigns from Klaviyo",
            'klaviyo_campaigns_get': "Get specific campaign details by ID",
            'klaviyo_campaign_metrics': "Get campaign performance metrics",
            'klaviyo_metrics': "List all available metrics",
            'klaviyo_metrics_aggregate': "Aggregate metrics data with custom parameters",
            'klaviyo_segments': "List customer segments",
            'klaviyo_lists': "List email lists",
            'klaviyo_flows': "List automation flows",
            'klaviyo_profiles_get': "Get customer profile by ID",
            'klaviyo_templates': "List email templates",
            'klaviyo_reporting_revenue': "Get revenue reporting data",
            'klaviyo_reporting_performance': "Get performance reporting data"
        }
        
        for langchain_name, mcp_method in ENHANCED_MCP_TOOL_MAPPING.items():
            description = descriptions.get(langchain_name, f"Klaviyo tool: {mcp_method}")
            tool = self.create_langchain_tool(langchain_name, mcp_method, description)
            
            # Inject default client_id if provided
            if default_client_id:
                original_func = tool.func
                def wrapped_func(query: str = "", **kwargs):
                    kwargs.setdefault('client_id', default_client_id)
                    return original_func(query, **kwargs)
                tool.func = wrapped_func
            
            tools.append(tool)
        
        logger.info(f"Created {len(tools)} Enhanced MCP tools for LangChain")
        return tools
    
    def get_tools_for_agent(self, 
                           agent_name: str,
                           client_id: str = None) -> List[Tool]:
        """
        Get specific tools for an agent based on its needs
        
        Args:
            agent_name: Name of the agent
            client_id: Default client ID
        
        Returns:
            List of relevant tools for the agent
        """
        # Define tool sets for different agent types
        agent_tool_sets = {
            # High-priority agents
            'monthly_goals_generator_v3': [
                'klaviyo_metrics_aggregate',
                'klaviyo_campaigns',
                'klaviyo_reporting_revenue'
            ],
            'calendar_planner': [
                'klaviyo_campaigns',
                'klaviyo_campaign_metrics',
                'klaviyo_flows',
                'klaviyo_segments'
            ],
            'ab_test_coordinator': [
                'klaviyo_segments',
                'klaviyo_metrics_aggregate',
                'klaviyo_campaigns'
            ],
            # Revenue and analysis agents
            'revenue_analyst': [
                'klaviyo_reporting_revenue',
                'klaviyo_metrics_aggregate',
                'klaviyo_campaigns'
            ],
            'campaign_strategist': [
                'klaviyo_campaigns',
                'klaviyo_segments',
                'klaviyo_flows'
            ],
            # Default set for all agents
            'default': [
                'klaviyo_campaigns',
                'klaviyo_segments',
                'klaviyo_metrics'
            ]
        }
        
        # Get tool names for this agent
        tool_names = agent_tool_sets.get(agent_name, agent_tool_sets['default'])
        
        # Create tools
        tools = []
        for tool_name in tool_names:
            if tool_name in ENHANCED_MCP_TOOL_MAPPING:
                mcp_method = ENHANCED_MCP_TOOL_MAPPING[tool_name]
                tool = self.create_langchain_tool(tool_name, mcp_method)
                
                # Inject client_id if provided
                if client_id:
                    original_func = tool.func
                    def wrapped_func(query: str = "", **kwargs):
                        kwargs.setdefault('client_id', client_id)
                        return original_func(query, **kwargs)
                    tool.func = wrapped_func
                
                tools.append(tool)
        
        logger.info(f"Created {len(tools)} tools for agent {agent_name}")
        return tools
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

# Global adapter instance
_adapter_instance = None

def get_enhanced_mcp_adapter() -> EnhancedMCPAdapter:
    """Get or create the global Enhanced MCP adapter instance"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = EnhancedMCPAdapter()
    return _adapter_instance

def get_enhanced_tools_for_agent(agent_name: str, client_id: str = None) -> List[Tool]:
    """
    Convenience function to get Enhanced MCP tools for an agent
    
    Args:
        agent_name: Name of the agent
        client_id: Default client ID
    
    Returns:
        List of LangChain tools
    """
    adapter = get_enhanced_mcp_adapter()
    return adapter.get_tools_for_agent(agent_name, client_id)