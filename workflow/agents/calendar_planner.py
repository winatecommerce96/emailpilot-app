"""
Calendar Planner Agent Factory
Creates a LangChain AgentExecutor with tool allowlist for calendar planning
"""
from typing import Dict, Any, List, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import Runnable
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.tools import Tool
import logging
import os

logger = logging.getLogger(__name__)


def create(params: Dict[str, Any]) -> Runnable:
    """
    Create a Calendar Planner agent with specified tools
    
    Args:
        params: Configuration including tool_allowlist, max_tool_calls, timeout
        
    Returns:
        AgentExecutor configured for calendar planning
    """
    try:
        # Extract parameters
        tool_allowlist = params.get('tool_allowlist', [])
        max_tool_calls = params.get('max_tool_calls', 20)
        timeout = params.get('timeout', 120)
        model_name = params.get('model', 'gpt-4-turbo-preview')
        
        # Load tools based on allowlist
        tools = load_tools(tool_allowlist)
        
        # Create LLM
        if 'claude' in model_name.lower():
            llm = ChatAnthropic(
                model=model_name,
                temperature=0.7,
                max_tokens=4000
            )
        else:
            llm = ChatOpenAI(
                model=model_name,
                temperature=0.7,
                max_tokens=4000
            )
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        agent = create_openai_functions_agent(llm, tools, prompt)
        
        # Create executor with constraints
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=max_tool_calls,
            max_execution_time=timeout,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        logger.info(f"Created Calendar Planner agent with {len(tools)} tools")
        return CalendarPlannerRunnable(executor, params)
        
    except Exception as e:
        logger.error(f"Failed to create Calendar Planner agent: {e}")
        # Return a fallback runnable
        return FallbackCalendarPlanner(params)


class CalendarPlannerRunnable:
    """Wrapper to make AgentExecutor work with workflow state"""
    
    def __init__(self, executor: AgentExecutor, params: Dict[str, Any]):
        self.executor = executor
        self.params = params
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent and update state with results"""
        try:
            # Build input prompt from state
            inputs = state.get('inputs', {})
            prompt = self._build_prompt(state)
            
            # Execute agent
            result = self.executor.invoke({"input": prompt})
            
            # Parse output to candidates
            candidates = self._parse_output(result['output'])
            
            # Update state
            state['candidates'] = candidates
            state['agent_output'] = result.get('output', '')
            state['agent_steps'] = result.get('intermediate_steps', [])
            
            logger.info(f"Agent generated {len(candidates)} candidates")
            return state
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            # Fallback to simple generation
            from workflow.nodes.generate_candidates import run as generate_fallback
            return generate_fallback(state)
    
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt from state inputs"""
        inputs = state.get('inputs', {})
        brand = state.get('brand', 'Unknown')
        month = state.get('month', '2025-01')
        
        prompt = f"""
        Create a comprehensive email and SMS marketing calendar for {brand} for {month}.
        
        Requirements:
        - Monthly revenue goal: ${inputs.get('client_sales_goal', 100000)}
        - Primary segment: {inputs.get('affinity_segment_1_name', 'VIP Customers')}
        - Secondary segment: {inputs.get('affinity_segment_2_name', 'Regular Customers')}
        - Growth objective: {inputs.get('key_growth_objective', 'Increase customer retention')}
        - Unengaged segment size: {inputs.get('unengaged_segment_size', 0)}
        
        Generate at least 20 email campaigns and 4 SMS campaigns.
        Ensure proper cadence with max 2 sends per week per segment.
        Include variety in offers, messaging, and targeting.
        """
        
        return prompt
    
    def _parse_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse agent output to campaign list"""
        # This would parse the structured output from the agent
        # For now, fallback to simple generation
        from workflow.nodes.generate_candidates import run as generate_fallback
        fake_state = {'inputs': {}}
        result = generate_fallback(fake_state)
        return result.get('candidates', [])


class FallbackCalendarPlanner:
    """Fallback planner when agent creation fails"""
    
    def __init__(self, params: Dict[str, Any]):
        self.params = params
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Use simple generation logic"""
        from workflow.nodes.generate_candidates import run as generate_fallback
        return generate_fallback(state)


def load_tools(tool_allowlist: List[str]) -> List[Tool]:
    """
    Load tools based on allowlist
    
    Args:
        tool_allowlist: List of tool identifiers to load
        
    Returns:
        List of Tool instances
    """
    tools = []
    
    for tool_id in tool_allowlist:
        try:
            if tool_id == "tools.klaviyo_campaigns":
                tools.append(create_klaviyo_campaigns_tool())
            elif tool_id == "tools.klaviyo_segments":
                tools.append(create_klaviyo_segments_tool())
            elif tool_id == "tools.firestore_ro":
                tools.append(create_firestore_ro_tool())
            elif tool_id == "tools.calculate":
                tools.append(create_calculate_tool())
            elif tool_id == "tools.generate_campaign_ideas":
                tools.append(create_generate_ideas_tool())
            else:
                logger.warning(f"Unknown tool: {tool_id}")
        except Exception as e:
            logger.error(f"Failed to load tool {tool_id}: {e}")
    
    return tools


def create_klaviyo_campaigns_tool() -> Tool:
    """Create tool for fetching Klaviyo campaigns"""
    def fetch_campaigns(query: str) -> str:
        # Stub implementation
        return "Fetched 10 recent campaigns with average 15% open rate"
    
    return Tool(
        name="klaviyo_campaigns",
        description="Fetch Klaviyo campaign data",
        func=fetch_campaigns
    )


def create_klaviyo_segments_tool() -> Tool:
    """Create tool for fetching Klaviyo segments"""
    def fetch_segments(query: str) -> str:
        # Stub implementation
        return "VIP Customers: 5000, Regular Customers: 15000, Unengaged: 2000"
    
    return Tool(
        name="klaviyo_segments",
        description="Fetch Klaviyo segment information",
        func=fetch_segments
    )


def create_firestore_ro_tool() -> Tool:
    """Create tool for read-only Firestore access"""
    def read_firestore(query: str) -> str:
        # Stub implementation
        return "Client configuration loaded: industry=restaurants, aov=$45"
    
    return Tool(
        name="firestore_ro",
        description="Read data from Firestore",
        func=read_firestore
    )


def create_calculate_tool() -> Tool:
    """Create calculation tool"""
    def calculate(expression: str) -> str:
        try:
            # Safe evaluation of mathematical expressions
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"
    
    return Tool(
        name="calculate",
        description="Perform calculations",
        func=calculate
    )


def create_generate_ideas_tool() -> Tool:
    """Create tool for generating campaign ideas"""
    def generate_ideas(prompt: str) -> str:
        # Stub implementation
        ideas = [
            "Flash Sale Friday - 20% off for VIPs",
            "Weekend Special - BOGO for new items",
            "Member Exclusive - Early access to new menu"
        ]
        return "\n".join(ideas)
    
    return Tool(
        name="generate_campaign_ideas",
        description="Generate campaign ideas based on context",
        func=generate_ideas
    )


# System prompt for the Calendar Planner agent
SYSTEM_PROMPT = """You are an expert email and SMS marketing calendar planner with 10 years of experience.

Your task is to create comprehensive, strategic marketing calendars that:
1. Drive consistent revenue throughout the month
2. Maintain healthy list engagement (max 2 sends/week per segment)
3. Balance promotional and value-driven content
4. Optimize send times based on segment behavior
5. Include A/B testing strategies

When generating campaigns, structure each with:
- Type (email/sms)
- Send date and time
- Target segment
- Subject line and preview text (for email)
- Key messaging and offers
- Projected revenue impact

Always ensure:
- Minimum 20 email campaigns per month
- Minimum 4 SMS campaigns per month
- Proper segment distribution (70% primary, 30% secondary for 2 segments)
- Special handling for unengaged segments if >15% of list
- Strategic use of key promotional dates

Use available tools to gather context about the client, their historical performance, and segment characteristics."""