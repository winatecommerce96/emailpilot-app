"""
Agent Configuration API
Manages agent-to-prompt mappings and AI model preferences
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from google.cloud import firestore
from app.deps import get_db
from app.deps.secrets import get_secret_manager_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent-config", tags=["agent-configuration"])

# Import enhanced agent service (optional)
try:
    from app.services.agent_service_enhanced import get_enhanced_agent_service
    ENHANCED_SERVICE_AVAILABLE = True
except Exception:
    ENHANCED_SERVICE_AVAILABLE = False
    get_enhanced_agent_service = None  # type: ignore
    logger.warning("Enhanced agent service not available (using fallback where possible)")

from pathlib import Path
import json

AGENT_CONFIG_PATH = Path(__file__).parent.parent.parent / "email-sms-mcp-server"
INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "agents_config.json"

def _fallback_agent_status() -> Dict[str, Any]:
    agents: Dict[str, Any] = {}
    try:
        if INSTRUCTIONS_FILE.exists():
            with open(INSTRUCTIONS_FILE, 'r') as f:
                data = json.load(f)
            for name, cfg in (data.get("agents", {}) or {}).items():
                agents[name] = {
                    "name": name,
                    "role": cfg.get("role", ""),
                    "prompt_configured": False,
                    "prompt_id": None,
                    "preferred_provider": cfg.get("preferred_provider", "gemini"),
                    "preferred_model": cfg.get("preferred_model"),
                    "fallback_providers": cfg.get("fallback_providers", ["openai", "claude"]) or [],
                }
    except Exception as e:
        logger.warning(f"Fallback agent status failed: {e}")
    return {"total_agents": len(agents), "agents": agents}

class AgentConfiguration(BaseModel):
    agent_name: str
    prompt_id: Optional[str] = None
    preferred_provider: str = "gemini"
    preferred_model: Optional[str] = None
    fallback_providers: List[str] = ["openai", "claude"]
    custom_instructions: Optional[str] = None
    active: bool = True

class AgentPromptMapping(BaseModel):
    agent_name: str
    prompt_id: str
    
class BulkAgentUpdate(BaseModel):
    provider: str  # Apply to all agents
    model: Optional[str] = None

@router.get("/agents")
async def get_agent_configurations(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get all agent configurations including their prompt mappings"""
    
    try:
        # Get agent status
        if ENHANCED_SERVICE_AVAILABLE and get_enhanced_agent_service:
            service = get_enhanced_agent_service(db, get_secret_manager_service())
            agent_status = await service.get_status()
        else:
            agent_status = _fallback_agent_status()
        
        # Get prompt mappings from Firestore
        agent_prompts = {}
        prompts = db.collection("ai_prompts").where("category", "==", "agent").stream()
        
        for doc in prompts:
            prompt_data = doc.to_dict()
            agent_type = prompt_data.get("metadata", {}).get("agent_type")
            if agent_type:
                agent_prompts[agent_type] = {
                    "prompt_id": doc.id,
                    "prompt_name": prompt_data.get("name"),
                    "provider": prompt_data.get("model_provider"),
                    "model": prompt_data.get("model_name"),
                    "active": prompt_data.get("active", True)
                }
        
        # Combine service status with Firestore data
        for agent_name, status in agent_status.get("agents", {}).items():
            if agent_name in agent_prompts:
                status.update(agent_prompts[agent_name])
        
        return {
            "agents": agent_status.get("agents", {}),
            "total_agents": agent_status.get("total_agents", 0),
            "configured_count": len([a for a in agent_status.get("agents", {}).values() if a.get("prompt_configured")]),
            "unconfigured_agents": [
                name for name, agent in agent_status.get("agents", {}).items() 
                if not agent.get("prompt_configured")
            ]
        }
    
    except Exception as e:
        logger.error(f"Error fetching agent configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_name}/configure")
async def configure_agent(
    agent_name: str,
    config: AgentConfiguration,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Configure an agent with a specific prompt and model preferences"""
    
    try:
        # Check if a prompt exists for this agent
        existing_prompts = db.collection("ai_prompts")\
            .where("category", "==", "agent")\
            .where("metadata.agent_type", "==", agent_name)\
            .limit(1).stream()
        
        existing_prompt = None
        for doc in existing_prompts:
            existing_prompt = doc
            break
        
        if config.prompt_id:
            # Verify the prompt exists
            prompt_doc = db.collection("ai_prompts").document(config.prompt_id).get()
            if not prompt_doc.exists:
                raise HTTPException(status_code=404, detail=f"Prompt {config.prompt_id} not found")
            
            # Update the prompt's metadata to link it to this agent
            db.collection("ai_prompts").document(config.prompt_id).update({
                "metadata.agent_type": agent_name,
                "category": "agent",
                "model_provider": config.preferred_provider,
                "model_name": config.preferred_model
            })
        
        # Store agent configuration in a dedicated collection
        agent_config_ref = db.collection("agent_configurations").document(agent_name)
        agent_config_ref.set({
            "agent_name": agent_name,
            "prompt_id": config.prompt_id,
            "preferred_provider": config.preferred_provider,
            "preferred_model": config.preferred_model,
            "fallback_providers": config.fallback_providers,
            "custom_instructions": config.custom_instructions,
            "active": config.active,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        
        # Reload agents in the service
        if ENHANCED_SERVICE_AVAILABLE and get_enhanced_agent_service:
            service = get_enhanced_agent_service(db, get_secret_manager_service())
            reload_result = await service.reload_agents()
            
            return {
                "success": True,
                "agent_name": agent_name,
                "configuration": config.dict(),
                "service_reload": reload_result
            }
        
        return {
            "success": True,
            "agent_name": agent_name,
            "configuration": config.dict(),
            "message": "Configuration saved (service reload pending)"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/map-prompts")
async def bulk_map_prompts(
    mappings: List[AgentPromptMapping],
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Bulk map agents to prompts"""
    
    try:
        success_count = 0
        failed = []
        
        for mapping in mappings:
            try:
                # Verify prompt exists
                prompt_doc = db.collection("ai_prompts").document(mapping.prompt_id).get()
                if not prompt_doc.exists:
                    failed.append({
                        "agent": mapping.agent_name,
                        "reason": f"Prompt {mapping.prompt_id} not found"
                    })
                    continue
                
                # Update prompt metadata
                db.collection("ai_prompts").document(mapping.prompt_id).update({
                    "metadata.agent_type": mapping.agent_name,
                    "category": "agent"
                })
                
                # Update agent configuration
                db.collection("agent_configurations").document(mapping.agent_name).set({
                    "agent_name": mapping.agent_name,
                    "prompt_id": mapping.prompt_id,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)
                
                success_count += 1
                
            except Exception as e:
                failed.append({
                    "agent": mapping.agent_name,
                    "reason": str(e)
                })
        
        # Reload agents (best effort)
        if ENHANCED_SERVICE_AVAILABLE and get_enhanced_agent_service:
            service = get_enhanced_agent_service(db, get_secret_manager_service())
            await service.reload_agents()
        
        return {
            "success": True,
            "mapped_count": success_count,
            "failed_count": len(failed),
            "failed": failed
        }
    
    except Exception as e:
        logger.error(f"Error in bulk mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/set-default-provider")
async def set_default_provider(
    update: BulkAgentUpdate,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Set a default AI provider for all agents"""
    
    try:
        # Update all agent configurations
        agent_configs = db.collection("agent_configurations").stream()
        update_count = 0
        
        for doc in agent_configs:
            doc.reference.update({
                "preferred_provider": update.provider,
                "preferred_model": update.model,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            update_count += 1
        
        # Update all agent prompts
        agent_prompts = db.collection("ai_prompts").where("category", "==", "agent").stream()
        
        for doc in agent_prompts:
            doc.reference.update({
                "model_provider": update.provider,
                "model_name": update.model
            })
        
        # Reload agents
        if ENHANCED_SERVICE_AVAILABLE:
            service = get_enhanced_agent_service(db, get_secret_manager_service())
            await service.reload_agents()
        
        return {
            "success": True,
            "message": f"Updated {update_count} agents to use {update.provider}",
            "provider": update.provider,
            "model": update.model
        }
    
    except Exception as e:
        logger.error(f"Error setting default provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/reload")
async def reload_agents(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Reload all agent configurations"""
    
    try:
        if ENHANCED_SERVICE_AVAILABLE and get_enhanced_agent_service:
            service = get_enhanced_agent_service(db, get_secret_manager_service())
            result = await service.reload_agents()
            return result
        return {"status": "success", "message": "Reload skipped (enhanced service not available)"}
    except Exception as e:
        logger.error(f"Error reloading agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_name}/test")
async def test_agent(
    agent_name: str,
    test_data: Optional[Dict[str, Any]] = None,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Test an agent with sample data"""
    
    try:
        if not (ENHANCED_SERVICE_AVAILABLE and get_enhanced_agent_service):
            raise HTTPException(status_code=501, detail="Enhanced agent service not available")
        service = get_enhanced_agent_service(db, get_secret_manager_service())
        
        # Use provided test data or default
        if not test_data:
            test_data = {
                "client_name": "Test Client",
                "campaign_type": "promotional",
                "target_audience": "existing customers",
                "objective": "increase sales"
            }
        
        # Execute single agent
        if agent_name not in service.orchestrator.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
        agent = service.orchestrator.agents[agent_name]
        result = await agent.process_request(test_data)
        
        return {
            "agent_name": agent_name,
            "test_data": test_data,
            "result": result,
            "success": result.get("status") == "success"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow-types")
async def get_workflow_types() -> Dict[str, Any]:
    """Get available workflow types for agent orchestration"""
    
    return {
        "workflow_types": [
            {
                "name": "sequential",
                "description": "Agents execute one after another based on next_steps",
                "default": True
            },
            {
                "name": "parallel",
                "description": "All agents execute simultaneously for faster processing",
                "default": False
            }
        ],
        "start_agents": [
            "content_strategist",
            "copywriter", 
            "designer",
            "segmentation_expert"
        ]
    }
