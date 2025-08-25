"""
Instrumentation for LangSmith tracing
"""
import os
from typing import Dict, Any, Optional
from functools import wraps
from langsmith import Client
from langsmith.run_helpers import traceable
import logging

logger = logging.getLogger(__name__)

# Initialize client if tracing enabled
ENABLE_TRACING = os.getenv("ENABLE_TRACING", "true").lower() == "true"
LANGSMITH_CLIENT = Client() if ENABLE_TRACING else None

def instrument_node(node_id: str, run_context: Dict[str, Any]):
    """Decorator to instrument workflow nodes"""
    def decorator(func):
        if not ENABLE_TRACING:
            return func
        
        @wraps(func)
        @traceable(
            run_type="chain",
            name=f"node_{node_id}",
            tags=[
                f"graph:{run_context.get('graph', 'unknown')}",
                f"node:{node_id}",
                f"brand:{run_context.get('brand', 'unknown')}",
                f"month:{run_context.get('month', 'unknown')}",
                f"env:{run_context.get('env', 'dev')}",
                f"run_id:{run_context.get('run_id', 'unknown')}"
            ]
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_trace_url(run_id: str) -> Optional[str]:
    """Get LangSmith trace URL for a run"""
    if not LANGSMITH_CLIENT:
        return None
    
    try:
        project = os.getenv("LANGSMITH_PROJECT", "default")
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://smith.langchain.com")
        return f"{endpoint}/projects/{project}/runs?query=run_id:{run_id}"
    except Exception as e:
        logger.error(f"Failed to get trace URL: {e}")
        return None

def create_langsmith_callback(run_context: Dict[str, Any]):
    """Create a LangSmith callback handler with context"""
    if not ENABLE_TRACING:
        return None
    
    try:
        from langsmith.callbacks import LangSmithCallbackHandler
        return LangSmithCallbackHandler(
            project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar"),
            tags={
                "graph": run_context.get('graph', 'unknown'),
                "brand": run_context.get('brand', 'unknown'),
                "month": run_context.get('month', 'unknown'),
                "env": run_context.get('env', 'dev'),
                "run_id": run_context.get('run_id', 'unknown')
            }
        )
    except Exception as e:
        logger.error(f"Failed to create LangSmith callback: {e}")
        return None

def instrument_workflow(workflow_name: str, run_context: Dict[str, Any]):
    """Instrument an entire workflow for tracing"""
    def decorator(func):
        if not ENABLE_TRACING:
            return func
        
        @wraps(func)
        @traceable(
            run_type="workflow",
            name=workflow_name,
            project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar"),
            tags=[
                f"workflow:{workflow_name}",
                f"brand:{run_context.get('brand', 'unknown')}",
                f"month:{run_context.get('month', 'unknown')}",
                f"env:{run_context.get('env', 'dev')}"
            ]
        )
        def wrapper(*args, **kwargs):
            logger.info(f"Starting workflow {workflow_name} with context: {run_context}")
            result = func(*args, **kwargs)
            trace_url = get_trace_url(run_context.get('run_id'))
            if trace_url:
                logger.info(f"Trace available at: {trace_url}")
            return result
        return wrapper
    return decorator
