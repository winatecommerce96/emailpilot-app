"""
Dashboard API endpoints for aggregated metrics and real-time data (Firestore version)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
from app.deps.firestore import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_dashboard_data(db=Depends(get_db)) -> List[Dict[str, Any]]:
    """Return dashboard metrics as an array for frontend reducer"""
    
    # Mock dashboard data in expected array format
    dashboard_items = [
        {
            "id": "total_clients",
            "label": "Total Clients", 
            "value": 21,
            "type": "metric",
            "icon": "users",
            "change": "+2",
            "trend": "up"
        },
        {
            "id": "active_clients",
            "label": "Active Clients",
            "value": 11,
            "type": "metric", 
            "icon": "activity",
            "change": "+1",
            "trend": "up"
        },
        {
            "id": "revenue_mtd",
            "label": "Revenue MTD",
            "value": 125000,
            "type": "currency",
            "icon": "dollar-sign",
            "change": "+15%",
            "trend": "up"
        },
        {
            "id": "campaigns_sent",
            "label": "Campaigns Sent",
            "value": 45,
            "type": "metric",
            "icon": "mail",
            "change": "+8",
            "trend": "up"
        },
        {
            "id": "avg_open_rate",
            "label": "Avg Open Rate",
            "value": 28.5,
            "type": "percentage",
            "icon": "eye",
            "change": "+2.1%",
            "trend": "up"
        },
        {
            "id": "avg_click_rate", 
            "label": "Avg Click Rate",
            "value": 4.2,
            "type": "percentage",
            "icon": "mouse-pointer",
            "change": "+0.3%",
            "trend": "up"
        }
    ]
    
    # Try to get real client count from Firestore
    try:
        clients_ref = db.collection("clients")
        clients = list(clients_ref.stream())
        
        total_clients = len(clients)
        active_clients = 0
        
        for client_doc in clients:
            if client_doc.exists:
                client_data = client_doc.to_dict()
                if client_data.get("is_active", False):
                    active_clients += 1
        
        # Update the real values
        dashboard_items[0]["value"] = total_clients
        dashboard_items[1]["value"] = active_clients
        
        logger.info(f"Dashboard: Found {total_clients} total clients, {active_clients} active")
        
    except Exception as e:
        logger.warning(f"Could not fetch real client data from Firestore: {e}")
        # Use mock data if Firestore fails
        pass
    
    # Try to get goals data
    try:
        goals_ref = db.collection("goals")
        goals = list(goals_ref.stream())
        
        current_month_revenue = 0
        total_goals = len(goals)
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        for goal_doc in goals:
            if goal_doc.exists:
                goal_data = goal_doc.to_dict()
                if (goal_data.get("month") == current_month and 
                    goal_data.get("year") == current_year):
                    revenue_goal = goal_data.get("revenue_goal", 0)
                    if revenue_goal:
                        current_month_revenue += revenue_goal
        
        if current_month_revenue > 0:
            dashboard_items[2]["value"] = current_month_revenue
            
        logger.info(f"Dashboard: Found {total_goals} goals, current month revenue: {current_month_revenue}")
        
    except Exception as e:
        logger.warning(f"Could not fetch goals data from Firestore: {e}")
        pass
    
    return dashboard_items

@router.get("/summary")
async def get_dashboard_summary(db=Depends(get_db)) -> Dict[str, Any]:
    """Get dashboard summary with proper structure"""
    
    items = await get_dashboard_data(db)
    
    return {
        "items": items,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "total_items": len(items)
    }

@router.get("/overview")
async def get_dashboard_overview(db=Depends(get_db)) -> Dict[str, Any]:
    """Get comprehensive dashboard overview with all key metrics"""
    
    try:
        # Get clients data
        clients_ref = db.collection("clients")
        clients = list(clients_ref.stream())
        
        total_clients = len(clients)
        active_clients = sum(1 for c in clients if c.exists and c.to_dict().get("is_active", False))
        
        # Get goals data
        goals_ref = db.collection("goals")
        goals = list(goals_ref.stream())
        total_goals = len(goals)
        
        # Calculate current month statistics
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        month_goals = 0
        total_goal_amount = 0
        current_month_goal_amount = 0
        
        for goal_doc in goals:
            if goal_doc.exists:
                goal_data = goal_doc.to_dict()
                revenue_goal = goal_data.get("revenue_goal", 0)
                
                if revenue_goal:
                    total_goal_amount += revenue_goal
                    
                if (goal_data.get("year") == current_year and 
                    goal_data.get("month") == current_month):
                    month_goals += 1
                    if revenue_goal:
                        current_month_goal_amount += revenue_goal
        
        # Get reports data (if collection exists)
        total_reports = 0
        month_reports = 0
        last_report_date = None
        
        try:
            reports_ref = db.collection("reports")
            reports = list(reports_ref.stream())
            total_reports = len(reports)
            
            start_of_month = datetime(now.year, now.month, 1)
            
            for report_doc in reports:
                if report_doc.exists:
                    report_data = report_doc.to_dict()
                    created_at = report_data.get("created_at")
                    
                    if created_at:
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        
                        if created_at >= start_of_month:
                            month_reports += 1
                        
                        if not last_report_date or created_at > last_report_date:
                            last_report_date = created_at
                            
        except Exception as e:
            logger.warning(f"Could not fetch reports data: {e}")
        
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
                    "last_generated": last_report_date.isoformat() if last_report_date else None
                }
            },
            "month_progress": {
                "days_passed": now.day,
                "days_in_month": (datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31,
                "percentage": (now.day / ((datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31)) * 100
            },
            "timestamp": now.isoformat(),
            "data_source": "firestore"
        }
        
    except Exception as e:
        logger.error(f"Dashboard overview error: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard overview failed: {str(e)}")

@router.get("/clients-performance")
async def get_clients_performance_summary(db=Depends(get_db)) -> Dict[str, Any]:
    """Get performance summary for all active clients"""
    
    try:
        clients_ref = db.collection("clients")
        clients = list(clients_ref.stream())
        
        active_clients = []
        for client_doc in clients:
            if client_doc.exists:
                client_data = client_doc.to_dict()
                if client_data.get("is_active", False):
                    active_clients.append({
                        "id": client_doc.id,
                        "data": client_data
                    })
        
        client_summaries = []
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        for client in active_clients:
            client_id = client["id"]
            client_data = client["data"]
            
            # Get client's goals for current month
            current_month_goal = 0
            try:
                goals_ref = db.collection("goals")
                client_goals = goals_ref.where("client_id", "==", client_id)\
                                       .where("year", "==", current_year)\
                                       .where("month", "==", current_month)\
                                       .stream()
                
                for goal_doc in client_goals:
                    if goal_doc.exists:
                        goal_data = goal_doc.to_dict()
                        current_month_goal += goal_data.get("revenue_goal", 0)
                        
            except Exception as e:
                logger.warning(f"Could not fetch goals for client {client_id}: {e}")
            
            # Get client's reports count
            reports_count = 0
            try:
                reports_ref = db.collection("reports")
                client_reports = reports_ref.where("client_id", "==", client_id).stream()
                reports_count = len(list(client_reports))
            except Exception as e:
                logger.warning(f"Could not fetch reports for client {client_id}: {e}")
            
            client_summaries.append({
                "id": client_id,
                "name": client_data.get("name", "Unknown"),
                "metric_id": client_data.get("metric_id", ""),
                "current_month_goal": current_month_goal,
                "reports_generated": reports_count,
                "status": "active"
            })
        
        total_monthly_goal = sum(c["current_month_goal"] for c in client_summaries)
        average_goal = total_monthly_goal / len(client_summaries) if client_summaries else 0
        
        return {
            "clients": client_summaries,
            "summary": {
                "total_active": len(client_summaries),
                "total_monthly_goal": total_monthly_goal,
                "average_goal": average_goal
            },
            "timestamp": datetime.now().isoformat(),
            "data_source": "firestore"
        }
        
    except Exception as e:
        logger.error(f"Clients performance error: {e}")
        raise HTTPException(status_code=500, detail=f"Clients performance failed: {str(e)}")

@router.get("/quick-stats")
async def get_quick_stats(db=Depends(get_db)) -> Dict[str, Any]:
    """Get quick statistics for dashboard tiles"""
    
    try:
        # Get clients count
        clients_ref = db.collection("clients")
        clients = list(clients_ref.stream())
        active_clients_count = sum(1 for c in clients if c.exists and c.to_dict().get("is_active", False))
        
        # Get goals count
        goals_ref = db.collection("goals")
        goals = list(goals_ref.stream())
        total_goals = len(goals)
        
        # Get reports count
        total_reports = 0
        last_activity = None
        
        try:
            reports_ref = db.collection("reports")
            reports = list(reports_ref.stream())
            total_reports = len(reports)
            
            # Find most recent activity
            latest_report_date = None
            for report_doc in reports:
                if report_doc.exists:
                    report_data = report_doc.to_dict()
                    created_at = report_data.get("created_at")
                    if created_at:
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if not latest_report_date or created_at > latest_report_date:
                            latest_report_date = created_at
            
            if latest_report_date:
                last_activity = {
                    "type": "report",
                    "date": latest_report_date.isoformat()
                }
                
        except Exception as e:
            logger.warning(f"Could not fetch reports for quick stats: {e}")
        
        return {
            "total_clients": active_clients_count,
            "total_goals": total_goals,
            "total_reports": total_reports,
            "last_activity": last_activity,
            "timestamp": datetime.now().isoformat(),
            "data_source": "firestore"
        }
        
    except Exception as e:
        logger.warning(f"Quick stats error: {e}")
        # Return safe defaults on error
        return {
            "total_clients": 0,
            "total_goals": 0,
            "total_reports": 0,
            "last_activity": None,
            "timestamp": datetime.now().isoformat(),
            "data_source": "firestore_error"
        }