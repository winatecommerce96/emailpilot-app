#!/usr/bin/env python3

"""
Test script for Email/SMS Multi-Agent MCP Server cloud deployment
Validates all endpoints and agent functionality
"""

import asyncio
import aiohttp
import json
import time
import sys
from typing import Dict, Any

class CloudMCPTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health_check(self) -> bool:
        """Test health check endpoint"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health Check: {data}")
                    return True
                else:
                    print(f"❌ Health Check Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
            return False
    
    async def test_list_tools(self) -> bool:
        """Test MCP list tools endpoint"""
        try:
            async with self.session.post(f"{self.base_url}/mcp/list_tools") as response:
                if response.status == 200:
                    data = await response.json()
                    tools = data.get('tools', [])
                    print(f"✅ List Tools: Found {len(tools)} tools")
                    for tool in tools:
                        print(f"   - {tool['name']}: {tool['description']}")
                    return len(tools) > 0
                else:
                    print(f"❌ List Tools Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ List Tools Error: {e}")
            return False
    
    async def test_list_resources(self) -> bool:
        """Test MCP list resources endpoint"""
        try:
            async with self.session.post(f"{self.base_url}/mcp/list_resources") as response:
                if response.status == 200:
                    data = await response.json()
                    resources = data.get('resources', [])
                    print(f"✅ List Resources: Found {len(resources)} resources")
                    for resource in resources:
                        print(f"   - {resource['name']}: {resource['uri']}")
                    return len(resources) > 0
                else:
                    print(f"❌ List Resources Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ List Resources Error: {e}")
            return False
    
    async def test_email_campaign_creation(self) -> bool:
        """Test email campaign creation tool"""
        try:
            request_data = {
                "name": "create_email_campaign",
                "arguments": {
                    "campaign_type": "promotional",
                    "target_audience": "high-value customers",
                    "objectives": ["increase_sales", "drive_engagement"],
                    "brand_guidelines": {
                        "tone": "professional",
                        "colors": {"primary": "#007bff"}
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp/call_tool", 
                json=request_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get('content', [])
                    if content:
                        result = json.loads(content[0]['text'])
                        print("✅ Email Campaign Creation: Success")
                        print(f"   - Workflow completed: {result.get('campaign_creation_complete')}")
                        print(f"   - Results sections: {len(result.get('workflow_results', {}))}")
                        return True
                    else:
                        print("❌ Email Campaign Creation: Empty response")
                        return False
                else:
                    print(f"❌ Email Campaign Creation Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Email Campaign Creation Error: {e}")
            return False
    
    async def test_sms_campaign_creation(self) -> bool:
        """Test SMS campaign creation tool"""
        try:
            request_data = {
                "name": "create_sms_campaign",
                "arguments": {
                    "campaign_type": "flash_sale",
                    "target_audience": "mobile-engaged users",
                    "objectives": ["create_urgency"],
                    "character_limit": 160
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp/call_tool",
                json=request_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get('content', [])
                    if content:
                        result = json.loads(content[0]['text'])
                        print("✅ SMS Campaign Creation: Success")
                        print(f"   - Workflow completed: {result.get('campaign_creation_complete')}")
                        return True
                    else:
                        print("❌ SMS Campaign Creation: Empty response")
                        return False
                else:
                    print(f"❌ SMS Campaign Creation Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ SMS Campaign Creation Error: {e}")
            return False
    
    async def test_agent_consultation(self) -> bool:
        """Test individual agent consultation"""
        try:
            request_data = {
                "name": "consult_agent",
                "arguments": {
                    "agent_name": "copywriter",
                    "request": {
                        "content_type": "email",
                        "campaign_context": {
                            "type": "newsletter",
                            "audience": "subscribers"
                        }
                    }
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/mcp/call_tool",
                json=request_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get('content', [])
                    if content:
                        result = json.loads(content[0]['text'])
                        print("✅ Agent Consultation: Success")
                        print(f"   - Agent: {result.get('agent')}")
                        print(f"   - Copy elements: {list(result.get('copy_elements', {}).keys())}")
                        return True
                    else:
                        print("❌ Agent Consultation: Empty response")
                        return False
                else:
                    print(f"❌ Agent Consultation Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Agent Consultation Error: {e}")
            return False
    
    async def test_emailpilot_api_endpoints(self) -> bool:
        """Test EmailPilot-specific API endpoints"""
        try:
            # Test agents list endpoint
            async with self.session.get(f"{self.base_url}/api/agents") as response:
                if response.status == 200:
                    data = await response.json()
                    agents = data.get('agents', {})
                    print(f"✅ EmailPilot API - List Agents: Found {len(agents)} agents")
                    return True
                else:
                    print(f"❌ EmailPilot API - List Agents Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ EmailPilot API Error: {e}")
            return False
    
    async def test_performance(self) -> bool:
        """Test response performance"""
        try:
            start_time = time.time()
            
            # Test a simple health check
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    print(f"✅ Performance Test: {response_time:.2f}ms response time")
                    return response_time < 5000  # Should respond in under 5 seconds
                else:
                    print(f"❌ Performance Test Failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Performance Test Error: {e}")
            return False

async def main():
    if len(sys.argv) != 2:
        print("Usage: python test_cloud_deployment.py <service_url>")
        print("Example: python test_cloud_deployment.py https://email-sms-mcp-server-xyz.a.run.app")
        sys.exit(1)
    
    service_url = sys.argv[1]
    
    print("🧪 Testing Email/SMS Multi-Agent MCP Server Cloud Deployment")
    print("=" * 70)
    print(f"Service URL: {service_url}")
    print("")
    
    async with CloudMCPTester(service_url) as tester:
        tests = [
            ("Health Check", tester.test_health_check),
            ("Performance", tester.test_performance),
            ("List Tools", tester.test_list_tools),
            ("List Resources", tester.test_list_resources),
            ("Email Campaign Creation", tester.test_email_campaign_creation),
            ("SMS Campaign Creation", tester.test_sms_campaign_creation),
            ("Agent Consultation", tester.test_agent_consultation),
            ("EmailPilot API Endpoints", tester.test_emailpilot_api_endpoints),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...")
            try:
                result = await test_func()
                results.append((test_name, result))
                if result:
                    print(f"   ✅ {test_name} PASSED")
                else:
                    print(f"   ❌ {test_name} FAILED")
            except Exception as e:
                print(f"   ❌ {test_name} ERROR: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! MCP server is ready for production use.")
            print(f"\n📋 Configure in Claude Code:")
            print(f"claude mcp add email-sms-agents --transport http {service_url}")
            return 0
        else:
            print("⚠️  Some tests failed. Please check the deployment.")
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())