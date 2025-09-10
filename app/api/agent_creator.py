"""
Agent Creator API - Create, optimize, and auto-register new AI agents

TESTING GUIDE:
==============

The /agent/{agent_name}/test endpoint accepts the following request formats:

1. Basic Test (for general agents):
   POST /api/admin/agent-creator/agent/my_agent/test
   {
     "input": "Analyze the Q3 performance metrics for email campaigns",
     "user_id": "test_user",
     "brand": "test_brand"
   }

2. RAG Agent Test:
   POST /api/admin/agent-creator/agent/rag/test
   {
     "input": "What are the best practices for email subject lines?",
     "user_id": "analyst_123"
   }

3. Revenue Analyst Test:
   POST /api/admin/agent-creator/agent/revenue_analyst/test
   {
     "input": "Analyze revenue performance for December 2024",
     "brand": "acme_corp",
     "user_id": "revenue_team"
   }

4. Campaign Planner Test:
   POST /api/admin/agent-creator/agent/campaign_planner/test
   {
     "input": "Create a 5-email holiday campaign plan",
     "brand": "fashion_retailer",
     "user_id": "marketing_manager"
   }

Required fields:
- "input": The task or query for the agent (required)

Optional fields:
- "user_id": For policy resolution and context
- "brand": Brand context for specialized agents
- Additional context fields as needed

Response format:
{
  "agent_name": "agent_name",
  "input": "user_input",
  "output": "agent_response",
  "status": "success|failed",
  "run_id": "uuid",
  "execution_time": "123ms",
  "tool_calls": 2,
  "model": "gemini-1.5-flash",
  "variables_used": ["brand", "task"],
  "error": null
}
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
import os
from pathlib import Path

# Import LangChain system components
try:
    import sys
    sys.path.insert(0, "multi-agent")
    from integrations.langchain_core.admin.registry import AgentRegistry
    from integrations.langchain_core.engine.facade import prepare_run, invoke_agent
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Import Firestore
from google.cloud import firestore
from app.deps.firestore import get_db
from app.deps.secrets import get_secret_manager_service
from app.services.ai_models_service import AIModelsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/agent-creator")


class AgentVariable(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None


class AgentPolicy(BaseModel):
    allowed_tools: List[str] = []
    max_tool_calls: int = 10
    timeout_seconds: int = 30


class AgentConfig(BaseModel):
    name: str = Field(..., description="Agent name (lowercase, underscore-separated)")
    description: str = Field(..., description="Agent description")
    type: str = Field(default="general", description="Agent type")
    version: str = Field(default="1.0", description="Agent version")
    status: str = Field(default="active", description="Agent status")
    prompt_template: str = Field(..., description="System prompt template")
    variables: List[AgentVariable] = []
    policy: AgentPolicy = AgentPolicy()


class PromptOptimizationRequest(BaseModel):
    prompt: str
    agent_type: str = "general"
    optimization_goals: List[str] = ["clarity", "specificity", "task_completion", "safety", "efficiency"]


class PromptOptimizationResponse(BaseModel):
    score: int
    summary: str
    suggestions: List[Dict[str, str]] = []
    optimized_prompt: Optional[str] = None


class PromptOptimizationAIRequest(BaseModel):
    prompt: str
    agent_type: str = "general"
    provider: str = "gemini"  # openai, anthropic, gemini
    include_variables: bool = True  # Whether to suggest EmailPilot variables
    available_variables: Optional[List[str]] = None  # List of available variables to suggest
    workflow_metadata: Optional[Dict[str, Any]] = None  # Workflow context for optimization


class PromptOptimizationAIResponse(BaseModel):
    optimized_prompt: str
    score: Optional[Dict[str, int]] = None  # {"before": 60, "after": 85}
    improvements: List[str] = []
    suggestions: List[str] = []
    provider: str
    model: Optional[str] = None


@router.post("/agents", response_model=Dict[str, Any])
async def create_agent(
    config: AgentConfig,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Create a new AI agent and register it in the system"""
    try:
        # Validate agent name
        if not config.name.islower() or ' ' in config.name:
            raise HTTPException(400, "Agent name must be lowercase with underscores only")
        
        # Check if agent already exists
        agents_ref = db.collection('agents')
        existing = agents_ref.document(config.name).get()
        if existing.exists:
            raise HTTPException(400, f"Agent '{config.name}' already exists")
        
        # Create agent document
        agent_data = {
            "name": config.name,
            "description": config.description,
            "type": config.type,
            "version": config.version,
            "status": config.status,
            "prompt_template": config.prompt_template,
            "system_prompt": config.prompt_template,  # Also store as system_prompt for compatibility
            "variables": [v.dict() for v in config.variables],
            "policy": config.policy.dict(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "created_by": "agent_creator_api"
        }
        
        # Save to Firestore
        agents_ref.document(config.name).set(agent_data)
        logger.info(f"Created agent '{config.name}' in Firestore")
        
        # Register with agent registry in background
        if LANGCHAIN_AVAILABLE:
            background_tasks.add_task(register_agent_with_registry, config.name, agent_data)
        
        # Create agent file in multi-agent directory (optional)
        background_tasks.add_task(create_agent_file, config.name, agent_data)
        
        return {
            "success": True,
            "agent_id": config.name,
            "message": f"Agent '{config.name}' created successfully",
            "data": agent_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(500, f"Failed to create agent: {str(e)}")


@router.post("/optimize-prompt", response_model=PromptOptimizationResponse)
async def optimize_prompt(request: PromptOptimizationRequest):
    """Use AI to optimize and improve an agent prompt"""
    try:
        # Analyze the prompt
        analysis = analyze_prompt(request.prompt, request.agent_type)
        
        # Generate suggestions
        suggestions = generate_suggestions(request.prompt, request.agent_type, analysis)
        
        # Create optimized version
        optimized = create_optimized_prompt(request.prompt, suggestions, request.agent_type)
        
        return PromptOptimizationResponse(
            score=analysis["score"],
            summary=analysis["summary"],
            suggestions=suggestions,
            optimized_prompt=optimized
        )
        
    except Exception as e:
        logger.error(f"Prompt optimization failed: {e}")
        raise HTTPException(500, f"Prompt optimization failed: {str(e)}")


@router.post("/optimize-prompt-ai", response_model=PromptOptimizationAIResponse)
async def optimize_prompt_ai(
    request: PromptOptimizationAIRequest,
    db=Depends(get_db),
    secret_manager=Depends(get_secret_manager_service)
):
    """Use actual AI (LLM) to optimize and improve an agent prompt"""
    try:
        # Initialize AI service
        ai_service = AIModelsService(db, secret_manager)
        
        # First, do a traditional analysis to get the "before" score
        before_analysis = analyze_prompt(request.prompt, request.agent_type)
        before_score = before_analysis["score"]
        
        # Try to load the prompt_optimizer agent for customizable optimization
        optimization_prompt_template = None
        try:
            optimizer_doc = db.collection('agents').document('prompt_optimizer').get()
            if optimizer_doc.exists:
                optimizer_data = optimizer_doc.to_dict()
                optimization_prompt_template = optimizer_data.get('prompt_template') or optimizer_data.get('system_prompt')
                logger.info("Using custom prompt_optimizer agent for optimization")
        except Exception as e:
            logger.warning(f"Could not load prompt_optimizer agent: {e}")
        
        # Check for workflow metadata if provided
        workflow_context_text = ""
        if hasattr(request, 'workflow_metadata') and request.workflow_metadata:
            wm = request.workflow_metadata
            workflow_context_text = f"""
\n\nWORKFLOW CONTEXT:
- Workflow: {wm.get('workflow_id', 'Unknown')}
- Role: {wm.get('role', 'Not specified')}
- Execution Order: {wm.get('order', 'N/A')}
- Dependencies: {', '.join(wm.get('dependencies', [])) if wm.get('dependencies') else 'None'}
- Allowed Tools: {', '.join(wm.get('allowed_tools', [])) if wm.get('allowed_tools') else 'Any'}

Optimize this prompt considering its role in the workflow and its dependencies."""
        
        # Get available variables if requested
        suggested_variables_text = ""
        if request.include_variables and request.available_variables:
            # Filter variables relevant to agent type
            relevant_vars = []
            if request.agent_type == "email":
                relevant_vars = [v for v in request.available_variables if any(
                    keyword in v.lower() for keyword in ['email', 'campaign', 'click', 'open', 'subject']
                )]
            elif request.agent_type == "analytics":
                relevant_vars = [v for v in request.available_variables if any(
                    keyword in v.lower() for keyword in ['metric', 'revenue', 'rate', 'conversion', 'performance']
                )]
            elif request.agent_type == "planning":
                relevant_vars = [v for v in request.available_variables if any(
                    keyword in v.lower() for keyword in ['calendar', 'date', 'month', 'schedule', 'plan']
                )]
            else:
                relevant_vars = request.available_variables[:20]  # Limit for general agents
            
            if relevant_vars:
                suggested_variables_text = f"\n\nAVAILABLE VARIABLES TO CONSIDER ADDING:\n{', '.join(['{' + v + '}' for v in relevant_vars[:15]])}\nAdd these variables where they would provide useful dynamic context."
        
        # Build the optimization prompt - use custom template if available
        if optimization_prompt_template:
            # Replace variables in the template
            optimization_prompt = optimization_prompt_template.replace(
                "{current_prompt}", request.prompt
            ).replace(
                "{agent_type}", request.agent_type
            ).replace(
                "{issues_found}", chr(10).join('- ' + issue for issue in before_analysis.get('issues', [])) + suggested_variables_text + workflow_context_text
            )
        else:
            # Fall back to hardcoded prompt
            optimization_prompt = f"""You are an expert prompt engineer specializing in AI agent optimization for email marketing.

Analyze the following agent prompt and optimize it according to these criteria:

QUALITY CHECKLIST (score each item):
1. Role Definition (10 points): Does it start with "You are..." or clearly define the agent's role?
2. Specificity (10 points): Is the prompt >200 characters with detailed instructions?
3. Structure (10 points): Does it include step-by-step process or clear procedure?
4. Guidelines (10 points): Does it include rules using "must", "should", "always", "never"?
5. Type Relevance (varies): 
   - Email agents: mentions email-specific tasks
   - Analytics agents: mentions data, metrics, analysis
   - Planning agents: mentions strategy, calendars, timing
   - Creative agents: mentions copywriting, design, content
   - General agents: covers broad capabilities

CURRENT PROMPT:
{request.prompt}

AGENT TYPE: {request.agent_type}

CURRENT ISSUES FOUND:
{chr(10).join('- ' + issue for issue in before_analysis.get('issues', []))}
{suggested_variables_text}

ENHANCEMENT REQUIREMENTS:
1. Fix all identified issues above
2. Preserve all existing {{variable_name}} syntax exactly as-is
3. Add relevant context for {request.agent_type} agents
4. Include clear success criteria and output format
5. Add error handling guidelines
6. Make the prompt specific, actionable, and measurable
7. Ensure proper grammar and professional tone

Return ONLY a JSON object with this EXACT structure (no markdown, no extra text):
{{
  "optimized_prompt": "the complete enhanced prompt text here",
  "improvements": [
    "Added clear role definition starting with 'You are...'",
    "Included step-by-step process for task execution",
    "Added specific guidelines for {request.agent_type} tasks"
  ],
  "suggestions": [
    "Consider adding specific KPIs to track",
    "May want to include compliance guidelines"
  ]
}}"""

        # Execute with selected provider
        try:
            response_text = await ai_service.execute_direct(
                prompt=optimization_prompt,
                provider=request.provider
            )
            
            # Parse the AI response
            import re
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback if AI doesn't return proper JSON
                result = {
                    "optimized_prompt": response_text,
                    "improvements": ["AI optimization applied"],
                    "suggestions": []
                }
            
            # Analyze the optimized prompt to get "after" score
            after_analysis = analyze_prompt(result.get("optimized_prompt", request.prompt), request.agent_type)
            after_score = after_analysis["score"]
            
            # Get model info
            model_map = {
                "openai": "gpt-4",
                "gemini": "gemini-1.5-pro-latest",
                "anthropic": "claude-3-5-sonnet-20241022"
            }
            
            return PromptOptimizationAIResponse(
                optimized_prompt=result.get("optimized_prompt", request.prompt),
                score={"before": before_score, "after": after_score},
                improvements=result.get("improvements", []),
                suggestions=result.get("suggestions", []),
                provider=request.provider,
                model=model_map.get(request.provider, request.provider)
            )
            
        except json.JSONDecodeError as je:
            logger.error(f"Failed to parse AI response as JSON: {je}")
            # Return a basic optimization using the traditional method as fallback
            suggestions = generate_suggestions(request.prompt, request.agent_type, before_analysis)
            optimized = create_optimized_prompt(request.prompt, suggestions, request.agent_type)
            
            return PromptOptimizationAIResponse(
                optimized_prompt=optimized,
                score={"before": before_score, "after": 75},
                improvements=["Applied template-based optimization (AI response parsing failed)"],
                suggestions=[s["text"] for s in suggestions],
                provider=request.provider,
                model="fallback"
            )
        
    except Exception as e:
        logger.error(f"AI prompt optimization failed: {e}")
        raise HTTPException(500, f"AI prompt optimization failed: {str(e)}")


@router.post("/registry/update")
async def update_registry(agent_name: str):
    """Update the agent registry after creating a new agent"""
    try:
        if not LANGCHAIN_AVAILABLE:
            raise HTTPException(503, "LangChain system not available")
        
        registry = AgentRegistry()
        # Trigger registry refresh
        registry._initialize_defaults()
        
        return {"success": True, "message": f"Registry updated with agent '{agent_name}'"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registry update failed: {e}")
        raise HTTPException(500, f"Registry update failed: {str(e)}")


@router.post("/agent/{agent_name}/test")
async def test_agent(agent_name: str, request: dict, db=Depends(get_db)):
    """Test an agent with actual LangChain execution"""
    try:
        # Check if agent exists
        doc = db.collection('agents').document(agent_name).get()
        if not doc.exists:
            raise HTTPException(404, f"Agent '{agent_name}' not found")
        
        if not LANGCHAIN_AVAILABLE:
            raise HTTPException(503, "LangChain system not available for testing")
        
        input_text = request.get('input', '')
        if not input_text:
            raise HTTPException(400, "Input text is required for testing")
        
        # Prepare the agent run with defaults for testing
        try:
            prepared = prepare_run(
                agent_name=agent_name,
                user_id=request.get('user_id', 'test_user'),
                brand=request.get('brand', 'test_brand'),
                context={'test_mode': True, 'input': input_text}
            )
        except ValueError as e:
            raise HTTPException(400, f"Agent preparation failed: {str(e)}")
        except Exception as e:
            raise HTTPException(500, f"Failed to prepare agent: {str(e)}")
        
        # Execute the agent
        try:
            result = invoke_agent(
                prepared=prepared,
                task=input_text
            )
            
            return {
                "agent_name": agent_name,
                "input": input_text,
                "output": result.get('final_answer', 'No response generated'),
                "status": "success" if result.get('success') else "failed",
                "run_id": prepared.run_id,
                "execution_time": f"{result.get('metadata', {}).get('duration_ms', 0)}ms",
                "tool_calls": len(result.get('tool_calls', [])),
                "model": prepared.model_config.get('model', 'unknown'),
                "variables_used": list(prepared.variables.keys()),
                "error": result.get('error')
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Agent execution failed: {e}")
            
            # Provide helpful error messages for common issues
            if "not installed" in error_msg or "Provider" in error_msg:
                raise HTTPException(503, f"LangChain dependency missing: {error_msg}")
            elif "not found" in error_msg.lower():
                raise HTTPException(404, f"Agent or model not found: {error_msg}")
            else:
                raise HTTPException(500, f"Agent execution failed: {error_msg}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test agent: {e}")
        raise HTTPException(500, f"Failed to test agent: {str(e)}")


@router.delete("/agent/{agent_name}")
async def delete_agent(agent_name: str, db=Depends(get_db)):
    """Delete an agent by name"""
    try:
        # Check if agent exists
        doc_ref = db.collection('agents').document(agent_name)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(404, f"Agent '{agent_name}' not found")
        
        # Delete the agent
        doc_ref.delete()
        
        logger.info(f"Deleted agent: {agent_name}")
        return {
            "success": True,
            "message": f"Agent '{agent_name}' deleted successfully",
            "agent_name": agent_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_name}: {e}")
        raise HTTPException(500, f"Failed to delete agent: {str(e)}")


@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents(db=Depends(get_db)):
    """List all available agents"""
    try:
        agents_ref = db.collection('agents')
        agents = []
        
        for doc in agents_ref.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            agents.append(data)
        
        return agents
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(500, f"Failed to list agents: {str(e)}")


@router.get("/agents/all", response_model=Dict[str, Any])
async def get_all_agents(db=Depends(get_db)):
    """Get all agents from all sources with workflow metadata"""
    try:
        result = {
            "agents": [],
            "workflows": {},
            "stats": {
                "regular_agents": 0,
                "workflow_agents": 0,
                "system_agents": 0,
                "total": 0
            }
        }
        
        # 1. Get regular agents from 'agents' collection
        agents_ref = db.collection('agents')
        regular_agents = {}
        for doc in agents_ref.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            data['source'] = 'firestore_agents'
            data['agent_type'] = data.get('type', 'regular')
            regular_agents[doc.id] = data
            result['agents'].append(data)
            
            if data.get('type') == 'system':
                result['stats']['system_agents'] += 1
            else:
                result['stats']['regular_agents'] += 1
        
        # 2. Get workflow agents from 'workflow_agents' collection
        workflow_agents_ref = db.collection('workflow_agents')
        for doc in workflow_agents_ref.stream():
            data = doc.to_dict()
            agent_id = doc.id
            
            # Skip if already loaded from regular agents
            if agent_id not in regular_agents:
                # Normalize the structure - extract from config if present
                normalized_data = {
                    'id': agent_id,
                    'name': agent_id,
                    'source': 'firestore_workflow_agents',
                    'agent_type': 'workflow'
                }
                
                # Extract from config if it exists
                if 'config' in data:
                    config = data['config']
                    normalized_data['description'] = config.get('description', '')
                    normalized_data['prompt_template'] = config.get('prompt_template', '')
                    normalized_data['variables'] = config.get('variables', [])
                    normalized_data['policy'] = config.get('policy', {})
                    normalized_data['status'] = config.get('status', 'active')
                    normalized_data['version'] = config.get('version', '1.0')
                    # Keep the original config for reference
                    normalized_data['config'] = config
                else:
                    # If no config, use top-level fields
                    normalized_data.update(data)
                
                # Add workflow metadata
                normalized_data['workflow_metadata'] = {
                    'workflow_id': data.get('workflow', 'unknown'),
                    'role': data.get('role', ''),
                    'order': data.get('order', 0),
                    'dependencies': data.get('dependencies', [])
                }
                
                result['agents'].append(normalized_data)
                result['stats']['workflow_agents'] += 1
        
        # 3. Get workflow agents from calendar_workflow_agents.py if available
        try:
            from app.api.calendar_workflow_agents import AGENT_REGISTRY, WORKFLOWS
            
            # Add workflow metadata
            result['workflows'] = WORKFLOWS
            
            # Add agents from registry that aren't already loaded
            for agent_name, agent_data in AGENT_REGISTRY.items():
                if agent_name not in regular_agents:
                    agent_info = {
                        "id": agent_name,
                        "name": agent_name,
                        "description": agent_data["config"].get("description", ""),
                        "prompt_template": agent_data["config"].get("prompt_template", ""),
                        "variables": agent_data["config"].get("variables", []),
                        "policy": agent_data["config"].get("policy", {}),
                        "source": "workflow_registry",
                        "agent_type": "workflow",
                        "workflow_metadata": {
                            "workflow_id": agent_data.get("workflow"),
                            "role": agent_data.get("role"),
                            "order": agent_data.get("order"),
                            "dependencies": agent_data.get("dependencies", [])
                        }
                    }
                    
                    # Check if this agent was already added from Firestore
                    existing = next((a for a in result['agents'] if a['id'] == agent_name), None)
                    if not existing:
                        result['agents'].append(agent_info)
                        result['stats']['workflow_agents'] += 1
                    elif not existing.get('workflow_metadata'):
                        # Update existing agent with workflow metadata
                        existing['workflow_metadata'] = agent_info['workflow_metadata']
                        
        except ImportError:
            logger.warning("calendar_workflow_agents module not available")
        except Exception as e:
            logger.warning(f"Failed to load workflow agents from registry: {e}")
        
        result['stats']['total'] = len(result['agents'])
        
        # Sort agents by type and name
        result['agents'].sort(key=lambda x: (
            0 if x.get('agent_type') == 'system' else
            1 if x.get('agent_type') == 'workflow' else
            2,
            x.get('name', x.get('id', ''))
        ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get all agents: {e}")
        raise HTTPException(500, f"Failed to get all agents: {str(e)}")


@router.get("/agent/{agent_name}")
async def get_agent(agent_name: str, db=Depends(get_db)):
    """Get details of a specific agent from any collection"""
    try:
        # First try regular agents collection
        doc = db.collection('agents').document(agent_name).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        
        # Try workflow_agents collection
        workflow_doc = db.collection('workflow_agents').document(agent_name).get()
        if workflow_doc.exists:
            data = workflow_doc.to_dict()
            
            # Normalize the structure
            normalized_data = {
                'id': agent_name,
                'name': agent_name,
                'source': 'firestore_workflow_agents',
                'agent_type': 'workflow'
            }
            
            # Extract from config if it exists
            if 'config' in data:
                config = data['config']
                normalized_data['description'] = config.get('description', '')
                normalized_data['prompt_template'] = config.get('prompt_template', '')
                normalized_data['variables'] = config.get('variables', [])
                normalized_data['policy'] = config.get('policy', {})
                normalized_data['status'] = config.get('status', 'active')
                normalized_data['version'] = config.get('version', '1.0')
                normalized_data['config'] = config
            else:
                normalized_data.update(data)
            
            # Add workflow metadata
            normalized_data['workflow_metadata'] = {
                'workflow_id': data.get('workflow', 'unknown'),
                'role': data.get('role', ''),
                'order': data.get('order', 0),
                'dependencies': data.get('dependencies', [])
            }
            
            return normalized_data
        
        # If not found in any collection, try AGENT_REGISTRY
        try:
            from app.api.calendar_workflow_agents import AGENT_REGISTRY
            if agent_name in AGENT_REGISTRY:
                agent_data = AGENT_REGISTRY[agent_name]
                return {
                    "id": agent_name,
                    "name": agent_name,
                    "description": agent_data["config"].get("description", ""),
                    "prompt_template": agent_data["config"].get("prompt_template", ""),
                    "variables": agent_data["config"].get("variables", []),
                    "policy": agent_data["config"].get("policy", {}),
                    "source": "workflow_registry",
                    "agent_type": "workflow",
                    "workflow_metadata": {
                        "workflow_id": agent_data.get("workflow"),
                        "role": agent_data.get("role"),
                        "order": agent_data.get("order"),
                        "dependencies": agent_data.get("dependencies", [])
                    }
                }
        except ImportError:
            pass
        
        raise HTTPException(404, f"Agent '{agent_name}' not found in any collection")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(500, str(e))


@router.put("/agent/{agent_name}")
async def update_agent(
    agent_name: str,
    config: AgentConfig,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Update an existing AI agent"""
    try:
        # Check if agent exists
        agents_ref = db.collection('agents')
        existing = agents_ref.document(agent_name).get()
        if not existing.exists:
            raise HTTPException(404, f"Agent '{agent_name}' not found")
        
        # Update agent document
        agent_data = {
            "name": config.name,
            "description": config.description,
            "type": config.type,
            "version": config.version,
            "status": config.status,
            "prompt_template": config.prompt_template,
            "system_prompt": config.prompt_template,  # Also store as system_prompt for compatibility
            "variables": [v.dict() for v in config.variables],
            "policy": config.policy.dict(),
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": "agent_creator_api"
        }
        
        # Preserve creation metadata
        existing_data = existing.to_dict()
        agent_data["created_at"] = existing_data.get("created_at", datetime.utcnow().isoformat())
        agent_data["created_by"] = existing_data.get("created_by", "agent_creator_api")
        
        # Update in Firestore
        agents_ref.document(agent_name).set(agent_data, merge=True)
        logger.info(f"Updated agent '{agent_name}' in Firestore")
        
        # Register with agent registry in background
        if LANGCHAIN_AVAILABLE:
            background_tasks.add_task(register_agent_with_registry, agent_name, agent_data)
        
        # Update agent file in multi-agent directory
        background_tasks.add_task(create_agent_file, agent_name, agent_data)
        
        return {
            "success": True,
            "agent_id": agent_name,
            "message": f"Agent '{agent_name}' updated successfully",
            "data": agent_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent: {e}")
        raise HTTPException(500, f"Failed to update agent: {str(e)}")


# Helper functions

def analyze_prompt(prompt: str, agent_type: str) -> Dict[str, Any]:
    """Analyze a prompt for quality and completeness"""
    score = 60  # Base score
    issues = []
    
    # Check for role definition
    if any(phrase in prompt.lower() for phrase in ["you are", "act as", "role"]):
        score += 10
    else:
        issues.append("Missing clear role definition")
    
    # Check for specificity
    if len(prompt) > 200:
        score += 10
    elif len(prompt) < 50:
        issues.append("Prompt is too brief")
    
    # Check for structure
    if any(word in prompt.lower() for word in ["step", "process", "procedure", "follow"]):
        score += 10
    else:
        issues.append("Could benefit from step-by-step structure")
    
    # Check for guidelines
    if any(word in prompt.lower() for word in ["guideline", "rule", "must", "should", "always", "never"]):
        score += 10
    
    # Type-specific checks
    if agent_type == "email" and "email" not in prompt.lower():
        issues.append("Email agent should mention email-specific tasks")
        score -= 5
    
    if agent_type == "analytics" and not any(word in prompt.lower() for word in ["data", "metric", "analysis"]):
        issues.append("Analytics agent should mention data analysis")
        score -= 5
    
    # Cap score at 100
    score = min(100, max(0, score))
    
    summary = "Prompt is well-structured" if score >= 80 else "Prompt could be improved"
    if issues:
        summary = f"Found {len(issues)} area(s) for improvement"
    
    return {
        "score": score,
        "summary": summary,
        "issues": issues
    }


def generate_suggestions(prompt: str, agent_type: str, analysis: Dict) -> List[Dict[str, str]]:
    """Generate improvement suggestions based on analysis"""
    suggestions = []
    
    for issue in analysis.get("issues", []):
        if "role definition" in issue:
            suggestions.append({
                "type": "Identity",
                "text": "Start with 'You are a [specific role]' to establish clear identity"
            })
        elif "brief" in issue:
            suggestions.append({
                "type": "Detail",
                "text": "Add specific instructions about desired behavior and outputs"
            })
        elif "step-by-step" in issue:
            suggestions.append({
                "type": "Structure",
                "text": "Include numbered steps or a clear process flow"
            })
    
    # Type-specific suggestions
    if agent_type == "email":
        suggestions.append({
            "type": "Specialization",
            "text": "Include email-specific skills like subject line optimization, personalization"
        })
    elif agent_type == "analytics":
        suggestions.append({
            "type": "Specialization",
            "text": "Mention specific metrics, KPIs, and analysis methodologies"
        })
    
    return suggestions


def create_optimized_prompt(prompt: str, suggestions: List[Dict], agent_type: str) -> str:
    """Create an optimized version of the prompt"""
    
    # Templates for different agent types
    templates = {
        "general": """You are a specialized AI assistant for email marketing automation.

Core Responsibilities:
{responsibilities}

Guidelines:
- Be concise and actionable
- Provide data-driven recommendations
- Maintain consistency with brand guidelines

Process:
1. Understand the request
2. Analyze available data
3. Generate solution
4. Validate and refine

{original_context}""",
        
        "email": """You are an expert email marketing specialist.

Expertise:
- Copywriting (AIDA, PAS, FOMO frameworks)
- Subject line optimization
- Personalization and segmentation
- A/B testing strategies
- Compliance (CAN-SPAM, GDPR)

{original_context}

Always prioritize engagement and conversion while maintaining deliverability.""",
        
        "analytics": """You are a data analytics specialist for email marketing.

Capabilities:
- Performance metric analysis
- Revenue attribution
- Engagement tracking
- Predictive analytics
- Custom reporting

{original_context}

Focus on actionable insights that drive business outcomes."""
    }
    
    # Extract key points from original prompt
    original_context = prompt.strip()
    
    # Get template
    template = templates.get(agent_type, templates["general"])
    
    # Extract responsibilities from original if present
    responsibilities = "- " + "\n- ".join([
        "Analyze campaign performance",
        "Provide optimization recommendations",
        "Support strategic planning"
    ])
    
    # Build optimized prompt
    optimized = template.format(
        responsibilities=responsibilities,
        original_context=original_context
    )
    
    return optimized


async def register_agent_with_registry(agent_name: str, agent_data: Dict):
    """Register agent with the AgentRegistry"""
    try:
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain registry not available")
            return
        
        registry = AgentRegistry()
        registry.register_agent(agent_data)
        logger.info(f"Registered agent '{agent_name}' with registry")
    except Exception as e:
        logger.error(f"Failed to register agent with registry: {e}")


async def create_agent_file(agent_name: str, agent_data: Dict):
    """Create a Python file for the agent in the multi-agent directory"""
    try:
        agents_dir = Path("multi-agent/integrations/langchain_core/agents")
        if not agents_dir.exists():
            logger.warning("Agents directory does not exist")
            return
        
        # Create agent file
        agent_file = agents_dir / f"{agent_name}.py"
        
        # Generate Python code for agent
        code = f'''"""
{agent_data['description']}
Auto-generated by Agent Creator API
"""

from typing import Dict, Any
from ..agents.agent_v2 import Agent

class {agent_name.title().replace('_', '')}Agent(Agent):
    """
    {agent_data['description']}
    """
    
    def __init__(self):
        super().__init__(
            name="{agent_name}",
            description="""{agent_data['description']}""",
            system_prompt="""{agent_data['prompt_template']}""",
            tools={agent_data['policy'].get('allowed_tools', [])},
            max_iterations={agent_data['policy'].get('max_tool_calls', 10)}
        )
    
    async def run(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute the agent task"""
        return await self.execute(task, **kwargs)


# Export agent instance
{agent_name}_agent = {agent_name.title().replace('_', '')}Agent()
'''
        
        # Write file
        agent_file.write_text(code)
        logger.info(f"Created agent file at {agent_file}")
        
    except Exception as e:
        logger.error(f"Failed to create agent file: {e}")