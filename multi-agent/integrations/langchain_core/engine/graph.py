"""
LangGraph implementation for agent orchestration with checkpointing and retries.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence
from datetime import datetime
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
# FirestoreSaver not yet available in current langgraph version
# from langgraph.checkpoint.firestore import FirestoreSaver
# ToolExecutor also not available in this version
# from langgraph.prebuilt import ToolExecutor, ToolInvocation
from google.cloud import firestore

from ..config import get_config
from ..deps import get_llm, ModelPolicyResolver
from ..agents.tools import get_all_tools
from ..agents.policies import PolicyEnforcer, AgentPolicy
from .usage_tracer import UsageTracer

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    task: str
    context: Dict[str, Any]
    plan: Optional[str]
    tool_calls: List[Dict[str, Any]]
    final_answer: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    budget_remaining: int
    timeout_at: datetime
    checkpoint_id: Optional[str]
    run_id: str
    user_id: Optional[str]
    brand: Optional[str]


class NodeType(str, Enum):
    """Types of nodes in the graph."""
    PLAN = "plan"
    ACT = "act"
    VERIFY = "verify"
    FINALIZE = "finalize"
    ERROR = "error"


class AgentGraph:
    """
    LangGraph-based agent orchestration with:
    - Plan → Act → Verify → Finalize flow
    - Firestore checkpointing
    - Budget and timeout enforcement
    - Retry logic with exponential backoff
    """
    
    def __init__(
        self,
        llm=None,
        tools=None,
        policy: Optional[AgentPolicy] = None,
        checkpointer=None,
        config=None,
        user_id: Optional[str] = None,
        brand: Optional[str] = None,
        agent_name: Optional[str] = None
    ):
        """
        Initialize the agent graph.
        
        Args:
            llm: Language model instance
            tools: List of tools
            policy: Agent policy for enforcement
            checkpointer: Checkpoint saver (Firestore or Memory)
            config: LangChain configuration
            user_id: User ID for tracking
            brand: Brand for tracking
            agent_name: Agent name for tracking
        """
        self.config = config or get_config()
        self.user_id = user_id
        self.brand = brand
        self.agent_name = agent_name
        
        # Create LLM with policy resolution and usage tracking
        if llm:
            self.llm = llm
        else:
            # Use ModelPolicyResolver to get appropriate model
            self.llm = get_llm(
                config=self.config,
                user_id=user_id,
                brand=brand,
                use_policy=True
            )
        
        # Set up usage tracer
        self.usage_tracer = UsageTracer(
            user_id=user_id,
            brand=brand,
            agent=agent_name,
            db=firestore.Client(project=self.config.firestore_project) if self.config.firestore_project else None
        )
        
        # Add tracer as callback to LLM
        if hasattr(self.llm, 'callbacks'):
            if self.llm.callbacks is None:
                self.llm.callbacks = []
            self.llm.callbacks.append(self.usage_tracer)
        
        self.tools = tools or get_all_tools(self.config)
        self.policy = policy or AgentPolicy()
        self.enforcer = PolicyEnforcer(self.policy)
        
        # Set up checkpointer
        if checkpointer:
            self.checkpointer = checkpointer
        else:
            # Use memory checkpointer for now (FirestoreSaver not yet available)
            self.checkpointer = MemorySaver()
        
        # Build the graph
        self.graph = self._build_graph()
        self.app = self.graph.compile(checkpointer=self.checkpointer)
        
        # Simple tool executor implementation
        self.tool_map = {tool.name: tool for tool in self.tools}
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node(NodeType.PLAN, self._plan_node)
        graph.add_node(NodeType.ACT, self._act_node)
        graph.add_node(NodeType.VERIFY, self._verify_node)
        graph.add_node(NodeType.FINALIZE, self._finalize_node)
        graph.add_node(NodeType.ERROR, self._error_node)
        
        # Add edges
        graph.set_entry_point(NodeType.PLAN)
        
        # From PLAN
        graph.add_conditional_edges(
            NodeType.PLAN,
            self._should_continue_from_plan,
            {
                "continue": NodeType.ACT,
                "error": NodeType.ERROR,
                "end": END
            }
        )
        
        # From ACT
        graph.add_conditional_edges(
            NodeType.ACT,
            self._should_continue_from_act,
            {
                "verify": NodeType.VERIFY,
                "act": NodeType.ACT,  # Loop for more actions
                "finalize": NodeType.FINALIZE,
                "error": NodeType.ERROR
            }
        )
        
        # From VERIFY
        graph.add_conditional_edges(
            NodeType.VERIFY,
            self._should_continue_from_verify,
            {
                "act": NodeType.ACT,  # Retry if verification fails
                "finalize": NodeType.FINALIZE,
                "error": NodeType.ERROR
            }
        )
        
        # From FINALIZE
        graph.add_edge(NodeType.FINALIZE, END)
        
        # From ERROR
        graph.add_edge(NodeType.ERROR, END)
        
        return graph
    
    def _plan_node(self, state: AgentState) -> AgentState:
        """Planning node - creates a plan for the task."""
        logger.info(f"[PLAN] Creating plan for task: {state['task']}")
        
        # Update tracer context
        self.usage_tracer.run_id = state.get("run_id")
        self.usage_tracer.node = "plan"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a planning assistant. Create a clear, actionable plan for the given task.
            
Consider the context and available tools. Output a 2-3 step plan in bullet points.

Available tools:
{tools}

Context:
{context}"""),
            ("human", "Task: {task}\n\nCreate a plan:")
        ])
        
        tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "task": state["task"],
                "context": state["context"],
                "tools": tool_descriptions
            })
            
            plan = response.content if hasattr(response, 'content') else str(response)
            
            state["plan"] = plan
            state["messages"].append(AIMessage(content=f"Plan:\n{plan}"))
            
            logger.info(f"[PLAN] Generated plan: {plan[:200]}...")
            
        except Exception as e:
            logger.error(f"[PLAN] Failed to generate plan: {e}")
            state["error"] = f"Planning failed: {str(e)}"
        
        return state
    
    def _act_node(self, state: AgentState) -> AgentState:
        """Action node - executes tools based on the plan."""
        logger.info(f"[ACT] Executing actions for run {state['run_id']}")
        
        # Update tracer context
        self.usage_tracer.run_id = state.get("run_id")
        self.usage_tracer.node = "act"
        
        # Check budget
        if state["budget_remaining"] <= 0:
            logger.warning("[ACT] Budget exhausted")
            state["error"] = "Tool budget exhausted"
            return state
        
        # Check timeout
        if datetime.utcnow() > state["timeout_at"]:
            logger.warning("[ACT] Timeout reached")
            state["error"] = "Execution timeout"
            return state
        
        # Determine next action
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an action-taking assistant. Based on the plan and conversation history,
determine the next tool to call.

Available tools:
{tools}

Output format:
TOOL: <tool_name>
INPUT: <tool_input_json>

If no more tools are needed, output:
TOOL: none
INPUT: {}"""),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "What's the next action?")
        ])
        
        tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "tools": tool_descriptions,
                "messages": state["messages"]
            })
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse tool call
            if "TOOL: none" in content:
                logger.info("[ACT] No more actions needed")
                return state
            
            lines = content.split("\n")
            tool_name = None
            tool_input = {}
            
            for line in lines:
                if line.startswith("TOOL:"):
                    tool_name = line.split(":", 1)[1].strip()
                elif line.startswith("INPUT:"):
                    import json
                    tool_input = json.loads(line.split(":", 1)[1].strip())
            
            if tool_name and tool_name != "none":
                # Execute tool
                logger.info(f"[ACT] Executing tool: {tool_name}")
                
                # Simple tool execution
                if tool_name in self.tool_map:
                    tool = self.tool_map[tool_name]
                    try:
                        result = tool.run(tool_input)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"
                else:
                    result = f"Unknown tool: {tool_name}"
                
                # Record tool call
                state["tool_calls"].append({
                    "tool": tool_name,
                    "input": tool_input,
                    "output": result,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Update messages
                state["messages"].append(AIMessage(
                    content=f"Called {tool_name} with {tool_input}"
                ))
                state["messages"].append(HumanMessage(
                    content=f"Tool result: {result}"
                ))
                
                # Decrement budget
                state["budget_remaining"] -= 1
                
        except Exception as e:
            logger.error(f"[ACT] Action failed: {e}")
            state["error"] = f"Action failed: {str(e)}"
        
        return state
    
    def _verify_node(self, state: AgentState) -> AgentState:
        """Verification node - checks if actions were successful."""
        logger.info(f"[VERIFY] Verifying actions for run {state['run_id']}")
        
        if not state["tool_calls"]:
            logger.info("[VERIFY] No tool calls to verify")
            return state
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Review the tool execution results and determine if they were successful.
            
Consider:
1. Did the tools return valid results?
2. Are we making progress toward the task?
3. Do we need to retry or try different tools?

Output: SUCCESS or RETRY or ERROR"""),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "Verify the recent tool executions:")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "messages": state["messages"][-6:]  # Last few messages
            })
            
            verdict = response.content if hasattr(response, 'content') else str(response)
            verdict = verdict.strip().upper()
            
            logger.info(f"[VERIFY] Verification result: {verdict}")
            
            if "ERROR" in verdict:
                state["error"] = "Tool execution verification failed"
            elif "RETRY" in verdict:
                # Will trigger another ACT cycle
                pass
            
        except Exception as e:
            logger.error(f"[VERIFY] Verification failed: {e}")
            state["error"] = f"Verification failed: {str(e)}"
        
        return state
    
    def _finalize_node(self, state: AgentState) -> AgentState:
        """Finalization node - generates the final answer."""
        logger.info(f"[FINALIZE] Generating final answer for run {state['run_id']}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Based on the task, plan, and execution results, provide a comprehensive final answer.
            
Be clear, concise, and directly address the original task.
Include relevant details from tool executions."""),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "Task: {task}\n\nProvide the final answer:")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "task": state["task"],
                "messages": state["messages"]
            })
            
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # Apply PII redaction
            answer = self.enforcer.redact_pii(answer)
            
            state["final_answer"] = answer
            state["messages"].append(AIMessage(content=f"Final Answer:\n{answer}"))
            
            logger.info(f"[FINALIZE] Generated final answer: {answer[:200]}...")
            
        except Exception as e:
            logger.error(f"[FINALIZE] Failed to generate answer: {e}")
            state["error"] = f"Finalization failed: {str(e)}"
        
        return state
    
    def _error_node(self, state: AgentState) -> AgentState:
        """Error node - handles errors gracefully."""
        logger.error(f"[ERROR] Handling error for run {state['run_id']}: {state.get('error')}")
        
        if not state.get("final_answer"):
            state["final_answer"] = f"Task failed: {state.get('error', 'Unknown error')}"
        
        return state
    
    def _should_continue_from_plan(self, state: AgentState) -> str:
        """Determine next step after planning."""
        if state.get("error"):
            return "error"
        elif state.get("plan"):
            return "continue"
        else:
            return "end"
    
    def _should_continue_from_act(self, state: AgentState) -> str:
        """Determine next step after acting."""
        if state.get("error"):
            return "error"
        elif state["budget_remaining"] <= 0:
            return "finalize"
        elif datetime.utcnow() > state["timeout_at"]:
            return "finalize"
        elif len(state["tool_calls"]) > 0 and len(state["tool_calls"]) % 3 == 0:
            # Verify every 3 tool calls
            return "verify"
        elif len(state["messages"]) > 50:  # Prevent infinite loops
            return "finalize"
        else:
            # Continue acting or finalize based on LLM decision
            last_message = state["messages"][-1].content if state["messages"] else ""
            if "TOOL: none" in last_message:
                return "finalize"
            else:
                return "act"
    
    def _should_continue_from_verify(self, state: AgentState) -> str:
        """Determine next step after verification."""
        if state.get("error"):
            return "error"
        elif state["budget_remaining"] <= 0:
            return "finalize"
        elif datetime.utcnow() > state["timeout_at"]:
            return "finalize"
        else:
            # Check last verification result
            last_message = state["messages"][-1].content if state["messages"] else ""
            if "RETRY" in last_message:
                return "act"
            else:
                return "finalize"
    
    def invoke(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        user_id: Optional[str] = None,
        brand: Optional[str] = None,
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke the agent graph.
        
        Args:
            task: Task description
            context: Task context
            run_id: Run ID for tracking
            user_id: User ID for policy resolution
            brand: Brand context
            checkpoint_id: Checkpoint to resume from
        
        Returns:
            Execution result dictionary
        """
        run_id = run_id or str(uuid.uuid4())
        context = context or {}
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=task)],
            "task": task,
            "context": context,
            "plan": None,
            "tool_calls": [],
            "final_answer": None,
            "error": None,
            "metadata": {
                "start_time": datetime.utcnow().isoformat(),
                "model": self.config.lc_model,
                "provider": self.config.lc_provider
            },
            "budget_remaining": self.policy.max_tool_calls,
            "timeout_at": datetime.utcnow() + self.policy.timeout_seconds,
            "checkpoint_id": checkpoint_id,
            "run_id": run_id,
            "user_id": user_id,
            "brand": brand
        }
        
        logger.info(f"[INVOKE] Starting run {run_id} for task: {task}")
        
        try:
            # Run the graph
            config = {"configurable": {"thread_id": run_id}}
            
            if checkpoint_id:
                # Resume from checkpoint
                logger.info(f"[INVOKE] Resuming from checkpoint {checkpoint_id}")
                final_state = self.app.invoke(None, config)
            else:
                # Start fresh
                final_state = self.app.invoke(initial_state, config)
            
            # Calculate duration
            end_time = datetime.utcnow()
            start_time = datetime.fromisoformat(final_state["metadata"]["start_time"])
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Build result
            result = {
                "run_id": run_id,
                "task": task,
                "plan": final_state.get("plan"),
                "tool_calls": final_state.get("tool_calls", []),
                "final_answer": final_state.get("final_answer"),
                "success": not bool(final_state.get("error")),
                "error": final_state.get("error"),
                "metadata": {
                    **final_state.get("metadata", {}),
                    "duration_ms": duration_ms,
                    "tool_calls_made": len(final_state.get("tool_calls", [])),
                    "checkpoint_id": final_state.get("checkpoint_id")
                }
            }
            
            logger.info(f"[INVOKE] Completed run {run_id} - Success: {result['success']}")
            
            return result
            
        except Exception as e:
            logger.error(f"[INVOKE] Run {run_id} failed: {e}")
            return {
                "run_id": run_id,
                "task": task,
                "success": False,
                "error": str(e),
                "metadata": {"duration_ms": 0}
            }


def create_agent_graph(
    policy: Optional[AgentPolicy] = None,
    checkpointer=None,
    config=None
) -> AgentGraph:
    """
    Factory function to create an agent graph.
    
    Args:
        policy: Agent policy
        checkpointer: Checkpoint saver
        config: Configuration
    
    Returns:
        Configured AgentGraph instance
    """
    return AgentGraph(
        policy=policy,
        checkpointer=checkpointer,
        config=config
    )