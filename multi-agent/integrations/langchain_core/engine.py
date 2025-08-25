"""
LangGraph engine for composing RAG and Agent workflows.

Provides graph-based orchestration with checkpointing and retries.
"""

import logging
from typing import Dict, Any, Optional, List, TypedDict
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .config import LangChainConfig, get_config
from .deps import get_llm, initialize_tracing
from .rag import create_rag_chain
from .agents import run_agent_task, AgentPolicy

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State for workflow execution."""
    task: str
    context: Dict[str, Any]
    plan: Optional[str]
    actions: List[Dict[str, Any]]
    verification: Optional[Dict[str, Any]]
    final_output: Optional[str]
    errors: List[str]
    metadata: Dict[str, Any]


class NodeType(str, Enum):
    """Workflow node types."""
    PLAN = "plan"
    ACT = "act"
    VERIFY = "verify"
    FINALIZE = "finalize"


class LangGraphEngine:
    """
    LangGraph engine for orchestrating workflows.
    
    Composes graphs with nodes for plan → act → verify → finalize.
    """
    
    def __init__(
        self,
        config: Optional[LangChainConfig] = None,
        checkpointer: Optional[Any] = None
    ):
        """
        Initialize engine.
        
        Args:
            config: Configuration instance
            checkpointer: Checkpoint saver (uses memory if not provided)
        """
        self.config = config or get_config()
        self.llm = get_llm(self.config)
        self.checkpointer = checkpointer or MemorySaver()
        
        # Initialize tracing
        initialize_tracing(self.config)
        
        # Build graph
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        # Create state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node(NodeType.PLAN, self._plan_node)
        workflow.add_node(NodeType.ACT, self._act_node)
        workflow.add_node(NodeType.VERIFY, self._verify_node)
        workflow.add_node(NodeType.FINALIZE, self._finalize_node)
        
        # Set entry point
        workflow.set_entry_point(NodeType.PLAN)
        
        # Add edges
        workflow.add_edge(NodeType.PLAN, NodeType.ACT)
        workflow.add_conditional_edges(
            NodeType.ACT,
            self._should_verify,
            {
                True: NodeType.VERIFY,
                False: NodeType.FINALIZE
            }
        )
        workflow.add_conditional_edges(
            NodeType.VERIFY,
            self._verification_result,
            {
                "retry": NodeType.ACT,
                "finalize": NodeType.FINALIZE
            }
        )
        workflow.add_edge(NodeType.FINALIZE, END)
        
        # Compile graph
        self.graph = workflow.compile(checkpointer=self.checkpointer)
    
    def _plan_node(self, state: WorkflowState) -> WorkflowState:
        """
        Planning node - creates execution plan.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with plan
        """
        logger.info("Executing PLAN node")
        
        try:
            prompt = f"""Create a brief execution plan for this task:
Task: {state['task']}
Context: {state.get('context', {})}

Provide a 2-3 step plan."""
            
            response = self.llm.invoke(prompt)
            
            if hasattr(response, 'content'):
                plan = response.content
            else:
                plan = str(response)
            
            state["plan"] = plan
            state["metadata"]["plan_created_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Plan created: {plan[:100]}...")
        
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            state["errors"].append(f"Planning error: {str(e)}")
            state["plan"] = "No plan generated due to error"
        
        return state
    
    def _act_node(self, state: WorkflowState) -> WorkflowState:
        """
        Action node - executes tools and actions.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with action results
        """
        logger.info("Executing ACT node")
        
        try:
            # Run agent with tools
            policy = AgentPolicy(
                max_tool_calls=10,
                timeout_seconds=30
            )
            
            result = run_agent_task(
                task=state["task"],
                context=state.get("context", {}),
                policy=policy,
                config=self.config
            )
            
            # Store action results
            state["actions"].append({
                "type": "agent_execution",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update metadata
            state["metadata"]["tool_calls"] = result.get("tool_calls", [])
            state["metadata"]["agent_success"] = result.get("success", False)
            
            logger.info(f"Agent execution complete: {result.get('success')}")
        
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            state["errors"].append(f"Action error: {str(e)}")
            state["actions"].append({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return state
    
    def _verify_node(self, state: WorkflowState) -> WorkflowState:
        """
        Verification node - checks action results.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with verification results
        """
        logger.info("Executing VERIFY node")
        
        try:
            # Get last action result
            if not state["actions"]:
                state["verification"] = {
                    "passed": False,
                    "reason": "No actions to verify"
                }
                return state
            
            last_action = state["actions"][-1]
            
            # Simple verification logic
            if last_action.get("type") == "error":
                verification_passed = False
                reason = "Action resulted in error"
            elif last_action.get("result", {}).get("success"):
                verification_passed = True
                reason = "Action completed successfully"
            else:
                verification_passed = False
                reason = "Action did not complete successfully"
            
            state["verification"] = {
                "passed": verification_passed,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Verification result: {verification_passed} - {reason}")
        
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            state["errors"].append(f"Verification error: {str(e)}")
            state["verification"] = {
                "passed": False,
                "reason": f"Verification error: {str(e)}"
            }
        
        return state
    
    def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        """
        Finalization node - prepares final output.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with final output
        """
        logger.info("Executing FINALIZE node")
        
        try:
            # Compile final output from actions
            if state["actions"]:
                last_action = state["actions"][-1]
                
                if last_action.get("type") == "agent_execution":
                    result = last_action.get("result", {})
                    final_output = result.get("final_answer", "Task completed")
                else:
                    final_output = "Task could not be completed due to errors"
            else:
                final_output = "No actions were executed"
            
            state["final_output"] = final_output
            state["metadata"]["finalized_at"] = datetime.utcnow().isoformat()
            
            logger.info("Workflow finalized")
        
        except Exception as e:
            logger.error(f"Finalization failed: {e}")
            state["errors"].append(f"Finalization error: {str(e)}")
            state["final_output"] = f"Finalization failed: {str(e)}"
        
        return state
    
    def _should_verify(self, state: WorkflowState) -> bool:
        """
        Determine if verification is needed.
        
        Args:
            state: Current workflow state
        
        Returns:
            True if verification needed
        """
        # Skip verification if there were errors
        if state.get("errors"):
            return False
        
        # Skip verification if no actions
        if not state.get("actions"):
            return False
        
        # Otherwise verify
        return True
    
    def _verification_result(self, state: WorkflowState) -> str:
        """
        Determine next step based on verification.
        
        Args:
            state: Current workflow state
        
        Returns:
            Next node name
        """
        verification = state.get("verification", {})
        
        # Retry if verification failed and we haven't exceeded retries
        retry_count = state["metadata"].get("retry_count", 0)
        if not verification.get("passed") and retry_count < 2:
            state["metadata"]["retry_count"] = retry_count + 1
            return "retry"
        
        # Otherwise finalize
        return "finalize"
    
    def run_rag(
        self,
        question: str,
        k: int = 5,
        max_tokens: int = 600
    ) -> Dict[str, Any]:
        """
        Run RAG query through the engine.
        
        Args:
            question: Question to ask
            k: Number of documents to retrieve
            max_tokens: Maximum response tokens
        
        Returns:
            RAG result
        """
        logger.info(f"Running RAG query: {question}")
        
        try:
            # Update config
            self.config.rag_k_documents = k
            
            # Create RAG chain
            chain = create_rag_chain(self.config)
            
            # Run query
            response = chain.ask(
                question=question,
                max_tokens=max_tokens
            )
            
            return response.to_dict()
        
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "error": str(e),
                "question": question
            }
    
    def run_agent(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run agent task through the graph.
        
        Args:
            task: Task description
            context: Task context
        
        Returns:
            Execution result
        """
        logger.info(f"Running agent task: {task}")
        
        # Initialize state
        initial_state: WorkflowState = {
            "task": task,
            "context": context or {},
            "plan": None,
            "actions": [],
            "verification": None,
            "final_output": None,
            "errors": [],
            "metadata": {
                "started_at": datetime.utcnow().isoformat(),
                "engine_version": "1.0.0"
            }
        }
        
        try:
            # Run graph
            final_state = self.graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": "default"}}
            )
            
            # Prepare result
            return {
                "task": task,
                "plan": final_state.get("plan"),
                "actions": final_state.get("actions", []),
                "final_output": final_state.get("final_output"),
                "errors": final_state.get("errors", []),
                "metadata": final_state.get("metadata", {}),
                "success": len(final_state.get("errors", [])) == 0
            }
        
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "task": task,
                "error": str(e),
                "success": False
            }