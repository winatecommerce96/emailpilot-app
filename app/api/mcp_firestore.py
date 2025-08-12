"""
MCP Firestore Synchronization API endpoints
Handles synchronization between MCP clients and Firebase Firestore
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
import logging

from app.api.auth import verify_token
from app.core.database import get_db
from app.models.mcp_client import MCPClient
from app.services.mcp_firestore_sync import mcp_firestore_sync

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/sync/to-firestore")
async def sync_mcp_to_firestore(
    client_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Sync MCP clients from local database to Firestore"""
    try:
        if client_id:
            # Sync single client
            client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
            if not client:
                raise HTTPException(status_code=404, detail="MCP client not found")
            
            success = await mcp_firestore_sync.sync_mcp_client_to_firestore(client)
            if success:
                return {"message": f"Successfully synced client {client.name} to Firestore"}
            else:
                raise HTTPException(status_code=500, detail="Failed to sync client to Firestore")
        else:
            # Sync all clients
            result = await mcp_firestore_sync.sync_all_mcp_clients_to_firestore(db)
            if result["success"]:
                return {
                    "message": "Successfully synced MCP clients to Firestore",
                    "details": result
                }
            else:
                raise HTTPException(status_code=500, detail=result.get("message", "Sync failed"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing to Firestore: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/from-firestore")
async def sync_mcp_from_firestore(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Import MCP clients from Firestore to local database"""
    try:
        result = await mcp_firestore_sync.import_mcp_clients_from_firestore(db)
        
        if result["success"]:
            return {
                "message": "Successfully imported MCP clients from Firestore",
                "details": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Import failed"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing from Firestore: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/firestore-clients")
async def get_firestore_mcp_clients(
    current_user: dict = Depends(verify_token)
):
    """Get all MCP clients directly from Firestore"""
    try:
        clients = await mcp_firestore_sync.get_firestore_mcp_clients()
        return {
            "clients": clients,
            "total": len(clients),
            "source": "firestore"
        }
    
    except Exception as e:
        logger.error(f"Error fetching Firestore MCP clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/enable-realtime")
async def enable_realtime_sync(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(verify_token)
):
    """Enable real-time synchronization between Firestore and local database"""
    try:
        # This would typically be done on app startup, but can be triggered manually
        from app.core.database import SessionLocal
        
        def db_session_factory():
            return SessionLocal()
        
        # Start real-time sync in background
        background_tasks.add_task(
            mcp_firestore_sync.setup_realtime_sync,
            db_session_factory
        )
        
        return {
            "message": "Real-time sync listener initiated",
            "status": "background_task_started"
        }
    
    except Exception as e:
        logger.error(f"Error enabling real-time sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync/status")
async def get_sync_status(
    current_user: dict = Depends(verify_token)
):
    """Get the current status of Firestore synchronization"""
    try:
        return {
            "sync_enabled": mcp_firestore_sync.sync_enabled,
            "firestore_connected": mcp_firestore_sync.db is not None,
            "project_id": os.getenv('GOOGLE_CLOUD_PROJECT', 'emailpilot-438321')
        }
    
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/auto-populate")
async def auto_populate_mcp_clients(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Auto-populate MCP clients by syncing both directions"""
    try:
        # First, import any MCP clients from Firestore
        import_result = await mcp_firestore_sync.import_mcp_clients_from_firestore(db)
        
        # Then, sync all local MCP clients to Firestore
        sync_result = await mcp_firestore_sync.sync_all_mcp_clients_to_firestore(db)
        
        # Enable real-time sync for future updates
        from app.core.database import SessionLocal
        
        def db_session_factory():
            return SessionLocal()
        
        background_tasks.add_task(
            mcp_firestore_sync.setup_realtime_sync,
            db_session_factory
        )
        
        return {
            "message": "Auto-population completed successfully",
            "import_result": import_result,
            "sync_result": sync_result,
            "realtime_sync": "enabled"
        }
    
    except Exception as e:
        logger.error(f"Error in auto-population: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import os