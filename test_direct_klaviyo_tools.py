#!/usr/bin/env python3
"""
Test script for Direct Klaviyo API Tools
Verify that the direct tools work with real API calls
"""

import asyncio
import sys
import os
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from emailpilot_graph.direct_klaviyo_tools import get_klaviyo_tools_for_client

def test_klaviyo_tools():
    """Test the direct Klaviyo tools with a real client"""
    client_id = "milagro-mushrooms"  # Use a client we know has an API key
    
    print(f"🧪 Testing Direct Klaviyo API Tools for client: {client_id}")
    print("=" * 60)
    
    try:
        # Get tools for the client
        tools = get_klaviyo_tools_for_client(client_id)
        print(f"✅ Successfully created {len(tools)} tools")
        
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. Testing {tool.name}...")
            try:
                result = tool.func(f"Test query for {tool.name}", client_id=client_id)
                
                # Parse the JSON result
                data = json.loads(result)
                
                if "error" in data:
                    print(f"   ⚠️  Error: {data['error']}")
                else:
                    # Show summary of what we got
                    if "segments" in data:
                        segment_count = data.get("total_segments", 0)
                        print(f"   ✅ Found {segment_count} segments")
                    elif "campaigns" in data:
                        campaign_count = data.get("total_campaigns", 0)
                        print(f"   ✅ Found {campaign_count} campaigns")
                    elif "flows" in data:
                        flow_count = data.get("total_flows", 0)
                        print(f"   ✅ Found {flow_count} flows")
                    elif "metrics" in data:
                        metric_count = data.get("total_metrics", 0)
                        print(f"   ✅ Found {metric_count} metrics")
                    else:
                        print(f"   ✅ Success: {len(result)} characters of data")
                        
            except Exception as tool_error:
                print(f"   ❌ Failed: {tool_error}")
        
        print(f"\n{'='*60}")
        print(f"🏁 Test completed for {client_id}")
        
    except Exception as e:
        print(f"❌ Failed to create tools: {e}")

if __name__ == "__main__":
    test_klaviyo_tools()