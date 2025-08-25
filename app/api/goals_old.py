# app/api/goals.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from app.deps import get_db
from datetime import datetime
from google.cloud import firestore as fs

router = APIRouter(prefix="/api/goals", tags=["goals"])



@router.get("/hello")
def hello_goals():
    return {"message": "Hello from goals"}


@router.get("/clients")
def goals_by_client() -> Dict[str, Any]:
    return {"message": "Hello from goals"}

@router.get("/company/aggregated")
def company_aggregated() -> Dict[str, Any]:
    """
    Company-level aggregates used by dashboard.
    """
    total_open = total_in_progress = total_done = 0
    total_revenue_goal = 0.0
    
    db = get_db()
    for snap in db.collection("goals").stream():
        data = snap.to_dict() or {}
        
        # Determine status based on goal data
        if data.get("human_override"):
            total_in_progress += 1
        elif data.get("confidence") == "high":
            total_done += 1
        else:
            total_open += 1
            
        # Sum revenue goals
        revenue_goal = data.get("revenue_goal", 0)
        if isinstance(revenue_goal, (int, float)):
            total_revenue_goal += revenue_goal

    return {
        "totals": {
            "open": total_open,
            "in_progress": total_in_progress,
            "done": total_done,
            "total": total_open + total_in_progress + total_done,
            "revenue_goal": total_revenue_goal
        }
    }

@router.get("/data-status")
def get_data_status() -> Dict[str, Any]:
    """
    Check goals data completeness and system status.
    """
    total_goals = 0
    goals_with_revenue = 0
    goals_with_ai = 0
    goals_with_override = 0
    clients_with_goals = set()
    
    db = get_db()
    for snap in db.collection("goals").stream():
        data = snap.to_dict() or {}
        total_goals += 1
        
        if data.get("revenue_goal"):
            goals_with_revenue += 1
        if data.get("calculation_method") == "ai_suggested":
            goals_with_ai += 1
        if data.get("human_override"):
            goals_with_override += 1
            
        client_id = data.get("client_id")
        if client_id:
            clients_with_goals.add(client_id)
    
    # Get total clients
    total_clients = 0
    for _ in db.collection("clients").stream():
        total_clients += 1
    
    return {
        "status": "healthy" if total_goals > 0 else "no_data",
        "stats": {
            "total_goals": total_goals,
            "goals_with_revenue": goals_with_revenue,
            "goals_with_ai": goals_with_ai,
            "goals_with_override": goals_with_override,
            "clients_with_goals": len(clients_with_goals),
            "total_clients": total_clients,
            "coverage_percentage": (len(clients_with_goals) / total_clients * 100) if total_clients > 0 else 0
        },
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/accuracy/comparison")
def get_accuracy_comparison() -> Dict[str, Any]:
    """
    Compare AI-generated vs human-overridden goals accuracy.
    """
    ai_goals = []
    human_goals = []
    
    db = get_db()
    for snap in db.collection("goals").stream():
        data = snap.to_dict() or {}
        revenue_goal = data.get("revenue_goal", 0)
        
        if data.get("human_override"):
            human_goals.append(revenue_goal)
        elif data.get("calculation_method") == "ai_suggested":
            ai_goals.append(revenue_goal)
    
    def calculate_stats(goals: List[float]) -> Dict[str, Any]:
        if not goals:
            return {"count": 0, "average": 0, "min": 0, "max": 0}
        return {
            "count": len(goals),
            "average": sum(goals) / len(goals),
            "min": min(goals),
            "max": max(goals),
            "total": sum(goals)
        }
    
    return {
        "ai_suggested": calculate_stats(ai_goals),
        "human_override": calculate_stats(human_goals),
        "comparison": {
            "total_goals": len(ai_goals) + len(human_goals),
            "ai_percentage": (len(ai_goals) / (len(ai_goals) + len(human_goals)) * 100) if (ai_goals or human_goals) else 0,
            "human_percentage": (len(human_goals) / (len(ai_goals) + len(human_goals)) * 100) if (ai_goals or human_goals) else 0
        }
    }

@router.get("/{client_id}")
def get_client_goals(client_id: str) -> List[Dict[str, Any]]:
    """
    Get all goals for a specific client.
    """
    goals = []
    
    # Query goals for this client
    db = get_db()
    query = db.collection("goals").where("client_id", "==", client_id)
    
    for snap in query.stream():
        data = snap.to_dict() or {}
        data["id"] = snap.id
        
        # Add computed status field
        if data.get("human_override"):
            data["status"] = "in_progress"
        elif data.get("confidence") == "high":
            data["status"] = "done"
        else:
            data["status"] = "open"
            
        goals.append(data)
    
    # Sort by year and month descending
    goals.sort(key=lambda x: (x.get("year", 0), x.get("month", 0)), reverse=True)
    
    return goals

@router.get("/{goal_id}/versions")
def get_goal_versions(goal_id: str) -> Dict[str, Any]:
    """
    Get version history for a specific goal.
    Currently returns the current version as we don't track history yet.
    """
    try:
        db = get_db()
        goal_ref = db.collection("goals").document(goal_id)
        goal_doc = goal_ref.get()
        
        if not goal_doc.exists:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        current_data = goal_doc.to_dict()
        current_data["id"] = goal_id
        
        # For now, return just the current version
        # In future, we could store versions in a subcollection
        return {
            "goal_id": goal_id,
            "current_version": current_data,
            "versions": [
                {
                    "version": 1,
                    "timestamp": current_data.get("updated_at", current_data.get("created_at")),
                    "data": current_data,
                    "changes": "Initial version"
                }
            ],
            "total_versions": 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{client_id}")
def create_goal(client_id: str, goal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new goal for a client.
    """
    try:
        db = get_db()
        
        # Prepare goal document
        new_goal = {
            "client_id": client_id,
            "revenue_goal": goal_data.get("revenue_goal", 0),
            "year": goal_data.get("year", datetime.now().year),
            "month": goal_data.get("month", datetime.now().month),
            "calculation_method": goal_data.get("calculation_method", "manual"),
            "confidence": goal_data.get("confidence", "medium"),
            "human_override": goal_data.get("human_override", False),
            "notes": goal_data.get("notes", ""),
            "created_at": fs.SERVER_TIMESTAMP,
            "updated_at": fs.SERVER_TIMESTAMP
        }
        
        # Add to Firestore
        doc_ref = db.collection("goals").add(new_goal)
        goal_id = doc_ref[1].id
        
        # Return created goal with ID
        new_goal["id"] = goal_id
        new_goal["created_at"] = datetime.utcnow().isoformat()
        new_goal["updated_at"] = datetime.utcnow().isoformat()
        
        return {
            "success": True,
            "goal": new_goal,
            "message": "Goal created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{goal_id}")
def update_goal(goal_id: str, goal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing goal.
    """
    try:
        db = get_db()
        goal_ref = db.collection("goals").document(goal_id)
        
        # Check if goal exists
        if not goal_ref.get().exists:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Prepare update data
        update_data = {
            "updated_at": fs.SERVER_TIMESTAMP
        }
        
        # Only update provided fields
        allowed_fields = [
            "revenue_goal", "year", "month", "calculation_method",
            "confidence", "human_override", "notes"
        ]
        
        for field in allowed_fields:
            if field in goal_data:
                update_data[field] = goal_data[field]
        
        # Update in Firestore
        goal_ref.update(update_data)
        
        # Get updated document
        updated_doc = goal_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data["id"] = goal_id
        
        return {
            "success": True,
            "goal": updated_data,
            "message": "Goal updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
