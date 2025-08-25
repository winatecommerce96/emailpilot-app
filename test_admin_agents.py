#!/usr/bin/env python3

"""
Test script for Admin Agents Management Interface
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def test_admin_agents():
    # Create session with cookie jar for authentication
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, cookie_jar=aiohttp.CookieJar()) as session:
        # First, do dev login
        print("🔐 Logging in as admin...")
        login_data = {"email": "admin@emailpilot.ai"}
        async with session.post(f"{BASE_URL}/api/admin/dev-login", json=login_data) as response:
            if response.status == 200:
                print("✅ Logged in successfully")
            else:
                print(f"❌ Login failed: {response.status}")
                return
        
        # Test agent configuration endpoint
        print("\n📋 Testing agent configuration endpoint...")
        async with session.get(f"{BASE_URL}/api/admin/agents/config") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Configuration loaded: {len(data.get('default_config', {}).get('agents', {}))} agents")
            else:
                print(f"❌ Failed to load config: {response.status}")
        
        # Test templates endpoint
        print("\n📄 Testing templates endpoint...")
        async with session.get(f"{BASE_URL}/api/admin/agents/templates") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Templates loaded: {list(data.keys())}")
            else:
                print(f"❌ Failed to load templates: {response.status}")
        
        # Test performance metrics endpoint
        print("\n📊 Testing performance metrics endpoint...")
        async with session.get(f"{BASE_URL}/api/admin/agents/performance") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Metrics loaded: {data.get('overall', {}).get('total_campaigns', 0)} campaigns")
            else:
                print(f"❌ Failed to load metrics: {response.status}")
        
        # Test admin agents page
        print("\n🌐 Testing admin agents web interface...")
        async with session.get(f"{BASE_URL}/admin/agents") as response:
            if response.status == 200:
                print("✅ Admin agents interface accessible")
                print(f"   URL: {BASE_URL}/admin/agents")
            else:
                print(f"❌ Admin interface not accessible: {response.status}")
        
        print("\n✨ All tests complete!")
        print(f"📎 Access the admin interface at: {BASE_URL}/admin/agents")

if __name__ == "__main__":
    asyncio.run(test_admin_agents())