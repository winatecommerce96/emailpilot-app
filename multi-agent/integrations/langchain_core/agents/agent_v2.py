"""
Agent executor with LangChain/LangGraph - V2 implementation.

Simplified implementation to avoid pydantic v1/v2 conflicts.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel

from .tools import get_all_tools
from .policies import AgentPolicy, PolicyEnforcer
from ..config import LangChainConfig, get_config
from ..deps import get_llm

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """Represents a single agent step."""
    step_number: int
    action: str
    thought: Optional[str]
    tool: Optional[str]
    tool_input: Optional[Dict[str, Any]]
    tool_output: Optional[Any]
    timestamp: datetime


@dataclass
class AgentResult:
    """Result from agent execution."""
    task: str
    plan: Optional[str]
    steps: List[AgentStep]
    tool_calls: List[Dict[str, Any]]
    final_answer: str
    success: bool
    error: Optional[str]
    policy_summary: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "plan": self.plan,
            "steps": [
                {
                    "step_number": s.step_number,
                    "action": s.action,
                    "thought": s.thought,
                    "tool": s.tool,
                    "tool_input": s.tool_input,
                    "tool_output": s.tool_output,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in self.steps
            ],
            "tool_calls": self.tool_calls,
            "final_answer": self.final_answer,
            "success": self.success,
            "error": self.error,
            "policy_summary": self.policy_summary,
            "metadata": self.metadata
        }


class SimpleAgentExecutor:
    """Simplified agent executor using chain composition to avoid pydantic conflicts."""
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        policy: Optional[AgentPolicy] = None,
        config: Optional[LangChainConfig] = None
    ):
        """
        Initialize agent executor.
        
        Args:
            llm: LLM instance
            tools: List of tools
            policy: Agent policy
            config: Configuration
        """
        self.config = config or get_config()
        self.llm = llm or get_llm(self.config)
        self.tools = tools or get_all_tools(self.config)
        self.policy = policy or AgentPolicy()
        self.enforcer = PolicyEnforcer(self.policy)
        
        # Build tool map for execution
        self.tool_map = {tool.name: tool for tool in self.tools}
    
    def _execute_tool(self, tool_name: str, tool_input: Any) -> str:
        """Execute a tool by name."""
        if tool_name not in self.tool_map:
            return f"Error: Tool '{tool_name}' not found"
        
        try:
            tool = self.tool_map[tool_name]
            result = tool.run(tool_input)
            return str(result)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing tool: {str(e)}"
    
    def _create_plan(self, task: str, context: Dict[str, Any]) -> str:
        """Create a plan for the task."""
        planning_prompt = PromptTemplate.from_template(
            """Create a brief plan to accomplish this task:
{task}

Context: {context}

Provide a 2-3 step plan in bullet points."""
        )
        
        planning_chain = planning_prompt | self.llm | StrOutputParser()
        
        try:
            plan = planning_chain.invoke({
                "task": task,
                "context": json.dumps(context, indent=2)
            })
            return plan
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return "No explicit plan generated"
    
    def _run_reasoning_chain(self, task: str, context: Dict[str, Any]) -> str:
        """Run a simple reasoning chain without tool execution."""
        # Build tool descriptions
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        ])
        
        # Create reasoning prompt
        reasoning_prompt = PromptTemplate.from_template(
            """You are a helpful AI assistant. Answer the following task based on the context provided.

Available tools (for reference only - you cannot execute them):
{tool_descriptions}

Context: {context}

Task: {task}

Provide a clear, comprehensive answer. If the task would require tool execution, explain what tools would be needed and why."""
        )
        
        # Create chain
        reasoning_chain = reasoning_prompt | self.llm | StrOutputParser()
        
        # Execute
        answer = reasoning_chain.invoke({
            "tool_descriptions": tool_descriptions,
            "context": json.dumps(context, indent=2),
            "task": task
        })
        
        return answer
    
    def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        Run agent on a task.
        
        Args:
            task: Task description
            context: Optional context (brand, month, etc.)
        
        Returns:
            AgentResult with execution details
        """
        start_time = datetime.utcnow()
        context = context or {}
        
        logger.info(f"Starting agent task: {task}")
        
        # Reset policy enforcer
        self.enforcer.reset()
        
        try:
            # Create plan
            plan = self._create_plan(task, context)
            
            # Check timeout after planning
            if self.enforcer.check_timeout():
                raise TimeoutError("Timeout during planning phase")
            
            # Run reasoning chain (simplified - no actual tool execution)
            final_answer = self._run_reasoning_chain(task, context)
            
            # Apply PII redaction to final answer
            final_answer = self.enforcer.redact_pii(final_answer)
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Build result
            return AgentResult(
                task=task,
                plan=plan,
                steps=[],  # No actual tool execution in this simplified version
                tool_calls=[],
                final_answer=final_answer,
                success=True,
                error=None,
                policy_summary=self.enforcer.get_summary(),
                metadata={
                    "duration_ms": duration_ms,
                    "model": self.config.lc_model,
                    "provider": self.config.lc_provider,
                    "context": context,
                    "note": "Simplified agent - tool execution not implemented"
                }
            )
        
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return AgentResult(
                task=task,
                plan=None,
                steps=[],
                tool_calls=[],
                final_answer=f"Task failed: {str(e)}",
                success=False,
                error=str(e),
                policy_summary=self.enforcer.get_summary(),
                metadata={
                    "duration_ms": duration_ms,
                    "model": self.config.lc_model,
                    "provider": self.config.lc_provider,
                    "context": context
                }
            )


def run_agent_task(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    policy: Optional[AgentPolicy] = None,
    config: Optional[LangChainConfig] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to run an agent task.
    
    Args:
        task: Task description
        context: Task context
        policy: Agent policy
        config: Configuration
        **kwargs: Additional arguments (timeout, max_tools, etc.)
    
    Returns:
        Result dictionary
    """
    # Create policy with overrides from kwargs
    if policy is None:
        policy = AgentPolicy()
    
    if "timeout" in kwargs:
        policy.timeout_seconds = kwargs["timeout"]
    if "max_tools" in kwargs:
        policy.max_tool_calls = kwargs["max_tools"]
    
    # Create and run executor
    executor = SimpleAgentExecutor(
        policy=policy,
        config=config
    )
    
    result = executor.run(task=task, context=context)
    
    return result.to_dict()