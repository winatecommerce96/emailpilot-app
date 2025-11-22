#!/usr/bin/env python3
"""
Minimal API server for client management
This is a workaround while the main server import issue is being fixed
"""
import os
import sys
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

# Add parent directory to path for shared_modules
sys.path.insert(0, '/Users/Damon/klaviyo/klaviyo-audit-automation')

load_dotenv()

app = FastAPI(title="Clients API", version="1.0.0")

# Import multi-platform schemas
try:
    from shared_modules.clients.schemas import ClientCreate, ClientUpdate
    from shared_modules.clients.constants import ESPPlatform
    SCHEMAS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import schemas: {e}")
    SCHEMAS_AVAILABLE = False
    # Fallback basic schema
    class ClientCreate(BaseModel):
        client_name: str
        esp_platform: str = "klaviyo"

    class ClientUpdate(BaseModel):
        pass

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8003",
        "http://127.0.0.1:8003",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/clients")
@app.get("/api/clients/")
async def get_clients():
    """Get all clients from Firestore"""
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
        if not project_id:
            return {"error": "No Google Cloud project configured"}

        db = firestore.Client(project=project_id)
        clients = []

        for doc in db.collection('clients').stream():
            client_data = doc.to_dict()
            clients.append({
                "name": client_data.get("client_name", "Unknown"),
                "slug": client_data.get("client_slug", doc.id),
                **client_data
            })

        return clients
    except Exception as e:
        print(f"Error: {e}")
        return []

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "clients-api"}

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

@app.post("/clients/validate")
async def validate_client(client_data: Dict[str, Any] = Body(...)):
    """Validate client data before creation"""
    try:
        if SCHEMAS_AVAILABLE:
            # Use proper schema validation
            client = ClientCreate(**client_data)
            return {"valid": True, "message": "Client data is valid"}
        else:
            # Basic validation
            if not client_data.get("client_name"):
                raise HTTPException(status_code=400, detail="client_name is required")
            return {"valid": True, "message": "Client data is valid"}
    except ValidationError as e:
        return {"valid": False, "errors": e.errors()}
    except Exception as e:
        return {"valid": False, "errors": str(e)}

@app.post("/clients")
async def create_client(client_data: Dict[str, Any] = Body(...)):
    """Create a new client"""
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
        if not project_id:
            raise HTTPException(status_code=500, detail="No Google Cloud project configured")

        # Validate with schema if available
        if SCHEMAS_AVAILABLE:
            client = ClientCreate(**client_data)
            client_dict = client.model_dump()
        else:
            client_dict = client_data

        # Generate slug
        client_name = client_dict.get("client_name", "unknown")
        client_slug = slugify(client_name)

        # Add timestamps and slug
        client_dict["client_slug"] = client_slug
        client_dict["created_at"] = datetime.utcnow().isoformat()
        client_dict["updated_at"] = datetime.utcnow().isoformat()

        # Save to Firestore
        db = firestore.Client(project=project_id)
        db.collection('clients').document(client_slug).set(client_dict)

        return {
            "data": client_dict,
            "log": ["Client created successfully"],
            "errors": []
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/clients/{slug}")
async def update_client(slug: str, client_data: Dict[str, Any] = Body(...)):
    """Update an existing client"""
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
        if not project_id:
            raise HTTPException(status_code=500, detail="No Google Cloud project configured")

        db = firestore.Client(project=project_id)
        doc_ref = db.collection('clients').document(slug)

        # Check if client exists
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Client not found")

        # Add updated timestamp
        client_data["updated_at"] = datetime.utcnow().isoformat()

        # Update in Firestore
        doc_ref.update(client_data)

        # Get updated client
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()

        return {
            "data": updated_data,
            "log": ["Client updated successfully"],
            "errors": []
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clients/{slug}")
async def delete_client(slug: str):
    """Delete a client"""
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
        if not project_id:
            raise HTTPException(status_code=500, detail="No Google Cloud project configured")

        db = firestore.Client(project=project_id)
        doc_ref = db.collection('clients').document(slug)

        # Check if client exists
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Client not found")

        # Delete from Firestore
        doc_ref.delete()

        return {
            "message": "Client deleted successfully",
            "log": [f"Client {slug} deleted"],
            "errors": []
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
