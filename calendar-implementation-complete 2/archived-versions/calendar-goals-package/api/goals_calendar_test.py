"""
Goals-aware Calendar API endpoints for EmailPilot - Test Version (No Auth)
Enhanced calendar with revenue goals integration and AI planning assistance
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging
import uuid

from app.services.gemini_service import GeminiService
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from firebase_goals_calendar_integration import firebase_goals_calendar

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
gemini_service = GeminiService()

@router.get("/goals/{client_id}")
async def get_client_goals(
    client_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Get revenue goals for a client - NO AUTH"""
    try:
        goals = await firebase_goals_calendar.get_client_goals(
            client_id=client_id,
            year=year,
            month=month
        )
        return goals
    except Exception as e:
        logger.error(f"Error fetching client goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/{client_id}")
async def get_goals_dashboard(client_id: str):
    """Get enhanced goals dashboard with progress tracking - NO AUTH"""
    try:
        # TODO: Verify client exists when client service is available
        # client = await firebase_clients.get_client(client_id)
        # if not client:
        #     raise HTTPException(status_code=404, detail="Client not found")
        
        dashboard = await firebase_goals_calendar.get_goals_dashboard(client_id)
        return dashboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching goals dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/{client_id}")
async def get_goal_recommendations(client_id: str):
    """Get AI recommendations for goal achievement - NO AUTH"""
    try:
        # TODO: Verify client exists when client service is available
        # client = await firebase_clients.get_client(client_id)
        # if not client:
        #     raise HTTPException(status_code=404, detail="Client not found")
        
        recommendations = await firebase_goals_calendar.get_goal_based_recommendations(client_id)
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching goal recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/goal-aware")
async def goal_aware_chat(chat_data: dict):
    """Goal-aware AI chat that considers revenue targets - NO AUTH"""
    try:
        client_id = chat_data.get('client_id')
        message = chat_data.get('message')
        chat_history = chat_data.get('chat_history', [])
        
        if not client_id or not message:
            raise HTTPException(status_code=400, detail="Missing client_id or message")
        
        # TODO: Verify client exists when client service is available
        # client = await firebase_clients.get_client(client_id)
        # if not client:
        #     raise HTTPException(status_code=404, detail="Client not found")
        
        # Get client's goals and current campaigns
        current_date = datetime.now()
        goals = await firebase_goals_calendar.get_client_goals(
            client_id=client_id,
            year=current_date.year,
            month=current_date.month
        )
        
        # Get enhanced dashboard data
        dashboard = await firebase_goals_calendar.get_goals_dashboard(client_id)
        
        # Process with goal-aware AI
        response = await firebase_goals_calendar.process_goal_aware_chat(
            client_id=client_id,
            message=message,
            chat_history=chat_history,
            client_name="Test Client",  # TODO: Use actual client name when client service is available
            goals=goals,
            dashboard=dashboard
        )
        
        return {
            "response": response.get('message', ''),
            "is_action": response.get('is_action', False),
            "action_type": response.get('action_type'),
            "action_data": response.get('action_data'),
            "goal_context": response.get('goal_context', {}),
            "recommendations": response.get('recommendations', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing goal-aware chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/goal-progress")
async def analyze_goal_progress(analysis_data: dict):
    """Analyze goal progress and provide strategic recommendations - NO AUTH"""
    try:
        client_id = analysis_data.get('client_id')
        
        if not client_id:
            raise HTTPException(status_code=400, detail="Missing client_id")
        
        # TODO: Verify client exists when client service is available
        # client = await firebase_clients.get_client(client_id)
        # if not client:
        #     raise HTTPException(status_code=404, detail="Client not found")
        
        # Get comprehensive goal analysis
        analysis = await firebase_goals_calendar.analyze_goal_progress(client_id)
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing goal progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize/campaign-mix")
async def optimize_campaign_mix(optimization_data: dict):
    """AI-powered campaign mix optimization for goal achievement - NO AUTH"""
    try:
        client_id = optimization_data.get('client_id')
        target_revenue = optimization_data.get('target_revenue')
        time_frame = optimization_data.get('time_frame', 'month')
        
        if not client_id:
            raise HTTPException(status_code=400, detail="Missing client_id")
        
        # TODO: Verify client exists when client service is available
        # client = await firebase_clients.get_client(client_id)
        # if not client:
        #     raise HTTPException(status_code=404, detail="Client not found")
        
        # Get AI optimization recommendations
        optimization = await firebase_goals_calendar.optimize_campaign_mix(
            client_id=client_id,
            target_revenue=target_revenue,
            time_frame=time_frame
        )
        
        return optimization
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing campaign mix: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/benchmark/{client_id}")
async def get_performance_benchmarks(client_id: str):
    """Get performance benchmarks for campaign planning - NO AUTH"""
    try:
        # TODO: Verify client exists when client service is available
        # client = await firebase_clients.get_client(client_id)
        # if not client:
        #     raise HTTPException(status_code=404, detail="Client not found")
        
        benchmarks = await firebase_goals_calendar.get_performance_benchmarks(client_id)
        return benchmarks
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching performance benchmarks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/forecast/revenue")
async def forecast_revenue(forecast_data: dict):
    """Generate revenue forecasts based on planned campaigns - NO AUTH"""
    try:
        client_id = forecast_data.get('client_id')
        campaign_plan = forecast_data.get('campaign_plan', [])
        time_horizon = forecast_data.get('time_horizon', 3)  # months
        
        if not client_id:
            raise HTTPException(status_code=400, detail="Missing client_id")
        
        # TODO: Verify client exists when client service is available
        # client = await firebase_clients.get_client(client_id)
        # if not client:
        #     raise HTTPException(status_code=404, detail="Client not found")
        
        # Generate AI-powered revenue forecast
        forecast = await firebase_goals_calendar.forecast_revenue(
            client_id=client_id,
            campaign_plan=campaign_plan,
            time_horizon=time_horizon
        )
        
        return forecast
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating revenue forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))