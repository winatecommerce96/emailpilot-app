#!/usr/bin/env python3

import asyncio
import json
from typing import Any, Dict, List, Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent
from mcp.server.stdio import stdio_server
import logging
from pathlib import Path
import os
from logging.handlers import RotatingFileHandler

# Configure logging with rotation to avoid runaway files in dev
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("email-sms-mcp-server")
try:
    os.makedirs("logs", exist_ok=True)
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        fh = RotatingFileHandler(os.path.join("logs", "agent_orchestrator.log"), maxBytes=5*1024*1024, backupCount=5)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(fh)
except Exception:
    # continue without file rotation if filesystem not available
    pass

# Path to agent configuration files
AGENT_CONFIG_PATH = Path(__file__).parent
INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "agents_config.json"
CUSTOM_INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "custom_instructions.json"

class EmailSMSAgent:
    """Generic class for specialized email/SMS creation agents"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.role = config.get("role", "No role defined")
        self.expertise = config.get("expertise", [])
        self.responsibilities = config.get("responsibilities", [])
        self.context = config
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request based on agent specialization"""
        # In a real implementation, this would involve calling an LLM
        # with the agent's instructions and the user's request.
        # For now, we'll simulate a response.
        
        logger.info(f"Agent '{self.name}' processing request with context: {self.context}")
        
        # Simulate generating a response based on the agent's role and the request
        response_content = {
            "agent_name": self.name,
            "role": self.role,
            "input_request": request,
            "simulated_output": f"This is a simulated response from the {self.name} agent, whose role is '{self.role}'.",
            "next_steps": self.context.get("collaboration_with", [])
        }
        
        return response_content

class MultiAgentOrchestrator:
    """Orchestrates multiple agents for collaborative email/SMS creation"""
    
    def __init__(self):
        self.agents: Dict[str, EmailSMSAgent] = {}
        self._load_agents()
    
    def _load_agents(self):
        """Loads agent configurations from JSON files and creates agent instances."""
        
        # Load default configuration
        if not INSTRUCTIONS_FILE.exists():
            logger.error(f"Default agent configuration file not found at {INSTRUCTIONS_FILE}")
            return
            
        with open(INSTRUCTIONS_FILE, 'r') as f:
            default_config = json.load(f)
        
        # Load custom instructions if they exist
        custom_config = {}
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                custom_config = json.load(f)
        
        # Merge configurations, with custom instructions overriding defaults
        final_config = {**default_config, **custom_config}
        
        # Create agent instances
        for agent_name, agent_config in final_config.get("agents", {}).items():
            self.agents[agent_name] = EmailSMSAgent(agent_name, agent_config)
            logger.info(f"Loaded agent: {agent_name}")

    async def orchestrate_campaign_creation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate the multi-agent campaign creation process"""
        
        workflow_results = {}
        self.workflow_context = request.copy()
        
        # Safety guards to prevent infinite loops and log spam
        MAX_STEPS = 50  # hard cap on orchestration steps
        steps = 0
        last_agent: Optional[str] = None

        # This is a simplified, sequential workflow. A more advanced orchestrator
        # could use a graph-based approach to determine the next agent to call.
        
        # Start with the content_strategist
        current_agent_name = "content_strategist"
        
        while current_agent_name:
            # Step cap guard
            steps += 1
            if steps > MAX_STEPS:
                logger.warning(
                    "Maximum orchestration steps (%d) reached; terminating to avoid infinite loop",
                    MAX_STEPS,
                )
                break

            if current_agent_name not in self.agents:
                logger.error(f"Agent '{current_agent_name}' not found in configuration.")
                break
            
            agent = self.agents[current_agent_name]
            logger.info(f"Invoking agent: {current_agent_name}")
            
            # Pass the current workflow context to the agent
            result = await agent.process_request(self.workflow_context)
            
            # Store the result and update the context
            workflow_results[current_agent_name] = result
            self.workflow_context.update({current_agent_name: result})
            
            # Determine the next agent to call
            next_agents = result.get("next_steps", [])
            # Detect trivial ping-pong cycles like A->B->A->B and break
            proposed_next = next_agents[0] if next_agents else None
            if proposed_next and last_agent and proposed_next == last_agent:
                logger.warning(
                    "Detected potential ping-pong cycle between '%s' and '%s'; stopping orchestration",
                    last_agent,
                    current_agent_name,
                )
                break
            last_agent = current_agent_name
            current_agent_name = proposed_next

        return {
            "campaign_creation_complete": True,
            "workflow_results": workflow_results,
            "final_recommendations": self._generate_final_recommendations(workflow_results)
        }
    
    def _generate_final_recommendations(self, workflow_results: Dict) -> List[str]:
        return [
            "Review all agent outputs for consistency",
            "Conduct A/B testing on subject lines",
            "Monitor performance metrics post-launch",
            "Iterate based on engagement data"
        ]

# Initialize the MCP server
server = Server("email-sms-mcp-server")
orchestrator = MultiAgentOrchestrator()

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources for email/SMS creation"""
    resources = [
        Resource(
            uri=f"agent://{name}",
            name=f"{name.replace('_', ' ').title()} Agent",
            description=agent.role,
            mimeType="application/json"
        ) for name, agent in orchestrator.agents.items()
    ]
    
    resources.append(
        Resource(
            uri="workflow://campaign_creation",
            name="Multi-Agent Campaign Creation Workflow",
            description="Complete email/SMS campaign creation using all agents",
            mimeType="application/json"
        )
    )
    return resources

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools for email/SMS creation"""
    return [
        Tool(
            name="create_email_campaign",
            description="Create a complete email campaign using multi-agent collaboration",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_type": {
                        "type": "string",
                        "description": "Type of campaign (promotional, newsletter, etc.)"
                    },
                    "target_audience": {
                        "type": "string", 
                        "description": "Target audience description"
                    },
                    "objectives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Campaign objectives"
                    }
                },
                "required": ["campaign_type", "target_audience"]
            }
        ),
        Tool(
            name="consult_agent",
            description="Consult a specific agent for specialized expertise",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "enum": list(orchestrator.agents.keys()),
                        "description": "Name of the agent to consult"
                    },
                    "request": {
                        "type": "object",
                        "description": "Request parameters for the specific agent"
                    }
                },
                "required": ["agent_name", "request"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls for email/SMS creation"""
    
    if name == "create_email_campaign":
        result = await orchestrator.orchestrate_campaign_creation(arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "consult_agent":
        agent_name = arguments["agent_name"]
        agent_request = arguments["request"]
        
        if agent_name not in orchestrator.agents:
            return [TextContent(type="text", text=f"Error: Agent '{agent_name}' not found")]
        
        agent = orchestrator.agents[agent_name]
        result = await agent.process_request(agent_request)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reading requests"""
    
    if uri.startswith("agent://"):
        agent_name = uri.split("//")[1]
        if agent_name in orchestrator.agents:
            agent = orchestrator.agents[agent_name]
            agent_info = {
                "name": agent.name,
                "role": agent.role,
                "expertise": agent.expertise,
                "responsibilities": agent.responsibilities
            }
            return json.dumps(agent_info, indent=2)
    
    elif uri == "workflow://campaign_creation":
        workflow_info = {
            "description": "Multi-agent campaign creation workflow",
            "agents_involved": list(orchestrator.agents.keys()),
        }
        return json.dumps(workflow_info, indent=2)
    
    return f"Resource not found: {uri}"

async def main():
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="email-sms-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
