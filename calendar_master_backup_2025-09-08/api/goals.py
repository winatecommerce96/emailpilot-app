# app/api/goals.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.deps import get_db
from app.deps import get_secret_manager_service
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver
from app.services.goals_mcp_service import GoalsMCPService
from app.services.goal_predictor import GoalPredictor
from app.services.goals_backfill_service import GoalsBackfillService
from datetime import datetime
from google.cloud import firestore as fs
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["goals"])

@router.get("/clients")
def goals_by_client() -> Dict[str, Any]:
    """
    Return per-client goal counts grouped by status with client names.
    Since goals don't have status field, we'll group by achievement status.
    """
    counts: Dict[str, Dict[str, int]] = {}
    total_goals = 0
    
    db = get_db()
    
    # First pass: collect goal statistics by client ID
    for snap in db.collection("goals").stream():
        data = snap.to_dict() or {}
        cid = data.get("client_id") or data.get("clientId")
        if not cid:
            continue
            
        total_goals += 1
        
        # Determine status based on goal data
        # If human_override is true, consider it "in_progress"
        # If confidence is "high", consider it "done" 
        # Otherwise "open"
        if data.get("human_override"):
            status = "in_progress"
        elif data.get("confidence") == "high":
            status = "done"
        else:
            status = "open"
            
        bucket = counts.setdefault(cid, {"open": 0, "in_progress": 0, "done": 0, "goals_count": 0})
        bucket[status] += 1
        bucket["goals_count"] += 1

    # Second pass: fetch client names from clients collection
    client_names: Dict[str, str] = {}
    try:
        clients_ref = db.collection("clients")
        for client_snap in clients_ref.stream():
            client_data = client_snap.to_dict() or {}
            client_id = client_snap.id
            client_name = client_data.get("name", f"Client {client_id[:8]}")
            client_names[client_id] = client_name
    except Exception as e:
        # Log the error but continue with fallback names
        print(f"Warning: Failed to fetch client names: {e}")

    # Build final client list with names
    clients: List[Dict[str, Any]] = []
    for cid, stats in counts.items():
        client_name = client_names.get(cid, f"Client {cid[:8]}")
        clients.append({
            "id": cid,
            "clientId": cid, 
            "name": client_name,
            **stats
        })
    
    return {
        "clients": clients, 
        "count": len(clients),
        "total_goals": total_goals
    }

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

@router.get("/historical/{client_id}")
async def get_historical_performance(
    client_id: str,
    metric_type: str = "revenue",
    timeframe: str = "last_12_months",
    db: fs.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Get historical performance metrics from Klaviyo
    
    Args:
        client_id: Client identifier
        metric_type: Type of metric (revenue, open_rate, click_rate, bounce_rate, etc.)
        timeframe: Time period (last_12_months, last_year, last_30_days, etc.)
    """
    try:
        # Initialize MCP service
        mcp_service = GoalsMCPService(key_resolver, db)
        
        # Fetch historical metrics
        metrics = [metric_type] if metric_type != "all" else [
            "revenue", "open_rate", "click_rate", "bounce_rate", "unsubscribe_rate"
        ]
        
        historical_data = await mcp_service.fetch_historical_metrics(
            client_id, metrics, timeframe
        )
        
        return {
            "success": True,
            "client_id": client_id,
            "timeframe": timeframe,
            "metrics": historical_data,
            "fetched_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching historical performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/{client_id}")
async def predict_goals_from_history(
    client_id: str,
    year: int,
    metrics: List[str] = ["revenue"],
    model: str = "yoy_growth",
    month: Optional[int] = None,
    db: fs.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Generate goal predictions based on historical data
    
    Args:
        client_id: Client identifier
        year: Year to predict for
        metrics: List of metrics to predict
        model: Prediction model (yoy_growth, seasonal, moving_average, trend_analysis)
        month: Specific month or None for all months
    """
    try:
        # Initialize services
        mcp_service = GoalsMCPService(key_resolver, db)
        predictor = GoalPredictor()
        
        predictions = {}
        
        for metric_type in metrics:
            # Fetch historical data
            historical_data = await mcp_service.fetch_historical_metrics(
                client_id, [metric_type], "last_12_months"
            )
            
            if metric_type in historical_data and not historical_data[metric_type].get("error"):
                # Format data for predictor
                formatted_data = []
                metric_data = historical_data[metric_type]
                
                if 'monthly_values' in metric_data:
                    for item in metric_data['monthly_values']:
                        # Parse month/year from item
                        formatted_data.append({
                            'month': item.get('month'),
                            'year': item.get('year', year - 1),
                            'value': item.get('value', 0)
                        })
                elif 'values' in metric_data:
                    formatted_data = metric_data['values']
                
                # Generate predictions
                prediction = predictor.predict_from_history(
                    formatted_data, metric_type, year, month, model
                )
                
                predictions[metric_type] = prediction
            else:
                predictions[metric_type] = {
                    "error": f"No historical data available for {metric_type}"
                }
        
        return {
            "success": True,
            "client_id": client_id,
            "year": year,
            "month": month,
            "model": model,
            "predictions": predictions,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-klaviyo/{client_id}")
async def sync_with_klaviyo(
    client_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
    metrics: List[str] = ["revenue", "open_rate", "click_rate"],
    db: fs.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Sync actual performance data from Klaviyo and update goals
    
    Args:
        client_id: Client identifier
        month: Specific month or current month
        year: Specific year or current year
        metrics: Metrics to sync
    """
    try:
        # Default to current month/year
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        # Initialize MCP service
        mcp_service = GoalsMCPService(key_resolver, db)
        
        # Determine timeframe for the specific month
        start_date = f"{year}-{month:02d}-01T00:00:00Z"
        if month == 12:
            end_date = f"{year}-12-31T23:59:59Z"
        else:
            end_date = f"{year}-{month+1:02d}-01T00:00:00Z"
        
        timeframe = f"custom_{start_date}_{end_date}"
        
        # Fetch current month's actual data
        actual_data = await mcp_service.fetch_historical_metrics(
            client_id, metrics, timeframe
        )
        
        # Update goals with actual values
        goals_ref = db.collection("goals")
        query = goals_ref.where("client_id", "==", client_id)\
                        .where("year", "==", year)\
                        .where("month", "==", month)
        
        docs = query.stream()
        goal_doc = None
        for doc in docs:
            goal_doc = doc
            break
        
        if goal_doc:
            # Update existing goal with actuals
            update_data = {
                "updated_at": fs.SERVER_TIMESTAMP,
                "last_synced": fs.SERVER_TIMESTAMP,
                "metrics": {}
            }
            
            for metric_type in metrics:
                if metric_type in actual_data and not actual_data[metric_type].get("error"):
                    metric_value = actual_data[metric_type]
                    
                    # Extract actual value
                    actual_value = 0
                    if 'total' in metric_value:
                        actual_value = metric_value['total']
                    elif 'average' in metric_value:
                        actual_value = metric_value['average']
                    elif 'monthly_values' in metric_value and metric_value['monthly_values']:
                        actual_value = metric_value['monthly_values'][0].get('value', 0)
                    
                    update_data["metrics"][metric_type] = {
                        "actual": actual_value,
                        "last_synced": datetime.utcnow().isoformat()
                    }
                    
                    # Keep backward compatibility for revenue
                    if metric_type == "revenue":
                        update_data["actual_revenue"] = actual_value
            
            goal_doc.reference.update(update_data)
            
            return {
                "success": True,
                "message": "Goals synced with Klaviyo",
                "client_id": client_id,
                "year": year,
                "month": month,
                "synced_metrics": update_data["metrics"]
            }
        else:
            return {
                "success": False,
                "message": f"No goal found for {client_id} in {year}-{month:02d}",
                "client_id": client_id,
                "year": year,
                "month": month
            }
            
    except Exception as e:
        logger.error(f"Error syncing with Klaviyo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-yearly/{client_id}")
async def generate_yearly_goals(
    client_id: str,
    year: int,
    metrics: List[str] = ["revenue", "open_rate", "click_rate"],
    model: str = "yoy_growth",
    auto_save: bool = False,
    db: fs.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Generate goals for an entire year based on historical data
    
    Args:
        client_id: Client identifier
        year: Year to generate goals for
        metrics: Metrics to generate goals for
        model: Prediction model to use
        auto_save: Whether to automatically save the generated goals
    """
    try:
        # Generate predictions for all months
        predictions = await predict_goals_from_history(
            client_id, year, metrics, model, None, db, key_resolver
        )
        
        if not predictions.get("success"):
            return predictions
        
        # Prepare goals for saving
        generated_goals = []
        predictor = GoalPredictor()
        
        for metric_type, metric_predictions in predictions["predictions"].items():
            if "predictions" in metric_predictions:
                for prediction in metric_predictions["predictions"]:
                    # Convert prediction to goal
                    goal_data = predictor.calculate_goal_from_prediction(prediction)
                    
                    goal = {
                        "client_id": client_id,
                        "year": prediction["year"],
                        "month": prediction["month"],
                        "metric_type": metric_type,
                        "calculation_method": "ai_suggested",
                        "confidence": goal_data.get("confidence", "medium"),
                        "confidence_score": goal_data.get("confidence_score", 0.65),
                        "human_override": False,
                        "created_at": datetime.utcnow().isoformat(),
                        "metrics": {
                            metric_type: {
                                "goal": goal_data["goal_value"],
                                "predicted": goal_data["predicted_value"],
                                "historical_basis": goal_data.get("historical_basis"),
                                "growth_rate": goal_data.get("growth_rate")
                            }
                        }
                    }
                    
                    # Backward compatibility for revenue
                    if metric_type == "revenue":
                        goal["revenue_goal"] = goal_data["goal_value"]
                    
                    generated_goals.append(goal)
        
        # Auto-save if requested
        saved_count = 0
        if auto_save:
            for goal in generated_goals:
                # Check if goal already exists
                existing_query = db.collection("goals")\
                    .where("client_id", "==", client_id)\
                    .where("year", "==", goal["year"])\
                    .where("month", "==", goal["month"])
                
                existing_docs = list(existing_query.stream())
                
                if existing_docs:
                    # Update existing goal (preserve human overrides)
                    doc = existing_docs[0]
                    existing_data = doc.to_dict()
                    
                    # Only update if not human override
                    if not existing_data.get("human_override", False):
                        doc.reference.update({
                            "metrics": goal["metrics"],
                            "confidence": goal["confidence"],
                            "confidence_score": goal["confidence_score"],
                            "updated_at": fs.SERVER_TIMESTAMP
                        })
                        saved_count += 1
                else:
                    # Create new goal
                    goal["created_at"] = fs.SERVER_TIMESTAMP
                    goal["updated_at"] = fs.SERVER_TIMESTAMP
                    db.collection("goals").add(goal)
                    saved_count += 1
        
        return {
            "success": True,
            "client_id": client_id,
            "year": year,
            "generated_goals": len(generated_goals),
            "saved_goals": saved_count if auto_save else 0,
            "goals": generated_goals
        }
        
    except Exception as e:
        logger.error(f"Error generating yearly goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class BackfillRequest(BaseModel):
    metrics: Optional[List[str]] = None
    years: int = 2

@router.post("/backfill/{client_id}")
async def backfill_historical_data(
    client_id: str,
    request: BackfillRequest,
    db: fs.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Backfill historical data using natural language queries
    
    This endpoint uses the Natural Language MCP system to fetch historical data
    from Klaviyo and generate goals based on that data.
    
    Args:
        client_id: Client identifier
        metrics: List of metrics to backfill (default: all key metrics)
        years: Number of years of historical data to fetch (default: 2)
    
    Returns:
        Summary of backfilled data and generated goals
    """
    try:
        # Initialize backfill service
        backfill_service = GoalsBackfillService(db, key_resolver)
        
        # Perform backfill
        logger.info(f"Starting backfill for client {client_id}")
        result = await backfill_service.backfill_client_data(
            client_id=client_id,
            metrics=request.metrics,
            years=request.years
        )
        
        logger.info(f"Backfill completed: {result['data_points']} data points, {result['goals_generated']} goals")
        
        return {
            "success": True,
            "client_id": client_id,
            "data_points_fetched": result["data_points"],
            "goals_generated": result["goals_generated"],
            "metrics_processed": result["metrics_processed"],
            "errors": result.get("errors", []),
            "message": f"Successfully backfilled {result['data_points']} data points and generated {result['goals_generated']} goals"
        }
        
    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backfill-all")
async def backfill_all_clients(
    request: BackfillRequest,
    db: fs.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Backfill historical data for all active clients with API keys
    
    Args:
        metrics: List of metrics to backfill (default: all key metrics)
        years: Number of years of historical data to fetch (default: 2)
    
    Returns:
        Summary of backfilled data for all clients
    """
    try:
        # Initialize backfill service
        backfill_service = GoalsBackfillService(db, key_resolver)
        
        logger.info("Starting backfill for all clients")
        result = await backfill_service.backfill_all_clients(
            metrics=request.metrics,
            years=request.years
        )
        
        logger.info(f"Backfill completed for {len(result['clients_processed'])} clients")
        
        return {
            "success": True,
            "clients_processed": len(result["clients_processed"]),
            "total_data_points": result["total_data_points"],
            "total_goals_generated": result["total_goals_generated"],
            "client_details": result["clients_processed"],
            "errors": result.get("errors", []),
            "message": f"Successfully processed {len(result['clients_processed'])} clients"
        }
        
    except Exception as e:
        logger.error(f"Error during bulk backfill: {e}")
        raise HTTPException(status_code=500, detail=str(e))