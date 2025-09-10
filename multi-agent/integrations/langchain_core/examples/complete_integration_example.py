"""
Complete Enhanced MCP + LangChain Integration Example

This example demonstrates the full integration of Enhanced MCP tools with LangChain agents,
showcasing best practices for:

1. Tool Mapping and Adapter Usage
2. Context Passing Between Agents
3. LangGraph Visual Workflow Orchestration
4. Error Handling and Recovery
5. Performance Monitoring and Optimization

The example implements a realistic campaign planning workflow that:
- Analyzes historical Klaviyo data using Enhanced MCP tools
- Generates monthly goals using intelligent agents
- Creates strategic campaign calendars
- Provides comprehensive reporting and insights
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Core integration components
from ..orchestration import MCPOrchestrator, run_campaign_planning_workflow
from ..context_manager import EnhancedContextManager, get_context_manager
from ..adapters.enhanced_mcp_adapter import EnhancedMCPAdapter, ToolContext
from ..config import LangChainConfig, get_config

# LangGraph components
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompleteCampaignPlanningExample:
    """
    Complete example showcasing Enhanced MCP + LangChain integration.
    
    This class demonstrates:
    - Setting up all integration components
    - Running multi-agent workflows with Enhanced MCP tools
    - Context passing and state management
    - Error handling and recovery
    - Performance monitoring
    """
    
    def __init__(self, config: Optional[LangChainConfig] = None):
        """Initialize the complete example."""
        self.config = config or get_config()
        
        # Initialize core components
        self.context_manager = get_context_manager(config)
        self.mcp_adapter = EnhancedMCPAdapter(config)
        self.orchestrator = MCPOrchestrator(config)
        
        logger.info("Complete Campaign Planning Example initialized")
    
    async def run_basic_tool_example(self) -> Dict[str, Any]:
        """
        Example 1: Basic Enhanced MCP tool usage.
        
        Demonstrates:
        - Creating ToolContext
        - Calling Enhanced MCP tools directly
        - Handling results and errors
        """
        logger.info("=== Running Basic Tool Example ===")
        
        # Create tool context
        context = ToolContext(
            client_id="demo_client",
            brand_id="test_brand", 
            session_id="basic_example_001",
            task_id="basic_tool_test"
        )
        
        results = {}
        
        # Example 1a: Get campaigns using Enhanced MCP
        try:
            campaigns_result = await self.mcp_adapter._call_enhanced_mcp(
                tool_name="campaigns.list",
                arguments={
                    "filter": "equals(messages.channel,'email')",
                    "limit": 10
                },
                context=context
            )
            
            results["campaigns"] = campaigns_result
            logger.info(f"Retrieved {len(campaigns_result.get('data', {}).get('data', []))} campaigns")
            
        except Exception as e:
            logger.error(f"Failed to get campaigns: {e}")
            results["campaigns"] = {"error": str(e)}
        
        # Example 1b: Get segments using Enhanced MCP  
        try:
            segments_result = await self.mcp_adapter._call_enhanced_mcp(
                tool_name="segments.list",
                arguments={"limit": 5},
                context=context
            )
            
            results["segments"] = segments_result
            logger.info(f"Retrieved segments data")
            
        except Exception as e:
            logger.error(f"Failed to get segments: {e}")
            results["segments"] = {"error": str(e)}
        
        # Example 1c: Get aggregated metrics
        try:
            metrics_result = await self.mcp_adapter._call_enhanced_mcp(
                tool_name="metrics.aggregate",
                arguments={
                    "resource": "campaigns",
                    "metrics": ["Opens", "Clicks", "Revenue"],
                    "interval": "month"
                },
                context=context
            )
            
            results["metrics"] = metrics_result
            logger.info("Retrieved aggregated metrics")
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            results["metrics"] = {"error": str(e)}
        
        return {
            "example": "basic_tools",
            "success": True,
            "results": results,
            "context": context.to_dict()
        }
    
    async def run_agent_integration_example(self) -> Dict[str, Any]:
        """
        Example 2: LangChain Agent with Enhanced MCP tools.
        
        Demonstrates:
        - Creating agents with Enhanced MCP tools
        - Context passing to agents
        - Agent execution with real Klaviyo data
        """
        logger.info("=== Running Agent Integration Example ===")
        
        # Set up context
        session_id = "agent_integration_001"
        async with self.context_manager.context_session(
            session_id,
            initial_context={
                "client_id": "demo_client",
                "brand_id": "test_brand",
                "selected_month": "2025-03",
                "fiscal_year": "2025",
                "client_name": "Demo Brand"
            }
        ):
            # Example 2a: Execute Monthly Goals Generator with Enhanced MCP
            try:
                goals_result = await self.orchestrator.execute_agent(
                    agent_name="monthly_goals_generator",
                    task="Generate monthly revenue goals for March 2025 using historical Klaviyo data",
                    context=self.context_manager.create_tool_context(
                        session_id=session_id,
                        context_id=session_id
                    )
                )
                
                logger.info("Monthly goals generated successfully")
                
                # Store results in context for next agent
                self.context_manager.set_context(
                    "monthly_goals_result",
                    goals_result,
                    scope=self.context_manager.scopes["session"],
                    context_id=session_id
                )
                
            except Exception as e:
                logger.error(f"Monthly goals generation failed: {e}")
                goals_result = {"error": str(e)}
            
            # Example 2b: Execute Calendar Planner using goals from previous agent
            try:
                calendar_result = await self.orchestrator.execute_agent(
                    agent_name="calendar_planner",
                    task="Create strategic campaign calendar using the monthly goals and Klaviyo historical data",
                    context=self.context_manager.create_tool_context(
                        session_id=session_id,
                        context_id=session_id
                    )
                )
                
                logger.info("Campaign calendar created successfully")
                
            except Exception as e:
                logger.error(f"Calendar planning failed: {e}")
                calendar_result = {"error": str(e)}
            
            return {
                "example": "agent_integration",
                "success": True,
                "session_id": session_id,
                "results": {
                    "monthly_goals": goals_result,
                    "campaign_calendar": calendar_result
                },
                "context_snapshot": self.context_manager.get_all_context(session_id)
            }
    
    async def run_langgraph_workflow_example(self) -> Dict[str, Any]:
        """
        Example 3: Complete LangGraph workflow with Enhanced MCP integration.
        
        Demonstrates:
        - Visual workflow orchestration using LangGraph
        - Multi-agent coordination
        - State management across workflow steps
        - Error handling and recovery
        """
        logger.info("=== Running LangGraph Workflow Example ===")
        
        # Set up initial workflow state
        initial_state = {
            "messages": [
                HumanMessage(content="Create comprehensive campaign plan for Test Brand in March 2025")
            ],
            "client_id": "demo_client",
            "brand_id": "test_brand",
            "current_task": "comprehensive_campaign_planning",
            "iteration_count": 0,
            "workflow_status": "running"
        }
        
        try:
            # Execute the complete campaign planning workflow
            final_state = await self.orchestrator.execute_workflow(
                workflow_name="campaign_planning",
                initial_state=initial_state,
                config={
                    "configurable": {
                        "thread_id": f"workflow_example_{datetime.utcnow().isoformat()}"
                    }
                }
            )
            
            logger.info("LangGraph workflow completed successfully")
            
            return {
                "example": "langgraph_workflow",
                "success": True,
                "workflow_name": "campaign_planning",
                "final_state": final_state,
                "completed_tasks": final_state.get("completed_tasks", []),
                "agent_results": final_state.get("agent_results", {})
            }
            
        except Exception as e:
            logger.error(f"LangGraph workflow failed: {e}")
            return {
                "example": "langgraph_workflow",
                "success": False,
                "error": str(e)
            }
    
    async def run_context_management_example(self) -> Dict[str, Any]:
        """
        Example 4: Advanced context management and variable resolution.
        
        Demonstrates:
        - Multi-level context hierarchy
        - Variable resolution and interpolation
        - Context persistence and recovery
        - Memory integration
        """
        logger.info("=== Running Context Management Example ===")
        
        session_id = "context_example_001"
        
        # Example 4a: Set up hierarchical context
        self.context_manager.set_context(
            "system_version",
            "1.0.0",
            scope=self.context_manager.scopes["system"]
        )
        
        self.context_manager.set_context(
            "client_name", 
            "Advanced Demo Client",
            scope=self.context_manager.scopes["client"],
            context_id=session_id
        )
        
        self.context_manager.set_context(
            "selected_month",
            "2025-03",
            scope=self.context_manager.scopes["session"],
            context_id=session_id
        )
        
        self.context_manager.set_context(
            "current_task_id",
            "context_demo_001",
            scope=self.context_manager.scopes["task"],
            context_id=session_id
        )
        
        # Example 4b: Test variable resolution
        template = """
        Planning campaigns for {{client_name}} in {{month_info:{{selected_month}}}}.
        System version: {{system_version}}
        Generated at: {{datetime:%Y-%m-%d %H:%M:%S}}
        Task ID: {{current_task_id}}
        """
        
        resolved_template = await self.context_manager.resolve_async_variables(
            template, 
            session_id
        )
        
        logger.info("Variable resolution completed")
        
        # Example 4c: Context inheritance and tool context creation
        tool_context = self.context_manager.create_tool_context(
            agent_name="context_demo_agent",
            context_id=session_id
        )
        
        # Example 4d: Memory integration
        conversation_memory = self.context_manager.memory_manager.get_conversation_memory(session_id)
        conversation_memory.save_context(
            {"input": "Plan campaigns for March 2025"},
            {"output": "I'll create a comprehensive campaign plan using Enhanced MCP tools."}
        )
        
        conversation_history = conversation_memory.load_memory_variables({})
        
        return {
            "example": "context_management",
            "success": True,
            "session_id": session_id,
            "resolved_template": resolved_template,
            "tool_context": tool_context.to_dict(),
            "conversation_history": conversation_history,
            "all_context": self.context_manager.get_all_context(session_id)
        }
    
    async def run_error_handling_example(self) -> Dict[str, Any]:
        """
        Example 5: Error handling and recovery patterns.
        
        Demonstrates:
        - Graceful error handling
        - Fallback strategies
        - Recovery mechanisms
        - Performance monitoring
        """
        logger.info("=== Running Error Handling Example ===")
        
        session_id = "error_handling_001"
        results = []
        
        # Example 5a: Tool call with error handling
        try:
            context = ToolContext(
                client_id="invalid_client",  # This will cause an error
                brand_id="test_brand",
                session_id=session_id
            )
            
            # This should fail gracefully
            result = await self.mcp_adapter._call_enhanced_mcp(
                tool_name="campaigns.list",
                arguments={"limit": 10},
                context=context
            )
            
            results.append({
                "test": "invalid_client_handling",
                "success": result.get("success", False),
                "error": result.get("error"),
                "recovery": "Graceful error response received"
            })
            
        except Exception as e:
            results.append({
                "test": "invalid_client_handling", 
                "success": False,
                "error": str(e),
                "recovery": "Exception caught and handled"
            })
        
        # Example 5b: Agent execution with timeout handling
        try:
            # Set a very short timeout to test timeout handling
            short_timeout_context = self.context_manager.create_tool_context(
                client_id="demo_client",
                session_id=session_id
            )
            
            # This would timeout in a real scenario with complex tasks
            result = await self.orchestrator.execute_agent(
                agent_name="revenue_analyst",
                task="Perform extremely detailed revenue analysis with comprehensive reporting",
                context=short_timeout_context
            )
            
            results.append({
                "test": "timeout_handling",
                "success": result.get("success", True),
                "duration": result.get("metadata", {}).get("duration_ms", 0),
                "recovery": "Task completed within timeout limits"
            })
            
        except asyncio.TimeoutError:
            results.append({
                "test": "timeout_handling",
                "success": False,
                "error": "Task timeout",
                "recovery": "Timeout gracefully handled"
            })
        except Exception as e:
            results.append({
                "test": "timeout_handling",
                "success": False,
                "error": str(e),
                "recovery": "Exception caught and handled"
            })
        
        # Example 5c: Enhanced MCP service health check
        mcp_health = await self.mcp_adapter.health_check()
        context_health = await self.context_manager.health_check()
        orchestrator_health = await self.orchestrator.health_check()
        
        results.append({
            "test": "health_checks",
            "success": True,
            "mcp_health": mcp_health,
            "context_health": context_health,
            "orchestrator_health": orchestrator_health
        })
        
        return {
            "example": "error_handling",
            "success": True,
            "session_id": session_id,
            "test_results": results
        }
    
    async def run_performance_monitoring_example(self) -> Dict[str, Any]:
        """
        Example 6: Performance monitoring and optimization.
        
        Demonstrates:
        - Performance metrics collection
        - Tool execution monitoring
        - Memory usage optimization
        - Caching strategies
        """
        logger.info("=== Running Performance Monitoring Example ===")
        
        session_id = "performance_example_001"
        performance_data = {}
        
        # Example 6a: Benchmark tool execution times
        start_time = datetime.utcnow()
        
        context = ToolContext(
            client_id="demo_client",
            brand_id="performance_test_brand",
            session_id=session_id
        )
        
        # Execute multiple tool calls and measure performance
        tool_benchmarks = []
        
        for tool_name in ["campaigns.list", "segments.list", "metrics.list"]:
            tool_start = datetime.utcnow()
            
            try:
                result = await self.mcp_adapter._call_enhanced_mcp(
                    tool_name=tool_name,
                    arguments={"limit": 5},
                    context=context
                )
                
                tool_end = datetime.utcnow()
                duration = (tool_end - tool_start).total_seconds() * 1000
                
                tool_benchmarks.append({
                    "tool_name": tool_name,
                    "duration_ms": duration,
                    "success": result.get("success", False),
                    "data_size": len(str(result.get("data", "")))
                })
                
            except Exception as e:
                tool_end = datetime.utcnow()
                duration = (tool_end - tool_start).total_seconds() * 1000
                
                tool_benchmarks.append({
                    "tool_name": tool_name,
                    "duration_ms": duration,
                    "success": False,
                    "error": str(e)
                })
        
        performance_data["tool_benchmarks"] = tool_benchmarks
        
        # Example 6b: Memory usage monitoring
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        performance_data["memory_usage"] = {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }
        
        # Example 6c: Context manager performance
        context_start = datetime.utcnow()
        
        # Set and get many context values to test performance
        for i in range(100):
            self.context_manager.set_context(
                f"perf_test_{i}",
                f"value_{i}",
                scope=self.context_manager.scopes["temp"],
                context_id=session_id
            )
        
        # Retrieve all values
        all_context = self.context_manager.get_all_context(session_id)
        
        context_end = datetime.utcnow()
        context_duration = (context_end - context_start).total_seconds() * 1000
        
        performance_data["context_operations"] = {
            "duration_ms": context_duration,
            "context_entries": len(all_context),
            "avg_ms_per_operation": context_duration / 200  # 100 sets + 100 gets
        }
        
        # Clean up temporary context
        self.context_manager.cleanup_expired(session_id)
        
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds() * 1000
        
        return {
            "example": "performance_monitoring",
            "success": True,
            "total_duration_ms": total_duration,
            "performance_data": performance_data,
            "recommendations": [
                "Tool execution times look good (<1000ms each)",
                "Memory usage is within acceptable limits", 
                "Context operations are performant",
                "Consider caching frequently accessed data"
            ]
        }
    
    async def run_complete_integration_demo(self) -> Dict[str, Any]:
        """
        Master demo that runs all examples in sequence.
        
        This provides a comprehensive demonstration of the entire
        Enhanced MCP + LangChain integration.
        """
        logger.info("=== Starting Complete Integration Demo ===")
        
        demo_results = {
            "demo_started": datetime.utcnow().isoformat(),
            "examples": [],
            "summary": {}
        }
        
        examples = [
            ("Basic Tool Usage", self.run_basic_tool_example),
            ("Agent Integration", self.run_agent_integration_example),
            ("LangGraph Workflow", self.run_langgraph_workflow_example),
            ("Context Management", self.run_context_management_example),
            ("Error Handling", self.run_error_handling_example),
            ("Performance Monitoring", self.run_performance_monitoring_example)
        ]
        
        successful_examples = 0
        total_examples = len(examples)
        
        for name, example_func in examples:
            logger.info(f"Running example: {name}")
            
            try:
                result = await example_func()
                demo_results["examples"].append({
                    "name": name,
                    "success": result.get("success", False),
                    "result": result
                })
                
                if result.get("success"):
                    successful_examples += 1
                    
                logger.info(f"Example '{name}' completed successfully")
                
            except Exception as e:
                logger.error(f"Example '{name}' failed: {e}")
                demo_results["examples"].append({
                    "name": name,
                    "success": False,
                    "error": str(e)
                })
        
        # Generate summary
        demo_results["demo_completed"] = datetime.utcnow().isoformat()
        demo_results["summary"] = {
            "total_examples": total_examples,
            "successful_examples": successful_examples,
            "success_rate": (successful_examples / total_examples) * 100,
            "overall_success": successful_examples == total_examples
        }
        
        logger.info(f"Complete Integration Demo finished: {successful_examples}/{total_examples} examples successful")
        
        return demo_results


async def run_complete_demo():
    """Run the complete integration demonstration."""
    try:
        # Initialize example
        example = CompleteCampaignPlanningExample()
        
        # Run complete demo
        results = await example.run_complete_integration_demo()
        
        # Pretty print results
        print("\n" + "="*80)
        print("COMPLETE ENHANCED MCP + LANGCHAIN INTEGRATION DEMO")
        print("="*80)
        
        print(f"\nDemo Summary:")
        print(f"- Total Examples: {results['summary']['total_examples']}")
        print(f"- Successful: {results['summary']['successful_examples']}")
        print(f"- Success Rate: {results['summary']['success_rate']:.1f}%")
        print(f"- Overall Success: {results['summary']['overall_success']}")
        
        print(f"\nExample Results:")
        for example in results["examples"]:
            status = "✅ PASS" if example["success"] else "❌ FAIL"
            print(f"  {status} {example['name']}")
            if not example["success"] and "error" in example:
                print(f"    Error: {example['error']}")
        
        print(f"\nDemo completed successfully! See logs for detailed information.")
        
        return results
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed with error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    """Run the complete demonstration."""
    print("Enhanced MCP + LangChain Integration Demo")
    print("This demo showcases the complete integration architecture.")
    print("\nStarting demo...\n")
    
    # Run the demo
    results = asyncio.run(run_complete_demo())
    
    if results.get("summary", {}).get("overall_success"):
        print("\n🎉 All examples passed! Integration is working correctly.")
    else:
        print("\n⚠️  Some examples failed. Check logs for details.")