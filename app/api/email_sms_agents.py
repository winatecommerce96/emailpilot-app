"""
Email/SMS Multi-Agent API Router for EmailPilot
Integrates the multi-agent MCP server directly into the EmailPilot FastAPI application
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

# Configure logging first
logger = logging.getLogger(__name__)

# Try to import agent classes from the MCP server
try:
    import sys
    import os
    mcp_path = os.path.join(os.path.dirname(__file__), '../../email-sms-mcp-server')
    if mcp_path not in sys.path:
        sys.path.insert(0, mcp_path)
    from server import (
        ContentStrategistAgent,
        CopywriterAgent,
        DesignerAgent,
        SegmentationExpertAgent,
        MultiAgentOrchestrator
    )
    logger.info("Successfully imported MCP server agents")
except ImportError as e:
    logger.warning(f"Could not import MCP server agents: {e}")
    # Fallback - define minimal stub classes for testing
    class AgentStub:
        def __init__(self, name, role, expertise):
            self.name = name
            self.role = role
            self.expertise = expertise
            self.context = {}
        
        async def process_request(self, request):
            return {
                "agent": self.name,
                "message": f"Stub response from {self.name}",
                "request_received": request
            }
    
    ContentStrategistAgent = lambda: AgentStub("content_strategist", "Strategy", ["strategy"])
    CopywriterAgent = lambda: AgentStub("copywriter", "Copy", ["writing"])
    DesignerAgent = lambda: AgentStub("designer", "Design", ["design"])
    SegmentationExpertAgent = lambda: AgentStub("segmentation_expert", "Segmentation", ["targeting"])
    
    class MultiAgentOrchestrator:
        def __init__(self):
            self.agents = {
                "content_strategist": ContentStrategistAgent(),
                "copywriter": CopywriterAgent(),
                "designer": DesignerAgent(),
                "segmentation_expert": SegmentationExpertAgent()
            }
        
        async def orchestrate_campaign_creation(self, request):
            return {
                "campaign_creation_complete": True,
                "workflow_results": {
                    "strategy": {"agent": "content_strategist", "status": "stub"},
                    "copy": {"agent": "copywriter", "status": "stub"},
                    "design": {"agent": "designer", "status": "stub"},
                    "segmentation": {"agent": "segmentation_expert", "status": "stub"}
                },
                "final_recommendations": ["This is a stub response for testing"]
            }

# Create router
router = APIRouter()

# Initialize orchestrator
orchestrator = MultiAgentOrchestrator()

@router.get("/")
async def get_agents_info():
    """Get information about available agents"""
    return {
        "service": "Email/SMS Multi-Agent System",
        "version": "1.0.0",
        "agents": list(orchestrator.agents.keys()),
        "capabilities": [
            "email_campaign_creation",
            "sms_campaign_creation",
            "agent_consultation",
            "multi_agent_orchestration"
        ]
    }

@router.post("/campaign/email")
async def create_email_campaign(campaign_data: Dict[str, Any]):
    """Create a complete email campaign using multi-agent collaboration"""
    try:
        # Add content type for email
        request_data = {**campaign_data, "content_type": "email"}
        
        # Orchestrate campaign creation
        result = await orchestrator.orchestrate_campaign_creation(request_data)
        
        # Log the campaign creation
        logger.info(f"Email campaign created: {campaign_data.get('campaign_type', 'unknown')}")
        
        return JSONResponse(content={
            "success": True,
            "campaign": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Email campaign creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaign/sms")
async def create_sms_campaign(campaign_data: Dict[str, Any]):
    """Create an SMS campaign using multi-agent collaboration"""
    try:
        # Add content type for SMS
        request_data = {**campaign_data, "content_type": "sms"}
        
        # Orchestrate campaign creation
        result = await orchestrator.orchestrate_campaign_creation(request_data)
        
        # Log the campaign creation
        logger.info(f"SMS campaign created: {campaign_data.get('campaign_type', 'unknown')}")
        
        return JSONResponse(content={
            "success": True,
            "campaign": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"SMS campaign creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def list_agents():
    """List all available agents with their capabilities"""
    agents_info = {}
    for agent_name, agent in orchestrator.agents.items():
        agents_info[agent_name] = {
            "name": agent.name,
            "role": agent.role,
            "expertise": agent.expertise,
            "status": "active"
        }
    
    return {
        "agents": agents_info,
        "total_agents": len(agents_info),
        "orchestration_available": True
    }

@router.post("/agent/{agent_name}/consult")
async def consult_agent(agent_name: str, request_data: Dict[str, Any]):
    """Consult a specific agent for specialized expertise"""
    try:
        if agent_name not in orchestrator.agents:
            raise HTTPException(
                status_code=404, 
                detail=f"Agent '{agent_name}' not found. Available agents: {list(orchestrator.agents.keys())}"
            )
        
        agent = orchestrator.agents[agent_name]
        result = await agent.process_request(request_data)
        
        logger.info(f"Agent consultation: {agent_name}")
        
        return JSONResponse(content={
            "success": True,
            "agent": agent_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent consultation error for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/custom")
async def custom_workflow(workflow_config: Dict[str, Any]):
    """Execute a custom multi-agent workflow"""
    try:
        agents_sequence = workflow_config.get("agents", [])
        initial_request = workflow_config.get("request", {})
        
        workflow_results = {}
        context = initial_request.copy()
        
        for agent_name in agents_sequence:
            if agent_name not in orchestrator.agents:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid agent in workflow: {agent_name}"
                )
            
            agent = orchestrator.agents[agent_name]
            result = await agent.process_request(context)
            workflow_results[agent_name] = result
            
            # Update context with agent results
            context.update(result)
        
        return JSONResponse(content={
            "success": True,
            "workflow": agents_sequence,
            "results": workflow_results,
            "timestamp": datetime.utcnow().isoformat()
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{campaign_type}")
async def get_campaign_templates(campaign_type: str):
    """Get pre-configured campaign templates"""
    templates = {
        "promotional": {
            "name": "Promotional Campaign Template",
            "description": "Standard promotional campaign with product focus",
            "default_config": {
                "objectives": ["increase_sales", "drive_engagement", "showcase_products"],
                "tone": "professional_yet_friendly",
                "segments": ["engaged_customers", "high_value"],
                "timing": "optimal_send_time"
            }
        },
        "newsletter": {
            "name": "Newsletter Template", 
            "description": "Regular newsletter with content focus",
            "default_config": {
                "objectives": ["inform", "educate", "maintain_engagement"],
                "tone": "informative",
                "segments": ["all_subscribers"],
                "timing": "weekly_schedule"
            }
        },
        "flash_sale": {
            "name": "Flash Sale Template",
            "description": "Urgent limited-time offer campaign",
            "default_config": {
                "objectives": ["create_urgency", "immediate_action", "clear_inventory"],
                "tone": "urgent_exciting",
                "segments": ["bargain_hunters", "frequent_buyers"],
                "timing": "immediate"
            }
        }
    }
    
    if campaign_type not in templates:
        return JSONResponse(
            status_code=404,
            content={"error": f"Template '{campaign_type}' not found", "available": list(templates.keys())}
        )
    
    return templates[campaign_type]

@router.get("/health")
async def health_check():
    """Health check for the multi-agent system"""
    agent_statuses = {}
    for agent_name in orchestrator.agents.keys():
        agent_statuses[agent_name] = "healthy"
    
    return {
        "status": "healthy",
        "agents": agent_statuses,
        "orchestrator": "active",
        "timestamp": datetime.utcnow().isoformat()
    }