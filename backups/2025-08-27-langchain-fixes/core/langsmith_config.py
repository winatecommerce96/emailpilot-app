"""
LangSmith Tracing Configuration for EmailPilot

This module configures LangSmith tracing for all LangChain operations,
providing observability into agent executions and calendar operations.
"""

import os
import logging
from typing import Optional, Dict, Any
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


def setup_langsmith_tracing(project_name: str = "emailpilot-calendar") -> Dict[str, Any]:
    """
    Configure LangSmith tracing for the EmailPilot application.
    
    Args:
        project_name: The LangSmith project name for tracing
    
    Returns:
        Dictionary with tracing configuration status
    """
    status = {
        "enabled": False,
        "project": None,
        "endpoint": None,
        "error": None
    }
    
    try:
        # First check if we're using Secret Manager
        use_secret_manager = os.getenv("USE_SECRET_MANAGER", "false").lower() == "true"
        
        if use_secret_manager:
            # Try to get API key from Secret Manager
            try:
                client = secretmanager.SecretManagerServiceClient()
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
                
                # Get LangSmith API key
                secret_name = os.getenv("LANGSMITH_SECRET_NAME", "langsmith-api-key")
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                
                response = client.access_secret_version(request={"name": name})
                api_key = response.payload.data.decode("UTF-8")
                
                if api_key:
                    os.environ["LANGSMITH_API_KEY"] = api_key
                    logger.info("✅ LangSmith API key loaded from Secret Manager")
                
                # Get project name from Secret Manager (optional)
                project_secret = os.getenv("LANGSMITH_PROJECT_SECRET", "langsmith-project-name")
                project_name_secret = f"projects/{project_id}/secrets/{project_secret}/versions/latest"
                
                try:
                    project_response = client.access_secret_version(request={"name": project_name_secret})
                    custom_project = project_response.payload.data.decode("UTF-8")
                    if custom_project:
                        project_name = custom_project
                        logger.info(f"✅ LangSmith project name loaded: {project_name}")
                except Exception:
                    # Use default project name if secret doesn't exist
                    pass
                    
            except Exception as e:
                logger.warning(f"Could not load LangSmith config from Secret Manager: {e}")
                # Fall back to environment variables
        
        # Check if API key is available
        api_key = os.getenv("LANGSMITH_API_KEY")
        
        if not api_key:
            # Try alternative env var names
            api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_KEY")
        
        if api_key:
            # Set up LangSmith environment variables
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = project_name
            os.environ["LANGSMITH_API_KEY"] = api_key
            
            # Optional: Set endpoint if using self-hosted LangSmith
            endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
            os.environ["LANGCHAIN_ENDPOINT"] = endpoint
            
            status.update({
                "enabled": True,
                "project": project_name,
                "endpoint": endpoint
            })
            
            logger.info(f"✅ LangSmith tracing enabled for project: {project_name}")
            logger.info(f"   View traces at: https://smith.langchain.com/o/{get_org_id()}/projects/p/{project_name}")
            
        else:
            status["error"] = "No LangSmith API key found"
            logger.info("⚠️ LangSmith tracing disabled - No API key configured")
            logger.info("   To enable, set LANGSMITH_API_KEY in .env or Secret Manager")
            
    except Exception as e:
        status["error"] = str(e)
        logger.error(f"Error setting up LangSmith tracing: {e}")
    
    return status


def get_org_id() -> str:
    """Get the LangSmith organization ID from environment or use default."""
    # This would typically come from your LangSmith account
    # Default to a placeholder that users can replace
    return os.getenv("LANGSMITH_ORG_ID", "your-org")


def create_traced_chain(chain, name: str = None, metadata: Dict[str, Any] = None):
    """
    Wrap a LangChain chain with tracing metadata.
    
    Args:
        chain: The LangChain chain to trace
        name: Optional name for the traced operation
        metadata: Optional metadata to include in traces
    
    Returns:
        The chain with tracing configured
    """
    if os.getenv("LANGCHAIN_TRACING_V2") == "true":
        # Add metadata to the chain if tracing is enabled
        if hasattr(chain, "with_config"):
            config = {
                "run_name": name or "EmailPilot Operation",
                "tags": ["emailpilot", "calendar"],
                "metadata": metadata or {}
            }
            return chain.with_config(config)
    
    return chain


def trace_calendar_operation(operation_type: str, client_name: str = None, **kwargs):
    """
    Create a trace context for calendar operations.
    
    Args:
        operation_type: Type of calendar operation (e.g., "create", "analyze", "optimize")
        client_name: Optional client name for the operation
        **kwargs: Additional metadata to include in the trace
    
    Returns:
        Context manager for the traced operation
    """
    from langsmith import traceable
    
    @traceable(
        name=f"Calendar-{operation_type}",
        tags=["calendar", operation_type],
        metadata={
            "client": client_name,
            "operation": operation_type,
            **kwargs
        }
    )
    def traced_operation(func):
        return func
    
    return traced_operation


# Initialize tracing when module is imported
if __name__ != "__main__":
    setup_status = setup_langsmith_tracing()
    if setup_status["enabled"]:
        logger.info("🔍 LangSmith tracing is active")