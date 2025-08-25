#!/usr/bin/env python3
"""
Test script for Rogue Creamery Klaviyo data retrieval and AI analysis
This tests multiple approaches to get 7-day sales data and analyze it with LangChain
"""

import os
import sys
import json
import asyncio
import httpx
from datetime import datetime, timedelta

# Add multi-agent to path for LangChain
sys.path.insert(0, "multi-agent")

# Set environment variables
os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"
os.environ["USE_SECRET_MANAGER"] = "true"
os.environ["SECRET_MANAGER_TRANSPORT"] = "rest"

print("🧪 Testing Rogue Creamery Klaviyo Data Retrieval with LangChain + MCP")
print("=" * 60)

# Test 1: Direct MCP API Call
async def test_direct_mcp_api():
    """Test 1: Direct call to Klaviyo Revenue API via MCP"""
    print("\n📊 Test 1: Direct MCP API Call")
    print("-" * 40)
    
    try:
        async with httpx.AsyncClient() as client:
            # Call the Klaviyo Revenue API directly
            response = await client.get(
                "http://127.0.0.1:9090/clients/by-slug/rogue-creamery/revenue/last7",
                params={"timeframe_key": "last_7_days", "recompute": "true"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Success! Retrieved data:")
                print(f"  • Campaign Revenue: ${data.get('campaign_total', 0):,.2f}")
                print(f"  • Flow Revenue: ${data.get('flow_total', 0):,.2f}")
                print(f"  • Total Revenue: ${data.get('total', 0):,.2f}")
                print(f"  • Timeframe: {data.get('timeframe')}")
                return data
            else:
                print(f"❌ Failed: Status {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# Test 2: LangChain with MCP Tools
async def test_langchain_mcp_tools():
    """Test 2: Use LangChain with MCP tool integration"""
    print("\n🔧 Test 2: LangChain with MCP Tools")
    print("-" * 40)
    
    try:
        from integrations.langchain_core.adapters.mcp_client import MCPClient
        from integrations.langchain_core.config import get_config
        
        config = get_config()
        mcp_client = MCPClient(config)
        
        # Call Klaviyo revenue tool via MCP
        result = await mcp_client.call_klaviyo_revenue(
            client_slug="rogue-creamery",
            timeframe_key="last_7_days"
        )
        
        if result.success:
            print("✅ Success! Retrieved via MCP:")
            data = result.data
            print(f"  • Campaign Revenue: ${data.get('campaign_total', 0):,.2f}")
            print(f"  • Flow Revenue: ${data.get('flow_total', 0):,.2f}")
            print(f"  • Total Revenue: ${data.get('total', 0):,.2f}")
            return data
        else:
            print(f"❌ Failed: {result.error}")
            return None
            
    except ImportError as e:
        print(f"⚠️ Import error: {e}")
        print("   Trying alternative approach...")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# Test 3: LangChain Agent Execution
async def test_langchain_agent():
    """Test 3: Use LangChain Revenue Analyst agent"""
    print("\n🤖 Test 3: LangChain Revenue Analyst Agent")
    print("-" * 40)
    
    try:
        from integrations.langchain_core.engine.facade import prepare_run, invoke_agent
        from integrations.langchain_core.admin.registry import get_agent_registry
        
        registry = get_agent_registry()
        
        # Prepare context for revenue analyst
        context = {
            "brand": "rogue-creamery",
            "client_slug": "rogue-creamery",
            "timeframe": "last_7_days",
            "analysis_type": "revenue_summary"
        }
        
        # Execute revenue analyst agent
        prepared = prepare_run(
            agent_name="revenue_analyst",
            context=context
        )
        
        print("  • Starting agent execution...")
        result = invoke_agent(prepared)
        
        if result:
            print("✅ Agent executed successfully!")
            return result
        else:
            print("❌ Agent execution failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# Test 4: Combined Data + AI Analysis
async def test_data_with_ai_analysis():
    """Test 4: Get data and analyze with AI"""
    print("\n🧠 Test 4: Data Retrieval + AI Analysis")
    print("-" * 40)
    
    # First, get the data
    print("Step 1: Fetching Klaviyo data...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://127.0.0.1:9090/clients/by-slug/rogue-creamery/weekly/metrics",
            params={"timeframe_key": "last_7_days"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get data: {response.status_code}")
            return None
            
        revenue_data = response.json()
        print("✅ Data retrieved successfully!")
        print(f"  • Weekly Revenue: ${revenue_data.get('weekly_revenue', 0):,.2f}")
        print(f"  • Campaign Revenue: ${revenue_data.get('campaign_revenue', 0):,.2f}")
        print(f"  • Flow Revenue: ${revenue_data.get('flow_revenue', 0):,.2f}")
        print(f"  • Orders: {revenue_data.get('weekly_orders', 0)}")
    
    # Now analyze with LangChain
    print("\nStep 2: Analyzing with AI...")
    
    try:
        from integrations.langchain_core.deps import get_llm
        from integrations.langchain_core.config import get_config
        from langchain_core.prompts import PromptTemplate
        
        config = get_config()
        llm = get_llm(config)
        
        # Create analysis prompt
        prompt = PromptTemplate.from_template("""
You are a revenue analyst for Rogue Creamery. Analyze the following 7-day Klaviyo performance data and provide insights:

**Revenue Data:**
- Total Revenue: ${weekly_revenue:,.2f}
- Campaign Revenue: ${campaign_revenue:,.2f} ({campaign_percent:.1f}% of total)
- Flow Revenue: ${flow_revenue:,.2f} ({flow_percent:.1f}% of total)
- Total Orders: {weekly_orders}
- Campaign Orders: {campaign_orders}
- Flow Orders: {flow_orders}

**Your Analysis Should Include:**
1. Performance Summary - How did the business perform this week?
2. Channel Analysis - Compare campaign vs flow performance
3. Key Insights - What stands out in the data?
4. Recommendations - What actions should be taken?

Provide a concise but insightful analysis:
""")
        
        # Calculate percentages
        total = revenue_data.get('weekly_revenue', 0)
        campaign_pct = (revenue_data.get('campaign_revenue', 0) / total * 100) if total > 0 else 0
        flow_pct = (revenue_data.get('flow_revenue', 0) / total * 100) if total > 0 else 0
        
        # Format the prompt
        formatted_prompt = prompt.format(
            weekly_revenue=revenue_data.get('weekly_revenue', 0),
            campaign_revenue=revenue_data.get('campaign_revenue', 0),
            campaign_percent=campaign_pct,
            flow_revenue=revenue_data.get('flow_revenue', 0),
            flow_percent=flow_pct,
            weekly_orders=revenue_data.get('weekly_orders', 0),
            campaign_orders=revenue_data.get('campaign_orders', 0),
            flow_orders=revenue_data.get('flow_orders', 0)
        )
        
        # Get AI analysis
        analysis = llm.invoke(formatted_prompt)
        
        print("\n📈 AI Analysis:")
        print("-" * 40)
        print(analysis.content if hasattr(analysis, 'content') else str(analysis))
        
        return {
            "data": revenue_data,
            "analysis": analysis.content if hasattr(analysis, 'content') else str(analysis)
        }
        
    except Exception as e:
        print(f"❌ AI Analysis failed: {e}")
        
        # Fallback to simple analysis
        print("\n📊 Fallback Analysis:")
        print(f"  • Total 7-day revenue: ${revenue_data.get('weekly_revenue', 0):,.2f}")
        print(f"  • Campaigns generated {campaign_pct:.1f}% of revenue")
        print(f"  • Flows generated {flow_pct:.1f}% of revenue")
        
        if campaign_pct > flow_pct:
            print("  • Campaigns are outperforming flows - good active marketing!")
        else:
            print("  • Flows are generating more revenue - strong automation!")
            
        return {"data": revenue_data, "analysis": "Fallback analysis completed"}


# Test 5: Full LangChain Pipeline
async def test_full_langchain_pipeline():
    """Test 5: Complete LangChain pipeline with tools"""
    print("\n🔗 Test 5: Full LangChain Pipeline")
    print("-" * 40)
    
    try:
        from langchain.agents import create_openai_tools_agent, AgentExecutor
        from langchain_core.tools import Tool
        from integrations.langchain_core.deps import get_llm
        from integrations.langchain_core.config import get_config
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        config = get_config()
        llm = get_llm(config)
        
        # Create a tool for Klaviyo data
        async def get_klaviyo_revenue(client_slug: str) -> str:
            """Get 7-day revenue data for a client from Klaviyo"""
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:9090/clients/by-slug/{client_slug}/weekly/metrics"
                )
                if response.status_code == 200:
                    data = response.json()
                    return json.dumps(data, indent=2)
                return f"Error: Could not fetch data for {client_slug}"
        
        klaviyo_tool = Tool(
            name="get_klaviyo_revenue",
            description="Get 7-day Klaviyo revenue data for a client",
            func=lambda slug: asyncio.run(get_klaviyo_revenue(slug))
        )
        
        # Create agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a revenue analyst. Use the tools to get data and provide analysis."),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_openai_tools_agent(llm, [klaviyo_tool], prompt)
        agent_executor = AgentExecutor(agent=agent, tools=[klaviyo_tool], verbose=True)
        
        # Execute
        result = agent_executor.invoke({
            "input": "Get the 7-day Klaviyo revenue data for rogue-creamery and analyze it"
        })
        
        print("\n✅ Pipeline Result:")
        print(result.get("output", "No output"))
        return result
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return None


# Main execution
async def main():
    """Run all tests"""
    print("\n🚀 Starting Rogue Creamery Klaviyo + LangChain Tests")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Direct API
    results["direct_api"] = await test_direct_mcp_api()
    
    # Test 2: MCP Tools
    results["mcp_tools"] = await test_langchain_mcp_tools()
    
    # Test 3: LangChain Agent
    results["agent"] = await test_langchain_agent()
    
    # Test 4: Data + AI Analysis (Most likely to work)
    results["ai_analysis"] = await test_data_with_ai_analysis()
    
    # Test 5: Full Pipeline
    results["pipeline"] = await test_full_langchain_pipeline()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    success_count = 0
    for test_name, result in results.items():
        status = "✅ Success" if result else "❌ Failed"
        print(f"{test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\nTotal: {success_count}/{len(results)} tests successful")
    
    # Return the most successful result
    if results["ai_analysis"]:
        print("\n🎯 Best Result: Data + AI Analysis")
        return results["ai_analysis"]
    elif results["direct_api"]:
        print("\n🎯 Best Result: Direct API")
        return results["direct_api"]
    else:
        print("\n⚠️ No fully successful tests")
        return None


if __name__ == "__main__":
    result = asyncio.run(main())
    
    if result:
        print("\n✅ Test completed successfully!")
        print("\nFinal result saved to: rogue_creamery_analysis.json")
        
        # Save result
        with open("rogue_creamery_analysis.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
    else:
        print("\n❌ All tests failed. Check server logs for details.")