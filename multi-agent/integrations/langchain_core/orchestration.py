"""
Enhanced MCP + LangChain + LangGraph Orchestration Architecture

This module provides a comprehensive orchestration system that combines:
- Enhanced MCP for real-time Klaviyo data access
- LangChain agents for individual specialized tasks
- LangGraph workflows for visual multi-agent orchestration
- Firestore for persistent context and checkpoints

Architecture Features:
- Visual workflow design using LangGraph Studio
- Context passing between agents using LangChain memory
- Persistent state management with Firestore checkpoints
- Enhanced MCP tool integration for all agents
- Async execution with proper error handling
- Comprehensive logging and observability
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Literal
from datetime import datetime
from dataclasses import dataclass
from functools import wraps

# LangGraph imports
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint import BaseCheckpointer

# LangChain imports  
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage
from langchain_core.callbacks import CallbackManager, BaseCallbackHandler
from langchain_core.memory import ConversationBufferMemory

# Project imports
from .config import LangChainConfig, get_config
from .adapters.enhanced_mcp_adapter import (
    EnhancedMCPAdapter, 
    ToolContext, 
    get_enhanced_mcp_tools
)
from .agents.agent_v2 import SimpleAgentExecutor
from ..deps import get_firestore_client

logger = logging.getLogger(__name__)


# State Definitions
class OrchestrationState(MessagesState):
    """
    State for multi-agent orchestration workflows.
    
    Extends LangGraph MessagesState with orchestration-specific fields.
    """
    # Context
    client_id: Optional[str] = None
    brand_id: Optional[str] = None  
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Task management
    current_task: Optional[str] = None
    task_queue: List[str] = []
    completed_tasks: List[str] = []
    
    # Agent coordination
    active_agent: Optional[str] = None
    agent_results: Dict[str, Any] = {}
    
    # Data and insights
    klaviyo_data: Dict[str, Any] = {}
    analysis_results: Dict[str, Any] = {}
    recommendations: List[str] = []
    
    # Workflow control
    iteration_count: int = 0
    max_iterations: int = 20
    workflow_status: Literal["running", "completed", "failed", "paused"] = "running"


@dataclass 
class AgentSpec:
    """Specification for an agent in the orchestration."""
    name: str
    description: str
    required_tools: List[str]
    max_iterations: int = 5
    timeout_seconds: int = 60


class FirestoreCheckpointer(BaseCheckpointer):
    """
    LangGraph checkpointer using Firestore for persistence.
    
    Enables workflow state to persist across restarts and provides
    visual workflow debugging through LangSmith.
    """
    
    def __init__(self, collection_name: str = "langgraph_checkpoints"):
        self.collection_name = collection_name
        self.firestore = get_firestore_client()
    
    def put(self, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> None:
        """Save checkpoint to Firestore."""
        if not self.firestore:
            logger.warning("Firestore not available, checkpoint not saved")
            return
        
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, checkpoint not saved")
            return
        
        try:
            doc_ref = self.firestore.collection(self.collection_name).document(thread_id)
            doc_ref.set({
                "checkpoint": checkpoint,
                "config": config,
                "timestamp": datetime.utcnow(),
                "version": checkpoint.get("version", 1)
            })
            logger.debug(f"Saved checkpoint for thread {thread_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def get(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Load checkpoint from Firestore."""
        if not self.firestore:
            return None
        
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None
        
        try:
            doc_ref = self.firestore.collection(self.collection_name).document(thread_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                logger.debug(f"Loaded checkpoint for thread {thread_id}")
                return data.get("checkpoint")
            
            return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None


class ContextCallbackHandler(BaseCallbackHandler):
    """
    Callback handler that maintains context across agent calls.
    
    Tracks tool usage, performance metrics, and cross-agent data flow.
    """
    
    def __init__(self, context: ToolContext):
        self.context = context
        self.tool_calls: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Track tool execution start."""
        tool_name = serialized.get("name", "unknown")
        call_data = {
            "tool_name": tool_name,
            "input": input_str,
            "start_time": datetime.utcnow().isoformat(),
            "context": self.context.to_dict()
        }
        self.tool_calls.append(call_data)
        logger.debug(f"Tool started: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Track tool execution completion."""
        if self.tool_calls:
            call_data = self.tool_calls[-1]
            call_data["output"] = output[:500]  # Truncate long outputs
            call_data["end_time"] = datetime.utcnow().isoformat()
            
            # Calculate duration
            start = datetime.fromisoformat(call_data["start_time"])
            end = datetime.utcnow()
            duration_ms = int((end - start).total_seconds() * 1000)
            call_data["duration_ms"] = duration_ms
            
            logger.debug(f"Tool completed: {call_data['tool_name']} ({duration_ms}ms)")
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Track tool execution errors."""
        if self.tool_calls:
            call_data = self.tool_calls[-1]
            call_data["error"] = str(error)
            call_data["end_time"] = datetime.utcnow().isoformat()
            
            logger.error(f"Tool error: {call_data.get('tool_name')} - {error}")


class MCPOrchestrator:
    """
    Main orchestrator class combining Enhanced MCP, LangChain, and LangGraph.
    
    This class provides:
    - Multi-agent workflow orchestration using LangGraph
    - Enhanced MCP tool integration for all agents
    - Context passing and memory management
    - Persistent state with Firestore checkpoints
    - Visual workflow design and debugging
    """
    
    def __init__(self, config: Optional[LangChainConfig] = None):
        """
        Initialize the orchestrator.
        
        Args:
            config: LangChain configuration
        """
        self.config = config or get_config()
        
        # Initialize components
        self.mcp_adapter = EnhancedMCPAdapter(config)
        self.enhanced_tools = get_enhanced_mcp_tools(config)
        self.checkpointer = FirestoreCheckpointer()
        
        # Agent registry
        self.agents: Dict[str, AgentSpec] = {}
        
        # Register core agents
        self._register_core_agents()
        
        logger.info(f"MCP Orchestrator initialized with {len(self.enhanced_tools)} Enhanced MCP tools")
    
    def _register_core_agents(self):
        """Register core agents that benefit from Enhanced MCP integration."""
        
        # Monthly Goals Generator
        self.agents["monthly_goals_generator"] = AgentSpec(
            name="monthly_goals_generator",
            description="Generate monthly revenue goals with seasonality analysis",
            required_tools=[
                "klaviyo_metrics_aggregate",
                "klaviyo_campaigns", 
                "klaviyo_segments",
                "firestore_ro_get"
            ],
            max_iterations=8,
            timeout_seconds=120
        )
        
        # Calendar Planner
        self.agents["calendar_planner"] = AgentSpec(
            name="calendar_planner", 
            description="Create strategic email campaign calendars",
            required_tools=[
                "klaviyo_campaigns",
                "klaviyo_segments",
                "klaviyo_flows",
                "klaviyo_metrics_aggregate"
            ],
            max_iterations=10,
            timeout_seconds=150
        )
        
        # A/B Test Coordinator
        self.agents["ab_test_coordinator"] = AgentSpec(
            name="ab_test_coordinator",
            description="Coordinate and analyze A/B testing campaigns", 
            required_tools=[
                "klaviyo_campaigns",
                "klaviyo_metrics_aggregate",
                "klaviyo_segments",
                "klaviyo_profiles"
            ],
            max_iterations=6,
            timeout_seconds=90
        )
        
        # Revenue Analyst
        self.agents["revenue_analyst"] = AgentSpec(
            name="revenue_analyst",
            description="Analyze revenue performance and attribution",
            required_tools=[
                "klaviyo_metrics_aggregate",
                "klaviyo_campaigns",
                "klaviyo_flows",
                "firestore_ro_get"
            ],
            max_iterations=5,
            timeout_seconds=90
        )
    
    def create_tool_context(self, state: OrchestrationState) -> ToolContext:
        """Create tool context from orchestration state."""
        return ToolContext(
            client_id=state.get("client_id"),
            brand_id=state.get("brand_id"),
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            agent_name=state.get("active_agent"),
            task_id=state.get("current_task"),
            metadata={
                "iteration_count": state.get("iteration_count", 0),
                "workflow_status": state.get("workflow_status", "running")
            }
        )
    
    async def execute_agent(
        self,
        agent_name: str,
        task: str,
        context: ToolContext
    ) -> Dict[str, Any]:
        """
        Execute a specific agent with Enhanced MCP tools.
        
        Args:
            agent_name: Name of agent to execute
            task: Task description
            context: Tool execution context
            
        Returns:
            Agent execution result
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not registered")
        
        agent_spec = self.agents[agent_name]
        
        # Create callback handler for context tracking
        callback_handler = ContextCallbackHandler(context)
        callback_manager = CallbackManager([callback_handler])
        
        # Create agent executor with Enhanced MCP tools
        executor = SimpleAgentExecutor(
            tools=self.enhanced_tools,
            config=self.config
        )
        
        try:
            # Execute the agent
            logger.info(f"Executing agent {agent_name} with task: {task[:100]}")
            
            result = executor.run(
                task=task,
                context=context.to_dict()
            )
            
            # Add performance metrics from callback
            result["tool_calls"] = callback_handler.tool_calls
            result["performance_metrics"] = callback_handler.performance_metrics
            
            logger.info(f"Agent {agent_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Agent {agent_name} execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_name": agent_name,
                "task": task
            }
    
    def create_workflow_graph(self, workflow_name: str) -> StateGraph:
        """
        Create a LangGraph workflow with Enhanced MCP integration.
        
        Args:
            workflow_name: Name of the workflow to create
            
        Returns:
            Compiled StateGraph
        """
        
        if workflow_name == "campaign_planning":
            return self._create_campaign_planning_workflow()
        elif workflow_name == "revenue_analysis":
            return self._create_revenue_analysis_workflow()
        elif workflow_name == "comprehensive_audit":
            return self._create_comprehensive_audit_workflow()
        else:
            raise ValueError(f"Unknown workflow: {workflow_name}")
    
    def _create_campaign_planning_workflow(self) -> StateGraph:
        """Create campaign planning workflow."""
        
        workflow = StateGraph(OrchestrationState)
        
        # Define workflow nodes
        async def analyze_historical_data(state: OrchestrationState):
            """Analyze historical campaign data."""
            context = self.create_tool_context(state)
            
            result = await self.execute_agent(
                "revenue_analyst",
                "Analyze historical campaign performance and revenue attribution for the past 3 months",
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "historical_analysis": result},
                "klaviyo_data": {**state.get("klaviyo_data", {}), "historical": result.get("data")},
                "active_agent": "revenue_analyst",
                "completed_tasks": state.get("completed_tasks", []) + ["historical_analysis"]
            }
        
        async def generate_monthly_goals(state: OrchestrationState):
            """Generate monthly revenue goals."""
            context = self.create_tool_context(state)
            
            # Use historical analysis results as context
            historical_data = state.get("agent_results", {}).get("historical_analysis", {})
            task = f"Generate monthly revenue goals using historical data: {json.dumps(historical_data.get('data', {}), indent=2)}"
            
            result = await self.execute_agent(
                "monthly_goals_generator",
                task,
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "monthly_goals": result},
                "active_agent": "monthly_goals_generator", 
                "completed_tasks": state.get("completed_tasks", []) + ["monthly_goals"]
            }
        
        async def create_campaign_calendar(state: OrchestrationState):
            """Create strategic campaign calendar."""
            context = self.create_tool_context(state)
            
            # Combine goals and historical data
            goals_data = state.get("agent_results", {}).get("monthly_goals", {})
            historical_data = state.get("agent_results", {}).get("historical_analysis", {})
            
            task = f"""Create campaign calendar using:
            Monthly Goals: {json.dumps(goals_data.get('data', {}), indent=2)}
            Historical Performance: {json.dumps(historical_data.get('data', {}), indent=2)}
            """
            
            result = await self.execute_agent(
                "calendar_planner",
                task,
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "campaign_calendar": result},
                "active_agent": "calendar_planner",
                "completed_tasks": state.get("completed_tasks", []) + ["campaign_calendar"],
                "workflow_status": "completed"
            }
        
        # Add nodes
        workflow.add_node("analyze_historical_data", analyze_historical_data)
        workflow.add_node("generate_monthly_goals", generate_monthly_goals) 
        workflow.add_node("create_campaign_calendar", create_campaign_calendar)
        
        # Define workflow flow
        workflow.set_entry_point("analyze_historical_data")
        workflow.add_edge("analyze_historical_data", "generate_monthly_goals")
        workflow.add_edge("generate_monthly_goals", "create_campaign_calendar")
        workflow.add_edge("create_campaign_calendar", END)
        
        # Compile with checkpointer
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _create_revenue_analysis_workflow(self) -> StateGraph:
        """Create revenue analysis workflow."""
        
        workflow = StateGraph(OrchestrationState)
        
        async def collect_revenue_data(state: OrchestrationState):
            """Collect comprehensive revenue data."""
            context = self.create_tool_context(state)
            
            result = await self.execute_agent(
                "revenue_analyst",
                "Collect and analyze comprehensive revenue data including campaigns, flows, and segments",
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "revenue_data": result},
                "active_agent": "revenue_analyst",
                "completed_tasks": state.get("completed_tasks", []) + ["revenue_collection"]
            }
        
        async def analyze_attribution(state: OrchestrationState):
            """Analyze revenue attribution across channels."""
            context = self.create_tool_context(state)
            
            revenue_data = state.get("agent_results", {}).get("revenue_data", {})
            task = f"Analyze revenue attribution using data: {json.dumps(revenue_data.get('data', {}), indent=2)}"
            
            result = await self.execute_agent(
                "revenue_analyst",
                task,
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "attribution_analysis": result},
                "active_agent": "revenue_analyst",
                "completed_tasks": state.get("completed_tasks", []) + ["attribution_analysis"],
                "workflow_status": "completed"
            }
        
        # Add nodes
        workflow.add_node("collect_revenue_data", collect_revenue_data)
        workflow.add_node("analyze_attribution", analyze_attribution)
        
        # Define flow
        workflow.set_entry_point("collect_revenue_data")
        workflow.add_edge("collect_revenue_data", "analyze_attribution")
        workflow.add_edge("analyze_attribution", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _create_comprehensive_audit_workflow(self) -> StateGraph:
        """Create comprehensive audit workflow using all agents."""
        
        workflow = StateGraph(OrchestrationState)
        
        async def audit_campaigns(state: OrchestrationState):
            """Audit campaign performance."""
            context = self.create_tool_context(state)
            
            result = await self.execute_agent(
                "ab_test_coordinator",
                "Conduct comprehensive campaign performance audit",
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "campaign_audit": result},
                "active_agent": "ab_test_coordinator",
                "completed_tasks": state.get("completed_tasks", []) + ["campaign_audit"]
            }
        
        async def audit_revenue(state: OrchestrationState):
            """Audit revenue performance.""" 
            context = self.create_tool_context(state)
            
            result = await self.execute_agent(
                "revenue_analyst",
                "Conduct comprehensive revenue performance audit",
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "revenue_audit": result},
                "active_agent": "revenue_analyst",
                "completed_tasks": state.get("completed_tasks", []) + ["revenue_audit"]
            }
        
        async def generate_recommendations(state: OrchestrationState):
            """Generate comprehensive recommendations."""
            context = self.create_tool_context(state)
            
            # Combine all audit results
            campaign_audit = state.get("agent_results", {}).get("campaign_audit", {})
            revenue_audit = state.get("agent_results", {}).get("revenue_audit", {})
            
            task = f"""Generate strategic recommendations based on comprehensive audit:
            Campaign Analysis: {json.dumps(campaign_audit.get('data', {}), indent=2)}
            Revenue Analysis: {json.dumps(revenue_audit.get('data', {}), indent=2)}
            """
            
            result = await self.execute_agent(
                "calendar_planner",
                task, 
                context
            )
            
            return {
                "agent_results": {**state.get("agent_results", {}), "recommendations": result},
                "active_agent": "calendar_planner",
                "completed_tasks": state.get("completed_tasks", []) + ["recommendations"],
                "workflow_status": "completed"
            }
        
        # Add nodes
        workflow.add_node("audit_campaigns", audit_campaigns)
        workflow.add_node("audit_revenue", audit_revenue)
        workflow.add_node("generate_recommendations", generate_recommendations)
        
        # Define flow (parallel audits, then recommendations)
        workflow.set_entry_point("audit_campaigns")
        workflow.add_edge("audit_campaigns", "audit_revenue")
        workflow.add_edge("audit_revenue", "generate_recommendations")
        workflow.add_edge("generate_recommendations", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def execute_workflow(
        self,
        workflow_name: str,
        initial_state: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow end-to-end.
        
        Args:
            workflow_name: Name of workflow to execute
            initial_state: Initial state for the workflow
            config: Optional execution configuration
            
        Returns:
            Final workflow state
        """
        graph = self.create_workflow_graph(workflow_name)
        
        # Default config
        if not config:
            config = {
                "configurable": {
                    "thread_id": f"{workflow_name}_{datetime.utcnow().isoformat()}"
                }
            }
        
        logger.info(f"Starting workflow {workflow_name} with thread_id: {config['configurable']['thread_id']}")
        
        try:
            # Execute workflow
            final_state = None
            async for chunk in graph.astream(initial_state, config):
                for node_name, state_update in chunk.items():
                    logger.info(f"Workflow node completed: {node_name}")
                    final_state = state_update
            
            logger.info(f"Workflow {workflow_name} completed successfully")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow {workflow_name} failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all orchestration components."""
        health = {
            "orchestrator": True,
            "enhanced_mcp": False,
            "firestore": False,
            "agents_registered": len(self.agents),
            "tools_available": len(self.enhanced_tools)
        }
        
        # Check Enhanced MCP
        try:
            health["enhanced_mcp"] = await self.mcp_adapter.health_check()
        except:
            pass
        
        # Check Firestore
        try:
            firestore = get_firestore_client()
            if firestore:
                # Simple test operation
                test_ref = firestore.collection("health_check").document("test")
                test_ref.set({"timestamp": datetime.utcnow()})
                health["firestore"] = True
        except:
            pass
        
        return health
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self.mcp_adapter, '__exit__'):
            self.mcp_adapter.__exit__(exc_type, exc_val, exc_tb)


# Convenience functions
def get_orchestrator(config: Optional[LangChainConfig] = None) -> MCPOrchestrator:
    """Get orchestrator instance."""
    return MCPOrchestrator(config)


async def run_campaign_planning_workflow(
    client_id: str,
    brand_id: str,
    month: str,
    config: Optional[LangChainConfig] = None
) -> Dict[str, Any]:
    """
    Run complete campaign planning workflow.
    
    Args:
        client_id: Client identifier
        brand_id: Brand identifier  
        month: Target month (YYYY-MM)
        config: Optional configuration
        
    Returns:
        Workflow results with campaign calendar
    """
    async with get_orchestrator(config) as orchestrator:
        
        initial_state = {
            "messages": [HumanMessage(content=f"Plan campaigns for {brand_id} in {month}")],
            "client_id": client_id,
            "brand_id": brand_id,
            "current_task": "campaign_planning",
            "iteration_count": 0,
            "workflow_status": "running"
        }
        
        return await orchestrator.execute_workflow(
            "campaign_planning",
            initial_state
        )


async def run_revenue_analysis_workflow(
    client_id: str,
    brand_id: str,
    config: Optional[LangChainConfig] = None
) -> Dict[str, Any]:
    """
    Run revenue analysis workflow.
    
    Args:
        client_id: Client identifier
        brand_id: Brand identifier
        config: Optional configuration
        
    Returns:
        Revenue analysis results
    """
    async with get_orchestrator(config) as orchestrator:
        
        initial_state = {
            "messages": [HumanMessage(content=f"Analyze revenue performance for {brand_id}")],
            "client_id": client_id,
            "brand_id": brand_id,
            "current_task": "revenue_analysis",
            "iteration_count": 0,
            "workflow_status": "running"
        }
        
        return await orchestrator.execute_workflow(
            "revenue_analysis", 
            initial_state
        )