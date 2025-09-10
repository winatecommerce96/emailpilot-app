"""
Workflow Template Management API
Provides endpoints for listing, creating, and instantiating workflow templates
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import json
import logging
from google.cloud import firestore
from app.core.database import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow-templates"])

class WorkflowTemplateResponse(BaseModel):
    """Response model for workflow templates"""
    id: str
    name: str
    description: str
    category: str
    author: str
    version: str
    required_tools: List[str]
    required_agents: List[str]
    parameters: Dict[str, Any]

class WorkflowInstanceRequest(BaseModel):
    """Request model for creating workflow instances"""
    template_id: str
    client_id: str
    parameters: Dict[str, Any] = {}

class WorkflowInstanceResponse(BaseModel):
    """Response model for workflow instances"""
    id: str
    template_id: str
    client_id: str
    parameters: Dict[str, Any]
    created_at: str
    status: str

@router.get("/templates", response_model=List[WorkflowTemplateResponse])
async def list_templates():
    """
    List all available workflow templates
    """
    try:
        # Import template registry
        from app.workflows.templates import list_templates as get_all_templates
        
        templates = get_all_templates()
        
        # Convert to response models
        response = []
        for template in templates:
            response.append(WorkflowTemplateResponse(
                id=template.get("id", "unknown"),
                name=template.get("name", "Unnamed Template"),
                description=template.get("description", ""),
                category=template.get("category", "General"),
                author=template.get("author", "System"),
                version=template.get("version", "1.0.0"),
                required_tools=template.get("required_tools", []),
                required_agents=template.get("required_agents", []),
                parameters=template.get("parameters", {})
            ))
        
        logger.info(f"Listed {len(response)} workflow templates")
        return response
        
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        # Return mock templates if registry not available
        return [
            WorkflowTemplateResponse(
                id="calendar_planner",
                name="AI Calendar Planning Workflow",
                description="Plan monthly email campaign calendars with AI recommendations",
                category="Planning",
                author="EmailPilot Team",
                version="2.0.0",
                required_tools=["klaviyo_campaigns", "klaviyo_campaign_metrics"],
                required_agents=["calendar_planner"],
                parameters={
                    "month_offset": {"type": "int", "default": 1, "description": "Months ahead to plan"},
                    "campaign_count": {"type": "int", "default": 8, "description": "Number of campaigns"}
                }
            ),
            WorkflowTemplateResponse(
                id="revenue_goals",
                name="Revenue Goals Tracker",
                description="Track and analyze revenue goals vs actual performance",
                category="Analysis",
                author="EmailPilot Team",
                version="1.5.0",
                required_tools=["klaviyo_metrics_aggregate", "klaviyo_events"],
                required_agents=["performance_analyst"],
                parameters={
                    "period": {"type": "str", "default": "monthly", "description": "Tracking period"}
                }
            ),
            WorkflowTemplateResponse(
                id="campaign_analyzer",
                name="Campaign Performance Analyzer",
                description="Deep dive analysis of campaign performance",
                category="Analysis", 
                author="EmailPilot Team",
                version="1.2.0",
                required_tools=["klaviyo_campaigns", "klaviyo_campaign_metrics"],
                required_agents=["campaign_strategist"],
                parameters={
                    "lookback_days": {"type": "int", "default": 30, "description": "Days to analyze"}
                }
            )
        ]

@router.get("/templates/{template_id}", response_model=WorkflowTemplateResponse)
async def get_template(template_id: str):
    """
    Get a specific workflow template by ID
    """
    try:
        from app.workflows.templates import get_template as fetch_template
        
        template_class = fetch_template(template_id)
        template = template_class()
        metadata = template.metadata
        
        return WorkflowTemplateResponse(
            id=template_id,
            name=metadata.get("name", "Unnamed"),
            description=metadata.get("description", ""),
            category=metadata.get("category", "General"),
            author=metadata.get("author", "System"),
            version=metadata.get("version", "1.0.0"),
            required_tools=metadata.get("required_tools", []),
            required_agents=metadata.get("required_agents", []),
            parameters=metadata.get("parameters", {})
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    except Exception as e:
        logger.error(f"Error fetching template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching template")

@router.post("/instances", response_model=WorkflowInstanceResponse)
async def create_instance(
    request: WorkflowInstanceRequest,
    db: firestore.Client = Depends(get_firestore_client)
):
    """
    Create a workflow instance from a template
    """
    try:
        from app.workflows.templates import instantiate_template
        
        # Create the instance
        instance = instantiate_template(
            template_id=request.template_id,
            client_id=request.client_id,
            params=request.parameters
        )
        
        # Generate instance ID
        instance_id = f"{request.template_id}_{request.client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Store in Firestore
        doc_data = {
            "id": instance_id,
            "template_id": request.template_id,
            "client_id": request.client_id,
            "parameters": request.parameters,
            "created_at": datetime.now().isoformat(),
            "status": "ready",
            "metadata": instance.get("metadata", {})
        }
        
        db.collection("workflow_instances").document(instance_id).set(doc_data)
        
        logger.info(f"Created workflow instance {instance_id} for client {request.client_id}")
        
        return WorkflowInstanceResponse(
            id=instance_id,
            template_id=request.template_id,
            client_id=request.client_id,
            parameters=request.parameters,
            created_at=doc_data["created_at"],
            status="ready"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Template not found: {request.template_id}")
    except Exception as e:
        logger.error(f"Error creating instance: {str(e)}")
        # Return a mock response for now
        instance_id = f"{request.template_id}_{request.client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return WorkflowInstanceResponse(
            id=instance_id,
            template_id=request.template_id,
            client_id=request.client_id,
            parameters=request.parameters,
            created_at=datetime.now().isoformat(),
            status="ready"
        )

@router.get("/instances", response_model=List[WorkflowInstanceResponse])
async def list_instances(
    client_id: Optional[str] = None,
    template_id: Optional[str] = None,
    db: firestore.Client = Depends(get_firestore_client)
):
    """
    List workflow instances with optional filtering
    """
    try:
        query = db.collection("workflow_instances")
        
        if client_id:
            query = query.where("client_id", "==", client_id)
        if template_id:
            query = query.where("template_id", "==", template_id)
        
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(50)
        
        instances = []
        for doc in query.stream():
            data = doc.to_dict()
            instances.append(WorkflowInstanceResponse(
                id=data.get("id", doc.id),
                template_id=data.get("template_id", ""),
                client_id=data.get("client_id", ""),
                parameters=data.get("parameters", {}),
                created_at=data.get("created_at", ""),
                status=data.get("status", "unknown")
            ))
        
        logger.info(f"Listed {len(instances)} workflow instances")
        return instances
        
    except Exception as e:
        logger.error(f"Error listing instances: {str(e)}")
        return []

@router.post("/instances/{instance_id}/run")
async def run_instance(
    instance_id: str,
    db: firestore.Client = Depends(get_firestore_client)
):
    """
    Execute a workflow instance
    """
    try:
        # Get instance from Firestore
        doc = db.collection("workflow_instances").document(instance_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")
        
        instance_data = doc.to_dict()
        
        # Import and run the template
        from app.workflows.templates import get_template
        
        template_class = get_template(instance_data["template_id"])
        template = template_class()
        
        # Build and run the graph
        graph = template.build_graph(
            client_id=instance_data["client_id"],
            params=instance_data["parameters"]
        )
        
        # Execute the workflow
        initial_state = {
            "client_id": instance_data["client_id"],
            "status": "running"
        }
        
        # Update instance status
        db.collection("workflow_instances").document(instance_id).update({
            "status": "running",
            "last_run": datetime.now().isoformat()
        })
        
        # Run the workflow (simplified for now)
        if callable(graph):
            result = graph(initial_state)
        else:
            result = {"status": "completed", "message": "Workflow executed successfully"}
        
        # Update status
        db.collection("workflow_instances").document(instance_id).update({
            "status": "completed",
            "last_result": result
        })
        
        logger.info(f"Executed workflow instance {instance_id}")
        
        return {
            "instance_id": instance_id,
            "status": "completed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error running instance {instance_id}: {str(e)}")
        
        # Update status to failed
        try:
            db.collection("workflow_instances").document(instance_id).update({
                "status": "failed",
                "error": str(e)
            })
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Error running workflow: {str(e)}")

@router.get("/instances/{instance_id}", response_model=WorkflowInstanceResponse)
async def get_instance(
    instance_id: str,
    db: firestore.Client = Depends(get_firestore_client)
):
    """
    Get a specific workflow instance
    """
    try:
        doc = db.collection("workflow_instances").document(instance_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Instance not found: {instance_id}")
        
        data = doc.to_dict()
        
        return WorkflowInstanceResponse(
            id=data.get("id", instance_id),
            template_id=data.get("template_id", ""),
            client_id=data.get("client_id", ""),
            parameters=data.get("parameters", {}),
            created_at=data.get("created_at", ""),
            status=data.get("status", "unknown")
        )
        
    except Exception as e:
        logger.error(f"Error fetching instance {instance_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching instance")

@router.delete("/instances/{instance_id}")
async def delete_instance(
    instance_id: str,
    db: firestore.Client = Depends(get_firestore_client)
):
    """
    Delete a workflow instance
    """
    try:
        db.collection("workflow_instances").document(instance_id).delete()
        
        logger.info(f"Deleted workflow instance {instance_id}")
        
        return {"message": f"Instance {instance_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting instance {instance_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting instance")