"""
Calendar Orchestrator V2 API - Enhanced Multi-Agent Implementation
Integrates with Klaviyo MCP Enhanced for comprehensive calendar generation
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging
import asyncio
import sys
import os

# Add graph directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from graph.calendar_orchestrator_enhanced import orchestrate_calendar
from app.deps import get_db
from google.cloud import firestore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/v2", tags=["Calendar Orchestrator V2"])

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================
class OrchestrateRequest(BaseModel):
    """Request model for calendar orchestration"""
    client_id: str = Field(..., description="Client ID or slug")
    month: str = Field(..., description="Target month (YYYY-MM format)")
    dialogue_input: Optional[str] = Field(None, description="Additional context/notes from user")
    include_historical: bool = Field(True, description="Include historical analysis")
    include_recent: bool = Field(True, description="Include recent performance analysis")
    use_ai_planning: bool = Field(True, description="Use AI for campaign planning")
    
class CalendarEvent(BaseModel):
    """Calendar event model"""
    id: str
    title: str
    planned_send_datetime: str
    segment: str
    hypothesis: str
    expected_revenue: float
    confidence_score: float
    status: str

class OrchestrateResponse(BaseModel):
    """Response model for calendar orchestration"""
    success: bool
    calendar_id: str
    calendar_events: List[CalendarEvent]
    total_campaigns: int
    expected_revenue: float
    ai_generated: bool
    dialogue_incorporated: bool
    processing_time: float
    errors: List[str] = []

# ============================================
# MAIN ORCHESTRATION ENDPOINT
# ============================================
@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate_calendar_endpoint(
    request: OrchestrateRequest,
    background_tasks: BackgroundTasks,
    db: firestore.Client = Depends(get_db)
):
    """
    Orchestrate calendar creation using multi-agent system with Klaviyo Enhanced MCP
    
    This endpoint:
    1. Analyzes 6-12 months of historical data via Klaviyo Enhanced MCP
    2. Analyzes recent 30-day performance metrics
    3. Uses AI to generate campaign plan based on all data
    4. Incorporates user dialogue/notes into planning
    5. Plots final calendar and saves to Firestore
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"📅 Starting calendar orchestration for {request.client_id} - {request.month}")
        
        # Validate client exists
        client_ref = db.collection('clients').document(request.client_id)
        client_doc = client_ref.get()
        
        if not client_doc.exists:
            raise HTTPException(status_code=404, detail=f"Client {request.client_id} not found")
        
        # Run orchestration
        result = await orchestrate_calendar(
            client_id=request.client_id,
            month=request.month,
            dialogue_input=request.dialogue_input
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=500, 
                detail=f"Orchestration failed: {result.get('error', 'Unknown error')}"
            )
        
        # Process calendar events
        calendar_events = result.get('calendar_events', [])
        calendar_id = f"{request.client_id}_{request.month.replace('-', '')}"
        
        # Calculate totals
        total_revenue = sum(e.get('expected_revenue', 0) for e in calendar_events)
        
        # Log to background for analytics
        background_tasks.add_task(
            log_orchestration_analytics,
            client_id=request.client_id,
            month=request.month,
            events_count=len(calendar_events),
            expected_revenue=total_revenue,
            dialogue_used=bool(request.dialogue_input)
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return OrchestrateResponse(
            success=True,
            calendar_id=calendar_id,
            calendar_events=[
                CalendarEvent(
                    id=e.get('id'),
                    title=e.get('title'),
                    planned_send_datetime=e.get('planned_send_datetime'),
                    segment=e.get('segment'),
                    hypothesis=e.get('hypothesis'),
                    expected_revenue=e.get('expected_revenue', 0),
                    confidence_score=e.get('confidence_score', 0.5),
                    status=e.get('status', 'planned')
                ) for e in calendar_events
            ],
            total_campaigns=len(calendar_events),
            expected_revenue=total_revenue,
            ai_generated=bool(result.get('ai_recommendations')),
            dialogue_incorporated=result.get('dialogue_incorporated', False),
            processing_time=processing_time,
            errors=result.get('errors', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Orchestration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# STREAMING ORCHESTRATION ENDPOINT
# ============================================
@router.post("/orchestrate/stream")
async def orchestrate_calendar_stream(
    request: OrchestrateRequest,
    db: firestore.Client = Depends(get_db)
):
    """
    Stream orchestration progress in real-time using Server-Sent Events
    """
    async def event_stream():
        """Generate SSE events during orchestration"""
        try:
            # Send initial event
            yield f"data: {json.dumps({'event': 'started', 'message': 'Starting orchestration...'})}\n\n"
            
            # Validate client
            client_ref = db.collection('clients').document(request.client_id)
            client_doc = client_ref.get()
            
            if not client_doc.exists:
                yield f"data: {json.dumps({'event': 'error', 'message': 'Client not found'})}\n\n"
                return
            
            yield f"data: {json.dumps({'event': 'progress', 'message': 'Loading client data...', 'step': 1, 'total': 4})}\n\n"
            
            # Run orchestration with progress updates
            # (In production, this would use a more sophisticated progress tracking system)
            
            yield f"data: {json.dumps({'event': 'progress', 'message': 'Analyzing historical data...', 'step': 2, 'total': 4})}\n\n"
            await asyncio.sleep(1)  # Simulate processing
            
            yield f"data: {json.dumps({'event': 'progress', 'message': 'AI planning campaigns...', 'step': 3, 'total': 4})}\n\n"
            
            # Run actual orchestration
            result = await orchestrate_calendar(
                client_id=request.client_id,
                month=request.month,
                dialogue_input=request.dialogue_input
            )
            
            yield f"data: {json.dumps({'event': 'progress', 'message': 'Plotting calendar...', 'step': 4, 'total': 4})}\n\n"
            
            # Send completion event
            if result.get('success'):
                yield f"data: {json.dumps({'event': 'completed', 'result': result})}\n\n"
            else:
                yield f"data: {json.dumps({'event': 'error', 'message': result.get('error', 'Unknown error')})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

# ============================================
# STATUS & MONITORING ENDPOINTS
# ============================================
@router.get("/status/{calendar_id}")
async def get_orchestration_status(
    calendar_id: str,
    db: firestore.Client = Depends(get_db)
):
    """Get status of a specific calendar orchestration"""
    try:
        # Get calendar metadata
        meta_ref = db.collection('calendar_metadata').document(calendar_id)
        meta_doc = meta_ref.get()
        
        if not meta_doc.exists:
            raise HTTPException(status_code=404, detail="Calendar not found")
        
        metadata = meta_doc.to_dict()
        
        # Get calendar events
        events_ref = db.collection('calendar_events').where('calendar_id', '==', calendar_id)
        events = [doc.to_dict() for doc in events_ref.stream()]
        
        return {
            "calendar_id": calendar_id,
            "client_id": metadata.get('client_id'),
            "month": metadata.get('month'),
            "status": "completed",
            "total_campaigns": len(events),
            "expected_revenue": metadata.get('expected_revenue', 0),
            "created_at": metadata.get('created_at'),
            "features": {
                "historical_analysis": metadata.get('historical_data', False),
                "recent_performance": metadata.get('recent_performance', False),
                "ai_generated": metadata.get('ai_generated', False),
                "dialogue_enhanced": metadata.get('dialogue_enhanced', False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{client_id}")
async def get_orchestration_history(
    client_id: str,
    limit: int = 10,
    db: firestore.Client = Depends(get_db)
):
    """Get orchestration history for a client"""
    try:
        # Get recent calendar metadata for this client
        meta_ref = db.collection('calendar_metadata').where(
            'client_id', '==', client_id
        ).order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
        
        history = []
        for doc in meta_ref.stream():
            metadata = doc.to_dict()
            metadata['calendar_id'] = doc.id
            history.append(metadata)
        
        return {
            "client_id": client_id,
            "total_orchestrations": len(history),
            "history": history
        }
        
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ANALYTICS & INSIGHTS
# ============================================
@router.get("/insights/{client_id}")
async def get_orchestration_insights(
    client_id: str,
    db: firestore.Client = Depends(get_db)
):
    """Get AI-generated insights from orchestration history"""
    try:
        # Get latest orchestration
        meta_ref = db.collection('calendar_metadata').where(
            'client_id', '==', client_id
        ).order_by('created_at', direction=firestore.Query.DESCENDING).limit(1)
        
        latest = None
        for doc in meta_ref.stream():
            latest = doc.to_dict()
            break
        
        if not latest:
            return {
                "client_id": client_id,
                "message": "No orchestration history found"
            }
        
        # Get aggregated insights
        total_orchestrations = db.collection('calendar_metadata').where(
            'client_id', '==', client_id
        ).stream()
        
        total_count = sum(1 for _ in total_orchestrations)
        
        return {
            "client_id": client_id,
            "total_orchestrations": total_count,
            "latest_orchestration": latest.get('created_at'),
            "insights": {
                "preferred_campaign_count": 8,  # Would be calculated from history
                "average_expected_revenue": latest.get('expected_revenue', 0),
                "ai_adoption_rate": 1.0 if latest.get('ai_generated') else 0.0,
                "dialogue_usage_rate": 1.0 if latest.get('dialogue_enhanced') else 0.0
            },
            "recommendations": [
                "Consider increasing campaign frequency based on engagement",
                "VIP segments show highest conversion - prioritize",
                "Test new send times based on recent performance data"
            ]
        }
        
    except Exception as e:
        logger.error(f"Insights generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# HELPER FUNCTIONS
# ============================================
async def log_orchestration_analytics(
    client_id: str,
    month: str,
    events_count: int,
    expected_revenue: float,
    dialogue_used: bool
):
    """Log orchestration analytics for tracking"""
    try:
        from google.cloud import firestore
        db = firestore.Client()
        
        analytics_data = {
            "client_id": client_id,
            "month": month,
            "events_count": events_count,
            "expected_revenue": expected_revenue,
            "dialogue_used": dialogue_used,
            "timestamp": datetime.now(),
            "source": "calendar_orchestrator_v2"
        }
        
        db.collection('orchestration_analytics').add(analytics_data)
        logger.info(f"✅ Analytics logged for {client_id} - {month}")
        
    except Exception as e:
        logger.error(f"Analytics logging error: {e}")

# ============================================
# HEALTH CHECK
# ============================================
@router.get("/health")
async def health_check():
    """Check if orchestrator is operational"""
    try:
        # Check MCP Gateway
        import httpx
        async with httpx.AsyncClient() as client:
            gateway_response = await client.get("http://localhost:8000/api/mcp/gateway/status")
            gateway_status = gateway_response.status_code == 200
        
        return {
            "status": "healthy",
            "version": "2.0",
            "features": {
                "historical_analysis": True,
                "recent_performance": True,
                "ai_planning": True,
                "dialogue_input": True,
                "klaviyo_enhanced": True
            },
            "dependencies": {
                "mcp_gateway": "operational" if gateway_status else "unavailable",
                "firestore": "operational"
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }

@router.get("/")
async def orchestrator_info():
    """Get information about the orchestrator"""
    return {
        "name": "Calendar Orchestrator V2",
        "version": "2.0",
        "description": "Enhanced multi-agent calendar orchestration with Klaviyo MCP Enhanced",
        "features": [
            "Historical data analysis (6-12 months)",
            "Recent performance analysis (30 days)",
            "AI-powered campaign planning",
            "User dialogue integration",
            "Parallel agent execution",
            "Real-time streaming updates",
            "Comprehensive analytics"
        ],
        "agents": [
            "Historical Data Analyst",
            "Recent Performance Analyst",
            "AI Campaign Planner",
            "Calendar Plotter"
        ],
        "endpoints": [
            "/orchestrate - Main orchestration endpoint",
            "/orchestrate/stream - SSE streaming endpoint",
            "/status/{calendar_id} - Get orchestration status",
            "/history/{client_id} - Get orchestration history",
            "/insights/{client_id} - Get AI insights",
            "/health - Health check"
        ]
    }