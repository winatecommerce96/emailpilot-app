"""
Unified AI Agents Management API
Single Source of Truth for all AI Agent definitions

This API replaces:
1. The "Prompts" section in ai-models.py (deprecated)
2. The "Available AI Agents" in copywriting tool (deprecated)
3. The agent management in admin-dashboard.html (deprecated)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging
import uuid

from app.deps import get_db
from app.deps.secrets import get_secret_manager_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["Unified Agents"])

# Pydantic Models for Agent Schema
class Agent(BaseModel):
    """
    Unified Agent Schema - Single Source of Truth
    """
    agent_id: str = Field(..., description="Unique agent identifier (slug)")
    display_name: str = Field(..., description="Human-readable display name")
    role: str = Field(..., description="Agent role/purpose (copywriter, strategist, etc.)")
    default_provider: str = Field("auto", description="Preferred AI provider (openai|claude|gemini|auto)")
    default_model_id: Optional[str] = Field(None, description="Specific model ID to use")
    prompt_template: str = Field(..., description="Main prompt template for this agent")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities/tags")
    active: bool = Field(True, description="Whether agent is active")
    description: Optional[str] = Field(None, description="Agent description")
    version: int = Field(1, description="Template version")
    variables: List[str] = Field(default_factory=list, description="Template variables")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class CreateAgentRequest(BaseModel):
    display_name: str
    role: str
    prompt_template: str
    default_provider: str = "auto"
    default_model_id: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    variables: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UpdateAgentRequest(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    prompt_template: Optional[str] = None
    default_provider: Optional[str] = None
    default_model_id: Optional[str] = None
    capabilities: Optional[List[str]] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    variables: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

# CRUD Operations

@router.get("/", response_model=Dict[str, Any])
async def list_agents(
    active_only: bool = Query(True, description="Return only active agents"),
    role: Optional[str] = Query(None, description="Filter by role"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    db: firestore.Client = Depends(get_db)
):
    """
    List all agents from the unified agents collection
    This is the primary endpoint for getting agents
    """
    try:
        agents_ref = db.collection("agents")
        
        # Apply filters
        if active_only:
            agents_ref = agents_ref.where("active", "==", True)
        if role:
            agents_ref = agents_ref.where("role", "==", role)
        
        agents = []
        for doc in agents_ref.stream():
            agent_data = doc.to_dict()
            agent_data["agent_id"] = doc.id  # Use document ID as agent_id
            
            # Filter by capability if specified
            if capability and capability not in agent_data.get("capabilities", []):
                continue
                
            agents.append(agent_data)
        
        # Sort by display_name
        agents.sort(key=lambda x: x.get("display_name", ""))
        
        return {
            "agents": agents,
            "total": len(agents),
            "filters": {
                "active_only": active_only,
                "role": role,
                "capability": capability
            },
            "source": "unified_agents_collection"
        }
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_agent_stats(
    db: firestore.Client = Depends(get_db)
):
    """Get statistics about the agents collection"""
    try:
        agents = db.collection("agents").stream()
        
        stats = {
            "total_agents": 0,
            "active_agents": 0,
            "by_role": {},
            "by_provider": {},
            "by_capability": {},
            "recent_updates": []
        }
        
        all_agents = []
        for doc in agents:
            agent_data = doc.to_dict()
            agent_data["agent_id"] = doc.id
            all_agents.append(agent_data)
            
            stats["total_agents"] += 1
            if agent_data.get("active", True):
                stats["active_agents"] += 1
            
            # Count by role
            role = agent_data.get("role", "unknown")
            stats["by_role"][role] = stats["by_role"].get(role, 0) + 1
            
            # Count by provider
            provider = agent_data.get("default_provider", "unknown")
            stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1
            
            # Count capabilities
            for capability in agent_data.get("capabilities", []):
                stats["by_capability"][capability] = stats["by_capability"].get(capability, 0) + 1
        
        # Get recent updates
        all_agents.sort(key=lambda x: x.get("updated_at", datetime.min), reverse=True)
        stats["recent_updates"] = [
            {
                "agent_id": agent["agent_id"],
                "display_name": agent.get("display_name"),
                "updated_at": agent.get("updated_at").isoformat() if agent.get("updated_at") else None
            }
            for agent in all_agents[:5]
        ]
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get agent stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_agent(
    agent_id: str,
    db: firestore.Client = Depends(get_db)
):
    """Get a specific agent by ID"""
    try:
        doc = db.collection("agents").document(agent_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        
        agent_data = doc.to_dict()
        agent_data["agent_id"] = doc.id
        
        return agent_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict[str, Any])
async def create_agent(
    request: CreateAgentRequest,
    db: firestore.Client = Depends(get_db)
):
    """Create a new agent"""
    try:
        # Generate unique agent_id from display_name
        agent_id = request.display_name.lower().replace(" ", "_").replace("-", "_")
        agent_id = "".join(c for c in agent_id if c.isalnum() or c == "_")
        
        # Check if agent_id already exists
        if db.collection("agents").document(agent_id).get().exists:
            # Append UUID to make it unique
            agent_id = f"{agent_id}_{uuid.uuid4().hex[:8]}"
        
        # Prepare agent data
        agent_data = request.dict()
        agent_data["agent_id"] = agent_id
        agent_data["active"] = True
        agent_data["version"] = 1
        agent_data["created_at"] = datetime.utcnow()
        agent_data["updated_at"] = datetime.utcnow()
        
        # Save to Firestore
        db.collection("agents").document(agent_id).set(agent_data)
        
        logger.info(f"Created new agent: {agent_id}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "message": f"Agent '{request.display_name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{agent_id}", response_model=Dict[str, Any])
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    db: firestore.Client = Depends(get_db)
):
    """Update an existing agent"""
    try:
        doc_ref = db.collection("agents").document(agent_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        
        # Prepare update data
        update_data = {}
        for field, value in request.dict(exclude_none=True).items():
            update_data[field] = value
        
        # Always update timestamp and increment version
        current_data = doc.to_dict()
        update_data["updated_at"] = datetime.utcnow()
        update_data["version"] = current_data.get("version", 1) + 1
        
        # Update in Firestore
        doc_ref.update(update_data)
        
        logger.info(f"Updated agent: {agent_id}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "message": f"Agent '{agent_id}' updated successfully",
            "version": update_data["version"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{agent_id}", response_model=Dict[str, Any])
async def delete_agent(
    agent_id: str,
    hard_delete: bool = Query(False, description="Permanently delete (vs soft delete)"),
    db: firestore.Client = Depends(get_db)
):
    """Delete an agent (soft delete by default)"""
    try:
        doc_ref = db.collection("agents").document(agent_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        
        if hard_delete:
            doc_ref.delete()
            message = f"Agent '{agent_id}' permanently deleted"
        else:
            doc_ref.update({
                "active": False,
                "updated_at": datetime.utcnow()
            })
            message = f"Agent '{agent_id}' deactivated"
        
        logger.info(f"Deleted agent: {agent_id} (hard_delete={hard_delete})")
        
        return {
            "success": True,
            "message": message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Migration and Utility Endpoints

@router.post("/migrate-from-prompts", response_model=Dict[str, Any])
async def migrate_from_prompts(
    db: firestore.Client = Depends(get_db)
):
    """
    Migrate agent-related prompts from ai_prompts collection to unified agents
    This handles the deprecation of the "Prompts" system
    """
    try:
        # Get all prompts with category="agent"
        prompts_ref = db.collection("ai_prompts").where("category", "==", "agent")
        agent_prompts = []
        
        for doc in prompts_ref.stream():
            prompt_data = doc.to_dict()
            agent_prompts.append({
                "prompt_id": doc.id,
                "data": prompt_data
            })
        
        migrated_count = 0
        for prompt in agent_prompts:
            data = prompt["data"]
            
            # Extract agent type from metadata
            agent_type = data.get("metadata", {}).get("agent_type", "general")
            
            # Create agent from prompt data
            agent_id = agent_type.lower().replace(" ", "_")
            
            # Check if agent already exists
            if not db.collection("agents").document(agent_id).get().exists:
                agent_data = {
                    "agent_id": agent_id,
                    "display_name": data.get("name", agent_type.title()),
                    "role": agent_type,
                    "default_provider": data.get("model_provider", "auto"),
                    "default_model_id": data.get("model_name"),
                    "prompt_template": data.get("prompt_template", ""),
                    "capabilities": data.get("variables", []),
                    "active": data.get("active", True),
                    "description": data.get("description", ""),
                    "version": data.get("version", 1),
                    "variables": data.get("variables", []),
                    "created_at": data.get("created_at", datetime.utcnow()),
                    "updated_at": datetime.utcnow(),
                    "metadata": {
                        "migrated_from": "ai_prompts",
                        "original_prompt_id": prompt["prompt_id"],
                        "migration_date": datetime.utcnow().isoformat()
                    }
                }
                
                db.collection("agents").document(agent_id).set(agent_data)
                migrated_count += 1
        
        return {
            "success": True,
            "migrated_count": migrated_count,
            "message": f"Migrated {migrated_count} agent prompts to unified agents collection"
        }
        
    except Exception as e:
        logger.error(f"Failed to migrate from prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/seed-default-agents", response_model=Dict[str, Any])
async def seed_default_agents(
    db: firestore.Client = Depends(get_db)
):
    """
    Seed the agents collection with default agents
    Includes agents from copywriting tool and common marketing agents
    """
    default_agents = [
        {
            "agent_id": "copywriter",
            "display_name": "Expert Copywriter",
            "role": "copywriter",
            "default_provider": "claude",
            "default_model_id": "claude-3-5-sonnet-20241022",
            "prompt_template": """You are an expert email copywriter with 10+ years of experience in direct-response marketing. Your specialty is creating compelling email campaigns that drive engagement and conversions.

Your key strengths:
- Writing attention-grabbing subject lines that increase open rates
- Crafting persuasive email body copy using proven frameworks (AIDA, PAS, FOMO, etc.)
- Creating strong calls-to-action that drive clicks and conversions
- Adapting tone and style to match brand voice and target audience
- A/B testing recommendations for optimization

Always consider:
- Brand voice and personality
- Target audience demographics and psychographics
- Campaign goals and KPIs
- Email deliverability best practices
- Mobile optimization""",
            "capabilities": ["email_copy", "subject_lines", "cta_creation", "brand_voice", "ab_testing"],
            "description": "Expert in email copy and messaging, specializing in direct-response marketing",
            "variables": ["brand_voice", "target_audience", "campaign_goal", "product_details"],
            "active": True,
            "metadata": {"category": "marketing", "expertise_level": "expert"}
        },
        {
            "agent_id": "content_strategist", 
            "display_name": "Content Strategist",
            "role": "strategist",
            "default_provider": "gemini",
            "default_model_id": "gemini-1.5-pro-latest",
            "prompt_template": """You are a senior content strategist with expertise in developing comprehensive email marketing strategies. You focus on the big picture - customer journey mapping, content planning, and campaign orchestration.

Your core responsibilities:
- Analyzing customer data and behavior patterns
- Creating content calendars and campaign sequences
- Developing audience segmentation strategies
- Planning customer journey touchpoints
- Coordinating cross-channel marketing efforts

Your approach:
- Data-driven decision making
- Customer-centric content planning
- Brand consistency across all touchpoints
- Performance optimization through testing
- ROI-focused strategy development""",
            "capabilities": ["strategy", "audience_targeting", "campaign_planning", "data_analysis", "customer_journey"],
            "description": "Strategic planning and campaign orchestration expert",
            "variables": ["customer_data", "business_goals", "campaign_timeline", "budget_constraints"],
            "active": True,
            "metadata": {"category": "strategy", "expertise_level": "senior"}
        },
        {
            "agent_id": "brand_specialist",
            "display_name": "Brand Specialist", 
            "role": "branding",
            "default_provider": "claude",
            "default_model_id": "claude-3-5-sonnet-20241022",
            "prompt_template": """You are a brand specialist focused on maintaining consistent brand voice, tone, and messaging across all email communications. You ensure every piece of content aligns with brand guidelines and values.

Your expertise includes:
- Brand voice development and maintenance
- Tone consistency across campaigns
- Brand personality expression in copy
- Visual brand alignment recommendations
- Brand guideline enforcement

Your focus areas:
- Authentic brand storytelling
- Emotional brand connection
- Brand differentiation in messaging
- Consistent brand experience
- Brand compliance and quality assurance""",
            "capabilities": ["brand_voice", "tone_consistency", "messaging_alignment", "brand_guidelines"],
            "description": "Ensures brand voice and consistency across all communications",
            "variables": ["brand_guidelines", "brand_values", "brand_personality", "target_perception"],
            "active": True,
            "metadata": {"category": "branding", "expertise_level": "specialist"}
        },
        {
            "agent_id": "performance_analyst",
            "display_name": "Performance Analyst",
            "role": "analytics", 
            "default_provider": "gemini",
            "default_model_id": "gemini-1.5-flash",
            "prompt_template": """You are a performance analyst specializing in email marketing metrics and optimization. You analyze campaign performance, identify trends, and provide actionable recommendations for improvement.

Your analytical focus:
- Email performance metrics (open rates, click rates, conversions)
- A/B test design and results interpretation
- Audience behavior analysis
- Campaign optimization recommendations
- ROI and revenue attribution

Your methodology:
- Statistical significance testing
- Trend analysis and pattern recognition
- Cohort analysis and segmentation insights
- Predictive performance modeling
- Actionable reporting and recommendations""",
            "capabilities": ["metrics_analysis", "performance_optimization", "ab_testing", "data_insights"],
            "description": "Analytics and optimization expert for email campaigns",
            "variables": ["performance_data", "test_results", "kpi_targets", "historical_trends"],
            "active": True,
            "metadata": {"category": "analytics", "expertise_level": "analyst"}
        },
        {
            "agent_id": "designer",
            "display_name": "Email Designer",
            "role": "design",
            "default_provider": "openai",
            "default_model_id": "gpt-4o",
            "prompt_template": """You are an email design specialist focused on creating visually compelling and conversion-optimized email layouts. You understand both aesthetic principles and email technical constraints.

Your design expertise:
- Email template design and layout optimization
- Visual hierarchy and user experience
- Brand-consistent visual elements
- Mobile-responsive design principles
- Email client compatibility considerations

Your design approach:
- Conversion-focused visual design
- Accessibility and inclusivity in design
- Brand alignment in visual elements
- Performance-optimized graphics and layout
- User experience best practices""",
            "capabilities": ["visual_design", "layout_optimization", "mobile_responsive", "brand_visual_alignment"],
            "description": "Visual design and creative direction specialist",
            "variables": ["brand_colors", "visual_style", "layout_preferences", "design_constraints"],
            "active": True,
            "metadata": {"category": "design", "expertise_level": "specialist"}
        }
    ]
    
    try:
        seeded_count = 0
        for agent_data in default_agents:
            agent_id = agent_data["agent_id"]
            
            # Check if agent already exists
            if not db.collection("agents").document(agent_id).get().exists:
                agent_data.update({
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "version": 1
                })
                
                db.collection("agents").document(agent_id).set(agent_data)
                seeded_count += 1
        
        return {
            "success": True,
            "seeded_count": seeded_count,
            "total_default_agents": len(default_agents),
            "message": f"Seeded {seeded_count} default agents"
        }
        
    except Exception as e:
        logger.error(f"Failed to seed default agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Invocation endpoint
@router.post("/{agent_id}/invoke", response_model=Dict[str, Any])
async def invoke_agent(
    agent_id: str,
    request: Dict[str, Any],
    db: firestore.Client = Depends(get_db)
):
    """
    Invoke an agent with the provided context
    This endpoint connects to the AI Orchestrator for actual execution
    """
    try:
        # Get the agent
        agent_doc = db.collection("agents").document(agent_id).get()
        if not agent_doc.exists:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        
        agent_data = agent_doc.to_dict()
        
        # TODO: Integrate with AI Orchestrator for actual execution
        # For now, return a mock response
        return {
            "success": True,
            "agent_id": agent_id,
            "agent_name": agent_data.get("display_name"),
            "provider": agent_data.get("default_provider"),
            "model": agent_data.get("default_model_id"),
            "message": "Agent invocation endpoint ready - integration with AI Orchestrator pending",
            "request_received": request
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invoke agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))