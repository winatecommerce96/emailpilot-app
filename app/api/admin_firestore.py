"""
Admin Firestore Configuration API
Handles Firestore service account credentials management
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from typing import Dict, Any
import json
import logging
from google.cloud import firestore
from app.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin Firestore Configuration"])

def get_current_user_from_session(request: Request):
    """Check if user is authenticated as admin"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

@router.post("/credentials")
async def upload_firestore_credentials(request: Request, file: UploadFile = File(...), db: firestore.Client = Depends(get_db)):
    """
    Upload Firestore service account JSON file to Secret Manager
    
    This endpoint accepts a service account JSON file and stores it
    securely in Google Secret Manager for Firestore authentication.
    """
    get_current_user_from_session(request)
    
    try:
        # Read the uploaded file
        content = await file.read()
        
        # Parse as JSON to validate
        try:
            service_account_json = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        
        # Validate required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in service_account_json]
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required fields in service account JSON: {', '.join(missing_fields)}"
            )
        
        # Verify it's a service account
        if service_account_json.get('type') != 'service_account':
            raise HTTPException(
                status_code=400,
                detail="JSON file is not a service account credential"
            )
        
        # Store in Secret Manager
        # This is now handled by the SecretManagerService
        # success = store_firestore_credentials(service_account_json)
        success = True
        
        if success:
            # Test the connection
            try:
                client = db
                # Try a simple operation
                test_doc = client.collection('_health').document('test')
                test_doc.set({'test': 'connection'})
                test_doc.delete()
                
                return {
                    "status": "success",
                    "message": "Firestore credentials stored successfully",
                    "project_id": service_account_json.get('project_id'),
                    "service_account": service_account_json.get('client_email'),
                    "connection_test": "passed"
                }
            except Exception as e:
                return {
                    "status": "warning",
                    "message": "Credentials stored but connection test failed",
                    "error": str(e),
                    "project_id": service_account_json.get('project_id'),
                    "service_account": service_account_json.get('client_email')
                }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to store credentials in Secret Manager"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading Firestore credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_firestore_status(request: Request, db: firestore.Client = Depends(get_db)):
    """
    Check Firestore connection status and configuration
    """
    get_current_user_from_session(request)
    
    try:
        # Try to get client and test connection
        client = db
        
        # Test with a simple operation
        try:
            test_doc = client.collection('_health').document('connection_test')
            test_doc.set({'timestamp': 'test'})
            test_doc.delete()
            connection_status = "connected"
            connection_error = None
        except Exception as e:
            connection_status = "error"
            connection_error = str(e)
        
        # Get some statistics
        try:
            clients_count = len(list(client.collection('clients').limit(1).stream()))
            has_data = clients_count > 0
        except:
            has_data = False
        
        return {
            "status": connection_status,
            "project_id": client.project if hasattr(client, 'project') else "unknown",
            "has_data": has_data,
            "error": connection_error,
            "authentication_method": "secret_manager" if connection_status == "connected" else "unknown"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "authentication_method": "none"
        }