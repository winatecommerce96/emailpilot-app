"""
Klaviyo Backfill API - Comprehensive data synchronization endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from app.services.klaviyo_data_service import KlaviyoDataService
from app.deps.firestore import get_db
from app.services.client_key_resolver import ClientKeyResolver
from app.services.secret_manager import SecretManagerService
from google.cloud import firestore
import os

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/backfill",
    tags=["Backfill Operations"]
)

class BackfillRequest(BaseModel):
    client_id: str
    years: int = 1
    include_orders: bool = True
    include_campaigns: bool = True
    include_flows: bool = True

class BackfillAllRequest(BaseModel):
    years: int = 1
    include_orders: bool = True
    test_mode: bool = False  # If true, only process first client

@router.post("/start/{client_id}")
async def start_backfill(
    client_id: str,
    background_tasks: BackgroundTasks,
    years: int = Query(1, description="Number of years to backfill"),
    include_orders: bool = Query(True, description="Include granular order data")
) -> Dict[str, Any]:
    """
    Start backfill process for a specific client.
    Runs in background and updates status in Firestore.
    """
    try:
        db = get_db()
        
        # Check if client exists
        client_ref = db.collection("clients").document(client_id)
        client_doc = client_ref.get()
        
        if not client_doc.exists:
            # Try to find by slug or name  
            clients_ref = db.collection("clients")
            
            # Try as slug
            slug_query = clients_ref.where("client_slug", "==", client_id.lower()).limit(1)
            for doc in slug_query.stream():
                client_id = doc.id
                client_doc = doc
                break
            
            if not client_doc or not client_doc.exists:
                # Try partial name match
                name_query = clients_ref.where("name", ">=", client_id).where("name", "<=", client_id + "\uf8ff").limit(1)
                for doc in name_query.stream():
                    client_id = doc.id
                    client_doc = doc
                    break
            
            if not client_doc or not client_doc.exists:
                raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
        
        client_data = client_doc.to_dict()
        client_name = client_data.get("name", client_id)
        
        # Check if backfill is already in progress
        backfill_status_ref = db.collection("backfill_status").document(client_id)
        status_doc = backfill_status_ref.get()
        
        if status_doc.exists:
            status_data = status_doc.to_dict()
            if status_data.get("status") == "in_progress":
                return {
                    "status": "already_running",
                    "message": f"Backfill already in progress for {client_name}",
                    "progress": status_data.get("progress", 0),
                    "started_at": status_data.get("started_at")
                }
        
        # Start backfill in background
        service = KlaviyoDataService(db)
        background_tasks.add_task(
            service.backfill_client_data,
            client_id,
            years,
            include_orders
        )
        
        return {
            "status": "started",
            "message": f"Backfill started for {client_name}",
            "client_id": client_id,
            "client_name": client_name,
            "years": years,
            "include_orders": include_orders
        }
        
    except Exception as e:
        logger.error(f"Failed to start backfill: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{client_id}")
async def get_backfill_status(client_id: str) -> Dict[str, Any]:
    """
    Get the current status of a backfill operation for a client.
    """
    try:
        db = get_db()
        
        # Get backfill status
        status_ref = db.collection("backfill_status").document(client_id)
        status_doc = status_ref.get()
        
        if not status_doc.exists:
            return {
                "status": "not_found",
                "message": f"No backfill status found for client {client_id}"
            }
        
        status_data = status_doc.to_dict()
        
        # Get client name
        client_ref = db.collection("clients").document(client_id)
        client_doc = client_ref.get()
        client_name = client_doc.to_dict().get("name", client_id) if client_doc.exists else client_id
        
        return {
            "client_id": client_id,
            "client_name": client_name,
            **status_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get backfill status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_all_backfill_status() -> Dict[str, Any]:
    """
    Get the status of all backfill operations.
    """
    try:
        db = get_db()
        
        # Get all backfill statuses
        status_ref = db.collection("backfill_status")
        statuses = []
        
        for status_doc in status_ref.stream():
            status_data = status_doc.to_dict()
            client_id = status_doc.id
            
            # Get client name
            client_ref = db.collection("clients").document(client_id)
            client_doc = client_ref.get()
            client_name = client_doc.to_dict().get("name", client_id) if client_doc.exists else client_id
            
            statuses.append({
                "client_id": client_id,
                "client_name": client_name,
                **status_data
            })
        
        # Sort by status (in_progress first, then by started_at)
        statuses.sort(key=lambda x: (
            0 if x.get("status") == "in_progress" else 1,
            x.get("started_at", "") if x.get("started_at") else ""
        ))
        
        return {
            "total": len(statuses),
            "in_progress": sum(1 for s in statuses if s.get("status") == "in_progress"),
            "completed": sum(1 for s in statuses if s.get("status") == "completed"),
            "failed": sum(1 for s in statuses if s.get("status") == "failed"),
            "statuses": statuses
        }
        
    except Exception as e:
        logger.error(f"Failed to get all backfill statuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start-all")
async def start_backfill_all(
    background_tasks: BackgroundTasks,
    request: BackfillAllRequest
) -> Dict[str, Any]:
    """
    Start backfill for all active clients with API keys.
    """
    try:
        db = get_db()
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        secret_manager = SecretManagerService(project_id=project_id)
        key_resolver = ClientKeyResolver(db=db, secret_manager=secret_manager)
        
        # Get all active clients
        clients_ref = db.collection("clients").where("is_active", "==", True)
        clients_to_process = []
        
        for client_doc in clients_ref.stream():
            client_data = client_doc.to_dict()
            client_id = client_doc.id
            
            # Check if client has API key
            try:
                api_key = await key_resolver.get_client_klaviyo_key(client_id)
                if api_key:
                    clients_to_process.append({
                        "id": client_id,
                        "name": client_data.get("name", client_id)
                    })
            except Exception as e:
                logger.warning(f"Skipping client {client_id}: {e}")
        
        if not clients_to_process:
            return {
                "status": "no_clients",
                "message": "No active clients with API keys found"
            }
        
        # In test mode, only process first client
        if request.test_mode:
            clients_to_process = clients_to_process[:1]
        
        # Start backfill for each client
        service = KlaviyoDataService(db)
        for client in clients_to_process:
            background_tasks.add_task(
                service.backfill_client_data,
                client["id"],
                request.years,
                request.include_orders
            )
        
        return {
            "status": "started",
            "message": f"Backfill started for {len(clients_to_process)} clients",
            "clients": clients_to_process,
            "years": request.years,
            "include_orders": request.include_orders,
            "test_mode": request.test_mode
        }
        
    except Exception as e:
        logger.error(f"Failed to start backfill for all clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear/{client_id}")
async def clear_backfill_status(client_id: str) -> Dict[str, Any]:
    """
    Clear the backfill status for a client.
    """
    try:
        db = get_db()
        
        # Delete backfill status
        status_ref = db.collection("backfill_status").document(client_id)
        status_ref.delete()
        
        return {
            "status": "cleared",
            "message": f"Backfill status cleared for {client_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear backfill status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{client_id}/orders")
async def get_backfilled_orders(
    client_id: str,
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Maximum number of orders to return")
) -> Dict[str, Any]:
    """
    Get backfilled order data for a client.
    """
    try:
        db = get_db()
        
        # Build query
        orders_ref = (
            db.collection("clients")
            .document(client_id)
            .collection("klaviyo")
            .document("data")
            .collection("orders")
        )
        
        if date:
            orders_ref = orders_ref.where("date", "==", date)
        
        orders_ref = orders_ref.limit(limit)
        
        # Get orders
        orders = []
        total_value = 0
        
        for order_doc in orders_ref.stream():
            order_data = order_doc.to_dict()
            orders.append(order_data)
            total_value += float(order_data.get("value", 0))
        
        return {
            "client_id": client_id,
            "date_filter": date,
            "total_orders": len(orders),
            "total_value": total_value,
            "orders": orders
        }
        
    except Exception as e:
        logger.error(f"Failed to get backfilled orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{client_id}/summary")
async def get_backfilled_summary(client_id: str) -> Dict[str, Any]:
    """
    Get a summary of all backfilled data for a client.
    """
    try:
        db = get_db()
        
        # Get counts from each collection
        base_ref = (
            db.collection("clients")
            .document(client_id)
            .collection("klaviyo")
            .document("data")
        )
        
        # Count campaigns
        campaigns_count = len(list(base_ref.collection("campaigns").limit(1000).stream()))
        
        # Count flows  
        flows_count = len(list(base_ref.collection("flows").limit(1000).stream()))
        
        # Count orders
        orders_ref = base_ref.collection("orders")
        orders_count = 0
        total_revenue = 0
        
        for order_doc in orders_ref.stream():
            orders_count += 1
            order_data = order_doc.to_dict()
            total_revenue += float(order_data.get("value", 0))
        
        # Get date range from backfill status
        status_ref = db.collection("backfill_status").document(client_id)
        status_doc = status_ref.get()
        
        date_range = {}
        if status_doc.exists:
            status_data = status_doc.to_dict()
            date_range = {
                "start_date": status_data.get("start_date"),
                "end_date": status_data.get("end_date"),
                "status": status_data.get("status"),
                "progress": status_data.get("progress")
            }
        
        return {
            "client_id": client_id,
            "summary": {
                "campaigns": campaigns_count,
                "flows": flows_count,
                "orders": orders_count,
                "total_revenue": total_revenue,
                "average_order_value": total_revenue / orders_count if orders_count > 0 else 0
            },
            "date_range": date_range
        }
        
    except Exception as e:
        logger.error(f"Failed to get backfilled summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))