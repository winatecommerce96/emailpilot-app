"""
EmailPilot Campaign Planning Graph
A LangGraph implementation for email campaign planning and optimization
"""

from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import json
from datetime import datetime, timedelta


# Define our state
class AgentState(MessagesState):
    """The state of our email campaign planning agent"""
    brand: str
    month: str
    campaigns: list
    analysis: str


# Define tools for the agent
@tool
def analyze_klaviyo_metrics(brand: str, month: str) -> str:
    """
    Analyze Klaviyo metrics for a brand and month.
    In production, this would connect to actual Klaviyo API.
    """
    # Mock data for demonstration
    return f"""
    Klaviyo Metrics Analysis for {brand} - {month}:
    - Email Open Rate: 24.5%
    - Click Rate: 3.2%
    - Revenue per Email: $1.45
    - Total Subscribers: 15,234
    - Active Segments: 8
    - Last Campaign: 3 days ago
    
    Recommendations:
    - Increase sending frequency for engaged segments
    - A/B test subject lines for better open rates
    - Focus on weekend sends for higher engagement
    """


@tool
def generate_campaign_calendar(brand: str, month: str, campaign_count: int = 4) -> str:
    """
    Generate a campaign calendar for the specified month.
    """
    # Parse month
    try:
        month_date = datetime.strptime(month, "%Y-%m")
    except:
        month_date = datetime.now()
    
    campaigns = []
    for i in range(campaign_count):
        campaign_date = month_date + timedelta(days=7 * i + 3)
        campaigns.append({
            "date": campaign_date.strftime("%Y-%m-%d"),
            "type": ["Newsletter", "Promotion", "Product Launch", "Seasonal"][i % 4],
            "subject": f"Campaign {i+1} for {brand}",
            "segment": ["VIP", "Active", "Win-back", "New"][i % 4]
        })
    
    return json.dumps(campaigns, indent=2)


@tool
def optimize_send_times(brand: str, timezone: str = "America/New_York") -> str:
    """
    Suggest optimal send times based on brand and timezone.
    """
    return f"""
    Optimal Send Times for {brand} ({timezone}):
    
    Best Days:
    - Tuesday: 10 AM (highest open rate)
    - Thursday: 2 PM (highest click rate)
    - Sunday: 7 PM (highest revenue)
    
    Avoid:
    - Monday mornings (low engagement)
    - Friday afternoons (competing with weekend plans)
    
    Recommendation: Test Tuesday 10 AM for next campaign
    """


# Create the tools node
tools = [analyze_klaviyo_metrics, generate_campaign_calendar, optimize_send_times]
tool_node = ToolNode(tools)


# Define the agent function
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Decide whether to continue or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If there are tool calls, execute them
    if last_message.tool_calls:
        return "tools"
    
    # Otherwise we're done
    return "end"


def call_model(state: AgentState):
    """Call the model to process the current state"""
    from langchain_openai import ChatOpenAI
    import os
    
    # Initialize the model
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder")
    ).bind_tools(tools)
    
    # Get messages from state
    messages = state["messages"]
    
    # If this is the first message, add context
    if len(messages) == 1:
        system_context = f"""
        You are an EmailPilot campaign planning assistant.
        Current context:
        - Brand: {state.get('brand', 'Unknown')}
        - Month: {state.get('month', datetime.now().strftime('%Y-%m'))}
        
        Help plan and optimize email campaigns using the available tools.
        """
        messages = [{"role": "system", "content": system_context}] + messages
    
    # Call the model
    response = model.invoke(messages)
    
    # Return the response
    return {"messages": [response]}


# Build the graph
def create_graph():
    """Create the EmailPilot campaign planning graph"""
    
    # Define the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    
    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")
    
    # Compile without custom checkpointer (handled by platform)
    graph = workflow.compile()
    
    return graph


# Create the graph instance
graph = create_graph()


# Example usage function (for testing)
def run_example():
    """Run an example campaign planning session"""
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content="Help me plan email campaigns for next month")],
        "brand": "Buca di Beppo",
        "month": "2025-02"
    }
    
    # Run the graph
    config = {"configurable": {"thread_id": "campaign_planning_001"}}
    
    for chunk in graph.stream(initial_state, config):
        for key, value in chunk.items():
            print(f"\n--- {key} ---")
            if "messages" in value:
                for msg in value["messages"]:
                    print(f"{msg.__class__.__name__}: {msg.content[:200] if hasattr(msg, 'content') else msg}")


if __name__ == "__main__":
    # Only run example if called directly
    print("EmailPilot Campaign Planning Graph loaded successfully!")
    print("Graph is ready to be served by LangGraph server.")