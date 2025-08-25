# app/api/performance.py
"""
Performance API
- Serves performance data stored by the performance_api service.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from app.deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/performance", tags=["performance"])

@router.get("/mtd/all")
async def get_all_clients_mtd_performance(db: firestore.Client = Depends(get_db)) -> Dict[str, Any]:
    """
    Aggregates the most recent weekly performance MTD revenue for all active clients.
    """
    total_mtd_revenue = 0.0
    clients_processed = 0
    clients_with_data = 0
    
    try:
        clients_ref = db.collection("clients")
        active_clients_stream = clients_ref.where("is_active", "==", True).stream()

        for client in active_clients_stream:
            clients_processed += 1
            client_id = client.id
            
            performance_ref = db.collection("clients").document(client_id).collection("performance")
            query = performance_ref.where("scope", "==", "weekly").order_by("created_at", direction=firestore.Query.DESCENDING).limit(1)
            docs = list(query.stream())
            
            if docs:
                latest_perf = docs[0].to_dict()
                total_mtd_revenue += latest_perf.get("total", 0.0)
                clients_with_data += 1

    except Exception as e:
        logger.error(f"Failed to aggregate MTD performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to process aggregated performance data.")

    return {
        "total_mtd_revenue": round(total_mtd_revenue, 2),
        "clients_processed": clients_processed,
        "clients_with_data": clients_with_data,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/mtd/{client_id}")
async def get_mtd_performance(client_id: str, db: firestore.Client = Depends(get_db)) -> Dict[str, Any]:
    """
    Gets the most recent weekly MTD performance data for a single client from Firestore.
    """
    try:
        performance_ref = db.collection("clients").document(client_id).collection("performance")
        query = performance_ref.where("scope", "==", "weekly").order_by("created_at", direction=firestore.Query.DESCENDING).limit(1)
        docs = list(query.stream())

        if not docs:
            return {
                "client_id": client_id,
                "total": 0.0,
                "data_source": "firestore",
                "message": "No weekly performance document found.",
                "timestamp": datetime.now().isoformat()
            }
            
        latest_perf = docs[0].to_dict()
        
        return {
            "client_id": client_id,
            "total": latest_perf.get("total", 0.0),
            "metric_id": latest_perf.get("metric_id"),
            "timeframe": latest_perf.get("timeframe"),
            "data_source": "firestore",
            "timestamp": latest_perf.get("created_at")
        }

    except Exception as e:
        logger.error(f"Failed to get MTD performance for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance data for client {client_id}.")
