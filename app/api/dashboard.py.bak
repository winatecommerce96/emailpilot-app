"""
Dashboard API endpoints for aggregated metrics and real-time data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import os
import httpx
import asyncio
from app.core.database import get_db
from app.models import Client, Goal, Report

router = APIRouter()

# Klaviyo API configuration
KLAVIYO_API_KEY = os.getenv("KLAVIYO_API_KEY")
KLAVIYO_API_URL = "https://a.klaviyo.com/api"

@router.get("/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    Get comprehensive dashboard overview with all key metrics
    """
    try:
        # Get database statistics
        total_clients = db.query(Client).count()
        active_clients = db.query(Client).filter(Client.is_active == True).count()
        total_goals = db.query(Goal).count()
        total_reports = db.query(Report).count()
        
        # Get recent activity
        recent_reports = db.query(Report).order_by(Report.created_at.desc()).limit(5).all()
        recent_goals = db.query(Goal).order_by(Goal.created_at.desc()).limit(5).all()
        
        # Calculate current month statistics
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        month_goals = db.query(Goal).filter(
            Goal.year == now.year,
            Goal.month == now.month
        ).count()
        
        month_reports = db.query(Report).filter(
            Report.created_at >= start_of_month
        ).count()
        
        # Calculate aggregated goal amounts
        total_goal_amount = 0
        current_month_goal_amount = 0
        
        all_goals = db.query(Goal).all()
        for goal in all_goals:
            if goal.revenue_goal:
                total_goal_amount += goal.revenue_goal
                if goal.year == now.year and goal.month == now.month:
                    current_month_goal_amount += goal.revenue_goal
        
        return {
            "statistics": {
                "clients": {
                    "total": total_clients,
                    "active": active_clients,
                    "inactive": total_clients - active_clients
                },
                "goals": {
                    "total": total_goals,
                    "current_month": month_goals,
                    "total_revenue_goal": total_goal_amount,
                    "current_month_revenue_goal": current_month_goal_amount
                },
                "reports": {
                    "total": total_reports,
                    "current_month": month_reports,
                    "last_generated": recent_reports[0].created_at.isoformat() if recent_reports else None
                }
            },
            "recent_activity": {
                "reports": [
                    {
                        "id": r.id,
                        "client_id": r.client_id,
                        "type": r.report_type,
                        "created_at": r.created_at.isoformat()
                    } for r in recent_reports
                ],
                "goals": [
                    {
                        "id": g.id,
                        "client_id": g.client_id,
                        "year": g.year,
                        "month": g.month,
                        "revenue_goal": g.revenue_goal,
                        "created_at": g.created_at.isoformat()
                    } for g in recent_goals
                ]
            },
            "month_progress": {
                "days_passed": now.day,
                "days_in_month": (datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31,
                "percentage": (now.day / ((datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31)) * 100
            }
        }
    except Exception as e:
        print(f"Dashboard overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clients-performance")
async def get_clients_performance_summary(db: Session = Depends(get_db)):
    """
    Get performance summary for all active clients
    """
    try:
        active_clients = db.query(Client).filter(Client.is_active == True).all()
        
        client_summaries = []
        for client in active_clients:
            # Get client's goals
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            client_goal = db.query(Goal).filter(
                Goal.client_id == client.id,
                Goal.year == current_year,
                Goal.month == current_month
            ).first()
            
            # Get client's reports count
            reports_count = db.query(Report).filter(
                Report.client_id == client.id
            ).count()
            
            client_summaries.append({
                "id": client.id,
                "name": client.name,
                "metric_id": client.metric_id,
                "current_month_goal": client_goal.revenue_goal if client_goal else 0,
                "reports_generated": reports_count,
                "status": "active" if client.is_active else "inactive"
            })
        
        return {
            "clients": client_summaries,
            "summary": {
                "total_active": len(active_clients),
                "total_monthly_goal": sum(c["current_month_goal"] for c in client_summaries),
                "average_goal": sum(c["current_month_goal"] for c in client_summaries) / len(client_summaries) if client_summaries else 0
            }
        }
    except Exception as e:
        print(f"Clients performance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quick-stats")
async def get_quick_stats(db: Session = Depends(get_db)):
    """
    Get quick statistics for dashboard tiles
    """
    try:
        # Simple counts for quick display
        stats = {
            "total_clients": db.query(Client).filter(Client.is_active == True).count(),
            "total_goals": db.query(Goal).count(),
            "total_reports": db.query(Report).count(),
            "last_activity": None
        }
        
        # Get most recent activity
        last_report = db.query(Report).order_by(Report.created_at.desc()).first()
        last_goal = db.query(Goal).order_by(Goal.created_at.desc()).first()
        
        if last_report and last_goal:
            if last_report.created_at > last_goal.created_at:
                stats["last_activity"] = {
                    "type": "report",
                    "date": last_report.created_at.isoformat()
                }
            else:
                stats["last_activity"] = {
                    "type": "goal",
                    "date": last_goal.created_at.isoformat()
                }
        elif last_report:
            stats["last_activity"] = {
                "type": "report",
                "date": last_report.created_at.isoformat()
            }
        elif last_goal:
            stats["last_activity"] = {
                "type": "goal",
                "date": last_goal.created_at.isoformat()
            }
        
        return stats
    except Exception as e:
        print(f"Quick stats error: {e}")
        return {
            "total_clients": 0,
            "total_goals": 0,
            "total_reports": 0,
            "last_activity": None
        }

@router.get("/klaviyo-metrics/{client_id}")
async def get_klaviyo_metrics(client_id: int, db: Session = Depends(get_db)):
    """
    Fetch real-time metrics from Klaviyo for a specific client
    """
    if not KLAVIYO_API_KEY:
        # Return mock data if no API key
        return {
            "client_id": client_id,
            "metrics": {
                "campaigns_sent": 12,
                "total_recipients": 45678,
                "average_open_rate": 28.5,
                "average_click_rate": 4.2,
                "total_revenue": 125000
            },
            "status": "mock_data"
        }
    
    try:
        # Get client's metric_id
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        headers = {
            "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
            "Accept": "application/json",
            "revision": "2024-10-15"
        }
        
        async with httpx.AsyncClient() as http_client:
            # Fetch account metrics
            metrics_url = f"{KLAVIYO_API_URL}/metrics"
            response = await http_client.get(metrics_url, headers=headers)
            
            if response.status_code == 200:
                metrics_data = response.json()
                # Process and return relevant metrics
                return {
                    "client_id": client_id,
                    "client_name": client.name,
                    "metrics": metrics_data,
                    "status": "live_data"
                }
            else:
                return {
                    "client_id": client_id,
                    "metrics": {},
                    "status": "api_error",
                    "error": f"Klaviyo API returned {response.status_code}"
                }
                
    except Exception as e:
        print(f"Klaviyo metrics error: {e}")
        return {
            "client_id": client_id,
            "metrics": {},
            "status": "error",
            "error": str(e)
        }