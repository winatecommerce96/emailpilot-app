"""
Agent executor with LangChain/LangGraph.

Provides ReAct/Tool-Calling agents with policy enforcement.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import Tool
from langchain_core.agents import AgentAction, AgentFinish
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub

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


class AgentExecutor:
    """Custom agent executor with policy enforcement."""
    
    SYSTEM_PROMPT = """You are a helpful AI assistant with access to various tools.

Your goal is to complete the given task using the available tools while following these rules:
1. Think step-by-step before taking any action
2. Use tools to gather information and complete tasks
3. Be efficient - avoid redundant tool calls
4. Provide clear, actionable answers
5. If you cannot complete a task, explain why

Available tools:
{tool_descriptions}

Task context:
{context}

Remember: You have a limited budget of {max_tools} tool calls and {timeout}s to complete the task."""
    
    PLANNING_PROMPT = """Create a brief plan to accomplish this task:
{task}

Context: {context}

Provide a 2-3 step plan in bullet points."""
    
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
        
        # Build agent
        self._build_agent()
    
    def _build_agent(self):
        """Build the LangChain agent using v2 patterns."""
        # Create tool descriptions
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        ])
        
        # Create a ReAct prompt that works with v2
        react_template = """You are a helpful AI assistant with access to various tools.

Your goal is to complete the given task using the available tools while following these rules:
1. Think step-by-step before taking any action
2. Use tools to gather information and complete tasks
3. Be efficient - avoid redundant tool calls
4. Provide clear, actionable answers
5. If you cannot complete a task, explain why

Available tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Context: {context}

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
        
        prompt = ChatPromptTemplate.from_template(react_template)
        
        # Create agent using ReAct pattern (more stable with v2)
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create agent executor
        self.agent = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=self.policy.max_tool_calls,
            max_execution_time=self.policy.timeout_seconds,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def _create_plan(self, task: str, context: Dict[str, Any]) -> str:
        """
        Create a plan for the task.
        
        Args:
            task: Task description
            context: Task context
        
        Returns:
            Plan as string
        """
        try:
            prompt = self.PLANNING_PROMPT.format(
                task=task,
                context=json.dumps(context, indent=2)
            )
            
            response = self.llm.invoke(prompt)
            
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
        
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return "No explicit plan generated"
    
    def _parse_intermediate_steps(
        self,
        intermediate_steps: List[Tuple[Any, Any]]
    ) -> Tuple[List[AgentStep], List[Dict[str, Any]]]:
        """
        Parse intermediate steps from agent execution.
        
        Args:
            intermediate_steps: Raw intermediate steps
        
        Returns:
            Tuple of (steps, tool_calls)
        """
        steps = []
        tool_calls = []
        
        for i, (action, observation) in enumerate(intermediate_steps):
            step = AgentStep(
                step_number=i + 1,
                action=str(action),
                thought=getattr(action, 'log', None),
                tool=getattr(action, 'tool', None),
                tool_input=getattr(action, 'tool_input', None),
                tool_output=observation,
                timestamp=datetime.utcnow()
            )
            steps.append(step)
            
            if hasattr(action, 'tool'):
                tool_calls.append({
                    "tool": action.tool,
                    "input": action.tool_input,
                    "output": observation
                })
        
        return steps, tool_calls
    
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
            
            # Execute agent
            result = self.agent.invoke({
                "input": task,
                "context": json.dumps(context)
            })
            
            # Parse results
            final_answer = result.get("output", "No answer generated")
            intermediate_steps = result.get("intermediate_steps", [])
            
            steps, tool_calls = self._parse_intermediate_steps(intermediate_steps)
            
            # Apply PII redaction to final answer
            final_answer = self.enforcer.redact_pii(final_answer)
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Build result
            return AgentResult(
                task=task,
                plan=plan,
                steps=steps,
                tool_calls=tool_calls,
                final_answer=final_answer,
                success=True,
                error=None,
                policy_summary=self.enforcer.get_summary(),
                metadata={
                    "duration_ms": duration_ms,
                    "model": self.config.lc_model,
                    "provider": self.config.lc_provider,
                    "context": context
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
    executor = AgentExecutor(
        policy=policy,
        config=config
    )
    
    result = executor.run(task=task, context=context)
    
    return result.to_dict()