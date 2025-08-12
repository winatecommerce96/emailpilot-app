"""
Clients API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models import Client, Goal, Report
from app.schemas.client import ClientResponse, ClientCreate, ClientUpdate

router = APIRouter()

@router.get("/", response_model=List[ClientResponse])
async def get_clients(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all clients"""
    query = db.query(Client)
    
    if active_only:
        query = query.filter(Client.is_active == True)
    
    clients = query.order_by(Client.name).all()
    return clients

@router.get("/{client_id}")
async def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get specific client with summary stats"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get goals count
    goals_count = db.query(Goal).filter(Goal.client_id == client_id).count()
    
    # Get reports count
    reports_count = db.query(Report).filter(Report.client_id == client_id).count()
    
    # Get latest report
    latest_report = db.query(Report).filter(
        Report.client_id == client_id
    ).order_by(Report.created_at.desc()).first()
    
    return {
        "id": client.id,
        "name": client.name,
        "is_active": client.is_active,
        "created_at": client.created_at,
        "stats": {
            "goals_count": goals_count,
            "reports_count": reports_count,
            "latest_report": latest_report.created_at if latest_report else None
        }
    }

@router.post("/")
async def create_client(client_data: ClientCreate, db: Session = Depends(get_db)):
    """Create new client"""
    # Check if client name already exists
    existing = db.query(Client).filter(Client.name == client_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Client name already exists")
    
    client = Client(
        name=client_data.name,
        metric_id=client_data.metric_id,
        is_active=True
    )
    
    db.add(client)
    db.commit()
    db.refresh(client)
    return client

@router.put("/{client_id}")
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    db: Session = Depends(get_db)
):
    """Update client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client_data.name is not None:
        # Check name uniqueness
        existing = db.query(Client).filter(
            Client.name == client_data.name,
            Client.id != client_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Client name already exists")
        client.name = client_data.name
    
    if client_data.metric_id is not None:
        client.metric_id = client_data.metric_id
    
    if client_data.is_active is not None:
        client.is_active = client_data.is_active
    
    client.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(client)
    return client

@router.delete("/{client_id}")
async def deactivate_client(client_id: int, db: Session = Depends(get_db)):
    """Deactivate client (soft delete)"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.is_active = False
    client.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Client deactivated successfully"}