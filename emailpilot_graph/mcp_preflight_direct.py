"""
Direct MCP Preflight Function
Replace the problematic natural language approach with working direct Klaviyo tools
"""

import json
import logging
from typing import Dict, Any
from .direct_klaviyo_tools import get_klaviyo_tools_for_client

logger = logging.getLogger(__name__)

async def preflight_mcp_check_direct(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct MCP Preflight Check using working Klaviyo API tools
    
    This creates LangChain tools that actually work with real Klaviyo data
    and pre-fetches data to verify connectivity
    """
    logger.info("🔧 Direct MCP Preflight Check - Creating working Klaviyo API tools")
    
    # Check if we should use mock data for testing
    if not state.get("use_real_data", True):
        logger.info("Using mock data - skipping MCP setup")
        state["mcp_tools"] = []
        state["mcp_adapter"] = None
        state["mcp_status"] = {"available": False, "reason": "Using mock data"}
        state["status"] = "mcp_check_complete"
        return state
    
    client_id = state["client_id"]
    client_name = state["client_name"]
    
    try:
        # Create direct Klaviyo API tools for this client
        klaviyo_tools = get_klaviyo_tools_for_client(client_id)
        logger.info(f"✅ Created {len(klaviyo_tools)} Klaviyo API tools")
        
        # Test and pre-fetch data from each tool
        segments_data = {}
        campaigns_data = {}
        flows_data = {}
        metrics_data = {}
        
        # Test segments tool
        segments_tool = next((tool for tool in klaviyo_tools if "segments" in tool.name), None)
        if segments_tool:
            try:
                segments_result = segments_tool.func("Get segments for workflow", client_id=client_id)
                segments_data = json.loads(segments_result)
                
                if "error" not in segments_data:
                    segment_count = segments_data.get("total_segments", 0)
                    logger.info(f"✅ Successfully fetched {segment_count} segments for {client_id}")
                    state["klaviyo_segments"] = segments_data
                else:
                    logger.warning(f"⚠️  Klaviyo Segments API error: {segments_data.get('error')}")
                    
            except Exception as test_error:
                logger.warning(f"Segments tool test failed: {test_error}")
        
        # Test campaigns tool
        campaigns_tool = next((tool for tool in klaviyo_tools if "campaigns" in tool.name), None)
        if campaigns_tool:
            try:
                campaigns_result = campaigns_tool.func("Get campaigns for workflow", client_id=client_id)
                campaigns_data = json.loads(campaigns_result)
                
                if "error" not in campaigns_data:
                    campaign_count = campaigns_data.get("total_campaigns", 0)
                    logger.info(f"✅ Successfully fetched {campaign_count} campaigns for {client_id}")
                    state["klaviyo_campaigns"] = campaigns_data
                else:
                    logger.warning(f"⚠️  Klaviyo campaigns API error: {campaigns_data.get('error')}")
                    
            except Exception as test_error:
                logger.warning(f"Campaigns tool test failed: {test_error}")
        
        # Test flows tool
        flows_tool = next((tool for tool in klaviyo_tools if "flows" in tool.name), None)
        if flows_tool:
            try:
                flows_result = flows_tool.func("Get flows for workflow", client_id=client_id)
                flows_data = json.loads(flows_result)
                
                if "error" not in flows_data:
                    flow_count = flows_data.get("total_flows", 0)
                    logger.info(f"✅ Successfully fetched {flow_count} flows for {client_id}")
                    state["klaviyo_flows"] = flows_data
                else:
                    logger.warning(f"⚠️  Klaviyo flows API error: {flows_data.get('error')}")
                    
            except Exception as test_error:
                logger.warning(f"Flows tool test failed: {test_error}")
        
        # Test metrics tool
        metrics_tool = next((tool for tool in klaviyo_tools if "metrics" in tool.name), None)
        if metrics_tool:
            try:
                metrics_result = metrics_tool.func("Get metrics for workflow", client_id=client_id)
                metrics_data = json.loads(metrics_result)
                
                if "error" not in metrics_data:
                    metric_count = metrics_data.get("total_metrics", 0)
                    logger.info(f"✅ Successfully fetched {metric_count} metrics for {client_id}")
                    state["klaviyo_metrics"] = metrics_data
                else:
                    logger.warning(f"⚠️  Klaviyo metrics API error: {metrics_data.get('error')}")
                    
            except Exception as test_error:
                logger.warning(f"Metrics tool test failed: {test_error}")
        
        # Store the working tools in state for LangGraph agents to use
        state["mcp_tools"] = klaviyo_tools
        state["mcp_tool_names"] = [tool.name for tool in klaviyo_tools]
        
        # Set MCP status with real connectivity info
        has_segments = bool(state.get("klaviyo_segments", {}).get("segments"))
        has_campaigns = bool(state.get("klaviyo_campaigns", {}).get("campaigns"))  
        has_flows = bool(state.get("klaviyo_flows", {}).get("flows"))
        has_metrics = bool(state.get("klaviyo_metrics", {}).get("metrics"))
        
        state["mcp_status"] = {
            "available": True,
            "service": "Direct Klaviyo API Integration",
            "endpoint": "https://a.klaviyo.com/api",
            "data_method": "direct_api_tools",
            "tools_created": len(klaviyo_tools),
            "data_prefetched": {
                "segments": has_segments,
                "campaigns": has_campaigns,
                "flows": has_flows,
                "metrics": has_metrics,
                "lists": False,  # Can be added later
                "revenue": False  # Can be added later
            }
        }
        
        state["status"] = "mcp_data_ready"
        logger.info(f"✅ Direct MCP preflight check passed with {len(klaviyo_tools)} working Klaviyo API tools")
        
        return state
        
    except Exception as e:
        logger.error(f"❌ Failed to create direct Klaviyo tools: {e}")
        
        # Fallback to mock data
        state["mcp_tools"] = []
        state["mcp_tool_names"] = []
        state["mcp_status"] = {
            "available": False,
            "service": "Failed - Using Mock Data",
            "endpoint": "N/A",
            "data_method": "mock_only",
            "error": str(e)
        }
        state["status"] = "mcp_check_complete"
        
        return state