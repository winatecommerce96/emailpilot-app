"""
Goals API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime

from app.core.database import get_db
from app.models import Goal, Client
from app.services.goal_manager import GoalManagerService
from app.schemas.goal import GoalResponse, GoalCreate, GoalUpdate

router = APIRouter()

@router.get("/clients", response_model=List[dict])
async def get_clients_with_goals(db: Session = Depends(get_db)):
    """Get all clients with their goal summary"""
    clients = db.query(Client).filter(Client.is_active == True).all()
    
    result = []
    for client in clients:
        # Get latest goals for this client
        latest_goals = db.query(Goal).filter(
            Goal.client_id == client.id,
            Goal.year == datetime.now().year
        ).all()
        
        total_yearly = sum(goal.revenue_goal for goal in latest_goals)
        
        result.append({
            "id": client.id,
            "name": client.name,
            "total_yearly_goal": total_yearly,
            "monthly_goals_count": len(latest_goals),
            "is_active": client.is_active
        })
    
    return result

@router.get("/{client_id}")
async def get_client_goals(
    client_id: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get goals for specific client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    query = db.query(Goal).filter(Goal.client_id == client_id)
    
    if year:
        query = query.filter(Goal.year == year)
    else:
        query = query.filter(Goal.year == datetime.now().year)
    
    goals = query.order_by(Goal.month).all()
    
    return {
        "client": {
            "id": client.id,
            "name": client.name
        },
        "goals": goals,
        "total_yearly": sum(goal.revenue_goal for goal in goals)
    }

@router.post("/{client_id}")
async def create_goal(
    client_id: int,
    goal_data: GoalCreate,
    db: Session = Depends(get_db)
):
    """Create or update a goal for specific client/month/year"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if goal already exists
    existing_goal = db.query(Goal).filter(
        Goal.client_id == client_id,
        Goal.year == goal_data.year,
        Goal.month == goal_data.month
    ).first()
    
    if existing_goal:
        # Update existing goal
        existing_goal.revenue_goal = goal_data.revenue_goal
        existing_goal.calculation_method = goal_data.calculation_method
        existing_goal.notes = goal_data.notes
        existing_goal.human_override = goal_data.human_override
        existing_goal.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_goal)
        return existing_goal
    else:
        # Create new goal
        new_goal = Goal(
            client_id=client_id,
            year=goal_data.year,
            month=goal_data.month,
            revenue_goal=goal_data.revenue_goal,
            calculation_method=goal_data.calculation_method,
            notes=goal_data.notes,
            human_override=goal_data.human_override
        )
        
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        return new_goal

@router.put("/{client_id}/{goal_id}")
async def update_goal(
    client_id: int,
    goal_id: int,
    goal_data: GoalUpdate,
    db: Session = Depends(get_db)
):
    """Update specific goal"""
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.client_id == client_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Update fields
    if goal_data.revenue_goal is not None:
        goal.revenue_goal = goal_data.revenue_goal
    if goal_data.notes is not None:
        goal.notes = goal_data.notes
    if goal_data.human_override is not None:
        goal.human_override = goal_data.human_override
    
    goal.calculation_method = "manual"  # Mark as manual when updated
    goal.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(goal)
    return goal

@router.post("/generate")
async def generate_ai_goals(
    background_tasks: BackgroundTasks,
    client_id: Optional[int] = None,
    year: int = datetime.now().year + 1,
    db: Session = Depends(get_db)
):
    """Generate AI-powered goals for client(s)"""
    
    goal_service = GoalManagerService(db)
    
    if client_id:
        # Generate for specific client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        background_tasks.add_task(
            goal_service.generate_yearly_goals,
            client_id,
            year
        )
        
        return {
            "message": f"AI goal generation started for {client.name}",
            "client_id": client_id,
            "year": year
        }
    else:
        # Generate for all active clients
        active_clients = db.query(Client).filter(Client.is_active == True).all()
        
        for client in active_clients:
            background_tasks.add_task(
                goal_service.generate_yearly_goals,
                client.id,
                year
            )
        
        return {
            "message": f"AI goal generation started for {len(active_clients)} clients",
            "clients": len(active_clients),
            "year": year
        }

@router.get("/progress/status")
async def get_goal_generation_progress():
    """Get progress of AI goal generation"""
    # This would connect to your existing progress tracking
    return {
        "status": "completed",
        "message": "All goal generation processes completed"
    }