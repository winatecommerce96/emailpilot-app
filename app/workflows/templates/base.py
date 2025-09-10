"""
Base class for workflow templates
Provides the foundation for creating reusable, client-agnostic workflows
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class WorkflowTemplate(ABC):
    """
    Abstract base class for workflow templates
    
    Templates are client-agnostic workflow definitions that can be
    instantiated for any client with appropriate parameters.
    """
    
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """
        Return workflow metadata
        
        Required fields:
        - name: Human-readable name
        - description: What this workflow does
        - category: Classification (Planning, Analysis, Automation, etc.)
        - author: Who created this template
        - version: Template version
        - required_tools: List of Enhanced MCP tools needed
        - required_agents: List of AI agents needed
        - parameters: Configurable parameters with defaults
        
        Example:
        return {
            "name": "Calendar Planning Workflow",
            "description": "AI-powered monthly campaign calendar planning",
            "category": "Planning",
            "author": "system",
            "version": "1.0.0",
            "required_tools": ["klaviyo_campaigns", "klaviyo_metrics_aggregate"],
            "required_agents": ["calendar_planner"],
            "parameters": {
                "month_offset": {"type": "int", "default": 1, "description": "Months ahead to plan"},
                "campaign_count": {"type": "int", "default": 8, "description": "Number of campaigns"}
            }
        }
        """
        pass
    
    @abstractmethod
    def build_graph(self, client_id: str, params: Dict[str, Any]) -> Any:
        """
        Build the workflow graph for a specific client
        
        Args:
            client_id: The Klaviyo client ID
            params: Runtime parameters for customization
            
        Returns:
            A LangGraph StateGraph or LangChain runnable
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and apply defaults to parameters
        
        Args:
            params: User-provided parameters
            
        Returns:
            Validated parameters with defaults applied
        """
        template_params = self.metadata.get("parameters", {})
        validated = {}
        
        for param_name, param_config in template_params.items():
            if param_name in params:
                # Validate type
                value = params[param_name]
                expected_type = param_config.get("type", "str")
                
                if expected_type == "int" and not isinstance(value, int):
                    try:
                        value = int(value)
                    except:
                        raise ValueError(f"Parameter {param_name} must be an integer")
                elif expected_type == "float" and not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except:
                        raise ValueError(f"Parameter {param_name} must be a number")
                elif expected_type == "bool" and not isinstance(value, bool):
                    value = str(value).lower() in ("true", "1", "yes")
                elif expected_type == "list" and not isinstance(value, list):
                    value = [value]
                    
                validated[param_name] = value
            else:
                # Use default
                validated[param_name] = param_config.get("default")
        
        # Include any extra params not in template
        for key, value in params.items():
            if key not in validated:
                validated[key] = value
        
        return validated
    
    def instantiate(self, client_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a workflow instance for a specific client
        
        Args:
            client_id: The Klaviyo client ID
            params: Optional parameters for customization
            
        Returns:
            Workflow instance configuration
        """
        # Validate parameters
        validated_params = self.validate_params(params or {})
        
        # Build the graph
        graph = self.build_graph(client_id, validated_params)
        
        # Create instance metadata
        instance = {
            "template_id": self.metadata.get("id", self.__class__.__name__),
            "template_version": self.metadata.get("version", "1.0.0"),
            "client_id": client_id,
            "parameters": validated_params,
            "created_at": datetime.now().isoformat(),
            "graph": graph,
            "metadata": self.metadata
        }
        
        logger.info(f"Created workflow instance for client {client_id} from template {self.metadata.get('name')}")
        
        return instance
    
    def get_required_resources(self) -> Dict[str, List[str]]:
        """
        Get list of required resources (tools, agents, etc.)
        
        Returns:
            Dictionary of resource types and their requirements
        """
        return {
            "tools": self.metadata.get("required_tools", []),
            "agents": self.metadata.get("required_agents", []),
            "models": self.metadata.get("required_models", ["gemini-1.5-flash"])
        }
    
    def to_code(self, client_id: str = "{{CLIENT_ID}}") -> str:
        """
        Generate Python code for this template
        
        Args:
            client_id: Client ID placeholder or actual ID
            
        Returns:
            Python code string
        """
        code = f'''# {self.metadata.get("name", "Workflow Template")}
# {self.metadata.get("description", "")}
# Version: {self.metadata.get("version", "1.0.0")}

from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any
from multi_agent.integrations.langchain_core.adapters.enhanced_mcp_adapter import get_enhanced_mcp_adapter

# Initialize Enhanced MCP
adapter = get_enhanced_mcp_adapter()

# Client ID (parameterized)
CLIENT_ID = "{client_id}"

# Build and run workflow
def run_workflow(client_id: str = CLIENT_ID, **params):
    """Execute the workflow for a specific client"""
    # Template implementation here
    pass
'''
        return code
    
    def to_json(self) -> str:
        """
        Serialize template metadata to JSON
        
        Returns:
            JSON string representation
        """
        return json.dumps({
            "class": self.__class__.__name__,
            "metadata": self.metadata,
            "resources": self.get_required_resources()
        }, indent=2)