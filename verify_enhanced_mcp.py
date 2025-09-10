#!/usr/bin/env python3
"""
Simple verification that Enhanced MCP is integrated with all agents
"""

import sys
import os
import json
import httpx
import asyncio

# Add multi-agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'multi-agent'))

# Configure environment
os.environ['KLAVIYO_MCP_URL'] = 'http://localhost:8000/api/mcp/gateway'
os.environ['LC_MODEL'] = 'gemini-1.5-flash'
os.environ['LC_PROVIDER'] = 'gemini'
os.environ['USE_ENHANCED_MCP'] = 'true'

from integrations.langchain_core.adapters.enhanced_mcp_adapter import get_enhanced_mcp_adapter

def main():
    print("=" * 60)
    print("ENHANCED MCP INTEGRATION VERIFICATION")
    print("=" * 60)
    
    # Check services
    print("\n🔍 Checking Services:")
    services = {
        "Main App": "http://localhost:8000/health",
        "MCP Gateway": "http://localhost:8000/api/mcp/gateway/status",
        "Enhanced MCP": "http://localhost:9095/health"
    }
    
    for name, url in services.items():
        try:
            response = httpx.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {name}: Online")
            else:
                print(f"  ⚠️ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name}: Offline - {e}")
    
    # Get adapter
    adapter = get_enhanced_mcp_adapter()
    
    # Define all priority agents
    agents = {
        "High Priority": [
            "monthly_goals_generator_v3",
            "calendar_planner", 
            "ab_test_coordinator"
        ],
        "Medium Priority": [
            "revenue_analyst",
            "campaign_strategist",
            "audience_architect",
            "compliance_checker",
            "engagement_optimizer",
            "performance_analyst"
        ]
    }
    
    # Check each agent
    print("\n📊 Agent Enhanced MCP Status:")
    total = 0
    enhanced = 0
    
    for priority, agent_list in agents.items():
        print(f"\n  {priority}:")
        for agent_name in agent_list:
            total += 1
            try:
                tools = adapter.get_tools_for_agent(agent_name, "rogue-creamery")
                enhanced_count = len([t for t in tools if 'klaviyo_' in t.name])
                if enhanced_count > 0:
                    enhanced += 1
                    print(f"    ✅ {agent_name}: {enhanced_count} Enhanced MCP tools")
                else:
                    print(f"    ⚠️ {agent_name}: No Enhanced MCP tools")
            except Exception as e:
                print(f"    ❌ {agent_name}: Error - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 SUMMARY")
    print("=" * 60)
    print(f"✅ {enhanced}/{total} agents have Enhanced MCP integration")
    
    if enhanced == total:
        print("\n🎉 SUCCESS! All priority agents are fully integrated with Enhanced MCP")
        print("   The system is ready for production use with real Klaviyo data")
    else:
        print("\n⚠️ Some agents are missing Enhanced MCP integration")
        print("   Review the output above for details")
    
    print("\n💡 Quick Test Command:")
    print('   curl -X POST http://localhost:8000/api/mcp/gateway/invoke \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"client_id": "rogue-creamery", "tool_name": "campaigns.list", "use_enhanced": true}\'')

if __name__ == "__main__":
    main()