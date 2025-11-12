"""
Public Clients API - No authentication required
Serves client list for calendar interface
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from google.cloud import firestore
from app.deps.firestore import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_clients(db: firestore.Client = Depends(get_db)):
    """Get all active clients (public endpoint for calendar)"""
    try:
        clients = []
        # Query active clients from Firestore
        query = db.collection("clients").stream()

        for doc in query:
            data = doc.to_dict()
            # Include client if it has necessary fields and is active
            if data.get("name") and data.get("client_slug"):
                clients.append({
                    "id": doc.id,
                    "name": data.get("name", "Unknown"),
                    "client_slug": data.get("client_slug", doc.id),
                    "description": data.get("description", ""),
                    "status": data.get("status", "active"),
                    "is_active": data.get("is_active", True)
                })

        logger.info(f"Retrieved {len(clients)} clients from Firestore")
        return sorted(clients, key=lambda x: x["name"])
    except Exception as e:
        logger.error(f"Error fetching clients: {str(e)}")
        return []
