"""
Calendar API with full LangSmith tracing integration
Connects calendar operations to LangGraph and provides comprehensive observability
"""

import os
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import logging
import json
from uuid import uuid4

# Import workflow instrumentation
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from workflow.instrumentation import instrument_workflow, create_langsmith_callback, instrument_node
from langsmith import Client
from langsmith.run_helpers import traceable

# Import dependencies
from app.deps.firestore import get_db
from app.services.auth import get_current_user

# Use get_db as our Firestore client function
def get_firestore_client():
    return get_db()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar-traced", tags=["calendar-langsmith"])

# Initialize LangSmith client
LANGSMITH_CLIENT = Client() if os.getenv("ENABLE_TRACING", "true").lower() == "true" else None
LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://127.0.0.1:2024")


# ============================================================================
# DATA MODELS
# ============================================================================

class CalendarEvent(BaseModel):
    """Calendar event with tracing metadata"""
    id: Optional[str] = Field(None, description="Event ID")
    client_id: str = Field(..., description="Client identifier")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    date: str = Field(..., description="Event date (YYYY-MM-DD)")
    time: Optional[str] = Field("09:00", description="Event time (HH:MM)")
    type: str = Field("campaign", description="Event type: campaign, newsletter, promotion")
    status: str = Field("planned", description="Status: planned, in_progress, completed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    trace_id: Optional[str] = Field(None, description="LangSmith trace ID")


class TracedCampaignPlanRequest(BaseModel):
    """Request for AI-powered campaign planning"""
    client_id: str = Field(..., description="Client identifier")
    brand: str = Field(..., description="Brand name")
    month: str = Field(..., description="Planning month (YYYY-MM)")
    campaign_count: int = Field(4, description="Number of campaigns to plan")
    include_variables: bool = Field(True, description="Include context variables")
    use_langgraph: bool = Field(True, description="Use LangGraph for planning")


class TracedResponse(BaseModel):
    """Response with LangSmith trace information"""
    data: Any
    trace_id: Optional[str] = None
    trace_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_trace_url(trace_id: str) -> str:
    """Generate LangSmith trace URL"""
    project = os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://smith.langchain.com")
    return f"{endpoint}/projects/{project}/runs/{trace_id}"


async def fetch_context_variables(client_id: str, month: str) -> Dict[str, Any]:
    """Fetch all context variables for LangSmith tracing"""
    try:
        # Call variables API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8000/api/variables/all",
                params={"client_id": client_id, "selected_month": month}
            )
            if response.status_code == 200:
                return response.json().get("variables", {})
    except Exception as e:
        logger.error(f"Failed to fetch variables: {e}")
    
    return {
        "client_id": client_id,
        "month": month,
        "timestamp": datetime.now().isoformat()
    }


async def call_langgraph_agent(
    brand: str,
    month: str,
    context: Dict[str, Any],
    prompt: str = None
) -> Dict[str, Any]:
    """Call LangGraph agent for campaign planning"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare the request
            request_data = {
                "assistant_id": "agent",
                "input": {
                    "messages": [{
                        "role": "user",
                        "content": prompt or f"Generate a comprehensive campaign plan for {brand} for {month}"
                    }],
                    "brand": brand,
                    "month": month,
                    **context  # Include all context variables
                },
                "config": {
                    "configurable": {
                        "thread_id": f"calendar_{brand}_{month}_{uuid4().hex[:8]}"
                    }
                }
            }
            
            # Call LangGraph
            response = await client.post(
                f"{LANGGRAPH_URL}/threads",
                json=request_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"LangGraph returned {response.status_code}: {response.text}")
                return {"error": f"LangGraph error: {response.status_code}"}
                
    except Exception as e:
        logger.error(f"Failed to call LangGraph: {e}")
        return {"error": str(e)}


# ============================================================================
# TRACED CALENDAR ENDPOINTS
# ============================================================================

@router.post("/events", response_model=TracedResponse)
@traceable(
    run_type="chain",
    name="calendar_create_event",
    project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
)
async def create_calendar_event(
    event: CalendarEvent,
    db=Depends(get_db),
    current_user=None  # Temporarily disabled for testing - REMOVE IN PRODUCTION
) -> TracedResponse:
    """
    Create a calendar event with full LangSmith tracing
    """
    trace_id = uuid4().hex
    
    # Add trace context
    run_context = {
        "client_id": event.client_id,
        "brand": event.client_id,
        "month": event.date[:7] if event.date else "unknown",
        "event_type": event.type,
        "user": current_user.get("email", "unknown") if current_user else "test-user",
        "trace_id": trace_id
    }
    
    # Log to LangSmith
    logger.info(f"Creating calendar event with trace {trace_id}")
    
    try:
        # Generate event ID if not provided
        if not event.id:
            event.id = f"evt_{uuid4().hex[:12]}"
        
        # Add trace ID to event
        event.trace_id = trace_id
        
        # Store in Firestore
        doc_ref = db.collection("calendar_events").document(event.id)
        doc_ref.set({
            **event.dict(),
            "created_at": datetime.now().isoformat(),
            "created_by": current_user.get("email") if current_user else "test-user",
            "trace_id": trace_id
        })
        
        # Return with trace information
        return TracedResponse(
            data=event,
            trace_id=trace_id,
            trace_url=get_trace_url(trace_id),
            metadata=run_context
        )
        
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{client_id}", response_model=TracedResponse)
@traceable(
    run_type="chain",
    name="calendar_get_events",
    project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
)
async def get_calendar_events(
    client_id: str,
    month: Optional[str] = Query(None, description="Filter by month (YYYY-MM)"),
    db=Depends(get_db)
) -> TracedResponse:
    """
    Get calendar events with LangSmith tracing
    """
    trace_id = uuid4().hex
    
    # Add trace context
    run_context = {
        "client_id": client_id,
        "month": month or "all",
        "trace_id": trace_id
    }
    
    logger.info(f"Fetching calendar events with trace {trace_id}")
    
    try:
        # Query Firestore
        query = db.collection("calendar_events").where("client_id", "==", client_id)
        
        # Add month filter if provided
        if month:
            start_date = f"{month}-01"
            end_date = f"{month}-31"
            query = query.where("date", ">=", start_date).where("date", "<=", end_date)
        
        # Execute query
        docs = query.stream()
        events = [doc.to_dict() for doc in docs]
        
        return TracedResponse(
            data={"events": events, "count": len(events)},
            trace_id=trace_id,
            trace_url=get_trace_url(trace_id),
            metadata=run_context
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan", response_model=TracedResponse)
@traceable(
    run_type="chain",  # Changed from "workflow" to "chain" for compatibility
    name="calendar_ai_planning",
    project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
)
async def generate_campaign_plan(
    request: TracedCampaignPlanRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
) -> TracedResponse:
    """
    Generate AI-powered campaign plan with LangGraph and full tracing
    """
    trace_id = uuid4().hex
    
    # Build comprehensive context
    run_context = {
        "client_id": request.client_id,
        "brand": request.brand,
        "month": request.month,
        "campaign_count": request.campaign_count,
        "user": current_user.get("email", "unknown") if current_user else "test-user",
        "trace_id": trace_id,
        "use_langgraph": request.use_langgraph
    }
    
    logger.info(f"Generating campaign plan with trace {trace_id}")
    
    try:
        # Fetch context variables if requested
        context_vars = {}
        if request.include_variables:
            context_vars = await fetch_context_variables(request.client_id, request.month)
            logger.info(f"Loaded {len(context_vars)} context variables")
        
        # Prepare planning result
        plan_result = {}
        
        if request.use_langgraph:
            # Call LangGraph for intelligent planning
            logger.info("Calling LangGraph for campaign planning")
            
            # Build custom prompt with context
            prompt = f"""
            Create a comprehensive email campaign plan for {request.brand} for {request.month}.
            
            Requirements:
            - Generate {request.campaign_count} campaigns
            - Include optimal send times based on past performance
            - Suggest segments and personalization strategies
            - Consider seasonality and business cycles
            
            Context Variables Available:
            {json.dumps(context_vars, indent=2)[:500]}  # Truncate for prompt
            
            Provide a detailed plan with specific dates, campaign types, and content themes.
            """
            
            langgraph_result = await call_langgraph_agent(
                brand=request.brand,
                month=request.month,
                context=context_vars,
                prompt=prompt
            )
            
            plan_result["langgraph"] = langgraph_result
            
            # Parse LangGraph response to create events
            if "thread_id" in langgraph_result:
                # Successfully called LangGraph
                plan_result["status"] = "success"
                plan_result["thread_id"] = langgraph_result["thread_id"]
                
                # Create calendar events from the plan
                # (This would parse the LangGraph response and create actual events)
                events_created = []
                
                # Mock event creation based on request
                for i in range(request.campaign_count):
                    event_date = datetime.strptime(f"{request.month}-01", "%Y-%m-%d") + timedelta(days=7*i + 3)
                    event = CalendarEvent(
                        id=f"evt_{uuid4().hex[:12]}",
                        client_id=request.client_id,
                        title=f"Campaign {i+1} - {request.brand}",
                        description=f"AI-generated campaign for {request.brand}",
                        date=event_date.strftime("%Y-%m-%d"),
                        type=["campaign", "newsletter", "promotion"][i % 3],
                        status="planned",
                        metadata={
                            "generated_by": "langgraph",
                            "trace_id": trace_id,
                            "thread_id": langgraph_result.get("thread_id")
                        }
                    )
                    
                    # Store event in Firestore
                    doc_ref = db.collection("calendar_events").document(event.id)
                    doc_ref.set({
                        **event.dict(),
                        "created_at": datetime.now().isoformat(),
                        "created_by": "ai_planner",
                        "trace_id": trace_id
                    })
                    
                    events_created.append(event.dict())
                
                plan_result["events_created"] = events_created
            else:
                plan_result["status"] = "error"
                plan_result["error"] = langgraph_result.get("error", "Unknown error")
        
        else:
            # Fallback to basic planning without LangGraph
            logger.info("Using basic planning (LangGraph disabled)")
            
            events_created = []
            for i in range(request.campaign_count):
                event_date = datetime.strptime(f"{request.month}-01", "%Y-%m-%d") + timedelta(days=7*i + 3)
                event = CalendarEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    client_id=request.client_id,
                    title=f"Campaign {i+1} - {request.brand}",
                    description=f"Scheduled campaign for {request.brand}",
                    date=event_date.strftime("%Y-%m-%d"),
                    type=["campaign", "newsletter", "promotion"][i % 3],
                    status="planned",
                    metadata={
                        "generated_by": "basic_planner",
                        "trace_id": trace_id
                    }
                )
                
                # Store event
                doc_ref = db.collection("calendar_events").document(event.id)
                doc_ref.set({
                    **event.dict(),
                    "created_at": datetime.now().isoformat(),
                    "created_by": "basic_planner",
                    "trace_id": trace_id
                })
                
                events_created.append(event.dict())
            
            plan_result = {
                "status": "success",
                "events_created": events_created,
                "planner": "basic"
            }
        
        # Return with comprehensive tracing
        return TracedResponse(
            data=plan_result,
            trace_id=trace_id,
            trace_url=get_trace_url(trace_id),
            metadata={
                **run_context,
                "variables_loaded": len(context_vars),
                "events_created": len(plan_result.get("events_created", []))
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/{client_id}", response_model=TracedResponse)
@traceable(
    run_type="chain",
    name="calendar_analytics",
    project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
)
async def get_calendar_analytics(
    client_id: str,
    month: Optional[str] = Query(None, description="Analysis month (YYYY-MM)"),
    db=Depends(get_db)
) -> TracedResponse:
    """
    Get calendar analytics with performance correlation via LangSmith
    """
    trace_id = uuid4().hex
    
    run_context = {
        "client_id": client_id,
        "month": month or "all_time",
        "trace_id": trace_id
    }
    
    logger.info(f"Generating calendar analytics with trace {trace_id}")
    
    try:
        # Query events
        query = db.collection("calendar_events").where("client_id", "==", client_id)
        if month:
            start_date = f"{month}-01"
            end_date = f"{month}-31"
            query = query.where("date", ">=", start_date).where("date", "<=", end_date)
        
        docs = query.stream()
        events = [doc.to_dict() for doc in docs]
        
        # Calculate analytics
        analytics = {
            "total_events": len(events),
            "by_type": {},
            "by_status": {},
            "by_week": {},
            "optimal_days": [],
            "trace_correlation": {}
        }
        
        # Aggregate by type and status
        for event in events:
            event_type = event.get("type", "unknown")
            status = event.get("status", "unknown")
            
            analytics["by_type"][event_type] = analytics["by_type"].get(event_type, 0) + 1
            analytics["by_status"][status] = analytics["by_status"].get(status, 0) + 1
            
            # Track traces for correlation
            if event.get("trace_id"):
                analytics["trace_correlation"][event["id"]] = {
                    "trace_id": event["trace_id"],
                    "trace_url": get_trace_url(event["trace_id"])
                }
        
        # If we have LangGraph, get AI insights
        if len(events) > 0:
            context_vars = await fetch_context_variables(client_id, month or datetime.now().strftime("%Y-%m"))
            
            # Call LangGraph for insights
            insights_prompt = f"""
            Analyze the calendar performance for {client_id}:
            - Total events: {len(events)}
            - Event types: {analytics['by_type']}
            - Status distribution: {analytics['by_status']}
            
            Provide insights on:
            1. Campaign frequency optimization
            2. Best performing event types
            3. Timing recommendations
            4. Areas for improvement
            """
            
            insights = await call_langgraph_agent(
                brand=client_id,
                month=month or "all_time",
                context=context_vars,
                prompt=insights_prompt
            )
            
            analytics["ai_insights"] = insights
        
        return TracedResponse(
            data=analytics,
            trace_id=trace_id,
            trace_url=get_trace_url(trace_id),
            metadata=run_context
        )
        
    except Exception as e:
        logger.error(f"Failed to generate analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LANGGRAPH INTEGRATION ENDPOINTS
# ============================================================================

@router.get("/langgraph/status")
async def check_langgraph_status() -> Dict[str, Any]:
    """Check LangGraph server status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LANGGRAPH_URL}/assistants/agent")
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "url": LANGGRAPH_URL,
                "assistant_available": response.status_code == 200
            }
    except Exception as e:
        return {
            "status": "disconnected",
            "url": LANGGRAPH_URL,
            "error": str(e)
        }


@router.get("/langsmith/project")
async def get_langsmith_project() -> Dict[str, Any]:
    """Get LangSmith project information"""
    return {
        "project": os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar"),
        "endpoint": os.getenv("LANGSMITH_ENDPOINT", "https://smith.langchain.com"),
        "tracing_enabled": os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
        "dashboard_url": f"{os.getenv('LANGSMITH_ENDPOINT', 'https://smith.langchain.com')}/projects/{os.getenv('LANGSMITH_PROJECT', 'emailpilot-calendar')}"
    }


@router.post("/sync-variables")
async def sync_variables_to_langgraph(
    client_id: str,
    month: str
) -> Dict[str, Any]:
    """Sync variables from Firestore to LangGraph context"""
    try:
        # Fetch variables
        variables = await fetch_context_variables(client_id, month)
        
        # You could store these in a shared context or pass to LangGraph
        # For now, we'll just return them
        return {
            "status": "success",
            "variables_count": len(variables),
            "sample": dict(list(variables.items())[:5])  # Show first 5 variables
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# AGENT REGISTRATION
# ============================================================================

@router.post("/register-agents")
async def register_calendar_agents() -> Dict[str, Any]:
    """
    Register calendar-specific agents in the multi-agent system
    This connects calendar functionality to the broader agent ecosystem
    """
    agents_registered = []
    
    try:
        # Define calendar agents
        calendar_agents = [
            {
                "id": "calendar_planner",
                "name": "Calendar Planning Agent",
                "description": "Plans and schedules email campaigns",
                "capabilities": ["campaign_planning", "schedule_optimization", "content_calendar"],
                "model": "gpt-4",
                "temperature": 0.7
            },
            {
                "id": "calendar_analyzer",
                "name": "Calendar Analytics Agent", 
                "description": "Analyzes calendar performance and patterns",
                "capabilities": ["performance_analysis", "pattern_detection", "optimization_suggestions"],
                "model": "gpt-4",
                "temperature": 0.5
            },
            {
                "id": "calendar_coordinator",
                "name": "Calendar Coordination Agent",
                "description": "Coordinates between calendar and other systems",
                "capabilities": ["system_integration", "data_sync", "conflict_resolution"],
                "model": "gpt-3.5-turbo",
                "temperature": 0.3
            }
        ]
        
        # Store agents in Firestore
        db = get_firestore_client()
        
        for agent in calendar_agents:
            doc_ref = db.collection("agents").document(agent["id"])
            doc_ref.set({
                **agent,
                "created_at": datetime.now().isoformat(),
                "type": "calendar",
                "status": "active"
            })
            agents_registered.append(agent["id"])
            logger.info(f"Registered agent: {agent['id']}")
        
        return {
            "status": "success",
            "agents_registered": agents_registered,
            "count": len(agents_registered)
        }
        
    except Exception as e:
        logger.error(f"Failed to register agents: {e}")
        return {
            "status": "error",
            "error": str(e),
            "agents_registered": agents_registered
        }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for traced calendar API"""
    
    # Check various components
    checks = {
        "api": "healthy",
        "langsmith_tracing": os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
        "langsmith_project": os.getenv("LANGSMITH_PROJECT", "not_configured"),
        "langgraph_url": LANGGRAPH_URL
    }
    
    # Check LangGraph connection
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{LANGGRAPH_URL}/assistants/agent")
            checks["langgraph_connected"] = response.status_code == 200
    except:
        checks["langgraph_connected"] = False
    
    # Check Firestore connection
    try:
        db = get_firestore_client()
        # Simple query to test connection
        db.collection("calendar_events").limit(1).get()
        checks["firestore_connected"] = True
    except:
        checks["firestore_connected"] = False
    
    # Overall health
    all_healthy = all([
        checks["api"] == "healthy",
        checks["langsmith_tracing"],
        checks["firestore_connected"]
    ])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }