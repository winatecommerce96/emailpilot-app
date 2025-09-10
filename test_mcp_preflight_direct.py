#!/usr/bin/env python3
"""
Test Direct MCP Preflight Function
"""

import asyncio
import sys
import os
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from emailpilot_graph.mcp_preflight_direct import preflight_mcp_check_direct

async def test_direct_preflight():
    """Test the direct MCP preflight function"""
    client_id = "milagro-mushrooms"
    client_name = "Milagro Mushrooms"
    
    print(f"🧪 Testing Direct MCP Preflight for: {client_name} ({client_id})")
    print("=" * 70)
    
    # Create test state
    state = {
        "client_id": client_id,
        "client_name": client_name,
        "use_real_data": True,
        "selected_month": "2025-02"
    }
    
    try:
        # Run the preflight check
        result_state = await preflight_mcp_check_direct(state)
        
        print(f"Status: {result_state.get('status')}")
        print(f"MCP Available: {result_state.get('mcp_status', {}).get('available')}")
        print(f"Service: {result_state.get('mcp_status', {}).get('service')}")
        print(f"Tools Created: {result_state.get('mcp_status', {}).get('tools_created', 0)}")
        
        # Show data prefetched
        data_status = result_state.get('mcp_status', {}).get('data_prefetched', {})
        print(f"\nData Prefetched:")
        for data_type, available in data_status.items():
            status_emoji = "✅" if available else "❌"
            print(f"  {status_emoji} {data_type}: {available}")
        
        # Show actual data counts if available
        print(f"\nActual Data Retrieved:")
        if "klaviyo_segments" in result_state:
            segments = result_state["klaviyo_segments"]
            segment_count = segments.get("total_segments", 0)
            print(f"  📊 Segments: {segment_count}")
            
        if "klaviyo_campaigns" in result_state:
            campaigns = result_state["klaviyo_campaigns"]
            campaign_count = campaigns.get("total_campaigns", 0)
            print(f"  📧 Campaigns: {campaign_count}")
            
        if "klaviyo_flows" in result_state:
            flows = result_state["klaviyo_flows"]
            flow_count = flows.get("total_flows", 0)
            print(f"  🔄 Flows: {flow_count}")
            
        if "klaviyo_metrics" in result_state:
            metrics = result_state["klaviyo_metrics"]
            metric_count = metrics.get("total_metrics", 0)
            print(f"  📈 Metrics: {metric_count}")
        
        # Show MCP tools
        if "mcp_tools" in result_state and result_state["mcp_tools"]:
            tools = result_state["mcp_tools"]
            print(f"\nMCP Tools Available for LangGraph:")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool.name} - {tool.description}")
        
        print(f"\n{'='*70}")
        print(f"🏁 Direct MCP Preflight Test Complete!")
        
        if result_state.get('mcp_status', {}).get('available'):
            print("✅ SUCCESS: Real Klaviyo data is now available to LangGraph agents!")
        else:
            print("❌ FAILED: Falling back to mock data")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_preflight())