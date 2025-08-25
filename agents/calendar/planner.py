"""
Planner node for Calendar Workflow
Converts input into actionable tasks
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner node that converts input messages into tasks
    """
    messages = state.get("messages", [])
    tasks = state.get("tasks", [])
    
    # If we have messages but no tasks, create tasks
    if messages and not tasks:
        last_message = messages[-1]
        content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
        
        # Parse the message to create tasks
        new_tasks = []
        
        if "plan" in content.lower() or "campaign" in content.lower():
            new_tasks.append({
                "id": "task_1",
                "type": "analyze_metrics",
                "description": "Analyze current campaign metrics",
                "requires_tool": True,
                "tool": "analyze_metrics"
            })
            new_tasks.append({
                "id": "task_2", 
                "type": "generate_calendar",
                "description": "Generate campaign calendar",
                "requires_tool": True,
                "tool": "generate_calendar"
            })
            new_tasks.append({
                "id": "task_3",
                "type": "optimize_timing",
                "description": "Optimize send times",
                "requires_tool": False
            })
        else:
            # Default task for other requests
            new_tasks.append({
                "id": "task_default",
                "type": "process_request",
                "description": f"Process: {content[:100]}",
                "requires_tool": False
            })
        
        logger.info(f"Planner created {len(new_tasks)} tasks")
        
        return {
            **state,
            "tasks": new_tasks
        }
    
    # If tasks are being processed, check if we're done
    if not tasks and state.get("artifacts"):
        return {
            **state,
            "completed": True
        }
    
    return state