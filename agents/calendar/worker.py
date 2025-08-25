"""
Worker node for Calendar Workflow
Executes individual tasks and appends artifacts
"""
from typing import Dict, Any, List
import logging
from datetime import datetime
from langchain_core.messages import AIMessage, ToolCall

logger = logging.getLogger(__name__)


def worker_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker node that executes one task at a time
    """
    current_task = state.get("current_task")
    artifacts = state.get("artifacts", [])
    
    if not current_task:
        logger.warning("Worker called without current task")
        return state
    
    logger.info(f"Worker processing task: {current_task.get('id')} - {current_task.get('type')}")
    
    # Process the task
    artifact = {
        "task_id": current_task.get("id"),
        "task_type": current_task.get("type"),
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    }
    
    # Check if task requires a tool
    if current_task.get("requires_tool"):
        tool_name = current_task.get("tool")
        logger.info(f"Task requires tool: {tool_name}")
        
        # Create AIMessage with tool call for LangGraph ToolNode
        messages = state.get("messages", [])
        
        # Create a proper tool call
        tool_call = ToolCall(
            name=tool_name,
            args={"brand": state.get("brand", ""), "month": state.get("month", "")},
            id=f"tool_{current_task.get('id')}"
        )
        
        # Create AIMessage with tool call
        ai_message = AIMessage(
            content=f"Calling tool {tool_name} for task {current_task.get('description')}",
            tool_calls=[tool_call]
        )
        
        # Add to messages for ToolNode to process
        messages.append(ai_message)
        
        # Mark for tool execution
        artifact["status"] = "requires_tool"
        artifact["tool"] = tool_name
        
        # Add artifact but keep task for tool processing
        artifacts.append(artifact)
        
        # Return state with updated messages for ToolNode
        return {
            **state,
            "messages": messages,
            "current_task": current_task,  # Keep task for tool to process
            "artifacts": artifacts
        }
    else:
        # Execute task directly (mock execution)
        logger.info(f"Executing task: {current_task.get('description')}")
        
        # Simulate task execution
        if current_task.get("type") == "optimize_timing":
            artifact["result"] = {
                "best_day": "Tuesday",
                "best_time": "10:00 AM",
                "timezone": "EST"
            }
        else:
            artifact["result"] = {
                "message": f"Completed: {current_task.get('description')}"
            }
        
        artifact["status"] = "completed"
    
    # Append artifact
    artifacts.append(artifact)
    
    # Clear current task if completed
    if artifact["status"] == "completed":
        current_task = None
    
    return {
        **state,
        "current_task": current_task,
        "artifacts": artifacts
    }