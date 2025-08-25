"""
Tool handler node for Calendar Workflow
Processes tool results and updates state
"""
from typing import Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def tool_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes tool results and clears current task
    """
    messages = state.get("messages", [])
    current_task = state.get("current_task")
    artifacts = state.get("artifacts", [])
    
    if not current_task:
        logger.warning("Tool handler called without current task")
        return state
    
    # Check if we have tool results in messages
    if messages and len(messages) > 0:
        # Get the last message which should be tool result
        last_message = messages[-1]
        
        logger.info(f"Processing tool result for task: {current_task.get('id')}")
        
        # Find the artifact for this task
        task_artifact = None
        for artifact in artifacts:
            if artifact.get("task_id") == current_task.get("id"):
                task_artifact = artifact
                break
        
        if task_artifact:
            # Update artifact with completion
            task_artifact["status"] = "completed"
            task_artifact["completed_at"] = datetime.now().isoformat()
            
            # Store tool result if available
            if hasattr(last_message, 'content'):
                task_artifact["result"] = last_message.content
            elif isinstance(last_message, dict):
                task_artifact["result"] = last_message
        
        logger.info(f"Task {current_task.get('id')} completed via tool")
    
    # Clear current task to allow router to pick next one
    return {
        **state,
        "current_task": None,  # Clear so router can pick next task
        "artifacts": artifacts
    }