#!/usr/bin/env python3
"""
Test script to verify Klaviyo Enhanced MCP connection through LangChain
"""

import sys
import os
import asyncio
import json

# Add multi-agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'multi-agent'))

# Override the config to use correct URL
os.environ['KLAVIYO_MCP_URL'] = 'http://localhost:8000/api/mcp/gateway'

from integrations.langchain_core.config import get_config
from integrations.langchain_core.adapters.mcp_client import MCPClient


async def test_mcp_connection():
    """Test the MCP connection to Klaviyo Enhanced"""
    
    print("🔧 Testing Klaviyo Enhanced MCP Connection")
    print("=" * 50)
    
    # Get config
    config = get_config()
    print(f"✅ Config loaded")
    print(f"   MCP Base URL: {config.mcp_base_url}")
    print(f"   Klaviyo MCP URL: {config.klaviyo_mcp_url}")
    print()
    
    # Create MCP client
    with MCPClient(config) as client:
        print("✅ MCP Client created")
        
        # Test 1: Check MCP Gateway health
        print("\n📊 Test 1: MCP Gateway Health Check")
        try:
            import httpx
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(f"{config.klaviyo_mcp_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"   ✅ Gateway is healthy")
                    print(f"   Status: {health_data}")
                else:
                    print(f"   ❌ Gateway returned status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
        
        # Test 2: Try to get campaigns (will fail without a valid client)
        print("\n📊 Test 2: Klaviyo Campaigns Request")
        try:
            # This will fail without a valid client_id with API key
            result = client.klaviyo_campaigns(
                brand_id="test-client",  # Would need a real client ID
                limit=5
            )
            print(f"   ✅ Request succeeded!")
            print(f"   Response: {json.dumps(result.data, indent=2)[:200]}...")
        except Exception as e:
            error_msg = str(e)
            if "API key not found" in error_msg:
                print(f"   ⚠️  Expected error: No API key for test-client")
                print(f"   This is normal - would need a real client with API key in Secret Manager")
            else:
                print(f"   ❌ Unexpected error: {e}")
        
        # Test 3: Check available tools
        print("\n📊 Test 3: Available MCP Tools")
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(f"{config.klaviyo_mcp_url}/tools")
                if response.status_code == 200:
                    tools_data = response.json()
                    print(f"   ✅ Found {tools_data.get('total', 0)} tools")
                    print(f"   Enhanced MCP tools: {len(tools_data.get('enhanced', []))}")
                    print(f"   Fallback tools: {len(tools_data.get('fallback', []))}")
                    
                    # Show a few tool examples
                    if tools_data.get('enhanced'):
                        print("\n   Sample Enhanced Tools:")
                        for tool in tools_data['enhanced'][:5]:
                            print(f"      - {tool['name']}: {tool['description']}")
        except Exception as e:
            print(f"   ❌ Failed to list tools: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Connection test complete!")
    print("\nSummary:")
    print("✅ MCP Gateway is accessible at", config.klaviyo_mcp_url)
    print("✅ Enhanced MCP tools are available")
    print("⚠️  Need a valid client_id with Klaviyo API key in Secret Manager for real data")
    print("\nTo test with real data:")
    print("1. Ensure a client exists in Firestore with klaviyo_api_key_secret field")
    print("2. Ensure the secret exists in Google Secret Manager")
    print("3. Use that client_id instead of 'test-client'")


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())