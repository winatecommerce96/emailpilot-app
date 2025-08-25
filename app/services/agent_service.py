"""
Agent Service
This service encapsulates the logic for loading agent configurations and running the MultiAgentOrchestrator.
"""

from pathlib import Path
import json
import logging
import sys
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Path to agent configuration files
AGENT_CONFIG_PATH = Path(__file__).parent.parent.parent / "email-sms-mcp-server"
INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "agents_config.json"
CUSTOM_INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "custom_instructions.json"

class AgentService:
    def __init__(self):
        # Dynamically import the orchestrator
        mcp_path = str(AGENT_CONFIG_PATH)
        if mcp_path not in sys.path:
            sys.path.insert(0, mcp_path)
        
        from server import MultiAgentOrchestrator
        self.orchestrator = MultiAgentOrchestrator()

        # Load custom instructions if available
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                custom_config = json.load(f)
                # Apply custom instructions to agents
                for agent_name, agent in self.orchestrator.agents.items():
                    if agent_name in custom_config.get("agents", {}):
                        agent_instructions = custom_config["agents"][agent_name]
                        # Apply instructions to agent context
                        agent.context.update({"custom_instructions": agent_instructions})

    async def invoke_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the agent orchestrator with the given data.
        """
        try:
            # Directly await the async orchestrator method to avoid returning a coroutine
            result = await self.orchestrator.orchestrate_campaign_creation(data)
            return {
                "status": "success",
                "result": result,
                "agents_used": list(self.orchestrator.agents.keys())
            }
        except Exception as e:
            logger.error(f"Error invoking agent orchestrator: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

def get_agent_service():
    """
    Factory function to get an instance of the AgentService.
    Uses enhanced version if available.
    """
    # Try to use enhanced agent service first
    try:
        from app.services.agent_service_enhanced import get_enhanced_agent_service
        logger.info("Using enhanced agent service with AI Models integration")
        return get_enhanced_agent_service()
    except ImportError:
        logger.info("Using standard agent service")
        return AgentService()
