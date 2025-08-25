"""
Main graph definition for Calendar Workflow
"""
import os
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from graph.state import CalendarState
from agents.calendar.planner import planner_node
from agents.calendar.router import router_node
from agents.calendar.worker import worker_node
from agents.calendar.tool_handler import tool_handler_node
from tools.calendar_tools import get_calendar_tools

# Create var directory if it doesn't exist
os.makedirs("var", exist_ok=True)

# Initialize memory checkpointer (SQLite requires langgraph[checkpoint-sqlite])
checkpointer = MemorySaver()

# Check if MCP is available
def get_tools_with_mcp_fallback():
    """Get tools with MCP enhancement if available"""
    try:
        from mcp_tools.calendar_mcp import get_mcp_calendar_tools
        tools = get_mcp_calendar_tools()
        print("✓ MCP tools loaded")
        return tools
    except ImportError:
        print("⚠ MCP not available, using base tools")
        return get_calendar_tools()

# Build the graph
def create_calendar_graph():
    """Create the calendar workflow graph"""
    
    # Initialize the graph
    graph = StateGraph(CalendarState)
    
    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("router", router_node)
    graph.add_node("worker", worker_node)
    graph.add_node("tool_handler", tool_handler_node)
    
    # Create tools node with MCP enhancement
    tools = get_tools_with_mcp_fallback()
    tool_node = ToolNode(tools)
    graph.add_node("tools", tool_node)
    
    # Set entry point
    graph.set_entry_point("planner")
    
    # Add edges
    graph.add_edge("planner", "router")
    
    # Conditional routing from router
    def router_condition(state):
        if state.get("completed"):
            return "end"
        if state.get("current_task") or state.get("tasks"):
            return "worker"
        return "end"
    
    graph.add_conditional_edges(
        "router",
        router_condition,
        {
            "worker": "worker",
            "end": END
        }
    )
    
    # Worker can call tools or go back to router
    graph.add_conditional_edges(
        "worker",
        lambda state: "tools" if state.get("current_task", {}).get("requires_tool") else "router",
        {
            "tools": "tools",
            "router": "router"
        }
    )
    
    # Tools go to handler which clears task, then back to router
    graph.add_edge("tools", "tool_handler")
    graph.add_edge("tool_handler", "router")
    
    # Compile without checkpointer for LangGraph Studio
    # Studio provides its own persistence
    return graph.compile()

# Create the compiled graph
calendar_graph = create_calendar_graph()