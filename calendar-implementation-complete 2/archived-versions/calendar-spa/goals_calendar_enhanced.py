"""
Enhanced Goals-Calendar API for EmailPilot SPA Integration
Provides optimized endpoints for the Goals-Aware Calendar SPA component
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.client import Client
from app.models.goal import Goal
from app.services.goal_manager import GoalManager
from app.services.klaviyo_direct import KlaviyoService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/dashboard/{client_id}")
async def get_enhanced_dashboard(
    client_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get enhanced dashboard data for Goals-Aware Calendar SPA
    Optimized for SPA performance with minimal API calls
    """
    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Initialize services
        goal_manager = GoalManager(db)
        klaviyo_service = KlaviyoService(client.klaviyo_api_key)
        
        # Get current goal
        current_goal = goal_manager.get_current_goal(client_id)
        
        dashboard_data = {
            "client_id": client_id,
            "client_name": client.name,
            "has_goal": current_goal is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if current_goal:
            # Calculate progress
            progress = goal_manager.calculate_progress(current_goal.id)
            
            # Get AI recommendations
            recommendations = await generate_ai_recommendations(
                client, current_goal, progress, klaviyo_service
            )
            
            # Get recent performance data
            performance_data = await get_performance_summary(
                client, klaviyo_service, days=30
            )
            
            dashboard_data.update({
                "goal": {
                    "id": current_goal.id,
                    "revenue_goal": float(current_goal.revenue_goal),
                    "start_date": current_goal.start_date.isoformat(),
                    "end_date": current_goal.end_date.isoformat(),
                    "goal_type": current_goal.goal_type,
                    "status": current_goal.status
                },
                "progress": {
                    "current_revenue": float(progress.get("current_revenue", 0)),
                    "remaining_revenue": float(progress.get("remaining_revenue", 0)),
                    "progress_percentage": progress.get("progress_percentage", 0),
                    "days_remaining": progress.get("days_remaining", 0),
                    "is_on_track": progress.get("is_on_track", False),
                    "daily_target": float(progress.get("daily_target", 0)),
                    "projected_revenue": float(progress.get("projected_revenue", 0))
                },
                "recommendations": recommendations,
                "performance": performance_data
            })
        else:
            # No goal set - provide basic client data
            dashboard_data.update({
                "message": "No revenue goals set for this client",
                "suggestion": "Set revenue goals to enable AI-powered campaign recommendations"
            })
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting enhanced dashboard for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar-events/{client_id}")
async def get_calendar_events_with_goals(
    client_id: int,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get calendar events enhanced with goals context
    """
    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Parse date range
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        else:
            start_dt = datetime.now() - timedelta(days=30)
            
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = datetime.now() + timedelta(days=30)
        
        # Get goal context
        goal_manager = GoalManager(db)
        current_goal = goal_manager.get_current_goal(client_id)
        
        # Get calendar events (from existing calendar service)
        # This would integrate with your existing calendar service
        events = await get_client_calendar_events(client, start_dt, end_dt)
        
        # Enhance events with goals context
        if current_goal:
            progress = goal_manager.calculate_progress(current_goal.id)
            enhanced_events = []
            
            for event in events:
                enhanced_event = event.copy()
                
                # Add goals context to event
                enhanced_event["goals_context"] = {
                    "daily_target": progress.get("daily_target", 0),
                    "is_goal_period": (
                        current_goal.start_date <= event["date"] <= current_goal.end_date
                    ),
                    "priority": calculate_event_priority(event, progress),
                    "recommendations": get_event_recommendations(event, progress)
                }
                
                enhanced_events.append(enhanced_event)
            
            return {
                "events": enhanced_events,
                "goal_context": {
                    "has_goal": True,
                    "goal_id": current_goal.id,
                    "progress_percentage": progress.get("progress_percentage", 0),
                    "is_on_track": progress.get("is_on_track", False)
                },
                "date_range": {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat()
                }
            }
        else:
            return {
                "events": events,
                "goal_context": {"has_goal": False},
                "date_range": {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat()
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting calendar events for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/{client_id}")
async def get_ai_recommendations(
    client_id: int,
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get AI recommendations for goals-aware campaign planning
    """
    try:
        # Get client and goal
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        goal_manager = GoalManager(db)
        current_goal = goal_manager.get_current_goal(client_id)
        
        if not current_goal:
            return {
                "recommendations": [],
                "message": "Set revenue goals to get AI-powered recommendations"
            }
        
        # Get progress and generate recommendations
        progress = goal_manager.calculate_progress(current_goal.id)
        klaviyo_service = KlaviyoService(client.klaviyo_api_key)
        
        recommendations = await generate_ai_recommendations(
            client, current_goal, progress, klaviyo_service, category
        )
        
        return {
            "recommendations": recommendations,
            "goal_context": {
                "revenue_goal": float(current_goal.revenue_goal),
                "progress_percentage": progress.get("progress_percentage", 0),
                "is_on_track": progress.get("is_on_track", False),
                "days_remaining": progress.get("days_remaining", 0)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting AI recommendations for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance-summary/{client_id}")
async def get_performance_summary_endpoint(
    client_id: int,
    days: int = Query(30, description="Number of days to analyze"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get performance summary for calendar context
    """
    try:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        klaviyo_service = KlaviyoService(client.klaviyo_api_key)
        
        performance_data = await get_performance_summary(client, klaviyo_service, days)
        
        return performance_data
        
    except Exception as e:
        logger.error(f"Error getting performance summary for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions

async def generate_ai_recommendations(
    client: Client, 
    goal: Goal, 
    progress: Dict, 
    klaviyo_service: KlaviyoService,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generate AI-powered recommendations based on goals and performance"""
    recommendations = []
    
    try:
        # Analyze current performance
        is_on_track = progress.get("is_on_track", False)
        progress_pct = progress.get("progress_percentage", 0)
        days_remaining = progress.get("days_remaining", 0)
        
        # Get recent campaign performance
        recent_campaigns = await klaviyo_service.get_recent_campaigns(limit=10)
        
        if not is_on_track and progress_pct < 70:
            # High priority recommendations for underperforming goals
            recommendations.append({
                "id": "urgent_revenue_boost",
                "title": "Urgent: Launch High-Converting Campaign",
                "description": f"You're {100-progress_pct:.0f}% behind your revenue goal with {days_remaining} days remaining. Consider launching a flash sale or promoting your best-selling products.",
                "priority": "high",
                "category": "campaign",
                "action_type": "create_campaign",
                "estimated_impact": "High revenue boost",
                "suggested_date": (datetime.now() + timedelta(days=1)).isoformat()
            })
            
            recommendations.append({
                "id": "win_back_campaign",
                "title": "Win-Back Campaign for Lapsed Customers",
                "description": "Target customers who haven't purchased in 60-90 days with a special offer to re-engage them.",
                "priority": "high",
                "category": "retention",
                "action_type": "create_segment",
                "estimated_impact": "15-25% revenue increase",
                "suggested_date": (datetime.now() + timedelta(days=2)).isoformat()
            })
            
        elif progress_pct >= 70 and is_on_track:
            # Optimization recommendations for on-track goals
            recommendations.append({
                "id": "optimize_best_performers",
                "title": "Scale Your Best-Performing Campaigns",
                "description": "You're on track to meet your goal. Consider scaling successful campaigns to exceed your target.",
                "priority": "medium",
                "category": "optimization",
                "action_type": "campaign_optimization",
                "estimated_impact": "10-20% revenue increase",
                "suggested_date": (datetime.now() + timedelta(days=3)).isoformat()
            })
            
        # Always include general recommendations
        recommendations.extend([
            {
                "id": "email_frequency_optimization",
                "title": "Optimize Email Send Frequency",
                "description": "Analyze your audience engagement to find the optimal sending frequency for maximum revenue.",
                "priority": "low",
                "category": "optimization",
                "action_type": "frequency_analysis",
                "estimated_impact": "5-10% engagement improvement",
                "suggested_date": (datetime.now() + timedelta(days=7)).isoformat()
            },
            {
                "id": "seasonal_campaign_planning",
                "title": "Plan Seasonal Campaigns",
                "description": "Prepare campaigns for upcoming holidays and seasonal trends to maximize revenue opportunities.",
                "priority": "medium",
                "category": "planning",
                "action_type": "campaign_planning",
                "estimated_impact": "Seasonal revenue boost",
                "suggested_date": (datetime.now() + timedelta(days=14)).isoformat()
            }
        ])
        
        # Filter by category if specified
        if category:
            recommendations = [r for r in recommendations if r["category"] == category]
        
        return recommendations[:5]  # Limit to top 5 recommendations
        
    except Exception as e:
        logger.error(f"Error generating AI recommendations: {e}")
        return [{
            "id": "error_fallback",
            "title": "Unable to Generate Recommendations",
            "description": "There was an issue generating AI recommendations. Please try again later.",
            "priority": "low",
            "category": "system",
            "action_type": "retry"
        }]

async def get_performance_summary(
    client: Client, 
    klaviyo_service: KlaviyoService, 
    days: int = 30
) -> Dict[str, Any]:
    """Get performance summary for the specified time period"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get campaign performance
        campaigns = await klaviyo_service.get_campaigns_in_period(start_date, end_date)
        
        total_revenue = sum(c.get("revenue", 0) for c in campaigns)
        total_emails_sent = sum(c.get("emails_sent", 0) for c in campaigns)
        avg_open_rate = sum(c.get("open_rate", 0) for c in campaigns) / len(campaigns) if campaigns else 0
        avg_click_rate = sum(c.get("click_rate", 0) for c in campaigns) / len(campaigns) if campaigns else 0
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "metrics": {
                "total_revenue": total_revenue,
                "total_campaigns": len(campaigns),
                "total_emails_sent": total_emails_sent,
                "average_open_rate": round(avg_open_rate, 2),
                "average_click_rate": round(avg_click_rate, 2),
                "revenue_per_email": round(total_revenue / total_emails_sent, 4) if total_emails_sent > 0 else 0
            },
            "trends": {
                "revenue_trend": "stable",  # Would calculate actual trend
                "engagement_trend": "improving" if avg_open_rate > 20 else "needs_attention"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return {
            "period": {"start_date": None, "end_date": None, "days": days},
            "metrics": {},
            "error": "Unable to fetch performance data"
        }

async def get_client_calendar_events(
    client: Client, 
    start_date: datetime, 
    end_date: datetime
) -> List[Dict[str, Any]]:
    """Get calendar events for client (integrate with existing calendar service)"""
    # This would integrate with your existing calendar service
    # For now, return mock data structure
    return [
        {
            "id": "event_1",
            "title": "Email Campaign: Summer Sale",
            "date": datetime.now().isoformat(),
            "type": "campaign",
            "status": "scheduled",
            "description": "Launch summer sale email campaign"
        },
        {
            "id": "event_2", 
            "title": "Review Campaign Performance",
            "date": (datetime.now() + timedelta(days=1)).isoformat(),
            "type": "review",
            "status": "pending",
            "description": "Analyze last week's campaign results"
        }
    ]

def calculate_event_priority(event: Dict, progress: Dict) -> str:
    """Calculate event priority based on goals progress"""
    is_on_track = progress.get("is_on_track", False)
    days_remaining = progress.get("days_remaining", 0)
    
    if not is_on_track and days_remaining < 7:
        return "high"
    elif not is_on_track and days_remaining < 14:
        return "medium"
    else:
        return "low"

def get_event_recommendations(event: Dict, progress: Dict) -> List[str]:
    """Get recommendations for a specific calendar event"""
    recommendations = []
    
    if event["type"] == "campaign" and not progress.get("is_on_track", False):
        recommendations.append("Consider increasing send volume")
        recommendations.append("Add urgency to subject line")
    
    return recommendations