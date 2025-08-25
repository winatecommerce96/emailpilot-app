#!/usr/bin/env python3
"""
Test script to verify MCP server connection and functionality.
Run this while the MCP server is running on port 9090.
"""

import httpx
import json
import asyncio
from typing import Dict, Any

async def test_mcp_server():
    """Test the MCP server connection and list available tools."""
    
    base_url = "http://localhost:9090"
    
    print("🔍 Testing MCP Server Connection...")
    print("="*50)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Check if server is responding
        try:
            # MCP servers typically expose a tools listing endpoint
            response = await client.post(
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1
                }
            )
            
            if response.status_code == 200:
                print("✅ MCP Server is responding!")
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            else:
                print(f"⚠️ Server returned status {response.status_code}")
                print(f"Response: {response.text}")
                
        except httpx.ConnectError:
            print("❌ Cannot connect to MCP server at localhost:9090")
            print("Make sure the server is running: python server.py --port 9090")
            return
        except Exception as e:
            print(f"❌ Error: {e}")
            return
        
        # Test 2: Try to call a specific tool
        print("\n📋 Testing agent tool call...")
        print("-"*50)
        
        try:
            response = await client.post(
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "content_strategist",
                        "arguments": {
                            "brand_id": "test-brand",
                            "month": "2024-11"
                        }
                    },
                    "id": 2
                }
            )
            
            if response.status_code == 200:
                print("✅ Tool call successful!")
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"⚠️ Tool call returned status {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Tool call error: {e}")
    
    print("\n" + "="*50)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())