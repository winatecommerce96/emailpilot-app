#!/usr/bin/env python3

"""
HTTP MCP Server for Email/SMS Multi-Agent System
Cloud-ready version for EmailPilot.ai deployment
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

# Import agent classes (inline for cloud deployment)
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("email-sms-mcp-http-server")

# Create orchestrator instance
orchestrator = MultiAgentOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("Starting Email/SMS MCP HTTP Server...")
    yield
    logger.info("Shutting down Email/SMS MCP HTTP Server...")

# Create FastAPI app for HTTP MCP server
app = FastAPI(
    title="Email/SMS Multi-Agent MCP Server",
    description="HTTP MCP server providing collaborative AI agents for email and SMS campaign creation",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for cloud deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Server Endpoints
@app.get("/")
async def root():
    """Root endpoint with server information"""
    return {
        "name": "email-sms-mcp-server",
        "version": "1.0.0",
        "description": "Multi-agent MCP server for email and SMS campaign creation",
        "transport": "http",
        "agents": list(orchestrator.agents.keys()),
        "tools": ["create_email_campaign", "create_sms_campaign", "consult_agent"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for cloud deployment"""
    return {"status": "healthy", "agents_available": len(orchestrator.agents)}

@app.post("/mcp/list_resources")
async def list_resources():
    """MCP: List available resources"""
    resources = [
        {
            "uri": "agent://content_strategist",
            "name": "Content Strategist Agent",
            "description": "Campaign strategy and messaging framework development",
            "mimeType": "application/json"
        },
        {
            "uri": "agent://copywriter", 
            "name": "Copywriter Agent",
            "description": "Email and SMS copy creation and optimization",
            "mimeType": "application/json"
        },
        {
            "uri": "agent://designer",
            "name": "Designer Agent", 
            "description": "Visual design and template creation for emails",
            "mimeType": "application/json"
        },
        {
            "uri": "agent://segmentation_expert",
            "name": "Segmentation Expert Agent",
            "description": "Audience targeting and personalization strategies",
            "mimeType": "application/json"
        },
        {
            "uri": "workflow://campaign_creation",
            "name": "Multi-Agent Campaign Creation Workflow",
            "description": "Complete email/SMS campaign creation using all agents",
            "mimeType": "application/json"
        }
    ]
    
    return {"resources": resources}

@app.post("/mcp/list_tools")
async def list_tools():
    """MCP: List available tools"""
    tools = [
        {
            "name": "create_email_campaign",
            "description": "Create a complete email campaign using multi-agent collaboration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "campaign_type": {
                        "type": "string",
                        "description": "Type of campaign (promotional, newsletter, transactional, etc.)"
                    },
                    "target_audience": {
                        "type": "string", 
                        "description": "Target audience description"
                    },
                    "objectives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Campaign objectives"
                    },
                    "brand_guidelines": {
                        "type": "object",
                        "description": "Brand guidelines and constraints"
                    },
                    "customer_data": {
                        "type": "object",
                        "description": "Available customer data for personalization"
                    }
                },
                "required": ["campaign_type", "target_audience"]
            }
        },
        {
            "name": "create_sms_campaign",
            "description": "Create an SMS campaign using multi-agent collaboration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "campaign_type": {
                        "type": "string",
                        "description": "Type of SMS campaign"
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "Target audience description"
                    },
                    "objectives": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Campaign objectives"
                    },
                    "character_limit": {
                        "type": "integer",
                        "description": "SMS character limit (default: 160)",
                        "default": 160
                    }
                },
                "required": ["campaign_type", "target_audience"]
            }
        },
        {
            "name": "consult_agent",
            "description": "Consult a specific agent for specialized expertise",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "enum": ["content_strategist", "copywriter", "designer", "segmentation_expert"],
                        "description": "Name of the agent to consult"
                    },
                    "request": {
                        "type": "object",
                        "description": "Request parameters for the specific agent"
                    }
                },
                "required": ["agent_name", "request"]
            }
        }
    ]
    
    return {"tools": tools}

@app.post("/mcp/call_tool")
async def call_tool(request: Dict[str, Any]):
    """MCP: Handle tool calls"""
    try:
        tool_name = request.get("name")
        arguments = request.get("arguments", {})
        
        if tool_name == "create_email_campaign":
            request_data = {**arguments, "content_type": "email"}
            result = await orchestrator.orchestrate_campaign_creation(request_data)
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        
        elif tool_name == "create_sms_campaign":
            request_data = {**arguments, "content_type": "sms"}
            result = await orchestrator.orchestrate_campaign_creation(request_data)
            
            return {
                "content": [{
                    "type": "text", 
                    "text": json.dumps(result, indent=2)
                }]
            }
        
        elif tool_name == "consult_agent":
            agent_name = arguments["agent_name"]
            agent_request = arguments["request"]
            
            if agent_name not in orchestrator.agents:
                raise HTTPException(status_code=400, detail=f"Agent '{agent_name}' not found")
            
            agent = orchestrator.agents[agent_name]
            result = await agent.process_request(agent_request)
            
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool '{tool_name}'")
            
    except Exception as e:
        logger.error(f"Tool call error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/read_resource")
async def read_resource(request: Dict[str, Any]):
    """MCP: Handle resource reading requests"""
    try:
        uri = request.get("uri")
        
        if uri.startswith("agent://"):
            agent_name = uri.split("//")[1]
            if agent_name in orchestrator.agents:
                agent = orchestrator.agents[agent_name]
                agent_info = {
                    "name": agent.name,
                    "role": agent.role,
                    "expertise": agent.expertise,
                    "available_methods": ["process_request", "update_context"]
                }
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(agent_info, indent=2)
                    }]
                }
        
        elif uri == "workflow://campaign_creation":
            workflow_info = {
                "description": "Multi-agent campaign creation workflow",
                "steps": [
                    "1. Content Strategist develops messaging framework",
                    "2. Copywriter creates subject lines and copy",
                    "3. Designer develops visual specifications", 
                    "4. Segmentation Expert optimizes audience targeting"
                ],
                "agents_involved": list(orchestrator.agents.keys()),
                "expected_output": "Complete campaign specifications ready for implementation"
            }
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json", 
                    "text": json.dumps(workflow_info, indent=2)
                }]
            }
        
        raise HTTPException(status_code=404, detail=f"Resource not found: {uri}")
        
    except Exception as e:
        logger.error(f"Resource read error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional EmailPilot integration endpoints
@app.post("/api/campaign/email")
async def create_email_campaign_api(campaign_data: Dict[str, Any]):
    """EmailPilot API endpoint for email campaign creation"""
    try:
        request_data = {**campaign_data, "content_type": "email"}
        result = await orchestrator.orchestrate_campaign_creation(request_data)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Email campaign creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/sms")
async def create_sms_campaign_api(campaign_data: Dict[str, Any]):
    """EmailPilot API endpoint for SMS campaign creation"""
    try:
        request_data = {**campaign_data, "content_type": "sms"}
        result = await orchestrator.orchestrate_campaign_creation(request_data)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"SMS campaign creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents")
async def list_agents():
    """List all available agents with their capabilities"""
    agents_info = {}
    for agent_name, agent in orchestrator.agents.items():
        agents_info[agent_name] = {
            "name": agent.name,
            "role": agent.role,
            "expertise": agent.expertise
        }
    return JSONResponse(content={"agents": agents_info})

@app.post("/api/agent/{agent_name}/consult")
async def consult_agent_api(agent_name: str, request_data: Dict[str, Any]):
    """Consult a specific agent via API"""
    try:
        if agent_name not in orchestrator.agents:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        agent = orchestrator.agents[agent_name]
        result = await agent.process_request(request_data)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Agent consultation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "server_http:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )