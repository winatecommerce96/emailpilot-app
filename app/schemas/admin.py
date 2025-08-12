"""
Admin-related Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class EnvironmentInfo(BaseModel):
    """Environment information response"""
    demoMode: bool
    environment: str
    debug: bool
    apiBase: str
    firestoreProject: str
    buildVersion: str
    commitSha: str
    secretManagerEnabled: Optional[bool] = False
    features: Optional[Dict[str, bool]] = {}
    error: Optional[str] = None

class ClientInfo(BaseModel):
    """Client information for admin dashboard"""
    id: str
    name: str
    metric_id: str = ""
    description: str = ""
    is_active: bool = True
    has_klaviyo_key: bool = False
    contact_email: str = ""
    contact_name: str = ""
    website: str = ""
    created_at: str = ""
    updated_at: str = ""
    klaviyo_key_preview: str = ""
    recent_revenue: float = 0
    recent_orders: int = 0
    
class ClientsResponse(BaseModel):
    """Response for getting all clients"""
    status: str
    total_clients: int
    active_clients: int
    clients_with_keys: int
    clients: List[ClientInfo]