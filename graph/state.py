"""
State definitions for LangGraph Calendar Workflow
"""
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import add_messages


class CalendarState(TypedDict):
    """State for the calendar workflow with reducers"""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    tasks: List[Dict[str, Any]]
    current_task: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    brand: str
    month: str
    run_context: Dict[str, Any]
    error: str
    completed: bool