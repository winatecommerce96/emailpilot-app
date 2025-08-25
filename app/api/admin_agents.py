"""
Admin API endpoints for Email/SMS Multi-Agent System
Allows editing instructions, testing agents, and monitoring performance
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime
import os
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Path to agent configuration files
AGENT_CONFIG_PATH = Path(__file__).parent.parent.parent / "email-sms-mcp-server"
INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "agents_config.json"
CUSTOM_INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "custom_instructions.json"

def get_current_user_from_session(request: Request):
    """Check if user is authenticated as admin"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    # Check if user is admin
    if user.get("email") not in ["damon@winatecommerce.com", "admin@emailpilot.ai"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("/config")
async def get_agent_configuration(request: Request):
    """Get current agent configuration and instructions"""
    user = get_current_user_from_session(request)
    
    try:
        # Load default configuration
        default_config = {}
        if INSTRUCTIONS_FILE.exists():
            with open(INSTRUCTIONS_FILE, 'r') as f:
                default_config = json.load(f)
        
        # Load custom instructions if they exist
        custom_config = {}
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                custom_config = json.load(f)
        
        return {
            "default_config": default_config,
            "custom_config": custom_config,
            "config_path": str(AGENT_CONFIG_PATH),
            "editable": True
        }
    except Exception as e:
        logger.error(f"Error loading agent configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def update_agent_configuration(request: Request, config_data: Dict[str, Any]):
    """Update agent configuration and instructions"""
    user = get_current_user_from_session(request)
    
    try:
        # Validate configuration structure
        if not config_data.get("agents"):
            raise HTTPException(status_code=400, detail="Invalid configuration: missing 'agents' key")
        
        # Create backup of current configuration
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            backup_file = AGENT_CONFIG_PATH / f"custom_instructions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                backup_data = json.load(f)
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
        
        # Save new configuration
        with open(CUSTOM_INSTRUCTIONS_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Agent configuration updated by {user.get('email')}")
        
        return {
            "status": "success",
            "message": "Configuration updated successfully",
            "backup_created": True
        }
    except Exception as e:
        logger.error(f"Error updating agent configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents")
async def add_agent(request: Request, agent_data: Dict[str, Any]):
    """Add a new agent"""
    user = get_current_user_from_session(request)
    
    try:
        agent_name = agent_data.get("name")
        instructions = agent_data.get("instructions")
        
        if not agent_name or not instructions:
            raise HTTPException(status_code=400, detail="Agent name and instructions are required")
        
        # Load current custom configuration
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                config = json.load(f)
        else:
            config = {"agents": {}}
        
        # Add new agent
        if "agents" not in config:
            config["agents"] = {}
        
        config["agents"][agent_name] = instructions
        config["last_updated"] = datetime.now().isoformat()
        config["updated_by"] = user.get("email")
        
        # Save updated configuration
        with open(CUSTOM_INSTRUCTIONS_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"New agent '{agent_name}' added by {user.get('email')}")
        
        return {
            "status": "success",
            "agent_name": agent_name,
            "message": f"Agent '{agent_name}' added successfully"
        }
    except Exception as e:
        logger.error(f"Error adding agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/instructions/{agent_name}")
async def get_agent_instructions(request: Request, agent_name: str):
    """Get instructions for a specific agent"""
    user = get_current_user_from_session(request)
    
    try:
        # Load custom instructions first, fall back to default
        instructions = {}
        
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                config = json.load(f)
                instructions = config.get("agents", {}).get(agent_name, {})
        
        if not instructions and INSTRUCTIONS_FILE.exists():
            with open(INSTRUCTIONS_FILE, 'r') as f:
                config = json.load(f)
                instructions = config.get("agents", {}).get(agent_name, {})
        
        if not instructions:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        return {
            "agent_name": agent_name,
            "instructions": instructions,
            "editable": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading agent instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/instructions/{agent_name}")
async def update_agent_instructions(
    request: Request, 
    agent_name: str, 
    instructions: Dict[str, Any]
):
    """Update instructions for a specific agent"""
    user = get_current_user_from_session(request)
    
    try:
        # Load current custom configuration
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                config = json.load(f)
        else:
            # Start with default configuration
            if INSTRUCTIONS_FILE.exists():
                with open(INSTRUCTIONS_FILE, 'r') as f:
                    config = json.load(f)
            else:
                config = {"agents": {}}
        
        # Update specific agent instructions
        if "agents" not in config:
            config["agents"] = {}
        
        config["agents"][agent_name] = instructions
        config["last_updated"] = datetime.now().isoformat()
        config["updated_by"] = user.get("email")
        
        # Save updated configuration
        with open(CUSTOM_INSTRUCTIONS_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Instructions for agent '{agent_name}' updated by {user.get('email')}")
        
        return {
            "status": "success",
            "agent_name": agent_name,
            "message": f"Instructions updated for {agent_name}"
        }
    except Exception as e:
        logger.error(f"Error updating agent instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_agent_configuration(request: Request, test_data: Dict[str, Any]):
    """Test agent configuration with sample data"""
    user = get_current_user_from_session(request)
    
    try:
        # Import the orchestrator
        import sys
        mcp_path = str(AGENT_CONFIG_PATH)
        if mcp_path not in sys.path:
            sys.path.insert(0, mcp_path)
        
        from server import MultiAgentOrchestrator
        
        # Create orchestrator with current configuration
        orchestrator = MultiAgentOrchestrator()
        
        # Load custom instructions if available
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                custom_config = json.load(f)
                # Apply custom instructions to agents
                for agent_name, agent in orchestrator.agents.items():
                    if agent_name in custom_config.get("agents", {}):
                        agent_instructions = custom_config["agents"][agent_name]
                        # Apply instructions to agent context
                        agent.context.update({"custom_instructions": agent_instructions})
        
        # Run test
        import asyncio
        result = asyncio.run(orchestrator.orchestrate_campaign_creation(test_data))
        
        return {
            "status": "success",
            "test_result": result,
            "agents_used": list(orchestrator.agents.keys()),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error testing agent configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_agent_performance_metrics(request: Request):
    """Get performance metrics for agents"""
    user = get_current_user_from_session(request)
    
    try:
        # Load performance logs if they exist
        performance_file = AGENT_CONFIG_PATH / "performance_metrics.json"
        
        if performance_file.exists():
            with open(performance_file, 'r') as f:
                metrics = json.load(f)
        else:
            # Return sample metrics for demonstration
            metrics = {
                "overall": {
                    "total_campaigns": 0,
                    "average_confidence": 0,
                    "average_execution_time": 0
                },
                "by_agent": {
                    "content_strategist": {
                        "executions": 0,
                        "average_confidence": 0,
                        "average_time": 0
                    },
                    "copywriter": {
                        "executions": 0,
                        "average_confidence": 0,
                        "average_time": 0
                    },
                    "designer": {
                        "executions": 0,
                        "average_confidence": 0,
                        "average_time": 0
                    },
                    "segmentation_expert": {
                        "executions": 0,
                        "average_confidence": 0,
                        "average_time": 0
                    }
                },
                "recent_campaigns": []
            }
        
        return metrics
    except Exception as e:
        logger.error(f"Error loading performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def get_instruction_templates(request: Request):
    """Get instruction templates for different campaign types"""
    user = get_current_user_from_session(request)
    
    templates = {
        "promotional": {
            "name": "Promotional Campaign",
            "description": "Instructions for promotional/sales campaigns",
            "agents": {
                "content_strategist": {
                    "focus": "urgency_and_value",
                    "psychological_triggers": ["scarcity", "social_proof", "reciprocity"],
                    "messaging_pillars": ["limited_time", "exclusive_access", "proven_results"]
                },
                "copywriter": {
                    "subject_line_style": "benefit_driven",
                    "tone": "urgent_but_friendly",
                    "cta_emphasis": "strong"
                }
            }
        },
        "welcome_series": {
            "name": "Welcome Series",
            "description": "Instructions for new subscriber welcome emails",
            "agents": {
                "content_strategist": {
                    "focus": "education_and_trust",
                    "psychological_triggers": ["authority", "liking", "consistency"],
                    "messaging_pillars": ["brand_story", "value_proposition", "community"]
                },
                "copywriter": {
                    "subject_line_style": "personal_welcome",
                    "tone": "warm_and_informative",
                    "cta_emphasis": "soft"
                }
            }
        },
        "re_engagement": {
            "name": "Re-engagement Campaign",
            "description": "Instructions for win-back campaigns",
            "agents": {
                "content_strategist": {
                    "focus": "rekindling_interest",
                    "psychological_triggers": ["loss_aversion", "nostalgia", "curiosity"],
                    "messaging_pillars": ["what_changed", "exclusive_offer", "feedback_request"]
                },
                "copywriter": {
                    "subject_line_style": "we_miss_you",
                    "tone": "personal_and_caring",
                    "cta_emphasis": "moderate"
                }
            }
        }
    }
    
    return templates

@router.post("/templates/apply")
async def apply_instruction_template(
    request: Request,
    template_data: Dict[str, Any]
):
    """Apply an instruction template to agents"""
    user = get_current_user_from_session(request)
    
    try:
        template_name = template_data.get("template_name")
        
        # Get templates
        templates_response = await get_instruction_templates(request)
        
        if template_name not in templates_response:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        template = templates_response[template_name]
        
        # Load current configuration
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                config = json.load(f)
        else:
            config = {"agents": {}}
        
        # Apply template to agents
        for agent_name, agent_instructions in template.get("agents", {}).items():
            if agent_name not in config["agents"]:
                config["agents"][agent_name] = {}
            
            # Merge template instructions with existing
            config["agents"][agent_name].update(agent_instructions)
        
        config["last_template_applied"] = template_name
        config["template_applied_at"] = datetime.now().isoformat()
        config["applied_by"] = user.get("email")
        
        # Save configuration
        with open(CUSTOM_INSTRUCTIONS_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Template '{template_name}' applied by {user.get('email')}")
        
        return {
            "status": "success",
            "template_applied": template_name,
            "agents_updated": list(template.get("agents", {}).keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_to_default_instructions(request: Request):
    """Reset all agent instructions to default"""
    user = get_current_user_from_session(request)
    
    try:
        # Create backup before reset
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            backup_file = AGENT_CONFIG_PATH / f"custom_instructions_reset_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                backup_data = json.load(f)
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Remove custom instructions file
            os.remove(CUSTOM_INSTRUCTIONS_FILE)
        
        logger.info(f"Agent instructions reset to default by {user.get('email')}")
        
        return {
            "status": "success",
            "message": "Instructions reset to default",
            "backup_created": True
        }
    except Exception as e:
        logger.error(f"Error resetting instructions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
