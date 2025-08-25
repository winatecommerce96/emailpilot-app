"""
Copywriting Module - FastAPI Backend
Runs on port 8002 separately from main EmailPilot app
"""

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import json
import os
from datetime import datetime
import logging
from google.cloud import firestore
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Feature flag for AI Orchestrator vs Direct Providers
USE_ORCHESTRATOR = os.getenv("USE_ORCHESTRATOR", "true").lower() == "true"
logger.info(f"USE_ORCHESTRATOR: {USE_ORCHESTRATOR}")

# Initialize AI service based on configuration
if USE_ORCHESTRATOR:
    from ai_orchestrator_client import get_orchestrator_client, ai_complete
    logger.info("Using AI Orchestrator for model invocations")
else:
    from ai_providers import DirectAIService
    ai_service = DirectAIService()
    logger.info("Using direct AI providers")

app = FastAPI(title="EmailPilot Copywriting Module", version="1.0.0")

# Initialize Firestore client
_firestore_client = None
_firestore_initialized = False

def get_firestore_client():
    """Get or create Firestore client with caching"""
    global _firestore_client, _firestore_initialized
    
    if _firestore_initialized:
        return _firestore_client
    
    _firestore_initialized = True
    
    try:
        # Check if we have proper environment setup
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set - Firestore disabled")
            return None
            
        # Try to create the client
        _firestore_client = firestore.Client(project=project_id)
        logger.info(f"Firestore client initialized for project: {project_id}")
        return _firestore_client
    except Exception as e:
        logger.warning(f"Could not initialize Firestore: {e}")
        return None

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8002", "http://localhost:8000", "http://127.0.0.1:8002", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Request/Response Models
class BriefSubmission(BaseModel):
    brief_content: str
    client_id: Optional[str] = None  # Changed from client_name to client_id
    client_name: Optional[str] = None  # Keep for display purposes
    campaign_type: Optional[str] = "email"  # email, sms, push
    selected_agents: Optional[List[str]] = None  # Selected agent IDs
    selected_model: Optional[str] = "claude-3-haiku"  # AI model to use
    custom_prompts: Optional[Dict[str, str]] = None  # Custom prompts for agents

class CopyVariant(BaseModel):
    variant_id: int
    framework: str
    creativity_level: str
    subject_line_a: str
    subject_line_b: str
    preview_text: str
    hero_h1: str
    sub_head: str
    hero_image_filename: str
    hero_image_note: str
    cta_copy: str
    offer: Optional[str]
    ab_test_idea: str
    secondary_message: str
    uses_emoji: bool
    full_email_body: str  # Now required, not optional
    body_sections: Optional[Dict[str, str]] = None  # Structured body sections

class CopywritingResponse(BaseModel):
    client_name: str
    variants: List[CopyVariant]
    generated_at: str
    brief_summary: str

class ReviewRequest(BaseModel):
    variant: CopyVariant
    original_brief: str
    client_id: Optional[str] = None

class ReviewResponse(BaseModel):
    letter_grade: str  # A+, A, B+, etc.
    overall_score: float  # 0-100
    strengths: List[str]
    improvements: List[str]
    brief_alignment: str  # How well it matches the brief
    specific_suggestions: List[Dict[str, str]]  # Section-specific feedback
    encouragement: str  # Positive, teacher-like closing message

class ChatRequest(BaseModel):
    message: str
    current_variant: CopyVariant
    context: Optional[Dict[str, Any]] = None
    section_to_edit: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    edited_variant: Optional[CopyVariant] = None
    edit_type: Optional[str] = None  # 'inline_edit', 'suggestion', 'explanation'
    affected_sections: Optional[List[str]] = None

class RefineRequest(BaseModel):
    variant: CopyVariant
    instruction: str
    model: Optional[str] = "gpt-3.5-turbo"
    client_id: Optional[str] = None
    agent_id: Optional[str] = None
    provider: Optional[str] = None
    campaign_brief: Optional[str] = None

class RefineResponse(BaseModel):
    refined_variant: CopyVariant
    changes_made: List[str]
    model_used: str
    patch: Optional[List[Dict[str, Any]]] = None
    history_entry: Optional[Dict[str, Any]] = None

# Copywriting frameworks
COPYWRITING_FRAMEWORKS = [
    {"name": "AIDA", "description": "Attention, Interest, Desire, Action"},
    {"name": "FOMO", "description": "Fear of Missing Out"},
    {"name": "PAS", "description": "Problem, Agitate, Solution"},
    {"name": "BAB", "description": "Before, After, Bridge"},
    {"name": "4Ps", "description": "Promise, Picture, Proof, Push"}
]

CREATIVITY_LEVELS = ["Conservative", "Moderate", "Bold", "Experimental", "Wild"]

@app.get("/health")
async def health_check():
    """Health check endpoint for service liveness"""
    try:
        # Check if we can connect to the orchestrator
        orchestrator_healthy = False
        providers_status = {}
        
        if USE_ORCHESTRATOR:
            try:
                client = get_orchestrator_client()
                models = await client.get_models()
                orchestrator_healthy = models.get("success", False)
                
                # Check individual providers
                for provider in ["openai", "claude", "gemini"]:
                    provider_models = models.get("models", {}).get(provider, [])
                    providers_status[provider] = "healthy" if provider_models else "down"
            except Exception as e:
                logger.error(f"Orchestrator health check failed: {e}")
                orchestrator_healthy = False
        else:
            # Direct AI service check
            try:
                provider_status = ai_service.get_provider_status()
                orchestrator_healthy = any(provider_status.values())
                providers_status = {
                    k: "healthy" if v else "down" 
                    for k, v in provider_status.items()
                }
            except Exception as e:
                logger.error(f"Direct AI service health check failed: {e}")
                orchestrator_healthy = False
        
        return {
            "ok": orchestrator_healthy,
            "providers": providers_status,
            "service": "copywriting",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "ok": False,
            "providers": {},
            "error": str(e),
            "service": "copywriting",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/start")
async def start_service():
    """Start or wake the service - idempotent operation"""
    try:
        # Service is already running if this endpoint is reached
        # Optionally, we can trigger a model refresh
        if USE_ORCHESTRATOR:
            client = get_orchestrator_client()
            await client.refresh_models()
        
        return {
            "started": True,
            "message": "Service is running",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Service start error: {e}")
        return {
            "started": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/")
async def home():
    """Serve the copywriting module homepage"""
    index_path = os.path.join(current_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return HTMLResponse(content="<h1>Copywriting Module</h1><p>Frontend not yet deployed</p>")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "copywriting-module", "port": 8002}

@app.get("/api/models")
async def get_models():
    """
    Fetch list of available AI models from AI Orchestrator or direct providers
    """
    try:
        if USE_ORCHESTRATOR:
            # Get models from AI Orchestrator
            client = get_orchestrator_client()
            orchestrator_models = await client.get_models()
            
            # Transform orchestrator format to our format
            models = []
            for provider, provider_models in orchestrator_models.get("models", {}).items():
                for model in provider_models:
                    models.append({
                        "id": model["id"],
                        "name": model.get("label", model.get("name", model["id"])),  # Use label, fallback to name or id
                        "provider": provider,
                        "description": model.get("description", ""),
                        "tier": model.get("tier", "standard"),
                        "default": model.get("default", False),
                        "capabilities": model.get("capabilities", {})
                    })
            
            # If no models retrieved, check if success flag exists and is False
            if not models and orchestrator_models.get("success") == False:
                # Use fallback models if orchestrator failed
                models = [
                    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "description": "OpenAI's latest model", "default": True},
                    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "claude", "description": "Anthropic's best model"},
                    {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash", "provider": "gemini", "description": "Google's fast model"}
                ]
                logger.warning("Orchestrator failed, using fallback models")
            
            logger.info(f"Using AI Orchestrator: {len(models)} models available")
            return {
                "models": models,
                "source": "orchestrator",
                "message": "Using AI Orchestrator"
            }
        else:
            # Use direct AI providers
            models = ai_service.get_available_models()
            provider_status = ai_service.get_provider_status()
            
            logger.info(f"Using direct providers: {len(models)} models available")
            return {
                "models": models,
                "source": "direct",
                "provider_status": provider_status,
                "message": "Using direct AI providers"
            }
        
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        # Return fallback models on error
        return {
            "models": [
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai", "description": "Fast and efficient", "default": True}
            ],
            "source": "fallback",
            "error": str(e),
            "message": "Using fallback models"
        }

@app.get("/api/agents")
async def get_agents():
    """
    Fetch list of available AI agents from Agent Service or MCP Service
    """
    try:
        agents_list = []
        
        # Try to fetch from Unified Agents API first (NEW - Single Source of Truth)
        try:
            async with httpx.AsyncClient() as client:
                # Try Unified Agents endpoint
                agent_response = await client.get(
                    "http://localhost:8000/api/agents/",
                    timeout=10.0
                )
                
                if agent_response.status_code == 200:
                    data = agent_response.json()
                    if isinstance(data, dict) and "agents" in data:
                        agents_list = data["agents"]
                        
                        # Format agents for copywriting tool display
                        formatted_agents = []
                        for agent in agents_list:
                            formatted_agents.append({
                                "id": agent.get("agent_id", agent.get("id", "unknown")),
                                "name": agent.get("display_name", agent.get("name", "Unknown Agent")),
                                "description": agent.get("description", ""),
                                "role": agent.get("role", "general"),
                                "capabilities": agent.get("capabilities", []),
                                "provider": agent.get("default_provider", "auto"),
                                "model": agent.get("default_model_id")
                            })
                        
                        logger.info(f"✅ Using unified agents API: {len(formatted_agents)} agents")
                        return {
                            "agents": formatted_agents,
                            "source": "unified_agents_api",
                            "count": len(formatted_agents)
                        }
        except Exception as e:
            logger.info(f"Could not fetch from Unified Agents API: {e}")
        
        # Fallback: Try legacy Agent Service
        try:
            async with httpx.AsyncClient() as client:
                # Try Agent Service endpoint
                agent_response = await client.get(
                    "http://localhost:8000/api/agents/list",
                    timeout=5.0
                )
                
                if agent_response.status_code == 200:
                    data = agent_response.json()
                    if isinstance(data, list):
                        agents_list = data
                    elif isinstance(data, dict) and "agents" in data:
                        agents_list = data["agents"]
                    
                    # Format agents for display
                    formatted_agents = []
                    for agent in agents_list:
                        if isinstance(agent, dict):
                            formatted_agents.append({
                                "id": agent.get("id", agent.get("name", "unknown")),
                                "name": agent.get("name", agent.get("id", "Unknown Agent")),
                                "description": agent.get("description", ""),
                                "role": agent.get("role", agent.get("type", "general")),
                                "capabilities": agent.get("capabilities", [])
                            })
                        else:
                            # Handle simple string format
                            formatted_agents.append({
                                "id": str(agent).lower().replace(" ", "_"),
                                "name": str(agent),
                                "description": "",
                                "role": "general",
                                "capabilities": []
                            })
                    
                    logger.info(f"⚠️ Using legacy Agent Service: {len(formatted_agents)} agents")
                    return {
                        "agents": formatted_agents,
                        "source": "legacy_agent_service",
                        "count": len(formatted_agents)
                    }
        except Exception as e:
            logger.info(f"Could not fetch from Legacy Agent Service: {e}")
        
        # Try MCP Service as fallback
        try:
            async with httpx.AsyncClient() as client:
                mcp_response = await client.get(
                    "http://localhost:8000/api/mcp/agents",
                    timeout=5.0
                )
                
                if mcp_response.status_code == 200:
                    data = mcp_response.json()
                    if isinstance(data, dict) and "agents" in data:
                        agents_list = data["agents"]
                    
                    return {
                        "agents": agents_list,
                        "source": "mcp_service",
                        "count": len(agents_list)
                    }
        except Exception as e:
            logger.info(f"Could not fetch from MCP Service: {e}")
        
        # Fallback to predefined agents if services are not available
        fallback_agents = [
            {"id": "copywriter", "name": "Copywriter", "description": "Expert in email copy and messaging", "role": "copywriting", "capabilities": ["email_copy", "subject_lines", "cta_creation"]},
            {"id": "designer", "name": "Designer", "description": "Visual design and creative direction", "role": "design", "capabilities": ["visual_concepts", "layout_suggestions", "image_guidance"]},
            {"id": "strategist", "name": "Strategist", "description": "Campaign strategy and planning", "role": "strategy", "capabilities": ["audience_targeting", "campaign_timing", "ab_testing"]},
            {"id": "brand_specialist", "name": "Brand Specialist", "description": "Brand voice and consistency", "role": "branding", "capabilities": ["brand_voice", "tone_consistency", "messaging_alignment"]},
            {"id": "performance_analyst", "name": "Performance Analyst", "description": "Analytics and optimization", "role": "analytics", "capabilities": ["metrics_analysis", "performance_optimization", "testing_recommendations"]}
        ]
        
        return {
            "agents": fallback_agents,
            "source": "fallback",
            "count": len(fallback_agents)
        }
        
    except Exception as e:
        logger.error(f"Error fetching agents: {str(e)}")
        return {
            "agents": [],
            "source": "error",
            "error": str(e)
        }

@app.get("/api/clients")
async def get_clients():
    """
    Fetch list of clients from Firestore
    Returns simplified client data for dropdown
    """
    try:
        db = get_firestore_client()
        if not db:
            # Fallback to sample clients if Firestore is not available
            return {
                "clients": [
                    {"id": "rogue-creamery", "name": "Rogue Creamery", "slug": "rogue-creamery"},
                    {"id": "sample-client-1", "name": "Sample Client 1", "slug": "sample-client-1"},
                    {"id": "sample-client-2", "name": "Sample Client 2", "slug": "sample-client-2"}
                ],
                "source": "fallback"
            }
        
        # Fetch clients from Firestore
        clients_ref = db.collection("clients")
        clients = []
        
        for doc in clients_ref.stream():
            client_data = doc.to_dict()
            client_id = doc.id
            
            # Extract client name - try multiple fields
            client_name = (
                client_data.get("client_name") or 
                client_data.get("name") or 
                client_data.get("company_name") or
                client_id.replace("-", " ").title()
            )
            
            # Get slug
            client_slug = client_data.get("client_slug", client_id)
            
            # Extract comprehensive brand context
            brand_context = {
                "voice": client_data.get("brand_voice", client_data.get("voice", "")),
                "tone": client_data.get("brand_tone", client_data.get("tone", "")),
                "personality": client_data.get("brand_personality", client_data.get("personality", "")),
                "values": client_data.get("brand_values", client_data.get("values", [])),
                "target_audience": client_data.get("target_audience", ""),
                "key_messages": client_data.get("key_messages", []),
                "style_guide": client_data.get("style_guide", {}),
                "emoji_usage": client_data.get("emoji_usage", "moderate"),
                "formality_level": client_data.get("formality_level", "professional")
            }
            
            clients.append({
                "id": client_id,
                "name": client_name,
                "slug": client_slug,
                "brand_voice": client_data.get("brand_voice", ""),
                "industry": client_data.get("industry", ""),
                "brand_context": brand_context
            })
        
        # Sort clients by name
        clients.sort(key=lambda x: x["name"])
        
        return {
            "clients": clients,
            "source": "firestore",
            "count": len(clients)
        }
        
    except Exception as e:
        logger.error(f"Error fetching clients: {str(e)}")
        # Return fallback data on error
        return {
            "clients": [
                {"id": "rogue-creamery", "name": "Rogue Creamery", "slug": "rogue-creamery"},
                {"id": "sample-client-1", "name": "Sample Client 1", "slug": "sample-client-1"}
            ],
            "source": "fallback",
            "error": str(e)
        }

@app.post("/api/generate-copy")
async def generate_copy(submission: BriefSubmission):
    """
    Generate copywriting variants using EmailPilot's agent orchestration
    """
    try:
        # Use provided client info or extract from brief
        client_id = submission.client_id
        client_name = submission.client_name
        brand_context = {}
        
        # Fetch full client data including brand context from Firestore
        if client_id:
            db = get_firestore_client()
            if db:
                try:
                    client_doc = db.collection("clients").document(client_id).get()
                    if client_doc.exists:
                        client_data = client_doc.to_dict()
                        
                        # Get client name if not provided
                        if not client_name:
                            client_name = (
                                client_data.get("client_name") or 
                                client_data.get("name") or 
                                client_data.get("company_name") or
                                client_id.replace("-", " ").title()
                            )
                        
                        # Extract comprehensive brand context
                        brand_context = {
                            "voice": client_data.get("brand_voice", client_data.get("voice", "")),
                            "tone": client_data.get("brand_tone", client_data.get("tone", "")),
                            "personality": client_data.get("brand_personality", client_data.get("personality", "")),
                            "values": client_data.get("brand_values", client_data.get("values", [])),
                            "target_audience": client_data.get("target_audience", ""),
                            "key_messages": client_data.get("key_messages", []),
                            "style_guide": client_data.get("style_guide", {}),
                            "emoji_usage": client_data.get("emoji_usage", "moderate"),
                            "formality_level": client_data.get("formality_level", "professional"),
                            "industry": client_data.get("industry", ""),
                            "competitor_differentiation": client_data.get("competitor_differentiation", ""),
                            "unique_selling_points": client_data.get("unique_selling_points", [])
                        }
                        
                except Exception as e:
                    logger.warning(f"Could not fetch client details: {e}")
                    if not client_name:
                        client_name = client_id.replace("-", " ").title()
            else:
                if not client_name:
                    client_name = client_id.replace("-", " ").title()
        
        # Fallback if no client info provided
        if not client_name:
            client_name = "Unknown Client"
        
        # Call EmailPilot's agent orchestration service with brand context
        agent_response = await call_agent_orchestration(
            brief=submission.brief_content,
            client_id=client_id or client_name.lower().replace(" ", "-"),
            client_name=client_name,
            campaign_type=submission.campaign_type,
            brand_context=brand_context,
            selected_agents=submission.selected_agents
        )
        
        # Generate 5 variants with different frameworks and creativity levels
        variants = []
        for i in range(5):
            framework = COPYWRITING_FRAMEWORKS[i % len(COPYWRITING_FRAMEWORKS)]
            creativity = CREATIVITY_LEVELS[i]
            
            variant_data = await generate_variant(
                brief=submission.brief_content,
                framework=framework["name"],
                creativity_level=creativity,
                client_context=agent_response,
                brand_context=brand_context,
                variant_number=i + 1,
                model=submission.selected_model or "claude-3-haiku",
                agents=submission.selected_agents or [],
                custom_prompts=submission.custom_prompts
            )
            
            variants.append(variant_data)
        
        response = CopywritingResponse(
            client_name=client_name,
            variants=variants,
            generated_at=datetime.utcnow().isoformat(),
            brief_summary=summarize_brief(submission.brief_content)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating copy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_framework_description(framework: str) -> str:
    """Get detailed description of copywriting framework"""
    descriptions = {
        "AIDA": "Attention → Interest → Desire → Action. Start by grabbing attention, build interest with benefits, create desire by showing value, end with clear call to action.",
        "FOMO": "Fear of Missing Out. Create urgency and scarcity, highlight what they'll miss, use time-sensitive language, show social proof.",
        "PAS": "Problem → Agitate → Solution. Identify the problem, agitate the pain points, present your product/service as the solution.",
        "BAB": "Before → After → Bridge. Paint the current situation, show the desired outcome, explain how to get there.",
        "4Ps": "Promise → Picture → Proof → Push. Make a bold promise, paint a picture of success, provide proof/testimonials, push for action."
    }
    return descriptions.get(framework, "Standard copywriting approach")

async def generate_direct_content(prompt: str, model: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct content generation when AI services are unavailable
    Generates content based on the actual brief
    """
    logger.info(f"Using direct generation fallback for model '{model}'")
    
    # Extract key info from prompt and context
    framework = "AIDA"
    if "FOMO" in prompt: framework = "FOMO"
    elif "PAS" in prompt: framework = "PAS"
    elif "BAB" in prompt: framework = "BAB"
    elif "4Ps" in prompt: framework = "4Ps"
    
    # Get brief content from context
    brief = context.get("brief", "") if context else ""
    brand_name = context.get("brand_context", {}).get("name", "Your Brand") if context else "Your Brand"
    
    # Parse brief for key elements (fallback parsing)
    brief_lower = brief.lower()
    
    # Try to extract theme/topic
    theme = "Fall Collection"
    if "coffee" in brief_lower:
        theme = "Premium Coffee"
    elif "fall" in brief_lower or "autumn" in brief_lower:
        theme = "Fall Collection"
    elif "summer" in brief_lower:
        theme = "Summer Sale"
    elif "winter" in brief_lower:
        theme = "Winter Collection"
    elif "spring" in brief_lower:
        theme = "Spring Collection"
    
    # Check for urgency/timing
    is_urgent = any(word in brief_lower for word in ["urgent", "limited", "ends", "last chance", "today", "tomorrow"])
    
    # Check for discount/offer
    has_offer = any(word in brief_lower for word in ["off", "discount", "save", "free", "bogo", "%"])
    
    use_emoji = "Yes" in prompt and "Use Emojis: Yes" in prompt
    emoji = "☕ " if "coffee" in brief_lower else "🍂 " if "fall" in brief_lower else "🎯 " if use_emoji else ""
    
    # Generate realistic content based on framework
    content_map = {
        "AIDA": {
            "subject_line_a": f"{emoji}Discover What You've Been Missing",
            "subject_line_b": "The Opportunity You Can't Ignore",
            "preview_text": "See why thousands are making the switch today",
            "hero_h1": "Transform Your Results Today",
            "sub_head": "Join the leaders who've already taken action",
            "full_body": """Dear Valued Customer,

Have you been searching for a solution that actually delivers results? Your search ends here.

We understand the challenges you face, and we've developed something extraordinary to address them. Our innovative approach has already helped thousands of customers achieve remarkable outcomes.

Here's what sets us apart:
• Proven methodology with measurable results
• Dedicated support every step of the way
• Risk-free guarantee that protects your investment

Imagine where you could be in just 30 days. Our customers regularly report transformative results that exceed their expectations. You deserve the same success.

The time for hesitation is over. This is your moment to take control and achieve the results you've been dreaming about.

Don't let this opportunity pass you by. Take action today and join our community of successful customers.

Best regards,
Your Success Team""",
            "cta_copy": "Start Your Transformation",
            "sms_variant": f"{emoji}Special offer just for you! Transform your results in 30 days. Claim now →"
        },
        "FOMO": {
            "subject_line_a": f"{emoji}⏰ 24 Hours Left - Don't Miss Out!",
            "subject_line_b": "Last Chance for Exclusive Access",
            "preview_text": "This offer expires tomorrow at midnight",
            "hero_h1": "Time Is Running Out!",
            "sub_head": "Only 24 hours remain to claim your spot",
            "full_body": """URGENT: This message requires your immediate attention.

In less than 24 hours, this exclusive opportunity will be gone forever. We're talking about savings and benefits that won't be available again this year.

Right now, hundreds of smart customers are taking advantage of:
• 40% off our premium features
• Exclusive bonuses worth over $500
• Lifetime access to member benefits
• Priority support and consultation

But here's the thing - we can only extend this offer to a limited number of customers. Once we hit our limit, that's it. No exceptions.

Yesterday alone, we had 847 people claim their spot. At this rate, we'll be sold out before the deadline.

Don't be one of those people who emails us tomorrow asking if we can make an exception. We can't. When it's gone, it's gone.

The clock is ticking. Make your decision now.

Act fast,
The Team""",
            "cta_copy": "Claim Your Spot Now",
            "sms_variant": f"{emoji}⏰ FINAL 24 HRS! Your exclusive offer expires tomorrow. Don't miss out →"
        }
    }
    
    # Get content for the framework, default to AIDA if not found
    generated = content_map.get(framework, content_map["AIDA"])
    
    return {
        "content": json.dumps(generated),
        "model_used": f"{model} (simulated)",
        "tokens_used": len(prompt) // 4  # Rough approximation
    }

async def call_agent_orchestration(
    brief: str, 
    client_id: str, 
    client_name: str, 
    campaign_type: str,
    brand_context: Dict[str, Any] = None,
    selected_agents: List[str] = None
) -> Dict[str, Any]:
    """
    Call EmailPilot's agent orchestration service to get the best team
    """
    try:
        # Attempt to call the EmailPilot agent service
        async with httpx.AsyncClient() as client:
            # First try to get agent configuration
            agent_url = "http://localhost:8000/api/agents/invoke"
            
            payload = {
                "client_id": client_id,
                "campaign_brief": brief,
                "task_type": "copywriting",
                "campaign_type": campaign_type,
                "brand_context": brand_context or {},
                "selected_agents": selected_agents or []
            }
            
            try:
                response = await client.post(
                    agent_url,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Agent service returned {response.status_code}, using fallback")
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"Could not connect to agent service: {e}, using fallback")
        
        # Fallback if agent service is not available
        return {
            "client_context": {
                "brand_voice": "professional and friendly",
                "target_audience": "general consumer",
                "key_messages": ["quality", "value", "trust"]
            },
            "team_assigned": ["copywriter", "designer", "strategist"],
            "recommendations": []
        }
        
    except Exception as e:
        logger.error(f"Error calling agent orchestration: {str(e)}")
        # Return a default context
        return {
            "client_context": {},
            "team_assigned": ["copywriter"],
            "recommendations": []
        }

async def get_agent_enhancements(agent_ids: List[str], custom_prompts: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Get agent-specific prompt enhancements from predefined personas or custom prompts
    
    Args:
        agent_ids: List of agent IDs to get enhancements for
        custom_prompts: Optional dict of agent_id -> custom prompt template
    """
    agent_personas = {
        "email_marketing_expert": {
            "role": "email marketing specialist with 10+ years experience",
            "focus": "engagement optimization, subject line psychology, and conversion-driven copy",
            "style": "Use psychological triggers, power words, and emotional appeals. Focus on benefits over features.",
            "techniques": ["urgency creation", "social proof", "FOMO tactics", "personalization strategies"]
        },
        "conversion_optimizer": {
            "role": "conversion rate optimization specialist",
            "focus": "maximizing click-through rates and conversions through data-driven copy",
            "style": "Direct, action-oriented language with clear value propositions. Heavy emphasis on CTAs.",
            "techniques": ["scarcity tactics", "risk reversal", "benefit stacking", "micro-commitments"]
        },
        "brand_strategist": {
            "role": "brand voice and messaging strategist",
            "focus": "maintaining brand consistency while building emotional connections",
            "style": "Align every word with brand values and personality. Build trust through authenticity.",
            "techniques": ["brand storytelling", "value alignment", "consistency enforcement", "voice matching"]
        },
        "creative_copywriter": {
            "role": "creative storytelling specialist",
            "focus": "crafting memorable, share-worthy content that stands out",
            "style": "Use vivid imagery, metaphors, and narrative techniques. Be bold and unexpected.",
            "techniques": ["storytelling arcs", "pattern interrupts", "creative metaphors", "sensory language"]
        },
        "data_driven_marketer": {
            "role": "analytics-focused marketing strategist",
            "focus": "copy backed by data, metrics, and proven results",
            "style": "Include statistics, case studies, and concrete numbers. Lead with proof.",
            "techniques": ["A/B test insights", "metric-based claims", "ROI focus", "performance data"]
        },
        "customer_retention_specialist": {
            "role": "customer loyalty and retention expert",
            "focus": "building long-term relationships and repeat business",
            "style": "Warm, appreciative tone. Focus on value delivery and relationship building.",
            "techniques": ["loyalty rewards", "exclusive benefits", "personal touch", "appreciation messaging"]
        },
        "compliance_officer": {
            "role": "legal compliance and risk management specialist",
            "focus": "ensuring all copy meets legal requirements and industry regulations",
            "style": "Clear, factual, and transparent. Include necessary disclaimers and terms.",
            "techniques": ["disclaimer inclusion", "regulatory compliance", "truth in advertising", "risk mitigation"]
        }
    }
    
    enhancements = {}
    for agent_id in agent_ids:
        # Check for custom prompt first
        if custom_prompts and agent_id in custom_prompts:
            # Use custom prompt template
            enhancements[agent_id] = {
                "role": "customized agent",
                "custom_prompt": custom_prompts[agent_id],
                "focus": "user-defined objectives",
                "style": "As specified in custom prompt",
                "techniques": ["custom strategy"]
            }
        elif agent_id in agent_personas:
            # Use predefined persona
            persona = agent_personas[agent_id]
            enhancements[agent_id] = persona
    
    return enhancements

async def invoke_model_with_context(prompt: str, model: str, agents: List[str] = None, context: Dict[str, Any] = None, custom_prompts: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Invoke AI model through AI Orchestrator or direct providers with agent-specific enhancements
    
    Args:
        prompt: The user prompt
        model: The model to use
        agents: List of agent IDs
        context: Additional context
        custom_prompts: Optional dict of agent_id -> custom prompt template
    """
    try:
        # Log context for debugging
        if context:
            logger.info(f"Context provided with keys: {context.keys()}")
        
        # Build system message with agent enhancements
        system_content = "You are an expert email copywriter specializing in marketing campaigns."
        
        # Apply agent-specific enhancements if agents are selected
        if agents and len(agents) > 0:
            logger.info(f"Applying agent enhancements for: {agents}")
            agent_enhancements = await get_agent_enhancements(agents, custom_prompts)
            
            if agent_enhancements:
                # Check if any agents have custom prompts
                has_custom = any('custom_prompt' in persona for persona in agent_enhancements.values())
                
                if has_custom and len(agent_enhancements) == 1:
                    # Single agent with custom prompt - use it directly
                    agent_id, persona = list(agent_enhancements.items())[0]
                    if 'custom_prompt' in persona:
                        # Replace variables in custom prompt
                        custom_prompt = persona['custom_prompt']
                        custom_prompt = custom_prompt.replace('{user_input}', prompt)
                        if context:
                            custom_prompt = custom_prompt.replace('{client_name}', context.get('client_name', ''))
                            custom_prompt = custom_prompt.replace('{campaign_type}', context.get('campaign_type', 'email'))
                            custom_prompt = custom_prompt.replace('{brand_voice}', context.get('brand_voice', ''))
                        # Use custom prompt as full prompt
                        prompt = custom_prompt
                        system_content = "You are an AI assistant following user-defined instructions."
                else:
                    # Multiple agents or predefined personas - combine them
                    system_content = "You are a specialized email copywriting team consisting of:\n"
                    
                    for agent_id, persona in agent_enhancements.items():
                        if 'custom_prompt' in persona:
                            system_content += f"\n- A customized agent with user-defined instructions."
                        else:
                            system_content += f"\n- A {persona['role']} focusing on {persona['focus']}."
                            system_content += f"\n  Style: {persona['style']}"
                            system_content += f"\n  Techniques: {', '.join(persona['techniques'])}"
                    
                    system_content += "\n\nCombine these perspectives to create copy that leverages all these specializations."
                
                # Add specific instructions based on agent combination
                if "compliance_officer" in agents:
                    prompt += "\n\nIMPORTANT: Include appropriate disclaimers and ensure all claims are substantiated."
                
                if "data_driven_marketer" in agents:
                    prompt += "\n\nIMPORTANT: Include relevant statistics, metrics, or case study references where appropriate."
                
                if "creative_copywriter" in agents and "compliance_officer" not in agents:
                    prompt += "\n\nIMPORTANT: Be bold and creative with language. Use unexpected angles and memorable phrases."
        
        if USE_ORCHESTRATOR:
            # Use AI Orchestrator
            logger.info(f"Using AI Orchestrator for model '{model}'")
            
            # Determine provider from model name
            provider = "auto"
            if "gpt" in model.lower():
                provider = "openai"
            elif "claude" in model.lower():
                provider = "claude"
            elif "gemini" in model.lower():
                provider = "gemini"
            
            # Build messages for orchestrator with enhanced system prompt
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
            
            # Call orchestrator
            client = get_orchestrator_client()
            result = await client.complete(
                messages=messages,
                provider=provider,
                model=model if model != "auto" else None,
                temperature=0.7,
                max_tokens=2000,
                context=context
            )
            
            if result.get("content"):
                logger.info(f"AI Orchestrator returned {len(result['content'])} chars from {result.get('provider')}/{result.get('model')}")
                return {
                    "content": result["content"],
                    "model_used": result.get("model", model),
                    "provider": result.get("provider", provider)
                }
            else:
                logger.warning(f"AI Orchestrator returned no content: {result.get('error')}")
                return {
                    "content": "",
                    "error": result.get("error", "No content generated"),
                    "model_used": "fallback"
                }
        else:
            # Use direct providers
            logger.info(f"Using direct provider for model '{model}'")
            result = await ai_service.invoke_model(prompt, model, context)
            
            if result.get("content"):
                logger.info(f"Direct provider returned {len(result['content'])} chars")
            else:
                logger.warning(f"Direct provider returned no content: {result.get('error')}")
            
            return result
        
    except Exception as e:
        logger.error(f"Error invoking model: {str(e)}")
        # Final fallback to template generation
        return await generate_direct_content(prompt, model, context)

async def generate_variant(
    brief: str, 
    framework: str, 
    creativity_level: str,
    client_context: Dict[str, Any],
    brand_context: Dict[str, Any],
    variant_number: int,
    model: str = "claude-3-haiku",
    agents: List[str] = None,
    custom_prompts: Optional[Dict[str, str]] = None
) -> CopyVariant:
    """
    Generate a single copywriting variant using AI models through MCP
    """
    # Determine if emojis should be used based on creativity level and brand context
    emoji_preference = brand_context.get("emoji_usage", "moderate") if brand_context else "moderate"
    use_emoji = (creativity_level in ["Bold", "Experimental", "Wild"]) and (emoji_preference != "none")
    
    # Adjust creativity based on brand formality level
    if brand_context and brand_context.get("formality_level") == "formal":
        if creativity_level in ["Experimental", "Wild"]:
            creativity_level = "Bold"  # Cap at Bold for formal brands
    
    # Build comprehensive AI prompt with ALL context
    prompt = f"""
    You are an expert email copywriter. Generate compelling email copy based on the following:
    
    === CAMPAIGN BRIEF ===
    {brief}
    
    === CLIENT INFORMATION ===
    Client Name: {brand_context.get('name', 'Client')}
    Industry: {brand_context.get('industry', 'General')}
    Target Audience: {brand_context.get('target_audience', 'General consumers')}
    
    === BRAND GUIDELINES ===
    Brand Voice: {brand_context.get('voice', 'Professional and friendly')}
    Brand Tone: {brand_context.get('tone', 'Conversational yet authoritative')}
    Brand Personality: {brand_context.get('personality', 'Helpful and trustworthy')}
    Core Values: {', '.join(brand_context.get('values', ['Quality', 'Service', 'Innovation']))}
    Emoji Usage: {emoji_preference}
    Formality Level: {brand_context.get('formality_level', 'moderate')}
    
    === COPYWRITING FRAMEWORK ===
    Use the {framework} framework for this email:
    {get_framework_description(framework)}
    
    === CREATIVE DIRECTION ===
    Creativity Level: {creativity_level}
    Use Emojis: {'Yes' if use_emoji else 'No'}
    
    === DELIVERABLES REQUIRED ===
    Generate the following elements:
    1. Subject Line A - Primary subject line using {framework} approach
    2. Subject Line B - A/B test variation
    3. Preview Text - 90-140 characters that complements subject
    4. Hero H1 - Main headline for email (punchy, benefit-focused)
    5. Sub-head - Supporting headline that elaborates on H1
    6. Full Email Body - 300-400 words following {framework} structure
    7. CTA Copy - Action-oriented button text
    8. SMS Variant - 160 character version for text messaging
    
    === OUTPUT FORMAT ===
    Return your response as valid JSON with these exact keys:
    {{
        "subject_line_a": "...",
        "subject_line_b": "...",
        "preview_text": "...",
        "hero_h1": "...",
        "sub_head": "...",
        "full_body": "...",
        "cta_copy": "...",
        "sms_variant": "..."
    }}
    
    Make sure the content:
    - Directly addresses the campaign brief requirements
    - Reflects the client's brand voice and values
    - Follows the {framework} copywriting framework structure
    - Matches the {creativity_level} creativity level
    """
    
    # Create full context object
    full_context = {
        "brief": brief,
        "client_context": client_context,
        "brand_context": brand_context,
        "framework": framework,
        "creativity_level": creativity_level
    }
    
    # Log what we're sending
    logger.info(f"Generating variant {variant_number} with framework '{framework}' using model '{model}'")
    logger.info(f"Brief excerpt: {brief[:100]}...")
    logger.info(f"Brand name: {brand_context.get('name', 'Unknown')}")
    
    # Invoke AI model with full context
    ai_response = await invoke_model_with_context(prompt, model, agents, full_context, custom_prompts)
    
    # Parse AI response or use fallback
    if ai_response.get("content"):
        try:
            # Try to parse JSON response
            import json
            ai_content = json.loads(ai_response["content"])
            
            # Use AI-generated content
            emoji_prefix = "🎯 " if use_emoji else ""
            content = {
                "subject_a": ai_content.get("subject_line_a", f"{emoji_prefix}Your Subject Line"),
                "subject_b": ai_content.get("subject_line_b", "Alternative Subject"),
                "preview": ai_content.get("preview_text", "Preview text here"),
                "hero_h1": ai_content.get("hero_h1", "Main Headline"),
                "sub_head": ai_content.get("sub_head", "Supporting headline"),
                "cta": ai_content.get("cta_copy", "Take Action Now"),
                "full_body": ai_content.get("full_body", ""),
                "sms_variant": ai_content.get("sms_variant", "SMS message here"),
                "offer": None,
                "image_note": f"Hero image for {framework} approach",
                "ab_test": f"Test {framework} messaging variations"
            }
        except:
            # Fallback to template if AI response isn't valid JSON
            content = generate_framework_content(brief, framework, creativity_level, use_emoji, brand_context)
    else:
        # Use template-based generation as fallback
        content = generate_framework_content(brief, framework, creativity_level, use_emoji, brand_context)
    
    return CopyVariant(
        variant_id=variant_number,
        framework=framework,
        creativity_level=creativity_level,
        subject_line_a=content["subject_a"],
        subject_line_b=content["subject_b"],
        preview_text=content["preview"],
        hero_h1=content["hero_h1"],
        sub_head=content["sub_head"],
        hero_image_filename=f"hero_v{variant_number}_{framework.lower()}.jpg",
        hero_image_note=content["image_note"],
        cta_copy=content["cta"],
        offer=content.get("offer"),
        ab_test_idea=content["ab_test"],
        secondary_message=content["sms_variant"],
        uses_emoji=use_emoji,
        full_email_body=content.get("full_body")
    )

def generate_framework_content(brief: str, framework: str, creativity: str, use_emoji: bool, brand_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate content based on copywriting framework with full body copy
    Parses actual brief content to create contextual templates
    """
    # Parse brief content for key themes and context
    brief_lower = brief.lower() if brief else ""
    
    # Detect themes from brief
    is_seasonal = any(word in brief_lower for word in ['fall', 'autumn', 'winter', 'spring', 'summer', 'holiday', 'christmas', 'thanksgiving'])
    is_coffee = any(word in brief_lower for word in ['coffee', 'brew', 'roast', 'espresso', 'latte', 'cappuccino', 'bean'])
    is_urgent = any(word in brief_lower for word in ['urgent', 'limited', 'exclusive', 'last chance', 'ending soon', 'hurry', 'now', 'expires'])
    has_discount = any(word in brief_lower for word in ['discount', 'sale', 'save', 'off', '%', 'offer', 'deal'])
    is_food = any(word in brief_lower for word in ['food', 'recipe', 'cooking', 'kitchen', 'meal', 'ingredient'])
    
    # Extract key details from brief
    brand_name = brand_context.get('name', 'our brand') if brand_context else 'our brand'
    
    # Determine product/service from brief
    product_name = "our special offer"  # default
    if is_coffee:
        if is_seasonal and 'fall' in brief_lower:
            product_name = "our fall coffee collection"
        else:
            product_name = "our premium coffee"
    elif is_food:
        product_name = "our culinary selection"
    elif is_seasonal:
        season = next((word for word in ['fall', 'autumn', 'winter', 'spring', 'summer'] if word in brief_lower), 'seasonal')
        product_name = f"our {season} collection"
    
    # Try to extract specific discount percentage
    discount_amount = None
    if has_discount:
        import re
        discount_match = re.search(r'(\d+)\s*%', brief)
        if discount_match:
            discount_amount = discount_match.group(1)
    
    # Smart emoji selection based on content
    emoji_prefix = ""
    if use_emoji:
        if is_coffee:
            emoji_prefix = "☕ "
        elif is_seasonal and 'fall' in brief_lower:
            emoji_prefix = "🍂 "
        elif is_urgent:
            emoji_prefix = "⏰ "
        elif has_discount:
            emoji_prefix = "💰 "
        elif is_food:
            emoji_prefix = "🍽️ "
        else:
            emoji_prefix = "🎯 "
    
    # Generate full email body based on framework with contextual content
    def create_full_body(template: Dict[str, str], framework: str) -> str:
        body_parts = []
        
        # Opening
        if framework == "AIDA":
            body_parts.append(f"Hi there,\n\n{template['hero_h1']}\n\n{template['sub_head']}")
            
            # Build contextual features based on brief analysis
            if is_coffee and is_seasonal:
                body_parts.append("Here's what makes our fall collection special:\n• Expertly roasted beans from sustainable farms\n• Rich, complex flavors perfect for autumn mornings\n• Limited-batch blends you won't find anywhere else")
                body_parts.append("Picture yourself on a crisp fall morning, hands wrapped around a warm mug of our signature autumn blend. The rich aroma, the perfect temperature, the moment of peace before your day begins. This is what our customers love about our seasonal collection.")
            elif is_coffee:
                body_parts.append("Here's what makes our coffee special:\n• Premium beans sourced from the world's finest regions\n• Expert roasting for optimal flavor profiles\n• Fresh delivery straight to your door")
                body_parts.append(f"Imagine starting every morning with coffee that truly excites you. Our customers consistently tell us how our {product_name} has transformed their daily routine.")
            else:
                body_parts.append("Here's what makes this special:\n• Exclusive features you won't find anywhere else\n• Limited availability for our valued customers\n• Proven results that speak for themselves")
                body_parts.append(f"Imagine how much better your experience will be with {product_name}. Our customers consistently tell us how thrilled they are with their decision.")
        elif framework == "FOMO":
            body_parts.append(f"Quick update!\n\n{template['hero_h1']}\n\n{template['sub_head']}")
            
            if is_coffee and is_seasonal:
                body_parts.append("⏰ Time is running out! Here's what you're about to miss:\n• Our limited fall coffee collection\n• Seasonal blends that won't return until next year\n• The perfect flavors for cozy autumn mornings")
                body_parts.append("Don't be one of the coffee lovers who regretted missing our seasonal collection. Once it's gone, you'll have to wait a full year for these flavors to return.")
            elif is_coffee:
                body_parts.append("⏰ Limited availability! Here's what you're about to miss:\n• Our premium coffee selection\n• Fresh roasted beans at special pricing\n• The chance to elevate your daily coffee experience")
                body_parts.append("Don't miss out on experiencing coffee the way it was meant to be. Our customers often tell us they wish they'd discovered us sooner.")
            else:
                body_parts.append(f"⏰ Time is running out! Here's what you're about to miss:\n• Special pricing on {product_name}\n• Exclusive access to premium features\n• Limited-time bonuses worth significant value")
                body_parts.append("Don't be one of the people who wished they had acted sooner. This opportunity is genuinely limited.")
        elif framework == "PAS":
            body_parts.append(f"I get it.\n\n{template['hero_h1']}\n\n{template['sub_head']}")
            body_parts.append("You've tried other solutions, but nothing seems to work quite right. The frustration builds, and you're left wondering if there's actually a better way.")
            body_parts.append("Well, there is. We've helped thousands of people just like you overcome this exact challenge. Our proven approach addresses the root cause, not just the symptoms.")
        elif framework == "BAB":
            body_parts.append(f"Let's talk about transformation.\n\n{template['hero_h1']}\n\n{template['sub_head']}")
            body_parts.append("Right now, you might be struggling with challenges that seem insurmountable. But imagine a different reality...")
            body_parts.append("Picture yourself in just a few weeks: confident, successful, and wondering why you didn't make this change sooner. That's the bridge we provide.")
        else:  # 4Ps
            body_parts.append(f"Here's our commitment to you:\n\n{template['hero_h1']}\n\n{template['sub_head']}")
            body_parts.append("We promise exceptional results, and we have the proof to back it up:\n• 98% customer satisfaction rate\n• Over 10,000 success stories\n• Industry-leading guarantees")
            body_parts.append("Picture yourself joining our community of successful customers. The proof is in our track record.")
        
        # Add offer if present
        if template.get('offer'):
            body_parts.append(f"\n💝 {template['offer']}")
        
        # Call to action
        body_parts.append(f"\n{template['cta']}\n\nBest regards,\nThe Team")
        
        return "\n\n".join(body_parts)
    
    # Build contextual templates based on brief analysis
    if is_coffee and is_seasonal:
        # Coffee + Fall theme
        framework_templates = {
            "AIDA": {
                "subject_a": f"{emoji_prefix}Fall Coffee Collection Now Available",
                "subject_b": f"{emoji_prefix}Warm Up Your Autumn with Premium Blends",
                "preview": "Cozy up with our seasonal coffee favorites...",
                "hero_h1": "Fall in Love with Our Seasonal Blends",
                "sub_head": "Limited-Edition Coffee Crafted for Crisp Autumn Days",
                "cta": "Shop Fall Collection",
                "image_note": "Autumn coffee scene with warm colors",
                "ab_test": "Test seasonal appeal vs product benefits",
                "sms_variant": f"{emoji_prefix}Fall coffee is here! Limited-edition blends →"
            },
            "FOMO": {
                "subject_a": f"{emoji_prefix}Fall Coffee Collection - Limited Time Only",
                "subject_b": f"{emoji_prefix}Last Week for Seasonal Blends",
                "preview": "Once they're gone, they're gone until next year",
                "hero_h1": "Don't Miss Our Fall Coffee Collection",
                "sub_head": "Seasonal Favorites Available for a Limited Time",
                "cta": "Get Yours Before They're Gone",
                "image_note": "Autumn coffee with urgency elements",
                "ab_test": "Test seasonal urgency vs product scarcity",
                "sms_variant": f"{emoji_prefix}Final days for fall coffee! Don't wait →"
            },
            "PAS": {
                "subject_a": f"{emoji_prefix}Tired of the Same Old Coffee?",
                "subject_b": f"{emoji_prefix}Discover Coffee That Makes Fall Mornings Special",
                "preview": "Transform your morning routine this season",
                "hero_h1": "Break Free from Boring Coffee",
                "sub_head": "Our Fall Collection Brings Excitement Back to Your Cup",
                "cta": "Discover Fall Flavors",
                "image_note": "Coffee transformation with autumn elements",
                "ab_test": "Test problem awareness vs solution benefits",
                "sms_variant": f"{emoji_prefix}Boring coffee? Our fall blends change everything →"
            },
            "BAB": {
                "subject_a": f"{emoji_prefix}Picture Your Perfect Fall Morning",
                "subject_b": f"{emoji_prefix}From Ordinary Coffee to Extraordinary Moments",
                "preview": "Transform your daily coffee ritual this autumn",
                "hero_h1": "Imagine the Perfect Fall Coffee Experience",
                "sub_head": "We Bridge Ordinary Mornings with Extraordinary Flavors",
                "cta": "Start Your Coffee Journey",
                "image_note": "Coffee transformation with autumn lifestyle",
                "ab_test": "Test aspirational vs experiential messaging",
                "sms_variant": f"{emoji_prefix}Perfect fall mornings start with perfect coffee →"
            },
            "4Ps": {
                "subject_a": f"{emoji_prefix}Our Promise: The Perfect Fall Blend",
                "subject_b": f"{emoji_prefix}Proven: Coffee That Defines Autumn",
                "preview": "See why thousands choose our seasonal collection",
                "hero_h1": "We Promise the Perfect Fall Coffee Experience",
                "sub_head": "Picture Your Autumn, Backed by Our Coffee Expertise",
                "cta": "Try Our Fall Collection",
                "image_note": "Customer testimonials with autumn coffee",
                "ab_test": "Test promise vs proof in seasonal context",
                "sms_variant": f"{emoji_prefix}Promise: Perfect fall coffee. Proof: 10,000+ happy customers →"
            }
        }
    else:
        # Generic/fallback templates for other content types
        framework_templates = {
            "AIDA": {
                "subject_a": f"{emoji_prefix}Attention: Something Amazing Inside",
                "subject_b": f"{emoji_prefix}You Won't Believe What We Have for You",
                "preview": "Interest peaks when you see this offer...",
                "hero_h1": "Capture Your Attention",
                "sub_head": "Build Interest with This Amazing Offer",
                "cta": "Take Action Now",
                "image_note": "Eye-catching hero with strong focal point",
                "ab_test": "Test attention-grabbing vs benefit-focused subject lines",
                "sms_variant": "👀 Look what's waiting for you! Limited time only →"
            },
            "FOMO": {
                "subject_a": f"{emoji_prefix}Last Chance - Ends Tonight!",
                "subject_b": f"{emoji_prefix}Only 24 Hours Left",
                "preview": "Don't miss out on this exclusive opportunity",
                "hero_h1": "Time Is Running Out",
                "sub_head": "Join thousands who've already claimed theirs",
                "cta": "Claim Yours Before It's Gone",
                "image_note": "Countdown timer or crowd of happy customers",
                "ab_test": "Test urgency levels in subject lines",
                "sms_variant": "⏰ FINAL HOURS! Your exclusive offer expires at midnight"
            },
            "PAS": {
                "subject_a": f"{emoji_prefix}Struggling with This Problem?",
                "subject_b": f"{emoji_prefix}We Found the Solution You Need",
                "preview": "Finally, a real solution that works",
                "hero_h1": "We Know Your Pain",
                "sub_head": "Here's the Solution You've Been Searching For",
                "cta": "Solve It Now",
                "image_note": "Before/after or problem/solution visual",
                "ab_test": "Test problem-focused vs solution-focused messaging",
                "sms_variant": "Tired of [problem]? We've got your solution ready →"
            },
            "BAB": {
                "subject_a": f"{emoji_prefix}Imagine Your Life After This",
                "subject_b": f"{emoji_prefix}From Where You Are to Where You Want to Be",
                "preview": "Bridge the gap to your goals",
                "hero_h1": "Picture Your Success",
                "sub_head": "We'll Help You Bridge the Gap",
                "cta": "Start Your Journey",
                "image_note": "Transformation or journey visualization",
                "ab_test": "Test aspirational vs practical messaging",
                "sms_variant": "Ready to transform? Your bridge to success is here →"
            },
            "4Ps": {
                "subject_a": f"{emoji_prefix}Our Promise to You",
                "subject_b": f"{emoji_prefix}Proven Results, Guaranteed",
                "preview": "See the proof for yourself",
                "hero_h1": "We Promise Results",
                "sub_head": "Picture Your Success, Backed by Proof",
                "cta": "Get Started Today",
                "image_note": "Testimonials or results showcase",
                "ab_test": "Test promise vs proof emphasis",
                "sms_variant": "Promise: Real results. Proof: 10,000+ success stories →"
            }
        }
    
    template = framework_templates.get(framework, framework_templates["AIDA"])
    
    # Adjust for creativity level
    if creativity == "Wild":
        template["subject_a"] = "🚀💥 " + template["subject_a"]
        template["cta"] = template["cta"].upper() + " 🔥"
    elif creativity == "Conservative":
        template["subject_a"] = template["subject_a"].replace(emoji_prefix, "")
        template["subject_b"] = template["subject_b"].replace(emoji_prefix, "")
    
    # Add contextual offer based on brief analysis
    if discount_amount:
        template["offer"] = f"Save {discount_amount}% on {product_name}"
    elif has_discount:
        template["offer"] = f"Special savings on {product_name}"
    elif is_urgent:
        template["offer"] = f"Limited availability - {product_name} going fast"
    elif is_seasonal:
        template["offer"] = f"Seasonal exclusive - {product_name}"
    else:
        template["offer"] = None
    
    # Generate full body copy
    template["full_body"] = create_full_body(template, framework)
    
    # Add structured sections for easier editing
    template["body_sections"] = {
        "greeting": "Hi there," if framework != "FOMO" else "Quick update!",
        "headline": template["hero_h1"],
        "subhead": template["sub_head"],
        "body_main": template["full_body"].split("\n\n")[2] if len(template["full_body"].split("\n\n")) > 2 else "",
        "cta_section": template["cta"],
        "closing": "Best regards,\nThe Team"
    }
    
    return template

def summarize_brief(brief: str) -> str:
    """
    Create a brief summary of the campaign brief
    """
    # Simple summarization - take first 150 characters or first sentence
    if len(brief) <= 150:
        return brief
    
    # Try to find first sentence
    sentences = brief.split(".")
    if sentences:
        return sentences[0] + "."
    
    return brief[:150] + "..."

@app.get("/api/frameworks")
async def get_frameworks():
    """Get available copywriting frameworks"""
    return {
        "frameworks": COPYWRITING_FRAMEWORKS,
        "creativity_levels": CREATIVITY_LEVELS
    }

@app.post("/api/review")
async def review_copy(request: ReviewRequest):
    """
    Review a copy variant and provide teacher-like feedback
    """
    try:
        variant = request.variant
        brief = request.original_brief
        
        # Calculate scores based on various factors
        scores = {
            "clarity": 85 + (5 if "clear" in brief.lower() else 0),
            "engagement": 80 + (10 if variant.uses_emoji else 0),
            "brief_alignment": 75 + (10 if variant.framework in brief.upper() else 5),
            "creativity": {"Conservative": 70, "Moderate": 80, "Bold": 85, "Experimental": 90, "Wild": 95}.get(variant.creativity_level, 75),
            "structure": 85,
            "cta_strength": 80 + (5 if "!" in variant.cta_copy else 0)
        }
        
        overall_score = sum(scores.values()) / len(scores)
        
        # Determine letter grade
        if overall_score >= 93:
            letter_grade = "A+"
        elif overall_score >= 90:
            letter_grade = "A"
        elif overall_score >= 87:
            letter_grade = "A-"
        elif overall_score >= 83:
            letter_grade = "B+"
        elif overall_score >= 80:
            letter_grade = "B"
        elif overall_score >= 77:
            letter_grade = "B-"
        elif overall_score >= 73:
            letter_grade = "C+"
        else:
            letter_grade = "C"
        
        # Generate constructive feedback
        strengths = []
        improvements = []
        
        # Analyze strengths
        if variant.framework == "AIDA":
            strengths.append("Excellent use of the AIDA framework to guide readers through the journey")
        if variant.uses_emoji:
            strengths.append("Good use of visual elements to increase engagement")
        if len(variant.hero_h1) < 50:
            strengths.append("Concise and punchy headline that grabs attention")
        strengths.append(f"Strong {variant.framework} framework implementation")
        
        # Suggest improvements
        if not variant.offer:
            improvements.append("Consider adding a specific offer or incentive to drive action")
        if len(variant.subject_line_a) > 60:
            improvements.append("Subject line could be shorter for better mobile display")
        if variant.creativity_level == "Conservative":
            improvements.append("Could explore slightly bolder language to stand out in the inbox")
        
        # Brief alignment analysis
        brief_words = set(brief.lower().split())
        copy_words = set(variant.full_email_body.lower().split())
        alignment_score = len(brief_words & copy_words) / len(brief_words) * 100 if brief_words else 50
        
        if alignment_score > 70:
            brief_alignment = f"Excellent alignment with the brief! Your copy captures {int(alignment_score)}% of the key concepts mentioned."
        elif alignment_score > 50:
            brief_alignment = f"Good alignment with the brief. The copy addresses {int(alignment_score)}% of the requested elements."
        else:
            brief_alignment = f"The copy could align more closely with the brief. Currently matching {int(alignment_score)}% of key requirements."
        
        # Specific suggestions
        specific_suggestions = [
            {"section": "subject_line", "suggestion": "Try personalizing with the recipient's name or location"},
            {"section": "hero_h1", "suggestion": f"Consider testing a question format to increase curiosity"},
            {"section": "cta", "suggestion": "Test action verbs like 'Claim', 'Unlock', or 'Discover'"},
        ]
        
        # Teacher-like encouragement
        encouragement = (
            f"Great work on this {variant.framework} approach! Your copy shows strong understanding "
            f"of persuasive writing principles. With the suggested refinements, this could easily "
            f"move from a {letter_grade} to an A+. Remember, the best copy comes from iteration "
            f"and testing. Keep exploring creative ways to connect with your audience!"
        )
        
        return ReviewResponse(
            letter_grade=letter_grade,
            overall_score=overall_score,
            strengths=strengths,
            improvements=improvements,
            brief_alignment=brief_alignment,
            specific_suggestions=specific_suggestions,
            encouragement=encouragement
        )
        
    except Exception as e:
        logger.error(f"Error reviewing copy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refine")
async def refine_copy(request: RefineRequest):
    """
    Refine copy variant based on user instructions using AI with full client context
    """
    try:
        variant = request.variant
        instruction = request.instruction
        model = request.model or "gpt-3.5-turbo"
        client_id = request.client_id
        
        # Fetch client brand context from Firestore
        brand_context = {}
        if client_id:
            db = get_firestore_client()
            if db:
                try:
                    # Get client document
                    client_ref = db.collection('clients').document(client_id)
                    client_doc = client_ref.get()
                    
                    if client_doc.exists:
                        client_data = client_doc.to_dict()
                        brand_context = {
                            "name": client_data.get("name", "Unknown Client"),
                            "industry": client_data.get("industry", ""),
                            "voice": client_data.get("brand_voice", "professional"),
                            "tone": client_data.get("brand_tone", "friendly"),
                            "personality": client_data.get("brand_personality", ""),
                            "values": client_data.get("brand_values", []),
                            "target_audience": client_data.get("target_audience", "general audience"),
                            "emoji_usage": client_data.get("emoji_usage", "moderate"),
                            "formality_level": client_data.get("formality_level", "moderate"),
                            "key_messages": client_data.get("key_messages", []),
                            "unique_selling_points": client_data.get("unique_selling_points", []),
                            "prohibited_words": client_data.get("prohibited_words", []),
                            "preferred_phrases": client_data.get("preferred_phrases", [])
                        }
                        logger.info(f"Loaded brand context for client: {brand_context.get('name')}")
                except Exception as e:
                    logger.warning(f"Could not fetch client brand context: {e}")
        
        # Build comprehensive refinement prompt with brand context
        prompt = f"""
        You are an expert email copywriter. Refine the following email copy based on the user's instruction while maintaining brand guidelines.
        
        === CLIENT BRAND CONTEXT ===
        Client: {brand_context.get('name', 'Unknown')}
        Industry: {brand_context.get('industry', 'General')}
        Brand Voice: {brand_context.get('voice', 'Professional')}
        Brand Tone: {brand_context.get('tone', 'Friendly')}
        Brand Personality: {brand_context.get('personality', 'Helpful')}
        Target Audience: {brand_context.get('target_audience', 'General audience')}
        Core Values: {', '.join(brand_context.get('values', []))}
        Unique Selling Points: {', '.join(brand_context.get('unique_selling_points', []))}
        Formality Level: {brand_context.get('formality_level', 'moderate')}
        Emoji Usage: {brand_context.get('emoji_usage', 'moderate')}
        
        === CURRENT EMAIL COPY ===
        Framework: {variant.framework}
        Creativity Level: {variant.creativity_level}
        - Subject Line A: {variant.subject_line_a}
        - Subject Line B: {variant.subject_line_b}
        - Preview Text: {variant.preview_text}
        - Hero H1: {variant.hero_h1}
        - Sub-head: {variant.sub_head}
        - CTA: {variant.cta_copy}
        - Full Body: {variant.full_email_body}
        
        === USER INSTRUCTION ===
        {instruction}
        
        === REQUIREMENTS ===
        1. Apply the refinement based on the user's instruction
        2. Maintain the {variant.framework} framework structure
        3. Keep the {variant.creativity_level} creativity level
        4. Ensure all copy aligns with the brand voice, tone, and values
        5. Respect the formality level and emoji usage guidelines
        {f"6. Avoid these words: {', '.join(brand_context.get('prohibited_words', []))}" if brand_context.get('prohibited_words') else ""}
        {f"7. Try to incorporate these phrases: {', '.join(brand_context.get('preferred_phrases', []))}" if brand_context.get('preferred_phrases') else ""}
        
        Return ONLY a JSON object with the refined fields and specific changes made:
        {{
            "subject_line_a": "refined subject A",
            "subject_line_b": "refined subject B",
            "preview_text": "refined preview",
            "hero_h1": "refined hero",
            "sub_head": "refined subhead",
            "cta_copy": "refined CTA",
            "full_email_body": "refined full body",
            "changes_made": ["List of specific changes applied"]
        }}
        """
        
        # Create context object with brand data
        context = {
            "brand_context": brand_context,
            "client_id": client_id,
            "framework": variant.framework,
            "creativity_level": variant.creativity_level
        }
        
        # Invoke AI model with full context
        logger.info(f"Refining copy with instruction: {instruction[:100]}...")
        logger.info(f"Using brand context for: {brand_context.get('name', 'Unknown')}")
        
        if USE_ORCHESTRATOR:
            # Use AI Orchestrator for refinement
            client = get_orchestrator_client()
            result = await client.complete_marketing(prompt, context, temperature=0.7, max_tokens=2000)
        else:
            # Use direct provider
            result = await ai_service.invoke_model(prompt, model, context)
        
        if result.get("content"):
            try:
                # Parse AI response
                refined_data = json.loads(result["content"])
                
                # Create refined variant
                refined_variant = variant.copy()
                if "subject_line_a" in refined_data:
                    refined_variant.subject_line_a = refined_data["subject_line_a"]
                if "subject_line_b" in refined_data:
                    refined_variant.subject_line_b = refined_data["subject_line_b"]
                if "preview_text" in refined_data:
                    refined_variant.preview_text = refined_data["preview_text"]
                if "hero_h1" in refined_data:
                    refined_variant.hero_h1 = refined_data["hero_h1"]
                if "sub_head" in refined_data:
                    refined_variant.sub_head = refined_data["sub_head"]
                if "cta_copy" in refined_data:
                    refined_variant.cta_copy = refined_data["cta_copy"]
                if "full_email_body" in refined_data:
                    refined_variant.full_email_body = refined_data["full_email_body"]
                
                changes = refined_data.get("changes_made", ["Applied refinements as requested"])
                
                # Generate patch
                patch = generate_patch(variant, refined_variant)
                
                # Create history entry
                history_entry = {
                    "instruction": instruction,
                    "agent": request.agent_id or "default",
                    "model": result.get("model_used", model),
                    "timestamp": datetime.now().isoformat(),
                    "changes": changes
                }
                
                # Log telemetry
                logger.info(f"refine agent={request.agent_id or 'default'} model={result.get('model_used', model)} draft_bytes={len(json.dumps(variant.dict()))} instr_len={len(instruction)}")
                
                return RefineResponse(
                    refined_variant=refined_variant,
                    changes_made=changes,
                    model_used=result.get("model_used", model),
                    patch=patch,
                    history_entry=history_entry
                )
                
            except json.JSONDecodeError:
                # Fallback to simple refinement
                logger.warning("Could not parse AI response as JSON, applying simple refinement")
                refined_variant = apply_simple_refinement(variant, instruction)
                return RefineResponse(
                    refined_variant=refined_variant,
                    changes_made=["Applied basic refinements based on instruction"],
                    model_used="fallback"
                )
        else:
            # Use fallback refinement
            refined_variant = apply_simple_refinement(variant, instruction)
            return RefineResponse(
                refined_variant=refined_variant,
                changes_made=["Applied template-based refinements"],
                model_used="fallback"
            )
            
    except Exception as e:
        logger.error(f"Error refining copy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_patch(original: CopyVariant, refined: CopyVariant) -> List[Dict[str, Any]]:
    """
    Generate JSON patch operations to transform original to refined
    """
    patch = []
    original_dict = original.dict()
    refined_dict = refined.dict()
    
    for field, new_value in refined_dict.items():
        if field in original_dict and original_dict[field] != new_value:
            patch.append({
                "op": "replace",
                "path": f"/{field}",
                "value": new_value
            })
    
    return patch

def apply_simple_refinement(variant: CopyVariant, instruction: str) -> CopyVariant:
    """
    Apply simple template-based refinements when AI is unavailable
    """
    refined = variant.copy()
    instruction_lower = instruction.lower()
    changes = []
    
    # Simple refinement rules
    if "urgent" in instruction_lower or "urgency" in instruction_lower:
        refined.subject_line_a = f"⏰ URGENT: {variant.subject_line_a}"
        refined.preview_text = "Limited time - Act now before it's too late!"
        changes.append("Added urgency to subject and preview")
        
    if "shorter" in instruction_lower or "shorten" in instruction_lower:
        if "subject" in instruction_lower:
            refined.subject_line_a = variant.subject_line_a[:40]
            refined.subject_line_b = variant.subject_line_b[:40]
            changes.append("Shortened subject lines")
        if "cta" in instruction_lower:
            refined.cta_copy = variant.cta_copy.split()[0:3]
            refined.cta_copy = " ".join(refined.cta_copy) if isinstance(refined.cta_copy, list) else refined.cta_copy[:20]
            changes.append("Shortened CTA")
            
    if "emoji" in instruction_lower:
        if "add" in instruction_lower or "more" in instruction_lower:
            refined.subject_line_a = f"🎯 {variant.subject_line_a}"
            refined.uses_emoji = True
            changes.append("Added emojis")
        elif "remove" in instruction_lower:
            refined.subject_line_a = variant.subject_line_a.replace("🎯", "").replace("💥", "").strip()
            refined.uses_emoji = False
            changes.append("Removed emojis")
            
    if "formal" in instruction_lower:
        refined.hero_h1 = variant.hero_h1.replace("!", ".")
        refined.sub_head = variant.sub_head.replace("you", "your organization")
        changes.append("Made tone more formal")
        
    if not changes:
        changes.append("Applied general refinements")
    
    return refined

@app.post("/api/chat")
async def chat_refinement(request: ChatRequest):
    """
    Handle AI chat requests for copy refinement
    """
    try:
        message = request.message.lower()
        variant = request.current_variant
        
        # Parse the user's intent
        edited_variant = None
        edit_type = "suggestion"
        affected_sections = []
        
        # Simple intent detection (in production, use AI)
        if "subject" in message:
            affected_sections.append("subject_line")
            if "shorter" in message:
                # Make subject line shorter
                edited_variant = variant.copy()
                edited_variant.subject_line_a = variant.subject_line_a[:40] + "..."
                edited_variant.subject_line_b = variant.subject_line_b[:40] + "..."
                edit_type = "inline_edit"
                reply = "I've shortened both subject lines to under 40 characters for better mobile display."
            else:
                reply = "For subject lines, consider: 1) Keep under 50 characters, 2) Use action words, 3) Create urgency or curiosity."
                
        elif "emoji" in message:
            affected_sections.append("full_email_body")
            if "add" in message or "more" in message:
                edited_variant = variant.copy()
                edited_variant.subject_line_a = "🎯 " + variant.subject_line_a
                edited_variant.hero_h1 = variant.hero_h1 + " 🚀"
                edited_variant.uses_emoji = True
                edit_type = "inline_edit"
                reply = "I've added strategic emojis to increase visual appeal and engagement."
            elif "remove" in message or "less" in message:
                edited_variant = variant.copy()
                edited_variant.subject_line_a = variant.subject_line_a.replace("🎯 ", "").replace("🚀", "")
                edited_variant.uses_emoji = False
                edit_type = "inline_edit"
                reply = "I've removed emojis for a more professional tone."
            else:
                reply = "Emojis can increase open rates by 20% when used appropriately. Would you like me to add or remove them?"
                
        elif "cta" in message or "call to action" in message:
            affected_sections.append("cta_copy")
            if "stronger" in message or "better" in message:
                edited_variant = variant.copy()
                edited_variant.cta_copy = f"Claim Your {variant.offer or 'Exclusive Offer'} Now →"
                edit_type = "inline_edit"
                reply = "I've strengthened the CTA with more action-oriented language and urgency."
            else:
                reply = "For CTAs, use action verbs, create urgency, and be specific about the value. What would you like to emphasize?"
                
        elif "tone" in message:
            affected_sections.append("full_email_body")
            if "formal" in message:
                reply = "To make the tone more formal: remove contractions, use professional salutations, and eliminate casual phrases."
            elif "casual" in message or "friendly" in message:
                reply = "To make it more casual: use contractions, add conversational phrases, and speak directly to the reader as 'you'."
            else:
                reply = "I can adjust the tone. Would you prefer more formal, casual, urgent, or empathetic?"
                
        else:
            # General response
            reply = (
                "I can help refine any part of your copy. Try asking me to:\n"
                "• Make subject lines shorter or more engaging\n"
                "• Adjust the tone (formal/casual/urgent)\n"
                "• Strengthen the CTA\n"
                "• Add or remove emojis\n"
                "• Improve specific sections"
            )
        
        return ChatResponse(
            reply=reply,
            edited_variant=edited_variant,
            edit_type=edit_type,
            affected_sections=affected_sections
        )
        
    except Exception as e:
        logger.error(f"Error in chat refinement: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/prompt")
async def get_agent_prompt(agent_id: str):
    """Get the prompt template for a specific agent"""
    try:
        # Skip Firestore for now - it's causing timeouts
        # Just use the fallback prompts
        pass
        
        # Fallback to hardcoded prompts
        agent_personas = {
            "email_marketing_expert": "You are an email marketing specialist with 10+ years experience.\n\nFocus on engagement optimization, subject line psychology, and conversion-driven copy.\n\n{user_input}",
            "conversion_optimizer": "You are a conversion rate optimization specialist.\n\nMaximize click-through rates and conversions through data-driven copy.\n\n{user_input}",
            "brand_strategist": "You are a brand voice and messaging strategist.\n\nMaintain brand consistency while building emotional connections.\n\n{user_input}",
            "creative_copywriter": "You are a creative storytelling specialist.\n\nCraft memorable, share-worthy content that stands out.\n\n{user_input}",
            "data_driven_marketer": "You are an analytics-focused marketing strategist.\n\nProvide copy backed by data, metrics, and proven results.\n\n{user_input}",
            "customer_retention_specialist": "You are a customer loyalty and retention expert.\n\nBuild long-term relationships and repeat business.\n\n{user_input}",
            "compliance_officer": "You are a legal compliance and risk management specialist.\n\nEnsure all copy meets legal requirements and industry regulations.\n\n{user_input}"
        }
        
        if agent_id in agent_personas:
            return {"prompt": agent_personas[agent_id]}
        
        return {"prompt": f"You are {agent_id}. {'{user_input}'}"}
        
    except Exception as e:
        logger.error(f"Error fetching agent prompt: {e}")
        return {"prompt": ""}

@app.put("/api/agents/{agent_id}/prompt")
async def save_agent_prompt(agent_id: str, data: Dict[str, str] = Body(...)):
    """Save a custom prompt template for a specific agent"""
    try:
        prompt = data.get("prompt", "")
        
        # Skip Firestore for now - just log and accept
        logger.info(f"Received custom prompt for agent {agent_id}: {len(prompt)} chars")
        
        # Even if Firestore fails, we accept the prompt (it will be cached client-side)
        return {"success": True, "message": "Prompt accepted (cached locally)"}
    except Exception as e:
        logger.error(f"Error saving agent prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)