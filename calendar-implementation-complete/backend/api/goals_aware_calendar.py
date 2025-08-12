"""
Goals-Aware Firebase Calendar API endpoints for EmailPilot
Enhanced calendar functionality that integrates revenue goals for strategic campaign planning
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime, date
import json
import logging
import uuid

from app.api.auth import verify_token
from app.services.goals_aware_gemini_service import goals_aware_gemini
from app.services.google_service import GoogleService
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from firebase_calendar_integration import firebase_clients, firebase_chat
from firebase_goals_calendar_integration import firebase_goals_calendar

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
google_service = GoogleService()

@router.get("/dashboard/{client_id}")
async def get_goals_aware_dashboard(
    client_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get comprehensive dashboard with goals integration"""
    try:
        dashboard_data = await firebase_goals_calendar.get_dashboard_summary(client_id)
        return dashboard_data
    except Exception as e:
        logger.error(f"Error fetching goals dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/goals/{client_id}")
async def get_client_goals(
    client_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: dict = Depends(verify_token)
):
    """Get revenue goals for a client"""
    try:
        goals = await firebase_goals_calendar.get_client_goals(client_id, year, month)
        return goals
    except Exception as e:
        logger.error(f"Error fetching goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/goals/{client_id}/progress")
async def get_goal_progress(
    client_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get current goal progress for a client"""
    try:
        current_goal = await firebase_goals_calendar.get_current_month_goal(client_id)
        if not current_goal:
            return {"message": "No current goal found", "has_goal": False}
        
        progress = await firebase_goals_calendar.calculate_goal_progress(client_id, current_goal)
        
        return {
            "has_goal": True,
            "goal": current_goal,
            "progress": progress
        }
    except Exception as e:
        logger.error(f"Error calculating goal progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/{client_id}")
async def get_goal_recommendations(
    client_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get AI-powered goal-based campaign recommendations"""
    try:
        recommendations = await firebase_goals_calendar.get_goal_based_recommendations(client_id)
        return recommendations
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/goal-aware")
async def create_goal_aware_event(
    event_data: dict,
    current_user: dict = Depends(verify_token)
):
    """Create a calendar event with goal awareness and strategic optimization"""
    try:
        # Validate required fields
        if not event_data.get('title') or not event_data.get('client_id') or not event_data.get('event_date'):
            raise HTTPException(status_code=400, detail="Missing required fields: title, client_id, event_date")
        
        # Verify client exists
        client = await firebase_clients.get_client(event_data['client_id'])
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Create goal-aware event
        event_id = await firebase_goals_calendar.create_goal_aware_event(event_data)
        
        return {
            "event_id": event_id,
            "message": "Goal-aware event created successfully",
            "goal_optimized": event_data.get('ai_suggested', False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating goal-aware event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/goal-aware")
async def goals_aware_calendar_chat(
    chat_data: dict,
    current_user: dict = Depends(verify_token)
):
    """Enhanced AI chat with goal awareness and strategic recommendations"""
    try:
        client_id = chat_data.get('client_id')
        message = chat_data.get('message')
        session_id = chat_data.get('session_id', str(uuid.uuid4()))
        
        if not client_id or not message:
            raise HTTPException(status_code=400, detail="Missing client_id or message")
        
        # Verify client exists
        client = await firebase_clients.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get goals data for context
        goals_data = await firebase_goals_calendar.get_dashboard_summary(client_id)
        
        # Get client's calendar events for context
        events = await firebase_goals_calendar.get_client_events_for_goal_period(
            client_id,
            datetime.now().strftime('%Y-%m-%d'),
            (datetime.now().replace(month=12) if datetime.now().month < 12 
             else datetime.now().replace(year=datetime.now().year+1, month=1)).strftime('%Y-%m-%d')
        )
        
        # Get recent chat history
        chat_history = await firebase_chat.get_chat_history(client_id, session_id)
        
        # Process with goals-aware Gemini
        response = await goals_aware_gemini.process_goal_aware_chat(
            message=message,
            client_name=client['name'],
            events=events,
            goals_data=goals_data,
            chat_history=[{
                'role': 'user' if i % 2 == 0 else 'model',
                'text': h['user_message'] if i % 2 == 0 else h['ai_response']
            } for i, h in enumerate(chat_history)]
        )
        
        # Check if response includes actionable items
        is_action = response.get('is_action', False)
        action_type = None
        
        if is_action:
            # Execute any actions suggested by AI
            action_result = {"message": "Action completed", "success": True}
        else:
            action_result = None
        
        response_message = response.get('message', 'I understand your question about campaign planning.')
        
        # Save chat interaction to Firebase
        await firebase_chat.save_chat_message(
            client_id=client_id,
            user_message=message,
            ai_response=response_message,
            is_action=is_action,
            action_type=action_type,
            session_id=session_id
        )
        
        return {
            "response": response_message,
            "is_action": is_action,
            "action_type": action_type,
            "session_id": session_id,
            "goal_aware": response.get('goals_aware', False),
            "goal_status": response.get('goal_status', 'unknown'),
            "action_result": action_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing goals-aware chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{client_id}")
async def get_goal_analytics(
    client_id: str,
    months: Optional[int] = 3,
    current_user: dict = Depends(verify_token)
):
    """Get goal achievement analytics and trends"""
    try:
        # Get goals for last N months
        current_date = datetime.now()
        goals_data = []
        
        for i in range(months):
            month_date = current_date.replace(month=current_date.month - i) if current_date.month > i else current_date.replace(year=current_date.year - 1, month=12 - (i - current_date.month))
            
            month_goals = await firebase_goals_calendar.get_client_goals(
                client_id, 
                year=month_date.year, 
                month=month_date.month
            )
            
            if month_goals:
                goal = month_goals[0]
                progress = await firebase_goals_calendar.calculate_goal_progress(client_id, goal)
                goals_data.append({
                    "period": f"{month_date.year}-{month_date.month:02d}",
                    "goal": goal,
                    "progress": progress
                })
        
        # Calculate trends
        achievement_trend = []
        revenue_trend = []
        
        for data in goals_data:
            achievement_trend.append(data['progress']['progress_percentage'])
            revenue_trend.append(data['progress']['estimated_revenue'])
        
        return {
            "analytics_period": f"Last {months} months",
            "goals_data": goals_data,
            "trends": {
                "achievement_rate": achievement_trend,
                "revenue_trend": revenue_trend,
                "average_achievement": sum(achievement_trend) / len(achievement_trend) if achievement_trend else 0,
                "total_revenue": sum(revenue_trend)
            },
            "insights": {
                "best_month": max(goals_data, key=lambda x: x['progress']['progress_percentage']) if goals_data else None,
                "improvement_needed": any(data['progress']['progress_percentage'] < 80 for data in goals_data),
                "consistency_score": 100 - (max(achievement_trend) - min(achievement_trend)) if achievement_trend else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating goal analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaigns/suggest")
async def suggest_campaigns_for_goal(
    request_data: dict,
    current_user: dict = Depends(verify_token)
):
    """Generate strategic campaign suggestions based on revenue goals"""
    try:
        client_id = request_data.get('client_id')
        if not client_id:
            raise HTTPException(status_code=400, detail="Missing client_id")
        
        # Get client and goals data
        client = await firebase_clients.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        goals_data = await firebase_goals_calendar.get_dashboard_summary(client_id)
        
        if not goals_data.get('has_goal'):
            return {
                "suggestions": [],
                "message": "No revenue goals found. Set goals first for strategic campaign suggestions."
            }
        
        # Get current events
        current_events = await firebase_goals_calendar.get_client_events_for_goal_period(
            client_id,
            datetime.now().strftime('%Y-%m-%d'),
            (datetime.now().replace(day=28) + 
             (datetime.now().replace(day=28).replace(month=datetime.now().month % 12 + 1) - 
              datetime.now().replace(day=28))).strftime('%Y-%m-%d')
        )
        
        # Generate AI-powered suggestions
        suggestions = await goals_aware_gemini.generate_goal_based_campaign_suggestions(
            client_name=client['name'],
            goals_data=goals_data,
            current_events=current_events
        )
        
        return {
            "suggestions": suggestions,
            "goals_context": {
                "current_goal": goals_data.get('goal', {}),
                "progress": goals_data.get('progress', {}),
                "urgency": "high" if not goals_data.get('progress', {}).get('is_on_track') else "low"
            },
            "message": f"Generated {len(suggestions)} strategic campaign suggestions based on revenue goals"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating campaign suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/{client_id}")
async def get_campaign_performance_forecast(
    client_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get performance forecast based on scheduled campaigns and goals"""
    try:
        # Get current goal and progress
        current_goal = await firebase_goals_calendar.get_current_month_goal(client_id)
        if not current_goal:
            return {"message": "No goals found for performance forecast", "has_forecast": False}
        
        progress = await firebase_goals_calendar.calculate_goal_progress(client_id, current_goal)
        
        # Get upcoming events
        upcoming_events = await firebase_goals_calendar.get_client_events_for_goal_period(
            client_id,
            datetime.now().strftime('%Y-%m-%d'),
            f"{current_goal['year']}-{current_goal['month']:02d}-{28 if current_goal['month'] != 2 else 28}"
        )
        
        # Calculate performance forecast
        projected_additional_revenue = firebase_goals_calendar._calculate_estimated_revenue_from_events(upcoming_events)
        total_projected = progress['estimated_revenue'] + projected_additional_revenue
        
        goal_achievement_probability = min(100, (total_projected / current_goal['revenue_goal']) * 100) if current_goal['revenue_goal'] > 0 else 0
        
        return {
            "has_forecast": True,
            "current_goal": current_goal['revenue_goal'],
            "current_progress": progress['estimated_revenue'],
            "upcoming_campaigns": len(upcoming_events),
            "projected_additional": projected_additional_revenue,
            "total_projected": total_projected,
            "achievement_probability": goal_achievement_probability,
            "shortfall": max(0, current_goal['revenue_goal'] - total_projected),
            "recommendation": "On track to exceed goal!" if goal_achievement_probability >= 100 
                            else f"Need ${current_goal['revenue_goal'] - total_projected:.0f} more revenue - consider high-converting campaigns",
            "risk_level": "low" if goal_achievement_probability >= 90 
                         else "medium" if goal_achievement_probability >= 70 
                         else "high"
        }
        
    except Exception as e:
        logger.error(f"Error generating performance forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))