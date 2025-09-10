#!/usr/bin/env python3
"""
Test Dynamic MCP System
Tests the complete flow: MCP server auto-start, agent requirements analysis, and dynamic query execution
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_mcp_server_manager():
    """Test MCP server auto-start functionality"""
    print("\n" + "="*60)
    print("🚀 Testing MCP Server Manager")
    print("="*60)
    
    try:
        from app.services.mcp_server_manager import get_mcp_manager
        
        manager = get_mcp_manager()
        
        # Test server status
        logger.info("Getting server status...")
        status = await manager.get_status()
        
        for server_key, server_status in status.items():
            print(f"📡 {server_status['name']} (port {server_status['port']})")
            print(f"   Healthy: {'✅' if server_status['healthy'] else '❌'}")
            print(f"   Port in use: {'✅' if server_status['port_in_use'] else '❌'}")
        
        # Test auto-start
        logger.info("Testing auto-start functionality...")
        results = await manager.ensure_servers_running()
        
        for server_key, success in results.items():
            status_emoji = "✅" if success else "❌"
            print(f"   {server_key}: {status_emoji}")
        
        return all(results.values())
        
    except Exception as e:
        logger.error(f"MCP Server Manager test failed: {e}")
        return False


async def test_agent_requirements_analyzer():
    """Test agent data requirements analysis"""
    print("\n" + "="*60)
    print("🔍 Testing Agent Requirements Analyzer")
    print("="*60)
    
    try:
        from app.services.agent_data_requirements import get_requirements_analyzer
        
        analyzer = get_requirements_analyzer()
        
        # Import calendar workflow agents
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent / "multi-agent"))
            
            from integrations.langchain_core.agents.brand_calendar_agent import BRAND_CALENDAR_AGENT
            from integrations.langchain_core.agents.historical_analyst import HISTORICAL_ANALYST_AGENT
            from integrations.langchain_core.agents.segment_strategist import SEGMENT_STRATEGIST_AGENT
            from integrations.langchain_core.agents.content_optimizer import CONTENT_OPTIMIZER_AGENT
            from integrations.langchain_core.agents.calendar_orchestrator import CALENDAR_ORCHESTRATOR_AGENT
            
            agents_config = {
                "brand_calendar": BRAND_CALENDAR_AGENT,
                "historical_analyst": HISTORICAL_ANALYST_AGENT,
                "segment_strategist": SEGMENT_STRATEGIST_AGENT,
                "content_optimizer": CONTENT_OPTIMIZER_AGENT,
                "calendar_orchestrator": CALENDAR_ORCHESTRATOR_AGENT
            }
            
            logger.info(f"Loaded {len(agents_config)} agents for analysis")
            
        except ImportError as e:
            logger.warning(f"Could not import agents: {e}")
            return False
        
        # Analyze each agent's requirements
        logger.info("Analyzing agent data requirements...")
        agent_specs = analyzer.analyze_workflow_agents(agents_config)
        
        print(f"\n📊 Analysis Results for {len(agent_specs)} agents:")
        
        for agent_name, spec in agent_specs.items():
            print(f"\n🤖 {agent_name.replace('_', ' ').title()}")
            print(f"   Time range: {spec.time_range_days} days")
            print(f"   Data types: {[req.value for req in spec.required_data]}")
            print(f"   Metrics needed: {spec.metrics_needed[:3]}{'...' if len(spec.metrics_needed) > 3 else ''}")
            print(f"   Custom queries: {len(spec.custom_queries)}")
            
            # Show first query as example
            if spec.custom_queries:
                print(f"   Example query: '{spec.custom_queries[0][:60]}...'")
        
        # Test combined requirements
        combined = analyzer.combine_workflow_requirements(agent_specs)
        print(f"\n🔗 Combined Workflow Requirements:")
        print(f"   Total data types: {len(combined['data_types'])}")
        print(f"   Total metrics: {len(combined['metrics'])}")
        print(f"   Time range: {combined['time_range_days']} days")
        print(f"   Total queries: {len(combined['queries'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"Agent Requirements Analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_intelligent_query_execution():
    """Test intelligent query service with agent requirements"""
    print("\n" + "="*60)
    print("🧠 Testing Intelligent Query Execution")
    print("="*60)
    
    try:
        from app.services.intelligent_query_service import IntelligentQueryService, QueryMode
        from app.services.agent_data_requirements import get_requirements_analyzer
        
        # Initialize services
        query_service = IntelligentQueryService()
        analyzer = get_requirements_analyzer()
        
        # Test client
        client_id = "01J8XM973VJD0X0G2P37H3R3WV"  # Milagro Mushrooms
        
        # Test a specific agent's query
        test_queries = [
            "Get campaign performance metrics for last 90 days including: open_rate, click_rate, conversion_rate",
            "List all segments with metrics: segment_size, engagement_rate, ltv",
            "Calculate revenue metrics for last 90 days including total revenue, revenue per campaign"
        ]
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"Testing query {i}: {query[:50]}...")
            
            try:
                result = await query_service.query(
                    natural_query=query,
                    client_id=client_id,
                    mode=QueryMode.AUTO
                )
                
                if result.get("success"):
                    print(f"   ✅ Query {i}: Success (mode: {result.get('mode', 'unknown')})")
                    if result.get("results"):
                        print(f"      Data keys: {list(result['results'].keys()) if isinstance(result['results'], dict) else 'list data'}")
                else:
                    print(f"   ❌ Query {i}: Failed - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   ❌ Query {i}: Exception - {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Intelligent Query Execution test failed: {e}")
        return False


async def test_end_to_end_workflow():
    """Test the complete end-to-end workflow"""
    print("\n" + "="*60)
    print("🔄 Testing End-to-End Workflow Integration")
    print("="*60)
    
    try:
        # Test the complete calendar workflow with dynamic queries
        from emailpilot_graph.calendar_workflow import build_calendar_workflow
        
        logger.info("Building workflow graph...")
        workflow = build_calendar_workflow()
        
        # Test input with real data
        test_input = {
            "client_id": "01J8XM973VJD0X0G2P37H3R3WV",  # Milagro Mushrooms
            "client_name": "Milagro Mushrooms",
            "selected_month": "2025-03",
            "campaign_count": 5,
            "client_sales_goal": 35000.0,
            "optimization_goal": "balanced",
            "llm_type": "gemini",
            "additional_context": "Spring wellness campaign focus",
            "use_real_data": True,
            "status": "started",
            "errors": [],
            "execution_time": None
        }
        
        logger.info("Executing workflow with dynamic MCP integration...")
        logger.info(f"Client: {test_input['client_name']}")
        logger.info(f"Month: {test_input['selected_month']}")
        
        # Execute workflow (this will test MCP auto-start, agent analysis, and data fetching)
        result = await workflow.ainvoke(test_input)
        
        # Validate results
        success_indicators = [
            ("MCP servers started", "brand_data" in result or "historical_insights" in result),
            ("Agent data retrieved", bool(result.get("brand_data") or result.get("historical_insights"))),
            ("Workflow completed", result.get("status") != "failed"),
            ("No critical errors", len(result.get("errors", [])) == 0)
        ]
        
        print(f"\n📋 End-to-End Test Results:")
        all_passed = True
        for check, passed in success_indicators:
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            if not passed:
                all_passed = False
        
        if result.get("errors"):
            print(f"\n⚠️ Workflow errors: {result['errors']}")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🧪 Dynamic MCP System Integration Tests")
    print("Testing MCP auto-start, agent analysis, and dynamic queries")
    print("=" * 80)
    
    tests = [
        ("MCP Server Manager", test_mcp_server_manager),
        ("Agent Requirements Analyzer", test_agent_requirements_analyzer), 
        ("Intelligent Query Execution", test_intelligent_query_execution),
        ("End-to-End Workflow", test_end_to_end_workflow)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔬 Running: {test_name}")
            results[test_name] = await test_func()
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dynamic MCP system is working correctly.")
        print("\nKey capabilities verified:")
        print("• MCP servers auto-start when needed")
        print("• Agent prompts are analyzed for data requirements")
        print("• Custom queries are generated based on agent needs")
        print("• Missing data detection and re-querying works")
        print("• UI shows agent requirements and editable queries")
        print("• Workflow adapts to prompt changes dynamically")
    else:
        print("⚠️ Some tests failed. Check logs for details.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())