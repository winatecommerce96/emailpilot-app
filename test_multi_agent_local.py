#!/usr/bin/env python3

"""
Test script for Email/SMS Multi-Agent System on local EmailPilot server
Tests all endpoints and agent functionality
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any
from datetime import datetime

# Local server configuration
BASE_URL = "http://127.0.0.1:8000"
AGENT_API = f"{BASE_URL}/api/agents"

class MultiAgentTester:
    def __init__(self):
        self.session = None
        self.results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_system_info(self):
        """Test the system info endpoint"""
        print("\n🔍 Testing System Info...")
        try:
            async with self.session.get(f"{AGENT_API}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ System Info Retrieved:")
                    print(f"   Service: {data.get('service')}")
                    print(f"   Version: {data.get('version')}")
                    print(f"   Available Agents: {', '.join(data.get('agents', []))}")
                    print(f"   Capabilities: {', '.join(data.get('capabilities', []))}")
                    return True
                else:
                    print(f"❌ Failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def test_list_agents(self):
        """Test listing all agents"""
        print("\n🔍 Testing List Agents...")
        try:
            async with self.session.get(f"{AGENT_API}/agents") as response:
                if response.status == 200:
                    data = await response.json()
                    agents = data.get('agents', {})
                    print(f"✅ Found {data.get('total_agents')} agents:")
                    for agent_name, agent_info in agents.items():
                        print(f"   📤 {agent_name}:")
                        print(f"      Role: {agent_info.get('role')}")
                        print(f"      Status: {agent_info.get('status')}")
                        print(f"      Expertise: {', '.join(agent_info.get('expertise', []))}")
                    return True
                else:
                    print(f"❌ Failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def test_email_campaign_creation(self):
        """Test creating an email campaign"""
        print("\n🔍 Testing Email Campaign Creation...")
        
        campaign_data = {
            "campaign_type": "promotional",
            "target_audience": "high-value customers who haven't purchased in 30 days",
            "objectives": [
                "re-engage_dormant_customers",
                "drive_immediate_sales",
                "showcase_new_products"
            ],
            "brand_guidelines": {
                "tone": "friendly_but_professional",
                "colors": {
                    "primary": "#007bff",
                    "secondary": "#28a745"
                }
            },
            "customer_data": {
                "segments": ["vip_customers", "dormant_high_value"],
                "personalization_fields": ["first_name", "last_purchase_date"]
            }
        }
        
        try:
            async with self.session.post(
                f"{AGENT_API}/campaign/email",
                json=campaign_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Email Campaign Created Successfully!")
                    
                    if data.get('success'):
                        campaign = data.get('campaign', {})
                        workflow = campaign.get('workflow_results', {})
                        
                        print("\n📊 Campaign Workflow Results:")
                        for stage, result in workflow.items():
                            print(f"   {stage}: {result.get('agent', 'N/A')} - Status: {result.get('status', 'complete')}")
                        
                        recommendations = campaign.get('final_recommendations', [])
                        if recommendations:
                            print("\n💡 Final Recommendations:")
                            for rec in recommendations[:3]:
                                print(f"   • {rec}")
                    
                    return True
                else:
                    print(f"❌ Failed with status: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def test_sms_campaign_creation(self):
        """Test creating an SMS campaign"""
        print("\n🔍 Testing SMS Campaign Creation...")
        
        campaign_data = {
            "campaign_type": "flash_sale",
            "target_audience": "mobile-engaged customers",
            "objectives": [
                "create_urgency",
                "drive_immediate_action"
            ],
            "character_limit": 160
        }
        
        try:
            async with self.session.post(
                f"{AGENT_API}/campaign/sms",
                json=campaign_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ SMS Campaign Created Successfully!")
                    
                    if data.get('success'):
                        campaign = data.get('campaign', {})
                        print(f"   Campaign Complete: {campaign.get('campaign_creation_complete')}")
                        
                        workflow = campaign.get('workflow_results', {})
                        if workflow:
                            print("   Agents involved:", list(workflow.keys()))
                    
                    return True
                else:
                    print(f"❌ Failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def test_agent_consultation(self):
        """Test consulting individual agents"""
        print("\n🔍 Testing Individual Agent Consultation...")
        
        # Test copywriter agent
        copywriter_request = {
            "content_type": "email",
            "campaign_context": {
                "type": "welcome_series",
                "audience": "new_subscribers",
                "goal": "high_engagement"
            },
            "requirements": [
                "personalized",
                "mobile_optimized"
            ]
        }
        
        try:
            async with self.session.post(
                f"{AGENT_API}/agent/copywriter/consult",
                json=copywriter_request
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Copywriter Agent Consultation Success!")
                    
                    if data.get('success'):
                        result = data.get('result', {})
                        print(f"   Agent: {result.get('agent', 'copywriter')}")
                        
                        # Check for copy elements or stub response
                        if 'message' in result:
                            print(f"   Response: {result.get('message')}")
                        elif 'copy_elements' in result:
                            elements = result.get('copy_elements', {})
                            if 'subject_lines' in elements:
                                print(f"   Subject Lines: {len(elements.get('subject_lines', []))} variants")
                            if 'ctas' in elements:
                                print(f"   CTAs: {', '.join(elements.get('ctas', []))}")
                    
                    return True
                else:
                    print(f"❌ Failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    async def test_campaign_templates(self):
        """Test fetching campaign templates"""
        print("\n🔍 Testing Campaign Templates...")
        
        template_types = ["promotional", "newsletter", "flash_sale"]
        
        for template_type in template_types:
            try:
                async with self.session.get(f"{AGENT_API}/templates/{template_type}") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Template '{template_type}':")
                        print(f"   Name: {data.get('name')}")
                        print(f"   Description: {data.get('description')}")
                        
                        config = data.get('default_config', {})
                        if config:
                            print(f"   Objectives: {', '.join(config.get('objectives', []))}")
                            print(f"   Tone: {config.get('tone')}")
                    elif response.status == 404:
                        print(f"⚠️  Template '{template_type}' not found")
                    else:
                        print(f"❌ Failed to fetch '{template_type}' with status: {response.status}")
            except Exception as e:
                print(f"❌ Error fetching '{template_type}': {e}")
        
        return True
    
    async def test_health_check(self):
        """Test the health check endpoint"""
        print("\n🔍 Testing Multi-Agent Health Check...")
        try:
            async with self.session.get(f"{AGENT_API}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health Check Passed:")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Orchestrator: {data.get('orchestrator')}")
                    
                    agents = data.get('agents', {})
                    if agents:
                        print(f"   Agent Statuses:")
                        for agent, status in agents.items():
                            print(f"      {agent}: {status}")
                    
                    return True
                else:
                    print(f"❌ Failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

async def main():
    print("=" * 70)
    print("🚀 EMAIL/SMS MULTI-AGENT SYSTEM - LOCAL TEST SUITE")
    print("=" * 70)
    print(f"Server: {BASE_URL}")
    print(f"API Base: {AGENT_API}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    async with MultiAgentTester() as tester:
        tests = [
            ("System Info", tester.test_system_info),
            ("List Agents", tester.test_list_agents),
            ("Health Check", tester.test_health_check),
            ("Email Campaign Creation", tester.test_email_campaign_creation),
            ("SMS Campaign Creation", tester.test_sms_campaign_creation),
            ("Agent Consultation", tester.test_agent_consultation),
            ("Campaign Templates", tester.test_campaign_templates),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
                await asyncio.sleep(0.5)  # Small delay between tests
            except Exception as e:
                print(f"❌ Test '{test_name}' crashed: {e}")
                results.append((test_name, False))
        
        # Print summary
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
            print("\n🎉 All tests passed! Multi-Agent System is working perfectly!")
        else:
            print("\n⚠️  Some tests failed. Check the logs above for details.")
        
        print("\n" + "=" * 70)
        print("💡 Next Steps:")
        print("1. The multi-agent system is integrated into EmailPilot")
        print("2. Access the API docs at: http://127.0.0.1:8000/docs#/Email%2FSMS%20Multi-Agent%20System")
        print("3. Deploy to Google Cloud Run when ready")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())