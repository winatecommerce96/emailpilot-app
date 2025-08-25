"""
Task-oriented agent implementation.

Provides ReAct/Tool-calling agents that can execute tasks,
call tools, and return structured results.
"""

import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents import create_structured_chat_agent
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Structured result from agent execution."""
    plan: str
    steps: List[Dict[str, Any]]
    final_answer: str
    tool_calls: List[Dict[str, Any]]
    time_ms: int
    policy_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "plan": self.plan,
            "steps": self.steps,
            "final_answer": self.final_answer,
            "tool_calls": self.tool_calls,
            "time_ms": self.time_ms,
            "policy_summary": self.policy_summary,
            "error": self.error
        }


class TaskAgent:
    """Task-oriented agent with tool calling capabilities."""
    
    SYSTEM_PROMPT = """You are a helpful assistant that completes tasks using available tools.

Available tools:
{tools}

Tool descriptions:
{tool_names}

When given a task:
1. First create a plan breaking down the task into steps
2. Execute each step using the appropriate tools
3. Synthesize the results into a final answer

Use this format:

Thought: I need to understand the task and create a plan
Plan:
1. [First step]
2. [Second step]
3. [Final step]

Thought: Now I'll execute step 1
Action: [tool_name]
Action Input: {{"param1": "value1", "param2": "value2"}}
Observation: [tool response]

Thought: Based on the observation, I'll proceed to step 2
Action: [tool_name]
Action Input: {{"param": "value"}}
Observation: [tool response]

... (continue for all steps)

Thought: I have completed all steps and can provide the final answer
Final Answer: [Your comprehensive answer based on all observations]

Begin!

Task: {input}
{agent_scratchpad}"""
    
    def __init__(
        self,
        llm: Any,
        tools: List[Any],
        policy_enforcer: Optional[Any] = None,
        config: Optional[Any] = None
    ):
        """
        Initialize the task agent.
        
        Args:
            llm: Language model for the agent
            tools: List of tools available to the agent
            policy_enforcer: PolicyEnforcer instance
            config: LangChainConfig instance
        """
        if config is None:
            from ..config import get_config
            config = get_config()
        
        self.config = config
        self.llm = llm
        self.tools = tools
        self.policy_enforcer = policy_enforcer
        
        # Create the agent
        self.agent = self._create_agent()
        
        # Create the executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=config.agent_max_iterations,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )
    
    def _create_agent(self) -> Any:
        """Create the underlying agent."""
        # Create prompt
        prompt = PromptTemplate(
            template=self.SYSTEM_PROMPT,
            input_variables=["input", "tools", "tool_names", "agent_scratchpad"]
        )
        
        # Create ReAct agent
        return create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
    
    def _extract_plan(self, text: str) -> str:
        """
        Extract plan from agent output.
        
        Args:
            text: Agent output text
        
        Returns:
            Extracted plan or empty string
        """
        import re
        
        plan_match = re.search(r'Plan:(.*?)(?:Thought:|Action:|$)', text, re.DOTALL)
        if plan_match:
            return plan_match.group(1).strip()
        return ""
    
    def _extract_steps(self, intermediate_steps: List[tuple]) -> List[Dict[str, Any]]:
        """
        Extract structured steps from intermediate results.
        
        Args:
            intermediate_steps: Raw intermediate steps from agent
        
        Returns:
            List of structured step dictionaries
        """
        steps = []
        for i, (action, observation) in enumerate(intermediate_steps):
            step = {
                "step_number": i + 1,
                "thought": getattr(action, "log", ""),
                "action": getattr(action, "tool", ""),
                "action_input": getattr(action, "tool_input", {}),
                "observation": str(observation)
            }
            steps.append(step)
        return steps
    
    def _extract_tool_calls(self, intermediate_steps: List[tuple]) -> List[Dict[str, Any]]:
        """
        Extract tool call information.
        
        Args:
            intermediate_steps: Raw intermediate steps
        
        Returns:
            List of tool call records
        """
        tool_calls = []
        for action, observation in intermediate_steps:
            if hasattr(action, "tool"):
                tool_call = {
                    "tool": action.tool,
                    "input": action.tool_input,
                    "output": str(observation)[:500]  # Truncate long outputs
                }
                tool_calls.append(tool_call)
        return tool_calls
    
    def run(self, task: str) -> AgentResult:
        """
        Run the agent on a task.
        
        Args:
            task: Task description
        
        Returns:
            AgentResult with structured output
        """
        start_time = time.time()
        
        try:
            # Start policy enforcement if available
            if self.policy_enforcer:
                self.policy_enforcer.start_execution()
            
            # Run the agent
            result = self.executor.invoke(
                {
                    "input": task,
                    "tools": "\n".join([t.description for t in self.tools]),
                    "tool_names": ", ".join([t.name for t in self.tools])
                }
            )
            
            # Extract components
            output = result.get("output", "")
            intermediate_steps = result.get("intermediate_steps", [])
            
            # Extract structured information
            plan = self._extract_plan(str(intermediate_steps))
            if not plan:
                # Try to infer plan from task
                plan = f"Execute task: {task}"
            
            steps = self._extract_steps(intermediate_steps)
            tool_calls = self._extract_tool_calls(intermediate_steps)
            
            # Apply output policies
            if self.policy_enforcer:
                output = self.policy_enforcer.check_output(output)
                policy_summary = self.policy_enforcer.get_summary()
            else:
                policy_summary = None
            
            # Calculate execution time
            time_ms = int((time.time() - start_time) * 1000)
            
            return AgentResult(
                plan=plan,
                steps=steps,
                final_answer=output,
                tool_calls=tool_calls,
                time_ms=time_ms,
                policy_summary=policy_summary
            )
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            
            time_ms = int((time.time() - start_time) * 1000)
            
            return AgentResult(
                plan="Failed to create plan",
                steps=[],
                final_answer=f"Error: {str(e)}",
                tool_calls=[],
                time_ms=time_ms,
                policy_summary=self.policy_enforcer.get_summary() if self.policy_enforcer else None,
                error=str(e)
            )


def create_agent(
    llm: Optional[Any] = None,
    tools: Optional[List[Any]] = None,
    policy: Optional[Any] = None,
    config: Optional[Any] = None
) -> TaskAgent:
    """
    Factory function to create a task agent.
    
    Args:
        llm: Language model (will create if not provided)
        tools: Tools list (will load defaults if not provided)
        policy: AgentPolicy instance
        config: LangChainConfig instance
    
    Returns:
        Configured TaskAgent instance
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    if llm is None:
        from ..deps import get_llm
        llm = get_llm(config)
    
    if tools is None:
        from .tools import get_agent_tools
        tools = get_agent_tools(config)
    
    # Create policy enforcer
    from .policies import PolicyEnforcer, AgentPolicy
    policy_enforcer = PolicyEnforcer(policy or AgentPolicy())
    
    return TaskAgent(llm, tools, policy_enforcer, config)


def run_agent_task(
    task: str,
    llm: Optional[Any] = None,
    tools: Optional[List[Any]] = None,
    policy: Optional[Any] = None,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Convenience function to run an agent task.
    
    Args:
        task: Task description
        llm: Language model
        tools: Tools list
        policy: AgentPolicy instance
        config: LangChainConfig instance
    
    Returns:
        Dictionary with agent results
    """
    agent = create_agent(llm, tools, policy, config)
    result = agent.run(task)
    return result.to_dict()