"""
Router node for Calendar Workflow
Handles conditional routing logic
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Router node that determines next step based on state
    """
    tasks = state.get("tasks", [])
    completed = state.get("completed", False)
    error = state.get("error")
    
    # Log routing decision
    if error:
        logger.error(f"Router detected error: {error}")
        return {
            **state,
            "tasks": [],  # Clear tasks on error
            "completed": True
        }
    
    if completed:
        logger.info("Router: Workflow completed")
        return state
    
    # Check if current task is still being processed
    current_task = state.get("current_task")
    if current_task:
        logger.info(f"Router: Current task still in progress: {current_task.get('id')}")
        return state
    
    if tasks:
        logger.info(f"Router: {len(tasks)} tasks pending")
        # Pop the first task to process
        current_task = tasks[0] if tasks else None
        remaining_tasks = tasks[1:] if len(tasks) > 1 else []
        
        return {
            **state,
            "current_task": current_task,
            "tasks": remaining_tasks
        }
    
    logger.info("Router: No more tasks to process, marking complete")
    return {
        **state,
        "completed": True
    }