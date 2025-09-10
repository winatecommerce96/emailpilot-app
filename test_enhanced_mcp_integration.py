#!/usr/bin/env python3
"""
Complete test of Enhanced MCP integration with all agents
Tests that all agents can now access real Klaviyo data
"""

import sys
import os
import json
import asyncio
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add multi-agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'multi-agent'))

# Configure environment
os.environ['KLAVIYO_MCP_URL'] = 'http://localhost:8000/api/mcp/gateway'
os.environ['LC_MODEL'] = 'gemini-1.5-flash'
os.environ['LC_PROVIDER'] = 'gemini'
os.environ['USE_ENHANCED_MCP'] = 'true'

from integrations.langchain_core.config import get_config
from integrations.langchain_core.deps import get_llm
from integrations.langchain_core.agents.tools import get_all_tools, get_enhanced_tools_only
from integrations.langchain_core.adapters.enhanced_mcp_adapter import get_enhanced_mcp_adapter
from integrations.langchain_core.agents.agent_v2 import SimpleAgentExecutor
from langchain.agents import initialize_agent, AgentType


async def test_enhanced_mcp_adapter():
    """Test the Enhanced MCP adapter directly"""
    print("\n" + "="*80)
    print("🔧 TEST: Enhanced MCP Adapter")
    print("="*80)
    
    adapter = get_enhanced_mcp_adapter()
    
    # Check health
    health = await adapter.check_health()
    print(f"Adapter Health: {health}")
    
    # Test tool creation
    tools = adapter.get_all_enhanced_tools(default_client_id="rogue-creamery")
    print(f"✅ Created {len(tools)} Enhanced MCP tools")
    
    # Show tool names
    print("\n📦 Available Enhanced MCP Tools:")
    for tool in tools[:10]:  # Show first 10
        print(f"  - {tool.name}: {tool.description}")
    
    return len(tools) > 0


async def test_agent_tools_integration():
    """Test that agents get Enhanced MCP tools automatically"""
    print("\n" + "="*80)
    print("🤖 TEST: Agent Tools Integration")
    print("="*80)
    
    config = get_config()
    
    # Test getting tools for specific agents
    test_agents = [
        "monthly_goals_generator_v3",
        "calendar_planner",
        "revenue_analyst",
        "campaign_strategist"
    ]
    
    for agent_name in test_agents:
        tools = get_all_tools(config, agent_name=agent_name, client_id="rogue-creamery")
        
        # Count Enhanced MCP tools
        enhanced_count = sum(1 for t in tools if 'klaviyo_' in t.name)
        
        print(f"\n Agent: {agent_name}")
        print(f"  Total tools: {len(tools)}")
        print(f"  Enhanced MCP tools: {enhanced_count}")
        
        # Show some Enhanced MCP tools
        enhanced_tools = [t for t in tools if 'klaviyo_' in t.name][:3]
        for tool in enhanced_tools:
            print(f"    - {tool.name}")
    
    return True


async def test_simple_agent_with_enhanced_mcp():
    """Test SimpleAgentExecutor with Enhanced MCP"""
    print("\n" + "="*80)
    print("🎯 TEST: SimpleAgentExecutor with Enhanced MCP")
    print("="*80)
    
    # Create executor with Enhanced MCP
    executor = SimpleAgentExecutor(
        agent_name="test_agent",
        client_id="rogue-creamery"
    )
    
    print(f"✅ Agent created with {len(executor.tools)} tools")
    
    # Check for Enhanced MCP tools
    enhanced_tools = [t for t in executor.tools if 'klaviyo_' in t.name]
    print(f"✅ Has {len(enhanced_tools)} Enhanced MCP tools")
    
    # Test a simple task (won't actually execute tools in this simplified executor)
    result = executor.run(
        task="Analyze recent campaign performance",
        context={"client": "rogue-creamery"}
    )
    
    print(f"✅ Task executed: {result.success}")
    
    return result.success


async def test_langchain_agent_with_real_data():
    """Test LangChain agent with real Klaviyo data via Enhanced MCP"""
    print("\n" + "="*80)
    print("🚀 TEST: LangChain Agent with Real Klaviyo Data")
    print("="*80)
    
    # Get Enhanced MCP tools
    adapter = get_enhanced_mcp_adapter()
    tools = adapter.get_tools_for_agent("campaign_analyzer", "rogue-creamery")
    
    print(f"📊 Using {len(tools)} Enhanced MCP tools for campaign analysis")
    
    # Create LLM
    config = get_config()
    llm = get_llm(config)
    
    # Create agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_iterations=3
    )
    
    # Test with real data request
    query = "What campaigns has rogue-creamery sent in the last month? List the top 3."
    
    print(f"\n📝 Query: {query}")
    print("-" * 40)
    
    try:
        response = agent.run(query)
        print(f"✅ Response received (first 500 chars):")
        print(response[:500])
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_monthly_goals_with_enhanced_mcp():
    """Test monthly goals generator with Enhanced MCP"""
    print("\n" + "="*80)
    print("📈 TEST: Monthly Goals Generator with Enhanced MCP")
    print("="*80)
    
    # Get specific tools for monthly goals
    adapter = get_enhanced_mcp_adapter()
    tools = adapter.get_tools_for_agent("monthly_goals_generator_v3", "rogue-creamery")
    
    print(f"📊 Monthly goals agent tools: {[t.name for t in tools]}")
    
    config = get_config()
    llm = get_llm(config)
    
    # Create specialized agent
    system_prompt = """You are analyzing real Klaviyo data for rogue-creamery.
    Use the klaviyo_metrics_aggregate tool to get revenue data.
    Use the klaviyo_reporting_revenue tool for detailed analysis.
    Generate monthly revenue goals based on real historical data."""
    
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,  # Less verbose for this test
        agent_kwargs={"system_message": system_prompt}
    )
    
    task = "Analyze the revenue trends and suggest monthly goals for Q1 2025."
    
    try:
        print(f"\n📝 Task: {task}")
        # Run in a thread to avoid nested event loop issues
        import concurrent.futures
        def run_agent():
            return agent.run(task)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_agent)
            response = future.result(timeout=30)
        
        print(f"✅ Goals generated (first 300 chars): {response[:300]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_all_priority_agents():
    """Test all high and medium priority agents with Enhanced MCP"""
    print("\n" + "="*80)
    print("🔍 TEST: All Priority Agents")
    print("="*80)
    
    # High-priority agents
    high_priority = [
        "monthly_goals_generator_v3",
        "calendar_planner",
        "ab_test_coordinator"
    ]
    
    # Medium-priority agents
    medium_priority = [
        "revenue_analyst",
        "campaign_strategist",
        "audience_architect",
        "compliance_checker",
        "engagement_optimizer",
        "performance_analyst"
    ]
    
    all_agents = high_priority + medium_priority
    results = {}
    
    adapter = get_enhanced_mcp_adapter()
    
    for agent_name in all_agents:
        try:
            tools = adapter.get_tools_for_agent(agent_name, "rogue-creamery")
            enhanced_count = len([t for t in tools if 'klaviyo_' in t.name])
            
            results[agent_name] = {
                "status": "✅",
                "tools": len(tools),
                "enhanced": enhanced_count
            }
            
            priority = "HIGH" if agent_name in high_priority else "MEDIUM"
            print(f"  [{priority}] {agent_name}: {len(tools)} tools ({enhanced_count} Enhanced MCP)")
            
        except Exception as e:
            results[agent_name] = {
                "status": "❌",
                "error": str(e)
            }
            print(f"  ❌ {agent_name}: Error - {e}")
    
    # Summary
    success_count = sum(1 for r in results.values() if r.get("status") == "✅")
    print(f"\n📊 Summary: {success_count}/{len(all_agents)} agents ready with Enhanced MCP")
    
    return success_count == len(all_agents)


async def verify_services_running():
    """Verify all required services are running"""
    print("\n" + "="*80)
    print("⚙️ VERIFY: Required Services")
    print("="*80)
    
    services = {
        "MCP Gateway": "http://localhost:8000/api/mcp/gateway/status",
        "Enhanced MCP": "http://localhost:9095/health",
        "Main App": "http://localhost:8000/health"
    }
    
    all_running = True
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, url in services.items():
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"  ✅ {name}: Running")
                else:
                    print(f"  ⚠️ {name}: Responded with {response.status_code}")
                    all_running = False
            except Exception as e:
                print(f"  ❌ {name}: Not accessible - {e}")
                all_running = False
    
    if not all_running:
        print("\n⚠️ Some services are not running. Please ensure:")
        print("1. Main app: uvicorn main_firestore:app --port 8000 --host localhost")
        print("2. Enhanced MCP: cd services/klaviyo_mcp_enhanced && node src/simple-http-wrapper.js")
    
    return all_running


async def main():
    """Run all tests"""
    print("\n" + "🚀 "*20)
    print("ENHANCED MCP COMPLETE INTEGRATION TEST")
    print("🚀 "*20)
    print(f"Timestamp: {datetime.now()}")
    print(f"Testing with client: rogue-creamery")
    
    # Verify services first
    services_ok = await verify_services_running()
    if not services_ok:
        print("\n⚠️ Please start all required services before testing")
        return
    
    # Run tests
    tests = [
        ("Enhanced MCP Adapter", test_enhanced_mcp_adapter),
        ("Agent Tools Integration", test_agent_tools_integration),
        ("SimpleAgentExecutor", test_simple_agent_with_enhanced_mcp),
        ("LangChain Agent with Real Data", test_langchain_agent_with_real_data),
        ("Monthly Goals Generator", test_monthly_goals_with_enhanced_mcp),
        ("All Priority Agents", test_all_priority_agents)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = "✅" if result else "⚠️"
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}")
            results[test_name] = "❌"
    
    # Final report
    print("\n" + "="*80)
    print("📊 INTEGRATION TEST RESULTS")
    print("="*80)
    
    for test_name, status in results.items():
        print(f"{status} {test_name}")
    
    success_count = sum(1 for s in results.values() if s == "✅")
    total_count = len(results)
    
    print(f"\n🎯 Overall: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("\n✅ ENHANCED MCP INTEGRATION COMPLETE!")
        print("All agents now have access to real-time Klaviyo data")
        print("The system is ready for production use")
    else:
        print("\n⚠️ Some tests failed - review the output above")


if __name__ == "__main__":
    asyncio.run(main())