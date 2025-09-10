"""
API endpoint for comprehensive multi-part queries
Designed for calendar workflow and complex analytical requests
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.services.comprehensive_query_handler import ComprehensiveQueryHandler
from app.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/comprehensive", tags=["Comprehensive Query"])

class ComprehensiveQueryRequest(BaseModel):
    """Request model for comprehensive queries"""
    query: str
    client_id: str
    include_ai_analysis: bool = True
    context: Optional[Dict[str, Any]] = None

class ComprehensiveQueryResponse(BaseModel):
    """Response model for comprehensive queries"""
    success: bool
    query: str
    client_id: str
    total_requests: int
    successful_requests: int
    aggregated_data: Dict[str, Any]
    ai_ready_analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Initialize handler (key_resolver will be created per request)
handler = ComprehensiveQueryHandler()

@router.post("/query", response_model=ComprehensiveQueryResponse)
async def execute_comprehensive_query(
    request: ComprehensiveQueryRequest,
    db = Depends(get_db)
) -> ComprehensiveQueryResponse:
    """
    Execute a comprehensive multi-part query
    
    This endpoint handles complex queries like:
    - Get all campaign performance metrics for last 30 days
    - List all active segments with size, engagement rates, and value metrics
    - Calculate revenue metrics for last 30 days including total revenue, revenue per campaign, and revenue by segment
    - Analyze optimal send times by day of week and hour based on engagement metrics
    - And many more complex combinations
    
    The system will:
    1. Parse the query into individual requests
    2. Execute them in parallel where possible
    3. Aggregate the results
    4. Prepare for AI analysis
    """
    try:
        logger.info(f"📊 Comprehensive query for client: {request.client_id}")
        
        # Get client context including metric IDs
        context = request.context or {}
        
        # Try to get revenue metric ID for the client
        try:
            # First try to get from Firestore
            client_doc = db.collection('clients').document(request.client_id).get()
            if client_doc.exists:
                client_data = client_doc.to_dict()
                context['revenue_metric_id'] = client_data.get('placed_order_metric_id', 'TPWsCU')
                context['client_name'] = client_data.get('name', request.client_id)
            else:
                # Default metric ID
                context['revenue_metric_id'] = 'TPWsCU'
        except Exception as e:
            logger.warning(f"Could not get client context: {e}")
            context['revenue_metric_id'] = 'TPWsCU'
        
        # Note: Enhanced MCP will handle API key resolution automatically
        logger.info(f"Using Enhanced MCP for client {request.client_id}")
        
        # Process the comprehensive query
        result = await handler.process_comprehensive_query(
            query=request.query,
            client_id=request.client_id,
            context=context
        )
        
        # Return the response
        return ComprehensiveQueryResponse(
            success=result['success'],
            query=request.query,
            client_id=request.client_id,
            total_requests=result['total_requests'],
            successful_requests=result['successful_requests'],
            aggregated_data=result['aggregated_data'],
            ai_ready_analysis=result['ai_ready_analysis'] if request.include_ai_analysis else None
        )
        
    except Exception as e:
        logger.error(f"Comprehensive query failed: {e}", exc_info=True)
        return ComprehensiveQueryResponse(
            success=False,
            query=request.query,
            client_id=request.client_id,
            total_requests=0,
            successful_requests=0,
            aggregated_data={},
            error=str(e)
        )

@router.post("/calendar-workflow")
async def execute_calendar_workflow_query(
    request: ComprehensiveQueryRequest,
    db = Depends(get_db)
) -> Dict[str, Any]:
    """
    Special endpoint optimized for calendar workflow queries
    
    This endpoint is specifically designed for the calendar workflow system
    and handles all the complex data gathering needed for calendar planning.
    """
    try:
        logger.info(f"📅 Calendar workflow query for client: {request.client_id}")
        
        # Add calendar-specific context
        context = request.context or {}
        context['workflow_type'] = 'calendar'
        context['include_historical'] = True
        context['include_projections'] = True
        
        # Get client context
        try:
            client_doc = db.collection('clients').document(request.client_id).get()
            if client_doc.exists:
                client_data = client_doc.to_dict()
                context['revenue_metric_id'] = client_data.get('placed_order_metric_id', 'TPWsCU')
                context['client_name'] = client_data.get('name', request.client_id)
                context['affinity_segments'] = client_data.get('affinity_segments', [])
        except Exception as e:
            logger.warning(f"Could not get client context: {e}")
        
        # Process the query
        result = await handler.process_comprehensive_query(
            query=request.query,
            client_id=request.client_id,
            context=context
        )
        
        # Add calendar-specific formatting
        calendar_data = {
            'success': result['success'],
            'client_id': request.client_id,
            'client_name': context.get('client_name', request.client_id),
            'data_timestamp': result['timestamp'],
            'metrics_summary': result['ai_ready_analysis']['summary'],
            'recommendations': result['ai_ready_analysis']['recommendations'],
            'calendar_insights': {
                'optimal_send_times': result['aggregated_data']['send_times'].get('optimal_times', []),
                'segment_opportunities': result['aggregated_data']['segments'],
                'revenue_trends': result['aggregated_data']['revenue'],
                'campaign_performance': result['aggregated_data']['campaigns'],
                'content_analysis': result['aggregated_data']['content']
            },
            'ready_for_ai_planning': True,
            'data_quality': result['ai_ready_analysis']['data_quality']
        }
        
        return calendar_data
        
    except Exception as e:
        logger.error(f"Calendar workflow query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_comprehensive_endpoint():
    """Test endpoint to verify the comprehensive query system is loaded"""
    return {
        "status": "ready",
        "endpoints": [
            "/api/comprehensive/query",
            "/api/comprehensive/calendar-workflow"
        ],
        "capabilities": [
            "Multi-line query parsing",
            "Parallel execution",
            "Result aggregation",
            "AI-ready analysis",
            "Calendar workflow optimization"
        ]
    }