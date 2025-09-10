"""
Calendar Workflow Agents API
Manages agents associated with the calendar workflow and other workflows
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from google.cloud import firestore

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "multi-agent"))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workflow-agents", tags=["workflow-agents"])

# Import all calendar workflow agents
try:
    from integrations.langchain_core.agents.brand_calendar_agent import BRAND_CALENDAR_AGENT
except ImportError:
    # Try alternative import path
    try:
        from multi_agent.integrations.langchain_core.agents.brand_calendar_agent import BRAND_CALENDAR_AGENT
    except ImportError:
        # Use default config if import fails
        BRAND_CALENDAR_AGENT = {
            "name": "brand_calendar",
            "description": "Brand specialist that retrieves client-specific brand events, affinity segments, and style preferences",
            "prompt_template": "You are a Brand Calendar Specialist...",
            "variables": [],
            "policy": {"allowed_tools": ["firestore_ro", "firestore_rw", "calculate"], "max_tool_calls": 8, "timeout_seconds": 30}
        }
# Import other agents with fallback
def safe_import_agent(module_name, agent_name, default_config):
    try:
        module = __import__(f"integrations.langchain_core.agents.{module_name}", fromlist=[agent_name])
        return getattr(module, agent_name)
    except ImportError:
        try:
            module = __import__(f"multi_agent.integrations.langchain_core.agents.{module_name}", fromlist=[agent_name])
            return getattr(module, agent_name)
        except ImportError:
            return default_config

HISTORICAL_ANALYST_AGENT = safe_import_agent(
    "historical_analyst", "HISTORICAL_ANALYST_AGENT",
    {"name": "historical_analyst", "description": "Analyzes historical campaign performance", "prompt_template": "", "variables": [], "policy": {}}
)

SEGMENT_STRATEGIST_AGENT = safe_import_agent(
    "segment_strategist", "SEGMENT_STRATEGIST_AGENT",  
    {"name": "segment_strategist", "description": "Customer segmentation strategy", "prompt_template": "", "variables": [], "policy": {}}
)

CONTENT_OPTIMIZER_AGENT = safe_import_agent(
    "content_optimizer", "CONTENT_OPTIMIZER_AGENT",
    {"name": "content_optimizer", "description": "Optimizes email content", "prompt_template": "", "variables": [], "policy": {}}
)

CALENDAR_ORCHESTRATOR_AGENT = safe_import_agent(
    "calendar_orchestrator", "CALENDAR_ORCHESTRATOR_AGENT",
    {"name": "calendar_orchestrator", "description": "Orchestrates calendar planning", "prompt_template": "", "variables": [], "policy": {}}
)

# Import the agent registry to get other workflow agents
from integrations.langchain_core.admin.registry import AgentRegistry

# Define workflow metadata
WORKFLOWS = {
    "calendar_workflow": {
        "name": "Calendar Planning Workflow",
        "description": "Multi-agent workflow for AI-powered campaign calendar creation",
        "icon": "📅",
        "color": "#8A6CF7",
        "agents": [
            "mcp_preflight",
            "brand_calendar",
            "historical_analyst",
            "segment_strategist",
            "content_optimizer",
            "calendar_orchestrator"
        ],
        "langgraph_enabled": True,
        "trace_url": "https://smith.langchain.com/studio/",
        "status": "active",
        "created_at": "2025-08-27",
        "version": "2.0",
        "category": "Marketing",
        "execution_time": "~45 seconds",
        "complexity": "high"
    },
    "email_campaign_workflow": {
        "name": "Email Campaign Generator",
        "description": "End-to-end email campaign creation with subject lines, content, and scheduling",
        "icon": "✉️",
        "color": "#10B981",
        "agents": [
            "audience_architect",
            "copy_smith",
            "layout_lab",
            "gatekeeper"
        ],
        "langgraph_enabled": True,
        "trace_url": "https://smith.langchain.com/studio/",
        "status": "active",
        "created_at": "2025-08-20",
        "version": "1.5",
        "category": "Marketing",
        "execution_time": "~30 seconds",
        "complexity": "medium"
    },
    "revenue_analysis_workflow": {
        "name": "Revenue Performance Analyzer",
        "description": "Deep dive into revenue metrics and performance optimization",
        "icon": "💰",
        "color": "#F59E0B",
        "agents": [
            "truth_teller",
            "revenue_analyst"
        ],
        "langgraph_enabled": False,
        "trace_url": "",
        "status": "active",
        "created_at": "2025-08-15",
        "version": "1.0",
        "category": "Analytics",
        "execution_time": "~20 seconds",
        "complexity": "low"
    }
}

# Agent registry with workflow associations
AGENT_REGISTRY = {
    "mcp_preflight": {
        "config": {
            "name": "mcp_preflight",
            "description": "MCP Data Connection - Creates LangChain tools from Enhanced Klaviyo MCP and pre-fetches data for all agents",
            "prompt_template": "Initializing MCP adapter, creating tools, and pre-fetching Klaviyo data for workflow agents",
            "variables": ["client_id", "use_real_data"],
            "policy": {"allowed_tools": ["enhanced_mcp_adapter"], "max_tool_calls": 10, "timeout_seconds": 30},
            "mcp_tools_created": ["segments.list", "campaigns.list", "flows.list", "lists.list", "metrics.aggregate", "reporting.revenue"]
        },
        "workflow": "calendar_workflow",
        "order": 0,
        "role": "MCP Tool Provider",
        "dependencies": [],
        "mcp_requirements": ["health_check", "tool_creation", "data_prefetch"]
    },
    "brand_calendar": {
        "config": BRAND_CALENDAR_AGENT,
        "workflow": "calendar_workflow",
        "order": 1,
        "role": "Brand Data Analysis",
        "dependencies": ["mcp_preflight"],
        "mcp_requirements": [],
        "mcp_tools_used": ["segments.list", "lists.list", "campaigns.list"],
        "data_sources": ["klaviyo_segments", "klaviyo_lists", "klaviyo_campaigns"]
    },
    "historical_analyst": {
        "config": HISTORICAL_ANALYST_AGENT,
        "workflow": "calendar_workflow",
        "order": 2,
        "role": "Performance Analysis",
        "dependencies": ["mcp_preflight", "brand_calendar"],
        "mcp_requirements": [],
        "mcp_tools_used": ["campaigns.get_metrics", "reporting.revenue"],
        "data_sources": ["klaviyo_campaigns", "klaviyo_flows"]
    },
    "segment_strategist": {
        "config": SEGMENT_STRATEGIST_AGENT,
        "workflow": "calendar_workflow",
        "order": 3,
        "role": "Audience Segmentation",
        "dependencies": ["mcp_preflight", "brand_calendar", "historical_analyst"],
        "mcp_requirements": ["segments.get", "segments.get_profiles", "lists.get_profiles"]
    },
    "content_optimizer": {
        "config": CONTENT_OPTIMIZER_AGENT,
        "workflow": "calendar_workflow",
        "order": 4,
        "role": "Content Generation",
        "dependencies": ["mcp_preflight", "brand_calendar", "segment_strategist"],
        "mcp_requirements": ["templates.list", "campaigns.list"]
    },
    "calendar_orchestrator": {
        "config": CALENDAR_ORCHESTRATOR_AGENT,
        "workflow": "calendar_workflow",
        "order": 5,
        "role": "Final Calendar Assembly",
        "dependencies": ["mcp_preflight", "brand_calendar", "historical_analyst", "segment_strategist", "content_optimizer"],
        "mcp_requirements": []
    },
    # Email Campaign Workflow Agents - will be loaded from registry
    "audience_architect": {
        "config": None,  # Will be loaded dynamically
        "workflow": "email_campaign_workflow",
        "order": 1,
        "role": "Audience Definition",
        "dependencies": []
    },
    "copy_smith": {
        "config": None,  # Will be loaded dynamically
        "workflow": "email_campaign_workflow",
        "order": 2,
        "role": "Copy Creation",
        "dependencies": ["audience_architect"]
    },
    "layout_lab": {
        "config": None,  # Will be loaded dynamically
        "workflow": "email_campaign_workflow",
        "order": 3,
        "role": "Layout Design",
        "dependencies": ["copy_smith"]
    },
    "gatekeeper": {
        "config": None,  # Will be loaded dynamically
        "workflow": "email_campaign_workflow",
        "order": 4,
        "role": "Quality Assurance",
        "dependencies": ["copy_smith", "layout_lab"]
    },
    # Revenue Analysis Workflow Agents - will be loaded from registry
    "truth_teller": {
        "config": None,  # Will be loaded dynamically
        "workflow": "revenue_analysis_workflow",
        "order": 1,
        "role": "Data Analysis",
        "dependencies": []
    },
    "revenue_analyst": {
        "config": None,  # Will be loaded dynamically
        "workflow": "revenue_analysis_workflow",
        "order": 2,
        "role": "Revenue Optimization",
        "dependencies": ["truth_teller"]
    }
}

def get_db():
    """Get Firestore client"""
    return firestore.Client()

def get_agent_config(agent_name: str):
    """Get agent configuration from registry or defaults"""
    # Initialize registry
    registry = AgentRegistry()
    
    # Try to get from registry first
    agent = registry.get_agent(agent_name)
    if agent:
        return agent
    
    # Fallback to hardcoded configs for calendar agents
    if agent_name in AGENT_REGISTRY:
        return AGENT_REGISTRY[agent_name]["config"]
    
    # Default config if not found
    return {
        "name": agent_name,
        "description": f"Agent: {agent_name}",
        "prompt_template": f"You are the {agent_name} agent."
    }

class WorkflowAgentRequest(BaseModel):
    """Request model for workflow agent operations"""
    workflow_name: str = Field(..., description="Name of the workflow")
    agent_name: Optional[str] = Field(None, description="Specific agent name")

class WorkflowAgentResponse(BaseModel):
    """Response model for workflow agents"""
    success: bool
    workflow: Optional[Dict[str, Any]]
    agents: List[Dict[str, Any]]
    message: str

class AgentUpdateRequest(BaseModel):
    """Request to update an agent's prompt or configuration"""
    prompt_template: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[List[Dict[str, Any]]] = None
    policy: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    max_tool_calls: Optional[int] = None
    timeout_seconds: Optional[int] = None

@router.get("/workflows")
async def list_workflows():
    """List all available workflows with their metadata"""
    workflows = []
    for workflow_id, workflow_data in WORKFLOWS.items():
        workflow_info = workflow_data.copy()
        workflow_info["id"] = workflow_id
        workflow_info["agent_count"] = len(workflow_data["agents"])
        workflows.append(workflow_info)
    
    return {
        "success": True,
        "workflows": workflows,
        "total": len(workflows)
    }

@router.get("/workflow/{workflow_name}")
async def get_workflow_agents(workflow_name: str):
    """Get all agents associated with a specific workflow"""
    if workflow_name not in WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    
    workflow = WORKFLOWS[workflow_name]
    agents = []
    
    for agent_name in workflow["agents"]:
        if agent_name in AGENT_REGISTRY:
            agent_data = AGENT_REGISTRY[agent_name]
            
            # Get agent config dynamically
            config = agent_data["config"]
            if config is None:
                config = get_agent_config(agent_name)
            
            agent_info = {
                "name": agent_name,
                "description": config.get("description", ""),
                "role": agent_data["role"],
                "order": agent_data["order"],
                "prompt_template": config.get("prompt_template", ""),
                "variables": config.get("variables", []),
                "policy": config.get("policy", {}),
                "dependencies": agent_data["dependencies"],
                "mcp_requirements": agent_data.get("mcp_requirements", []),
                "mcp_tools_used": agent_data.get("mcp_tools_used", []),
                "data_sources": agent_data.get("data_sources", []),
                "mcp_tools_created": config.get("mcp_tools_created", []),
                "workflow": agent_data["workflow"],
                "status": config.get("status", "active")
            }
            agents.append(agent_info)
    
    # Sort by execution order
    agents.sort(key=lambda x: x["order"])
    
    return WorkflowAgentResponse(
        success=True,
        workflow=workflow,
        agents=agents,
        message=f"Retrieved {len(agents)} agents for workflow '{workflow_name}'"
    )

@router.get("/agent/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed information about a specific agent"""
    if agent_name not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    agent_data = AGENT_REGISTRY[agent_name]
    workflow = WORKFLOWS.get(agent_data["workflow"], {})
    
    # Get config dynamically
    config = agent_data["config"]
    if config is None:
        config = get_agent_config(agent_name)
    
    return {
        "success": True,
        "agent": {
            "name": agent_name,
            "config": config,
            "workflow": {
                "id": agent_data["workflow"],
                "name": workflow.get("name", "Unknown"),
                "icon": workflow.get("icon", "🤖")
            },
            "role": agent_data["role"],
            "order": agent_data["order"],
            "dependencies": agent_data["dependencies"]
        }
    }

@router.get("/workflow/{workflow_name}/execution-graph")
async def get_workflow_execution_graph(workflow_name: str):
    """Get workflow execution graph with agent dependencies and order"""
    if workflow_name not in WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    
    workflow = WORKFLOWS[workflow_name]
    agents = []
    connections = []
    
    # Build agent nodes and connections
    for agent_name in workflow["agents"]:
        if agent_name in AGENT_REGISTRY:
            agent_data = AGENT_REGISTRY[agent_name]
            
            # Get config dynamically
            config = agent_data["config"]
            if config is None:
                config = get_agent_config(agent_name)
            
            # Create agent node
            node = {
                "id": agent_name,
                "name": agent_name.replace("_", " ").title(),
                "role": agent_data["role"],
                "order": agent_data["order"],
                "description": config.get("description", ""),
                "dependencies": agent_data["dependencies"],
                "status": config.get("status", "ready"),
                "execution_time": f"~{agent_data['order'] * 5} seconds"  # Estimate
            }
            agents.append(node)
            
            # Create connections from dependencies
            for dep in agent_data["dependencies"]:
                connections.append({
                    "from": dep,
                    "to": agent_name,
                    "type": "dependency"
                })
    
    # Sort agents by execution order
    agents.sort(key=lambda x: x["order"])
    
    return {
        "success": True,
        "workflow": {
            "id": workflow_name,
            "name": workflow["name"],
            "description": workflow["description"],
            "icon": workflow["icon"],
            "color": workflow["color"],
            "category": workflow.get("category", "General"),
            "complexity": workflow.get("complexity", "medium"),
            "execution_time": workflow.get("execution_time", "~30 seconds")
        },
        "agents": agents,
        "connections": connections,
        "stats": {
            "total_agents": len(agents),
            "total_connections": len(connections),
            "max_depth": max([a["order"] for a in agents]) if agents else 0
        }
    }

@router.post("/agent/{agent_name}/update")
async def update_agent(agent_name: str, request: AgentUpdateRequest, db=Depends(get_db)):
    """Update an agent's configuration"""
    if agent_name not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    try:
        # Get current agent data
        agent_data = AGENT_REGISTRY[agent_name]
        
        # Get current config (dynamically if needed)
        config = agent_data["config"]
        if config is None:
            config = get_agent_config(agent_name)
            
        # Update config with new values
        if request.prompt_template:
            config["prompt_template"] = request.prompt_template
        if request.description:
            config["description"] = request.description
        if request.variables:
            config["variables"] = request.variables
        if request.policy:
            config["policy"] = request.policy
        
        # Handle individual policy fields (for frontend compatibility)
        if request.tools is not None or request.max_tool_calls is not None or request.timeout_seconds is not None:
            if "policy" not in config:
                config["policy"] = {}
            if request.tools is not None:
                config["policy"]["allowed_tools"] = request.tools
            if request.max_tool_calls is not None:
                config["policy"]["max_tool_calls"] = request.max_tool_calls
            if request.timeout_seconds is not None:
                config["policy"]["timeout_seconds"] = request.timeout_seconds
        
        # Update the in-memory registry if it was a hardcoded agent
        if agent_data["config"] is not None:
            agent_data["config"] = config
        
        # Save to Firestore (for all agents, including dynamic ones)
        doc_ref = db.collection("workflow_agents").document(agent_name)
        doc_ref.set({
            "name": agent_name,
            "config": config,
            "workflow": agent_data["workflow"],
            "role": agent_data["role"],
            "order": agent_data["order"],
            "dependencies": agent_data["dependencies"],
            "updated_at": datetime.now(),
            "updated_by": "workflow_manager_ui"
        })
        
        logger.info(f"Updated agent '{agent_name}'")
        
        return {
            "success": True,
            "message": f"Agent '{agent_name}' updated successfully",
            "agent": config
        }
        
    except Exception as e:
        logger.error(f"Failed to update agent '{agent_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/register-all")
async def register_all_workflow_agents(db=Depends(get_db)):
    """Register all workflow agents to Firestore"""
    registered = []
    failed = []
    
    for agent_name, agent_data in AGENT_REGISTRY.items():
        try:
            doc_ref = db.collection("workflow_agents").document(agent_name)
            doc_ref.set({
                "name": agent_name,
                "config": agent_data["config"],
                "workflow": agent_data["workflow"],
                "role": agent_data["role"],
                "order": agent_data["order"],
                "dependencies": agent_data["dependencies"],
                "created_at": datetime.now(),
                "source": "calendar_workflow_agents.py"
            })
            registered.append(agent_name)
            logger.info(f"Registered agent: {agent_name}")
        except Exception as e:
            failed.append({"agent": agent_name, "error": str(e)})
            logger.error(f"Failed to register {agent_name}: {e}")
    
    return {
        "success": len(failed) == 0,
        "registered": registered,
        "failed": failed,
        "message": f"Registered {len(registered)} agents, {len(failed)} failed"
    }

@router.get("/all-agents")
async def get_all_agents(workflow_filter: Optional[str] = None):
    """Get all agents across all workflows"""
    agents = []
    
    for agent_name, agent_data in AGENT_REGISTRY.items():
        # Apply workflow filter if provided
        if workflow_filter and agent_data["workflow"] != workflow_filter:
            continue
        
        workflow = WORKFLOWS.get(agent_data["workflow"], {})
        
        agent_info = {
            "name": agent_name,
            "description": agent_data["config"].get("description", ""),
            "workflow": {
                "id": agent_data["workflow"],
                "name": workflow.get("name", "Unknown"),
                "icon": workflow.get("icon", "🤖"),
                "color": workflow.get("color", "#666")
            },
            "role": agent_data["role"],
            "order": agent_data["order"],
            "status": agent_data["config"].get("status", "active")
        }
        agents.append(agent_info)
    
    # Sort by workflow and order
    agents.sort(key=lambda x: (x["workflow"]["name"], x["order"]))
    
    return {
        "success": True,
        "agents": agents,
        "total": len(agents),
        "workflows": list(WORKFLOWS.keys())
    }

@router.post("/create-workflow")
async def create_workflow(workflow_config: Dict[str, Any], db=Depends(get_db)):
    """Create a new workflow and register it"""
    try:
        workflow_id = workflow_config.get("id") or workflow_config.get("name", "").lower().replace(" ", "_")
        
        # Add to in-memory registry
        WORKFLOWS[workflow_id] = {
            "name": workflow_config.get("name", "New Workflow"),
            "description": workflow_config.get("description", ""),
            "icon": workflow_config.get("icon", "🔄"),
            "color": workflow_config.get("color", "#666"),
            "agents": workflow_config.get("agents", []),
            "langgraph_enabled": workflow_config.get("langgraph_enabled", True),
            "trace_url": workflow_config.get("trace_url", "https://smith.langchain.com/studio/"),
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        # Save to Firestore
        doc_ref = db.collection("workflows").document(workflow_id)
        doc_ref.set(WORKFLOWS[workflow_id])
        
        logger.info(f"Created workflow: {workflow_id}")
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": f"Workflow '{workflow_config.get('name')}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/{workflow_id}/reorder")
async def reorder_workflow_agents(workflow_id: str, reorder_data: Dict[str, Any], db=Depends(get_db)):
    """Reorder agents in a workflow"""
    try:
        if workflow_id not in WORKFLOWS:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        workflow = WORKFLOWS[workflow_id]
        agents = workflow.get("agents", [])
        
        old_index = reorder_data.get("old_index")
        new_index = reorder_data.get("new_index")
        
        if old_index is None or new_index is None:
            raise HTTPException(status_code=400, detail="Both old_index and new_index are required")
        
        if old_index < 0 or old_index >= len(agents):
            raise HTTPException(status_code=400, detail="Invalid old_index")
        
        if new_index < 0 or new_index >= len(agents):
            raise HTTPException(status_code=400, detail="Invalid new_index")
        
        # Reorder the agents
        agent = agents.pop(old_index)
        agents.insert(new_index, agent)
        
        # Update workflow
        workflow["agents"] = agents
        WORKFLOWS[workflow_id] = workflow
        
        # Save to Firestore
        doc_ref = db.collection("workflows").document(workflow_id)
        doc_ref.update({"agents": agents})
        
        logger.info(f"Reordered agents in workflow {workflow_id}: moved from {old_index} to {new_index}")
        
        return {
            "success": True,
            "message": f"Agent order updated successfully",
            "agents": agents
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reorder agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/langgraph-status/{workflow_name}")
async def get_langgraph_status(workflow_name: str):
    """Get LangGraph tracing status for a workflow"""
    if workflow_name not in WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    
    workflow = WORKFLOWS[workflow_name]
    
    # Check if LangGraph is enabled
    if not workflow.get("langgraph_enabled", False):
        return {
            "enabled": False,
            "message": "LangGraph tracing is not enabled for this workflow"
        }
    
    # Return tracing information
    return {
        "enabled": True,
        "workflow": workflow_name,
        "trace_url": workflow.get("trace_url", "https://smith.langchain.com/studio/"),
        "message": "LangGraph tracing is active. Visit the trace URL to monitor execution.",
        "instructions": [
            "1. Open LangGraph Studio in your browser",
            "2. Select the 'calendar_workflow' graph",
            "3. Watch real-time execution when 'Generate with AI' is clicked",
            "4. View agent outputs, state transitions, and performance metrics"
        ]
    }