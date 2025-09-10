"""
Direct Klaviyo API Tools for LangGraph
Simple, working MCP tools that directly integrate with Klaviyo API
"""

import json
import httpx
import logging
from typing import Dict, Any, List, Optional
from langchain.tools import Tool
import os
from google.cloud import firestore

logger = logging.getLogger(__name__)

class DirectKlaviyoMCP:
    """Direct Klaviyo API integration for LangGraph agents"""
    
    def __init__(self):
        self.base_url = "https://a.klaviyo.com/api"
        # Initialize Firestore client directly
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        self.db = firestore.Client(project=project_id)
        
    async def get_api_key(self, client_id: str) -> Optional[str]:
        """Get Klaviyo API key for client from the working key endpoint"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use the working key endpoint
                response = await client.get(f"http://localhost:8000/api/mcp/klaviyo/keys/{client_id}/actual")
                
                if response.status_code == 200:
                    key_data = response.json()
                    api_key = key_data.get("api_key")
                    
                    if api_key:
                        logger.info(f"✅ Retrieved Klaviyo API key for client {client_id}")
                        return api_key
                    else:
                        logger.warning(f"⚠️  No api_key in response for client {client_id}")
                        return None
                else:
                    logger.error(f"❌ Key endpoint returned {response.status_code} for {client_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to get API key for {client_id}: {e}")
            return None
    
    async def call_klaviyo_api(self, endpoint: str, client_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make direct Klaviyo API call"""
        api_key = await self.get_api_key(client_id)
        if not api_key:
            return {"error": f"No API key found for client {client_id}"}
        
        headers = {
            "Authorization": f"Klaviyo-API-Key {api_key}",
            "Content-Type": "application/json",
            "revision": "2024-10-15"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/{endpoint}"
                if params:
                    response = await client.get(url, headers=headers, params=params)
                else:
                    response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Klaviyo API success: {endpoint} for {client_id}")
                    return {"success": True, "data": data}
                else:
                    logger.error(f"Klaviyo API error {response.status_code}: {response.text[:200]}")
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}
                    
        except Exception as e:
            logger.error(f"Klaviyo API exception: {e}")
            return {"success": False, "error": str(e)}
    
    def create_segments_tool(self) -> Tool:
        """Create LangChain tool for segments"""
        def get_segments(query: str = "", client_id: str = None, **kwargs) -> str:
            """Get customer segments from Klaviyo"""
            import asyncio
            
            if not client_id:
                client_id = kwargs.get('brand_id') or 'default'
            
            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async call
                result = loop.run_until_complete(
                    self.call_klaviyo_api("segments", client_id)
                )
                
                if result.get("success"):
                    segments_data = result.get("data", {})
                    segments = segments_data.get("data", [])
                    
                    # Format for agent consumption
                    formatted_segments = []
                    for segment in segments:
                        attrs = segment.get("attributes", {})
                        formatted_segments.append({
                            "id": segment.get("id"),
                            "name": attrs.get("name", "Unknown"),
                            "definition": attrs.get("definition", ""),
                            "is_active": attrs.get("is_active", False),
                            "created": attrs.get("created"),
                            "updated": attrs.get("updated")
                        })
                    
                    return json.dumps({
                        "client_id": client_id,
                        "total_segments": len(formatted_segments),
                        "segments": formatted_segments[:10],  # Limit to first 10
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                else:
                    return json.dumps({
                        "error": result.get("error"),
                        "client_id": client_id,
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                    
            except Exception as e:
                return json.dumps({
                    "error": str(e),
                    "client_id": client_id,
                    "source": "Direct Klaviyo API"
                }, indent=2)
        
        return Tool(
            name="klaviyo_segments_direct",
            description="Get customer segments directly from Klaviyo API",
            func=get_segments
        )
    
    def create_campaigns_tool(self) -> Tool:
        """Create LangChain tool for campaigns"""
        def get_campaigns(query: str = "", client_id: str = None, **kwargs) -> str:
            """Get email campaigns from Klaviyo"""
            import asyncio
            
            if not client_id:
                client_id = kwargs.get('brand_id') or 'default'
                
            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async call (campaigns API uses different parameter format)
                result = loop.run_until_complete(
                    self.call_klaviyo_api("campaigns", client_id, {"page[size]": "25"})
                )
                
                if result.get("success"):
                    campaigns_data = result.get("data", {})
                    campaigns = campaigns_data.get("data", [])
                    
                    # Format for agent consumption
                    formatted_campaigns = []
                    for campaign in campaigns:
                        attrs = campaign.get("attributes", {})
                        formatted_campaigns.append({
                            "id": campaign.get("id"),
                            "name": attrs.get("name", "Unknown"),
                            "subject": attrs.get("subject", ""),
                            "status": attrs.get("status", ""),
                            "send_time": attrs.get("send_time"),
                            "created_at": attrs.get("created_at"),
                            "updated_at": attrs.get("updated_at")
                        })
                    
                    return json.dumps({
                        "client_id": client_id,
                        "total_campaigns": len(formatted_campaigns),
                        "campaigns": formatted_campaigns,
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                else:
                    return json.dumps({
                        "error": result.get("error"),
                        "client_id": client_id,
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                    
            except Exception as e:
                return json.dumps({
                    "error": str(e),
                    "client_id": client_id,
                    "source": "Direct Klaviyo API"
                }, indent=2)
        
        return Tool(
            name="klaviyo_campaigns_direct",
            description="Get email campaigns directly from Klaviyo API",
            func=get_campaigns
        )
    
    def create_metrics_tool(self) -> Tool:
        """Create LangChain tool for metrics"""
        def get_metrics(query: str = "", client_id: str = None, **kwargs) -> str:
            """Get metrics from Klaviyo"""
            import asyncio
            
            if not client_id:
                client_id = kwargs.get('brand_id') or 'default'
                
            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async call
                result = loop.run_until_complete(
                    self.call_klaviyo_api("metrics", client_id)
                )
                
                if result.get("success"):
                    metrics_data = result.get("data", {})
                    metrics = metrics_data.get("data", [])
                    
                    # Format for agent consumption
                    formatted_metrics = []
                    for metric in metrics:
                        attrs = metric.get("attributes", {})
                        formatted_metrics.append({
                            "id": metric.get("id"),
                            "name": attrs.get("name", "Unknown"),
                            "integration": attrs.get("integration", {}),
                            "created": attrs.get("created")
                        })
                    
                    return json.dumps({
                        "client_id": client_id,
                        "total_metrics": len(formatted_metrics),
                        "metrics": formatted_metrics,
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                else:
                    return json.dumps({
                        "error": result.get("error"),
                        "client_id": client_id,
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                    
            except Exception as e:
                return json.dumps({
                    "error": str(e),
                    "client_id": client_id,
                    "source": "Direct Klaviyo API"
                }, indent=2)
        
        return Tool(
            name="klaviyo_metrics_direct",
            description="Get metrics directly from Klaviyo API",
            func=get_metrics
        )
    
    def create_flows_tool(self) -> Tool:
        """Create LangChain tool for flows (automation)"""
        def get_flows(query: str = "", client_id: str = None, **kwargs) -> str:
            """Get automation flows from Klaviyo"""
            import asyncio
            
            if not client_id:
                client_id = kwargs.get('brand_id') or 'default'
                
            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async call
                result = loop.run_until_complete(
                    self.call_klaviyo_api("flows", client_id)
                )
                
                if result.get("success"):
                    flows_data = result.get("data", {})
                    flows = flows_data.get("data", [])
                    
                    # Format for agent consumption
                    formatted_flows = []
                    for flow in flows:
                        attrs = flow.get("attributes", {})
                        formatted_flows.append({
                            "id": flow.get("id"),
                            "name": attrs.get("name", "Unknown"),
                            "status": attrs.get("status", ""),
                            "created": attrs.get("created"),
                            "updated": attrs.get("updated"),
                            "trigger_type": attrs.get("trigger_type", "")
                        })
                    
                    return json.dumps({
                        "client_id": client_id,
                        "total_flows": len(formatted_flows),
                        "flows": formatted_flows,
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                else:
                    return json.dumps({
                        "error": result.get("error"),
                        "client_id": client_id,
                        "source": "Direct Klaviyo API"
                    }, indent=2)
                    
            except Exception as e:
                return json.dumps({
                    "error": str(e),
                    "client_id": client_id,
                    "source": "Direct Klaviyo API"
                }, indent=2)
        
        return Tool(
            name="klaviyo_flows_direct",
            description="Get automation flows directly from Klaviyo API",
            func=get_flows
        )
    
    def get_all_tools_for_client(self, client_id: str) -> List[Tool]:
        """Get all Klaviyo tools configured for a specific client"""
        tools = [
            self.create_segments_tool(),
            self.create_campaigns_tool(),
            self.create_metrics_tool(),
            self.create_flows_tool()
        ]
        
        # Pre-configure client_id for all tools
        for tool in tools:
            original_func = tool.func
            def make_client_aware_func(client_id, original_func):
                def wrapper(query: str = "", **kwargs):
                    kwargs.setdefault('client_id', client_id)
                    return original_func(query, **kwargs)
                return wrapper
            tool.func = make_client_aware_func(client_id, original_func)
        
        logger.info(f"Created {len(tools)} direct Klaviyo tools for client {client_id}")
        return tools

# Global instance
_direct_klaviyo_mcp = None

def get_direct_klaviyo_mcp() -> DirectKlaviyoMCP:
    """Get global Direct Klaviyo MCP instance"""
    global _direct_klaviyo_mcp
    if _direct_klaviyo_mcp is None:
        _direct_klaviyo_mcp = DirectKlaviyoMCP()
    return _direct_klaviyo_mcp

def get_klaviyo_tools_for_client(client_id: str) -> List[Tool]:
    """Convenience function to get all Klaviyo tools for a client"""
    mcp = get_direct_klaviyo_mcp()
    return mcp.get_all_tools_for_client(client_id)