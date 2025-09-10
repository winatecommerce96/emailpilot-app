"""
Workflow Template System
Provides reusable workflow templates that can be instantiated for any client
"""

from typing import Dict, Type, List
from .base import WorkflowTemplate

# Global workflow template registry
WORKFLOW_TEMPLATE_REGISTRY: Dict[str, Type[WorkflowTemplate]] = {}

def register_template(template_id: str, template_class: Type[WorkflowTemplate]):
    """Register a workflow template"""
    WORKFLOW_TEMPLATE_REGISTRY[template_id] = template_class
    
def get_template(template_id: str) -> Type[WorkflowTemplate]:
    """Get a workflow template by ID"""
    if template_id not in WORKFLOW_TEMPLATE_REGISTRY:
        raise ValueError(f"Template {template_id} not found")
    return WORKFLOW_TEMPLATE_REGISTRY[template_id]

def list_templates() -> List[Dict]:
    """List all available workflow templates"""
    templates = []
    for template_id, template_class in WORKFLOW_TEMPLATE_REGISTRY.items():
        instance = template_class()
        templates.append({
            "id": template_id,
            **instance.metadata
        })
    return templates

def instantiate_template(template_id: str, client_id: str, params: Dict = None):
    """Create a workflow instance from a template"""
    template_class = get_template(template_id)
    template = template_class()
    return template.instantiate(client_id, params or {})

# Import and register built-in templates
try:
    from .calendar_planner import CalendarPlannerTemplate
    register_template("calendar_planner", CalendarPlannerTemplate)
except ImportError:
    pass

try:
    from .revenue_goals import RevenueGoalsTemplate
    register_template("revenue_goals", RevenueGoalsTemplate)
except ImportError:
    pass

try:
    from .campaign_analyzer import CampaignAnalyzerTemplate
    register_template("campaign_analyzer", CampaignAnalyzerTemplate)
except ImportError:
    pass

__all__ = [
    "WorkflowTemplate",
    "register_template",
    "get_template",
    "list_templates",
    "instantiate_template",
    "WORKFLOW_TEMPLATE_REGISTRY"
]