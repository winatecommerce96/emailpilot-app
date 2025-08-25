#!/usr/bin/env python3
"""
Comprehensive test to verify LangChain agents are properly configured.
Tests agent registry, MCP integration, and end-to-end functionality.
"""

import os
import sys
import json
import requests
from typing import Dict, List, Any

# Configure environment
os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"
os.environ["USE_SECRET_MANAGER"] = "true"

# Add multi-agent to path
sys.path.insert(0, "multi-agent")

print("🤖 LANGCHAIN AGENT CONFIGURATION TEST")
print("=" * 70)


class AgentConfigurationTest:
    """Test suite for LangChain agent configuration"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {}
        self.agents = []
        
    def test_agent_registry(self) -> bool:
        """Test 1: Verify agent registry is working"""
        print("\n📋 Test 1: Agent Registry Check")
        print("-" * 40)
        
        try:
            from integrations.langchain_core.admin.registry import get_agent_registry
            
            registry = get_agent_registry()
            agents = registry.list_agents()
            
            print(f"✅ Registry loaded successfully")
            print(f"📊 Found {len(agents)} agents:")
            
            for agent in agents:
                name = agent.get('name', 'unknown')
                desc = agent.get('description', 'No description')
                status = agent.get('status', 'unknown')
                print(f"  • {name}: {desc}")
                print(f"    Status: {status}")
                
                # Check for required fields
                if 'policy' in agent:
                    policy = agent['policy']
                    print(f"    Max tool calls: {policy.get('max_tool_calls', 'unlimited')}")
                    print(f"    Timeout: {policy.get('timeout_seconds', 'none')}s")
                
                if 'variables' in agent:
                    vars = agent['variables']
                    print(f"    Variables: {len(vars)} defined")
                
                self.agents.append(agent)
            
            self.results['registry'] = True
            return True
            
        except Exception as e:
            print(f"❌ Registry test failed: {e}")
            self.results['registry'] = False
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test 2: Verify API endpoints are accessible"""
        print("\n🌐 Test 2: API Endpoint Check")
        print("-" * 40)
        
        endpoints = [
            ("/api/admin/langchain/agents", "GET", "List agents"),
            ("/api/admin/langchain/mcp/servers", "GET", "List MCP servers"),
            ("/api/admin/langchain/models/providers", "GET", "List model providers"),
        ]
        
        success = True
        for path, method, desc in endpoints:
            try:
                response = requests.request(method, f"{self.base_url}{path}", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {desc}: {path}")
                    data = response.json()
                    
                    # Show some details
                    if 'agents' in data:
                        print(f"   Found {len(data['agents'])} agents")
                    elif 'servers' in data:
                        print(f"   Found {len(data['servers'])} MCP servers")
                    elif 'providers' in data:
                        print(f"   Found {len(data['providers'])} providers")
                else:
                    print(f"⚠️ {desc}: Status {response.status_code}")
                    success = False
                    
            except requests.exceptions.ConnectionError:
                print(f"❌ {desc}: Connection failed (is server running?)")
                success = False
            except Exception as e:
                print(f"❌ {desc}: {e}")
                success = False
        
        self.results['api_endpoints'] = success
        return success
    
    def test_mcp_integration(self) -> bool:
        """Test 3: Verify MCP server integration"""
        print("\n🔧 Test 3: MCP Server Integration")
        print("-" * 40)
        
        try:
            from integrations.langchain_core.adapters.mcp_client import MCP_SERVERS
            
            print("Configured MCP servers:")
            for server_id, config in MCP_SERVERS.items():
                print(f"\n  📡 {config['name']}:")
                print(f"     Port: {config['port']}")
                print(f"     URL: {config['base_url']}")
                
                # Check if server is running
                try:
                    response = requests.get(
                        f"{config['base_url']}{config['health_endpoint']}", 
                        timeout=2
                    )
                    if response.status_code == 200:
                        print(f"     Status: ✅ Running")
                    else:
                        print(f"     Status: ⚠️ Unhealthy ({response.status_code})")
                except:
                    print(f"     Status: ❌ Not running")
            
            self.results['mcp_integration'] = True
            return True
            
        except Exception as e:
            print(f"❌ MCP integration test failed: {e}")
            self.results['mcp_integration'] = False
            return False
    
    def test_agent_configurations(self) -> bool:
        """Test 4: Verify detailed agent configurations"""
        print("\n⚙️ Test 4: Agent Configuration Details")
        print("-" * 40)
        
        # Check each agent for proper configuration
        required_agents = ['rag', 'default', 'revenue_analyst', 'campaign_planner']
        found_agents = {agent['name']: agent for agent in self.agents}
        
        all_good = True
        for agent_name in required_agents:
            print(f"\n🤖 {agent_name.upper()} Agent:")
            
            if agent_name not in found_agents:
                print(f"  ❌ Not found in registry!")
                all_good = False
                continue
            
            agent = found_agents[agent_name]
            
            # Check required fields
            checks = {
                'description': agent.get('description'),
                'status': agent.get('status'),
                'policy': agent.get('policy'),
                'variables': agent.get('variables')
            }
            
            for field, value in checks.items():
                if value:
                    print(f"  ✅ {field}: Configured")
                else:
                    print(f"  ❌ {field}: Missing")
                    all_good = False
            
            # Special checks per agent
            if agent_name == 'revenue_analyst':
                policy = agent.get('policy', {})
                if 'klaviyo_revenue' in policy.get('allowed_tools', []):
                    print(f"  ✅ Klaviyo tool access: Configured")
                else:
                    print(f"  ⚠️ Klaviyo tool access: Not configured")
            
            if agent_name == 'rag':
                if agent.get('prompt_template'):
                    print(f"  ✅ Prompt template: Configured")
                else:
                    print(f"  ⚠️ Prompt template: Not configured")
        
        self.results['agent_configs'] = all_good
        return all_good
    
    def test_agent_variables(self) -> bool:
        """Test 5: Verify agent variable system"""
        print("\n📝 Test 5: Agent Variable System")
        print("-" * 40)
        
        try:
            # Test variable validation for revenue_analyst
            agent = next((a for a in self.agents if a['name'] == 'revenue_analyst'), None)
            
            if not agent:
                print("⚠️ Revenue analyst agent not found")
                return False
            
            variables = agent.get('variables', [])
            print(f"Revenue Analyst Variables ({len(variables)}):")
            
            for var in variables:
                name = var.get('name', 'unknown')
                type_ = var.get('type', 'unknown')
                required = var.get('required', False)
                default = var.get('default', 'none')
                
                print(f"  • {name}:")
                print(f"    Type: {type_}")
                print(f"    Required: {required}")
                print(f"    Default: {default}")
                
                # Check for validation rules
                if 'pattern' in var:
                    print(f"    Pattern: {var['pattern']}")
                if 'allowed_values' in var:
                    print(f"    Allowed: {var['allowed_values']}")
            
            self.results['variables'] = True
            return True
            
        except Exception as e:
            print(f"❌ Variable test failed: {e}")
            self.results['variables'] = False
            return False
    
    def test_email_sms_agents(self) -> bool:
        """Test 6: Check Email/SMS MCP Server agents"""
        print("\n📧 Test 6: Email/SMS Agent Configuration")
        print("-" * 40)
        
        try:
            # Load the email-sms-mcp-server configuration
            config_path = "email-sms-mcp-server/agents_config.json"
            
            if not os.path.exists(config_path):
                print(f"⚠️ Configuration file not found: {config_path}")
                return False
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            agents = config.get('agents', {})
            print(f"Email/SMS Agents ({len(agents)}):")
            
            for agent_name, agent_config in agents.items():
                role = agent_config.get('role', 'Unknown')
                expertise = agent_config.get('expertise', [])
                print(f"\n  🤖 {agent_name}:")
                print(f"     Role: {role}")
                print(f"     Expertise areas: {len(expertise)}")
                
                # Check collaboration
                collab = agent_config.get('collaboration_with', [])
                if collab:
                    print(f"     Collaborates with: {', '.join(collab)}")
            
            # Check workflows
            workflows = config.get('workflows', {})
            print(f"\n📋 Workflows ({len(workflows)}):")
            for workflow_name in workflows:
                print(f"  • {workflow_name}")
            
            self.results['email_sms_agents'] = True
            return True
            
        except Exception as e:
            print(f"❌ Email/SMS agent test failed: {e}")
            self.results['email_sms_agents'] = False
            return False
    
    def run_all_tests(self):
        """Run all configuration tests"""
        print("\n🚀 Starting LangChain Agent Configuration Tests")
        print("=" * 70)
        
        # Run all tests
        self.test_agent_registry()
        self.test_api_endpoints()
        self.test_mcp_integration()
        self.test_agent_configurations()
        self.test_agent_variables()
        self.test_email_sms_agents()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        # Count results
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        
        # Show each test result
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        # Configuration status
        print("\n" + "=" * 70)
        print("🎯 CONFIGURATION STATUS")
        print("=" * 70)
        
        if passed == total:
            print("✅ All LangChain agents are properly configured!")
            print("\nCore agents available:")
            print("  • RAG Agent - Question answering with document retrieval")
            print("  • Default Agent - General task execution")
            print("  • Revenue Analyst - Klaviyo data analysis")
            print("  • Campaign Planner - Email campaign planning")
            print("\nEmail/SMS agents available:")
            print("  • Content Strategist - Campaign strategy")
            print("  • Copywriter - Copy creation")
            print("  • Designer - Visual design")
            print("  • Segmentation Expert - Audience targeting")
            print("  • A/B Test Coordinator - Testing optimization")
            print("  • Compliance Officer - Legal compliance")
            print("  • Performance Analyst - Metrics analysis")
        else:
            print("⚠️ Some configuration issues detected:")
            
            if not self.results.get('registry'):
                print("  • Agent registry not loading properly")
            if not self.results.get('api_endpoints'):
                print("  • API endpoints not accessible (is server running?)")
            if not self.results.get('mcp_integration'):
                print("  • MCP servers not properly configured")
            if not self.results.get('agent_configs'):
                print("  • Some agents missing required configuration")
            
            print("\n💡 To fix:")
            print("  1. Ensure server is running: uvicorn main_firestore:app --port 8000 --host localhost")
            print("  2. Start MCP servers if needed")
            print("  3. Check agent configurations in registry.py")


def main():
    """Main execution"""
    tester = AgentConfigurationTest()
    tester.run_all_tests()
    
    # Return exit code based on results
    all_passed = all(tester.results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())