"""
AI Models Management API
Handles API key management and prompt configuration for AI services
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from google.cloud import firestore
from app.deps import get_db
from app.deps.secrets import get_secret_manager_service
from app.services.secrets import SecretManagerService
from app.services.ai_models_service import AIModelsService
from app.services.model_catalog import get_model_catalog
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai-models", tags=["ai-models"])

# Pydantic models
class AIProvider(BaseModel):
    name: str  # "openai", "gemini", "claude"
    secret_name: str  # Secret Manager key name
    is_active: bool = True
    last_validated: Optional[datetime] = None

class AIPrompt(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    prompt_template: str
    model_provider: str  # "openai", "gemini", "claude"
    model_name: Optional[str] = None  # e.g., "gpt-4", "gemini-1.5-pro"
    category: str  # "campaign", "calendar", "goals", "agent", "analysis"
    variables: List[str] = []  # List of template variables
    active: bool = True
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    metadata: Dict[str, Any] = {}

class APIKeyUpdate(BaseModel):
    provider: str  # "openai", "gemini", "claude"
    api_key: str

class PromptTestRequest(BaseModel):
    prompt_id: str
    variables: Dict[str, Any] = {}
    use_mock: bool = True  # For testing without actually calling the AI

# Pipeline config model
class AIPipelineConfig(BaseModel):
    provider: str = Field(..., description="AI provider key, e.g., gemini|openai|claude|agents")
    model_name: Optional[str] = Field(None, description="Model identifier, e.g., gemini-1.5-pro-latest")
    use_orchestrator: bool = Field(False, description="Route via MultiAgentOrchestrator")
    prompt_id: Optional[str] = Field(None, description="Optional prompt template ID to use")
    updated_at: Optional[datetime] = None

# Provider configuration
PROVIDER_CONFIG = {
    "openai": {
        "secret_name": "openai-api-key",
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "default_model": "gpt-4"
    },
    "gemini": {
        "secret_name": "gemini-api-key",
        "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-pro-latest"],
        "default_model": "gemini-1.5-pro-latest"
    },
    "claude": {
        "secret_name": "emailpilot-claude",
        "models": [
            "claude-3-opus-20240229", 
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ],
        "default_model": "claude-3-5-sonnet-20241022"
    }
}

# Endpoints

@router.get("/providers")
async def get_providers(
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> Dict[str, Any]:
    """Get AI provider configuration and status"""
    providers = []
    
    for provider_name, config in PROVIDER_CONFIG.items():
        provider_info = {
            "name": provider_name,
            "secret_name": config["secret_name"],
            "models": config["models"],
            "default_model": config["default_model"],
            "has_key": False,
            "is_active": False
        }
        
        # Check if API key exists in Secret Manager
        try:
            secret = secret_manager.get_secret(config["secret_name"])
            provider_info["has_key"] = bool(secret)
            provider_info["is_active"] = bool(secret)
        except Exception as e:
            logger.warning(f"Could not check {provider_name} API key: {e}")
        
        providers.append(provider_info)
    
    return {"providers": providers}

@router.post("/providers/{provider}/api-key")
async def update_api_key(
    provider: str,
    request: APIKeyUpdate,
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> Dict[str, Any]:
    """Update API key for a provider in Secret Manager"""
    
    if provider not in PROVIDER_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
    
    secret_name = PROVIDER_CONFIG[provider]["secret_name"]
    
    try:
        # Create or update the secret
        secret_manager.create_or_update_secret(secret_name, request.api_key)
        
        return {
            "success": True,
            "provider": provider,
            "secret_name": secret_name,
            "message": f"API key for {provider} updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update API key for {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/providers/{provider}/api-key")
async def delete_api_key(
    provider: str,
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> Dict[str, Any]:
    """Delete API key for a provider from Secret Manager"""
    
    if provider not in PROVIDER_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
    
    secret_name = PROVIDER_CONFIG[provider]["secret_name"]
    
    try:
        # Delete the secret
        secret_manager.delete_secret(secret_name)
        
        return {
            "success": True,
            "provider": provider,
            "message": f"API key for {provider} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Failed to delete API key for {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prompts")
async def get_prompts(
    category: Optional[str] = None,
    provider: Optional[str] = None,
    active_only: bool = True,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    DEPRECATED: Get all AI prompts from Firestore
    
    This endpoint is deprecated. Agent-related prompts have been migrated to
    the unified agents system at /api/agents/. 
    
    Please use /api/agents/ for all agent management.
    """
    import warnings
    warnings.warn("The /api/ai-models/prompts endpoint is deprecated. Use /api/agents/ instead.", DeprecationWarning)
    
    try:
        prompts_ref = db.collection("ai_prompts")
        
        # Apply filters
        if active_only:
            prompts_ref = prompts_ref.where("active", "==", True)
        if category:
            prompts_ref = prompts_ref.where("category", "==", category)
        if provider:
            prompts_ref = prompts_ref.where("model_provider", "==", provider)
        
        prompts = []
        for doc in prompts_ref.stream():
            prompt_data = doc.to_dict()
            prompt_data["id"] = doc.id
            prompts.append(prompt_data)
        
        return {
            "prompts": prompts,
            "total": len(prompts),
            "filters": {
                "category": category,
                "provider": provider,
                "active_only": active_only
            },
            "deprecated": True,
            "deprecation_notice": "This endpoint is deprecated. Agent-related prompts have been migrated to /api/agents/. Please update your code to use the unified agents API.",
            "migration_url": "/api/agents/"
        }
    except Exception as e:
        logger.error(f"Failed to fetch prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pipelines/{pipeline_name}")
async def get_pipeline_config(
    pipeline_name: str,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get AI pipeline configuration (e.g., calendar_planning)."""
    try:
        doc = db.collection("ai_pipelines").document(pipeline_name).get()
        if not doc.exists:
            # Sensible default: gemini
            default_cfg = {
                "provider": "gemini",
                "model_name": PROVIDER_CONFIG["gemini"]["default_model"],
                "use_orchestrator": False,
                "prompt_id": None,
                "updated_at": datetime.utcnow().isoformat()
            }
            return {"exists": False, "config": default_cfg}
        cfg = doc.to_dict()
        return {"exists": True, "config": cfg}
    except Exception as e:
        logger.error(f"Failed to get pipeline {pipeline_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pipelines/{pipeline_name}")
async def set_pipeline_config(
    pipeline_name: str,
    config: AIPipelineConfig,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Create or update AI pipeline configuration."""
    try:
        cfg = config.dict(exclude_none=True)
        cfg["updated_at"] = datetime.utcnow().isoformat()
        db.collection("ai_pipelines").document(pipeline_name).set(cfg)
        return {"success": True, "pipeline": pipeline_name, "config": cfg}
    except Exception as e:
        logger.error(f"Failed to set pipeline {pipeline_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific prompt by ID"""
    
    try:
        doc = db.collection("ai_prompts").document(prompt_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        prompt_data = doc.to_dict()
        prompt_data["id"] = doc.id
        
        return prompt_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prompts")
async def create_or_update_prompt(
    prompt: AIPrompt,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Create or update an AI prompt"""
    
    try:
        prompt_data = prompt.dict(exclude_none=True)
        prompt_data["updated_at"] = datetime.utcnow()
        
        if prompt.id:
            # Update existing prompt
            doc_ref = db.collection("ai_prompts").document(prompt.id)
            doc = doc_ref.get()
            
            if doc.exists:
                # Increment version
                current_data = doc.to_dict()
                prompt_data["version"] = current_data.get("version", 1) + 1
            else:
                prompt_data["created_at"] = datetime.utcnow()
            
            doc_ref.set(prompt_data)
            prompt_id = prompt.id
        else:
            # Create new prompt
            prompt_data["created_at"] = datetime.utcnow()
            doc_ref = db.collection("ai_prompts").add(prompt_data)[1]
            prompt_id = doc_ref.id
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "message": "Prompt saved successfully"
        }
    except Exception as e:
        logger.error(f"Failed to save prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a prompt (soft delete by setting active=false)"""
    
    try:
        doc_ref = db.collection("ai_prompts").document(prompt_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        # Soft delete
        doc_ref.update({
            "active": False,
            "updated_at": datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": "Prompt deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prompts/{prompt_id}/test")
async def test_prompt(
    prompt_id: str,
    request: PromptTestRequest,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> Dict[str, Any]:
    """Test a prompt with variables (mock or real)"""
    
    try:
        # Get the prompt
        doc = db.collection("ai_prompts").document(prompt_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        prompt_data = doc.to_dict()
        prompt_template = prompt_data["prompt_template"]
        
        # Replace variables in template
        rendered_prompt = prompt_template
        for var_name, var_value in request.variables.items():
            rendered_prompt = rendered_prompt.replace(f"{{{var_name}}}", str(var_value))
        
        # Update usage stats
        db.collection("ai_prompts").document(prompt_id).update({
            "last_used": datetime.utcnow(),
            "usage_count": firestore.Increment(1)
        })
        
        if request.use_mock:
            # Return mock response
            return {
                "success": True,
                "rendered_prompt": rendered_prompt,
                "provider": prompt_data["model_provider"],
                "model": prompt_data.get("model_name"),
                "mock_response": f"This is a mock response for the {prompt_data['model_provider']} provider using prompt: {prompt_data['name']}",
                "variables_used": request.variables
            }
        else:
            # TODO: Integrate with actual AI services via AgentService
            return {
                "success": True,
                "rendered_prompt": rendered_prompt,
                "provider": prompt_data["model_provider"],
                "model": prompt_data.get("model_name"),
                "message": "Real AI integration pending AgentService connection",
                "variables_used": request.variables
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/migrate-existing-prompts")
async def migrate_existing_prompts(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """One-time migration to import existing prompts from the codebase"""
    
    # This is where we'll add the prompts found in the codebase
    initial_prompts = [
        {
            "name": "Campaign Planning Strategy",
            "description": "Comprehensive campaign planning with touchpoints",
            "prompt_template": """You are an expert email marketing strategist. Create a comprehensive campaign plan for the following:

**Campaign Details:**
- Client ID: {client_id}
- Campaign Type: {campaign_type}
- Start Date: {start_date}
- End Date: {end_date}
- Promotion Details: {promotion_details}

[Rest of prompt...]""",
            "model_provider": "gemini",
            "model_name": "gemini-1.5-pro-latest",
            "category": "campaign",
            "variables": ["client_id", "campaign_type", "start_date", "end_date", "promotion_details"],
            "active": True,
            "metadata": {
                "source_file": "app/services/gemini_service.py",
                "line_numbers": "57-112"
            }
        },
        {
            "name": "Calendar AI Assistant",
            "description": "Interactive calendar management assistant",
            "prompt_template": """You are a Calendar AI Assistant. Your capabilities are to answer questions about the calendar events and to perform actions to modify the calendar.

Today's date is: {today}
Current client: {client_name}
Calendar data: {events_data}

[Rest of prompt...]""",
            "model_provider": "gemini",
            "model_name": "gemini-1.5-pro-latest",
            "category": "calendar",
            "variables": ["today", "client_name", "events_data"],
            "active": True,
            "metadata": {
                "source_file": "app/services/gemini_service.py",
                "line_numbers": "318-342"
            }
        },
        {
            "name": "Revenue-Driven Strategy",
            "description": "Goal-aware campaign strategy with revenue focus",
            "prompt_template": """You are an AI marketing strategist for EmailPilot, specializing in revenue-driven email campaign planning.

{goals_context}
{events_context}
{history_context}

User Question: {message}""",
            "model_provider": "gemini",
            "model_name": "gemini-1.5-pro-latest",
            "category": "goals",
            "variables": ["goals_context", "events_context", "history_context", "message"],
            "active": True,
            "metadata": {
                "source_file": "app/services/goals_aware_gemini_service.py",
                "line_numbers": "77-101"
            }
        },
        {
            "name": "Content Strategist Agent",
            "description": "Senior email marketing strategist agent instructions",
            "prompt_template": """You are a senior email marketing strategist with 10+ years of experience in developing data-driven campaign strategies. Your role is to create comprehensive messaging frameworks that align with business objectives and customer psychology.

Constraints:
- Always consider the full customer journey
- Base strategies on data and best practices
- Maintain brand consistency across all touchpoints""",
            "model_provider": "claude",
            "model_name": "claude-3-5-sonnet-20241022",
            "category": "agent",
            "variables": [],
            "active": True,
            "metadata": {
                "source_file": "email-sms-mcp-server/agent_instructions.py",
                "agent_type": "content_strategist"
            }
        },
        {
            "name": "Monthly Goals Generator",
            "description": "Generate monthly revenue goals with seasonality",
            "prompt_template": """Generate monthly revenue goals for {client_name} for year {target_year}.
Base monthly goal: ${base_goal}

Consider seasonality patterns and provide monthly goals.
Return ONLY a JSON object with keys 1-12 (months) and revenue values.""",
            "model_provider": "gemini",
            "model_name": "gemini-1.5-flash",
            "category": "goals",
            "variables": ["client_name", "target_year", "base_goal"],
            "active": True,
            "metadata": {
                "source_file": "app/services/goal_generator.py",
                "line_numbers": "101-110"
            }
        }
    ]
    
    try:
        migrated_count = 0
        for prompt_data in initial_prompts:
            # Check if prompt already exists by name
            existing = db.collection("ai_prompts").where("name", "==", prompt_data["name"]).limit(1).get()
            
            if not existing:
                prompt_data["created_at"] = datetime.utcnow()
                prompt_data["updated_at"] = datetime.utcnow()
                prompt_data["version"] = 1
                prompt_data["usage_count"] = 0
                
                db.collection("ai_prompts").add(prompt_data)
                migrated_count += 1
        
        return {
            "success": True,
            "migrated_count": migrated_count,
            "message": f"Successfully migrated {migrated_count} prompts"
        }
    except Exception as e:
        logger.error(f"Failed to migrate prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats(
    timeframe: Optional[str] = Query(None, description="Usage window: mtd, last_month, 7d, 30d, 90d"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get statistics about AI models usage"""
    
    try:
        prompts = db.collection("ai_prompts").stream()
        
        stats = {
            "total_prompts": 0,
            "active_prompts": 0,
            "by_provider": {"openai": 0, "gemini": 0, "claude": 0},
            "by_category": {},
            "most_used": [],
            "recently_used": []
        }
        
        all_prompts = []
        for doc in prompts:
            prompt_data = doc.to_dict()
            prompt_data["id"] = doc.id
            all_prompts.append(prompt_data)
            
            stats["total_prompts"] += 1
            if prompt_data.get("active", True):
                stats["active_prompts"] += 1
            
            provider = prompt_data.get("model_provider", "unknown")
            if provider in stats["by_provider"]:
                stats["by_provider"][provider] += 1
            
            category = prompt_data.get("category", "uncategorized")
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        # Sort by usage count for most used
        all_prompts.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
        stats["most_used"] = [
            {"name": p["name"], "usage_count": p.get("usage_count", 0)}
            for p in all_prompts[:5]
        ]
        
        # Sort by last used for recently used
        prompts_with_usage = [p for p in all_prompts if p.get("last_used")]
        prompts_with_usage.sort(key=lambda x: x.get("last_used", datetime.min), reverse=True)
        stats["recently_used"] = [
            {"name": p["name"], "last_used": p.get("last_used").isoformat() if p.get("last_used") else None}
            for p in prompts_with_usage[:5]
        ]
        
        # Aggregate usage logs by user and by client
        try:
            usage_docs = db.collection("ai_prompt_usage").stream()
            # Timeframe filtering (in-Python for simplicity)
            start = None
            end = None
            now = datetime.utcnow()
            if timeframe:
                tf = timeframe.lower()
                if tf in ("7d", "7days"):
                    start = now.replace(microsecond=0) - timedelta(days=7)
                elif tf in ("30d", "30days"):
                    start = now.replace(microsecond=0) - timedelta(days=30)
                elif tf in ("90d", "90days"):
                    start = now.replace(microsecond=0) - timedelta(days=90)
                elif tf in ("mtd", "month_to_date"):
                    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                elif tf in ("last_month", "lm"):
                    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    last_month_end = first_of_this_month
                    if first_of_this_month.month == 1:
                        first_of_last_month = first_of_this_month.replace(year=first_of_this_month.year-1, month=12)
                    else:
                        first_of_last_month = first_of_this_month.replace(month=first_of_this_month.month-1)
                    start = first_of_last_month
                    end = last_month_end
            by_user: Dict[str, int] = {}
            by_client: Dict[str, int] = {}
            for d in usage_docs:
                u = d.to_dict() or {}
                user_id = (u.get("user_id") or "unknown").strip() if isinstance(u.get("user_id"), str) else (u.get("user_id") or "unknown")
                client_id = (u.get("client_id") or "unknown").strip() if isinstance(u.get("client_id"), str) else (u.get("client_id") or "unknown")
                ts = u.get("timestamp")
                try:
                    if isinstance(ts, str):
                        # Allow ISO strings
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    ts = None
                # Apply timeframe filter if present
                if start is not None:
                    if ts is None or ts < start:
                        continue
                if end is not None and ts is not None and ts >= end:
                    continue
                by_user[user_id] = by_user.get(user_id, 0) + 1
                by_client[client_id] = by_client.get(client_id, 0) + 1
            # Order and trim
            def top_list(d: Dict[str, int], n=5):
                return sorted(({"id": k, "count": v} for k, v in d.items()), key=lambda x: x["count"], reverse=True)[:n]
            stats["by_user"] = top_list(by_user, 10)
            stats["by_client"] = top_list(by_client, 10)
        except Exception as e:
            logger.warning(f"Failed to aggregate usage logs: {e}")

        stats["timeframe"] = timeframe
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variables")
async def get_variables(
    client_id: Optional[str] = None,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Return available variables for prompts: client fields and known context variables.

    If client_id is provided, returns top-level and shallow-nested keys from that client document.
    """
    def flatten_keys(d: Dict[str, Any], prefix: str = "", depth: int = 1) -> List[str]:
        keys: List[str] = []
        for k, v in (d or {}).items():
            path = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            keys.append(path)
            if depth > 0 and isinstance(v, dict):
                keys.extend(flatten_keys(v, path, depth-1))
        return keys

    known_variables = [
        "agent_name", "agent_role", "agent_expertise", "agent_responsibilities",
        "request_data", "timestamp", "collaboration_with",
        "campaign_type", "target_audience", "objective"
    ]

    client_variables: List[str] = []
    if client_id:
        try:
            doc = db.collection("clients").document(client_id).get()
            if doc.exists:
                client_variables = flatten_keys(doc.to_dict(), depth=2)
        except Exception as e:
            logger.warning(f"Failed to load client variables for {client_id}: {e}")

    services_variables = {
        "performance": ["mtd_revenue", "mtd_orders", "aov", "open_rate", "click_rate"],
        "goals": ["monthly_goal", "quarter_goal", "annual_goal"],
        "calendar": ["next_campaign_date", "campaign_count_week", "seasonality_tag"],
    }

    return {
        "known_variables": known_variables,
        "client_variables": client_variables,
        "services_variables": services_variables
    }
class PromptDesignerRequest(BaseModel):
    workflow: str = Field(..., description="Workflow context, e.g., 'klaviyo_weekly_full', 'klaviyo_monthly', 'mcp_chat'")
    goal: str = Field(..., description="User goal, e.g., 'generate per-client weekly insights with 4 bullets each section'")
    constraints: Optional[str] = Field(default=None, description="Any constraints like formatting or tokens")
    provider: Optional[str] = Field(default=None, description="Preferred provider: openai|gemini|claude")
    model: Optional[str] = Field(default=None, description="Model name, e.g., 'gpt-4', 'gpt-4o', 'gemini-1.5-pro-latest', 'claude-3-sonnet', 'gpt-5' if available")
    include_context: bool = Field(default=True, description="Include system context about app endpoints and MCP")

class ModelValidateRequest(BaseModel):
    provider: str = Field(..., description="Provider name: openai, claude, gemini")

@router.post("/prompt-designer/chat")
async def prompt_designer_chat(
    req: PromptDesignerRequest,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service),
):
    """Design or refine prompts optimized for MCP workflows using selected provider.

    Returns a structured prompt template, variables list, and rationale.
    """
    ai = AIModelsService(db, secret_manager)
    system = """
You are the EmailPilot Prompt Designer. You understand:
- Backend endpoints under /api/reports/mcp/v2 (weekly insights) and /api/reports/monthly/generate
- MCP Klaviyo API: weekly/metrics and weekly/full endpoints (campaign/flow and engagement)
- Admin prompt storage in Firestore (collection ai_prompts) with variables support
- Slack formatting limits (~3000 chars per block)
Design concise, robust prompts that yield deterministic bullet lists and adhere to specified formats.
""".strip()
    user = f"""
WORKFLOW: {req.workflow}
GOAL: {req.goal}
CONSTRAINTS: {req.constraints or 'none'}
Please output JSON:
{{
  "prompt_template": "...",
  "variables": ["var1","var2",...],
  "notes": "rationale and tips"
}}
""".strip()
    content = f"{system}\n\n{user}" if req.include_context else user
    provider = req.provider or "openai"
    model = req.model or ("gpt-4" if provider == "openai" else ("gemini-1.5-pro-latest" if provider == "gemini" else "claude-3-5-sonnet-20241022"))
    try:
        # Use plain text execution path; providers may ignore system vs user roles in this simplified interface
        if provider == "openai":
            text = await ai._execute_openai(content, model)
        elif provider == "gemini":
            text = await ai._execute_gemini(content, model)
        elif provider == "claude":
            text = await ai._execute_claude(content, model)
        else:
            return {"success": False, "error": f"Unsupported provider {provider}"}
        # Try to parse JSON
        data = None
        try:
            data = json.loads(text)
        except Exception:
            data = {"prompt_template": text, "variables": [], "notes": "Model did not return strict JSON"}
        return {"success": True, "provider": provider, "model": model, "result": data}
    except Exception as e:
        logger.error(f"Prompt designer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Model Chat endpoints
class ChatCompleteRequest(BaseModel):
    provider: str = Field(..., description="AI provider: openai|claude|gemini")
    model: str = Field(..., description="Model name, e.g., gpt-4, claude-3-sonnet")
    messages: List[Dict[str, str]] = Field(..., description="Chat messages with role and content")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(512, ge=1, le=4096, description="Maximum tokens in response")
    agent_type: Optional[str] = Field(None, description="Optional agent type to use for system prompt")

class ChatCompleteResponse(BaseModel):
    ok: bool
    output_message: Optional[Dict[str, str]] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None

@router.get("/models/health")
async def get_models_with_health() -> Dict[str, Any]:
    """Get all available models with health status"""
    try:
        from app.services.model_health_probe import get_health_probe
        probe = get_health_probe()
        
        # Get health status and models
        health_status = await probe.probe_all()
        models = await probe.get_healthy_models()
        
        return {
            "success": True,
            "models": models,
            "health": health_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get models with health: {e}")
        return {
            "success": False,
            "models": [],
            "health": {},
            "error": str(e)
        }

@router.get("/models")
async def get_models_for_provider(
    provider: str = Query(..., description="Provider name: openai|claude|gemini"),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> Dict[str, Any]:
    """Get available models for a specific provider from live discovery"""
    valid_providers = ["openai", "claude", "gemini"]
    if provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}. Must be one of: {', '.join(valid_providers)}")
    
    try:
        catalog = get_model_catalog(secret_manager)
        models = await catalog.get_models(provider)
        
        # Convert to response format
        model_list = [m.to_dict() for m in models if not m.deprecated]
        deprecated_list = [m.to_dict() for m in models if m.deprecated]
        
        # Get cache info
        cache_info = catalog.get_cache_info()
        provider_cache = cache_info["providers"].get(provider, {})
        
        return {
            "provider": provider,
            "models": model_list,
            "deprecated_models": deprecated_list,
            "cache_info": {
                "cached_at": provider_cache.get("cached_at"),
                "age_minutes": provider_cache.get("age_minutes"),
                "is_valid": provider_cache.get("is_valid", False)
            },
            "default_model": model_list[0]["id"] if model_list else None
        }
    except Exception as e:
        logger.error(f"Error getting models for {provider}: {e}")
        # Fallback to static config if catalog fails
        if provider in PROVIDER_CONFIG:
            return {
                "provider": provider,
                "models": [{"id": m, "label": m} for m in PROVIDER_CONFIG[provider]["models"]],
                "default_model": PROVIDER_CONFIG[provider]["default_model"],
                "error": str(e)
            }
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
async def refresh_models(
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> Dict[str, Any]:
    """Force refresh all provider model catalogs"""
    try:
        catalog = get_model_catalog(secret_manager)
        results = await catalog.refresh_all()
        
        summary = {}
        for provider, models in results.items():
            summary[provider] = {
                "count": len(models),
                "models": [m.id for m in models if not m.deprecated],
                "deprecated": [m.id for m in models if m.deprecated]
            }
        
        return {
            "success": True,
            "message": "Model catalogs refreshed",
            "summary": summary,
            "cache_info": catalog.get_cache_info()
        }
    except Exception as e:
        logger.error(f"Error refreshing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/complete", response_model=ChatCompleteResponse)
async def chat_complete(
    request: ChatCompleteRequest,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> ChatCompleteResponse:
    """
    Complete a chat conversation using the specified provider and model.
    Optionally prepend an agent's system prompt.
    """
    try:
        # Import AIModelsService if not already available
        try:
            from app.services.ai_models_service import AIModelsService as AIModelsSvc
        except ImportError:
            logger.error("Failed to import AIModelsService")
            return ChatCompleteResponse(
                ok=False,
                error={"message": "AI Models Service not available", "code": "service_unavailable"}
            )
        
        # Validate provider
        valid_providers = ["openai", "claude", "gemini"]
        if request.provider not in valid_providers:
            return ChatCompleteResponse(
                ok=False,
                error={"message": f"Invalid provider: {request.provider}", "code": "invalid_provider"}
            )
        
        # Validate model against live catalog
        catalog = get_model_catalog(secret_manager)
        models = await catalog.get_models(request.provider)
        model_ids = {m.id for m in models if not m.deprecated}
        
        if request.model not in model_ids:
            # Check if it's deprecated
            deprecated_ids = {m.id for m in models if m.deprecated}
            if request.model in deprecated_ids:
                return ChatCompleteResponse(
                    ok=False,
                    error={
                        "message": f"Model {request.model} is deprecated or unavailable",
                        "code": "model_deprecated"
                    }
                )
            else:
                # Suggest available models
                available = list(model_ids)[:3]
                return ChatCompleteResponse(
                    ok=False,
                    error={
                        "message": f"Unknown model {request.model} for {request.provider}. Available: {', '.join(available)}",
                        "code": "invalid_model"
                    }
                )
        
        # Initialize AI service
        ai_service = AIModelsSvc(db, secret_manager)
        
        # Prepare messages
        messages = request.messages.copy()
        
        # If agent_type is specified, prepend agent system prompt
        if request.agent_type:
            try:
                # Try to get agent-specific prompt from Firestore
                agent_prompts = await ai_service.get_prompts_by_category("agent")
                agent_prompt = None
                for prompt in agent_prompts:
                    if prompt.get("metadata", {}).get("agent_type") == request.agent_type:
                        agent_prompt = prompt
                        break
                
                if agent_prompt:
                    system_content = f"You are the {request.agent_type} agent. {agent_prompt.get('prompt_template', '')}"
                else:
                    # Fallback to basic agent description
                    system_content = f"You are the {request.agent_type} agent for EmailPilot."
                
                # Prepend system message
                messages.insert(0, {"role": "system", "content": system_content})
            except Exception as e:
                logger.warning(f"Could not load agent prompt for {request.agent_type}: {e}")
        
        # Call the AI service complete method
        result = await ai_service.complete(
            provider=request.provider,
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if result.get("success"):
            response = ChatCompleteResponse(
                ok=True,
                output_message={"role": "assistant", "content": result["response"]},
                usage=result.get("usage", {})
            )
            # Add warnings if any
            if result.get("warnings"):
                response.warnings = result["warnings"]
            return response
        else:
            return ChatCompleteResponse(
                ok=False,
                error={
                    "message": result.get("error", "Unknown error"),
                    "provider": request.provider,
                    "code": "completion_failed"
                }
            )
            
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        return ChatCompleteResponse(
            ok=False,
            error={
                "message": str(e),
                "provider": request.provider,
                "code": "internal_error"
            }
        )

# LangChain compatibility endpoints for admin interface
@router.post("/admin/langchain/models/validate")
async def validate_langchain_model(
    request: ModelValidateRequest,
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> Dict[str, Any]:
    """
    Validate API key for a specific provider.
    
    This endpoint validates that API keys are properly loaded from Secret Manager
    and have the correct format. It provides helpful hints for configuration.
    
    Args:
        request: Provider name to validate (openai, claude, gemini)
        secret_manager: Injected Secret Manager service
        
    Returns:
        Validation results with status and helpful messages
    """
    try:
        # Map provider names to standard API key names
        provider_to_key = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY", 
            "gemini": "GOOGLE_API_KEY"
        }
        
        # Validate provider
        if request.provider not in provider_to_key:
            return {
                "valid": False,
                "message": f"Invalid provider '{request.provider}'",
                "hint": f"Supported providers: {', '.join(provider_to_key.keys())}"
            }
        
        key_name = provider_to_key[request.provider]
        
        # Use the Secret Manager service to validate the key
        result = secret_manager.validate_ai_provider_key(key_name)
        
        # Add provider-specific information
        result["provider"] = request.provider
        result["key_name"] = key_name
        
        # Add configuration hints
        if not result["valid"]:
            secret_name = secret_manager.AI_PROVIDER_SECRETS.get(key_name)
            if secret_name:
                result["hint"] += f" | Secret name: {secret_name}"
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating {request.provider} model: {e}")
        return {
            "valid": False,
            "message": f"Validation error: {str(e)}",
            "hint": "Check Secret Manager configuration and permissions",
            "provider": request.provider
        }
