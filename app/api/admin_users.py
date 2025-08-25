"""
Admin Users Management API
Provides endpoints for managing users with Firestore, Asana, and Klaviyo integration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from google.cloud import firestore
from app.deps.firestore import get_db
from app.core.settings import get_settings, Settings
from app.services.auth import verify_admin_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/users", tags=["Admin Users"])

@router.get("")
async def get_all_users(
    domain: Optional[str] = Query(None, description="Filter by email domain"),
    role: Optional[str] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Get all users with optional filtering by domain and role"""
    try:
        # Start with users collection
        users_ref = db.collection("users")
        
        # Get all users (Firestore doesn't support complex queries easily)
        users_docs = users_ref.stream()
        
        all_users = []
        for doc in users_docs:
            user_data = doc.to_dict()
            user_data["id"] = doc.id
            
            # Apply domain filter if specified
            if domain:
                email_domain = user_data.get("email", "").split("@")[-1].lower()
                if email_domain != domain.lower():
                    continue
            
            # Apply role filter if specified
            if role and user_data.get("role") != role:
                continue
            
            # Extract email domain for grouping
            user_data["email_domain"] = user_data.get("email", "").split("@")[-1]
            
            # Check for Asana integration
            asana_doc = db.collection("asana_users").document(doc.id).get()
            if asana_doc.exists:
                user_data["asana_connected"] = True
                asana_data = asana_doc.to_dict()
                user_data["asana_gid"] = asana_data.get("gid")
                user_data["asana_name"] = asana_data.get("name")
            else:
                user_data["asana_connected"] = False
            
            # Check for Klaviyo integration
            klaviyo_doc = db.collection("klaviyo_users").document(doc.id).get()
            if klaviyo_doc.exists:
                user_data["klaviyo_connected"] = True
                klaviyo_data = klaviyo_doc.to_dict()
                user_data["klaviyo_account_id"] = klaviyo_data.get("account_id")
                user_data["klaviyo_company"] = klaviyo_data.get("company")
            else:
                user_data["klaviyo_connected"] = False
            
            all_users.append(user_data)
        
        # Sort by domain, then by email
        all_users.sort(key=lambda x: (x.get("email_domain", ""), x.get("email", "")))
        
        # Apply pagination
        paginated_users = all_users[skip:skip + limit]
        
        # Group by domain for the response
        domains_map = {}
        for user in paginated_users:
            domain = user.get("email_domain", "unknown")
            if domain not in domains_map:
                domains_map[domain] = []
            domains_map[domain].append(user)
        
        return {
            "total": len(all_users),
            "skip": skip,
            "limit": limit,
            "users": paginated_users,
            "by_domain": domains_map,
            "domains": list(domains_map.keys())
        }
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Get detailed information about a specific user"""
    try:
        # Get user document
        user_doc = db.collection("users").document(user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_doc.to_dict()
        user_data["id"] = user_id
        
        # Get Asana integration details
        asana_doc = db.collection("asana_users").document(user_id).get()
        if asana_doc.exists:
            user_data["asana"] = asana_doc.to_dict()
        
        # Get Klaviyo integration details
        klaviyo_doc = db.collection("klaviyo_users").document(user_id).get()
        if klaviyo_doc.exists:
            user_data["klaviyo"] = klaviyo_doc.to_dict()
        
        # Get user's clients
        clients_ref = db.collection("clients").where("user_id", "==", user_id)
        clients = []
        for doc in clients_ref.stream():
            client_data = doc.to_dict()
            client_data["id"] = doc.id
            clients.append(client_data)
        user_data["clients"] = clients
        
        # Get user's activity logs (last 10)
        activity_ref = db.collection("user_activity").where("user_id", "==", user_id).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10)
        activities = []
        for doc in activity_ref.stream():
            activity = doc.to_dict()
            activities.append(activity)
        user_data["recent_activity"] = activities
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    updates: Dict[str, Any],
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Update user information"""
    try:
        # Check if user exists
        user_ref = db.collection("users").document(user_id)
        if not user_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent changing certain fields
        protected_fields = ["id", "created_at", "google_id"]
        for field in protected_fields:
            updates.pop(field, None)
        
        # Add update timestamp
        updates["updated_at"] = datetime.now()
        updates["updated_by"] = current_user.get("email")
        
        # Update user document
        user_ref.update(updates)
        
        # Log the activity
        db.collection("user_activity").add({
            "user_id": user_id,
            "action": "user_updated",
            "updated_by": current_user.get("email"),
            "updates": updates,
            "timestamp": datetime.now()
        })
        
        # Return updated user
        updated_user = user_ref.get().to_dict()
        updated_user["id"] = user_id
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Delete a user (soft delete)"""
    try:
        # Check if user exists
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent deleting self
        if user_id == current_user.get("email"):
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Soft delete - mark as deleted
        user_ref.update({
            "deleted": True,
            "deleted_at": datetime.now(),
            "deleted_by": current_user.get("email")
        })
        
        # Log the activity
        db.collection("user_activity").add({
            "user_id": user_id,
            "action": "user_deleted",
            "deleted_by": current_user.get("email"),
            "timestamp": datetime.now()
        })
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/assign-role")
async def assign_user_role(
    user_id: str,
    role: str,
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Assign a role to a user"""
    try:
        # Validate role
        valid_roles = ["admin", "user", "viewer", "editor", "guest"]
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
        
        # Check if user exists
        user_ref = db.collection("users").document(user_id)
        if not user_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update role
        user_ref.update({
            "role": role,
            "role_updated_at": datetime.now(),
            "role_updated_by": current_user.get("email")
        })
        
        # If making admin, add to admins collection
        if role == "admin":
            db.collection("admins").document(user_id).set({
                "email": user_id,
                "is_active": True,
                "granted_by": current_user.get("email"),
                "granted_at": datetime.now()
            }, merge=True)
        else:
            # Remove from admins collection if exists
            admin_ref = db.collection("admins").document(user_id)
            if admin_ref.get().exists:
                admin_ref.update({"is_active": False})
        
        return {"message": f"Role '{role}' assigned to user successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning role: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/link-asana")
async def link_asana_account(
    user_id: str,
    asana_data: Dict[str, Any],
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Link an Asana account to a user"""
    try:
        # Check if user exists
        user_ref = db.collection("users").document(user_id)
        if not user_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Store Asana integration data
        asana_ref = db.collection("asana_users").document(user_id)
        asana_data.update({
            "linked_at": datetime.now(),
            "linked_by": current_user.get("email")
        })
        asana_ref.set(asana_data, merge=True)
        
        return {"message": "Asana account linked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking Asana account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/link-klaviyo")
async def link_klaviyo_account(
    user_id: str,
    klaviyo_data: Dict[str, Any],
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Link a Klaviyo account to a user"""
    try:
        # Check if user exists
        user_ref = db.collection("users").document(user_id)
        if not user_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Store Klaviyo integration data
        klaviyo_ref = db.collection("klaviyo_users").document(user_id)
        klaviyo_data.update({
            "linked_at": datetime.now(),
            "linked_by": current_user.get("email")
        })
        klaviyo_ref.set(klaviyo_data, merge=True)
        
        return {"message": "Klaviyo account linked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking Klaviyo account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/domains/stats")
async def get_domain_statistics(
    current_user: dict = Depends(verify_admin_token),
    db: firestore.Client = Depends(get_db)
):
    """Get statistics grouped by email domains"""
    try:
        users_ref = db.collection("users")
        users_docs = users_ref.stream()
        
        domain_stats = {}
        
        for doc in users_docs:
            user_data = doc.to_dict()
            email = user_data.get("email", "")
            
            if "@" in email:
                domain = email.split("@")[1].lower()
                
                if domain not in domain_stats:
                    domain_stats[domain] = {
                        "domain": domain,
                        "total_users": 0,
                        "roles": {},
                        "integrations": {
                            "asana": 0,
                            "klaviyo": 0
                        }
                    }
                
                domain_stats[domain]["total_users"] += 1
                
                # Count roles
                role = user_data.get("role", "user")
                if role not in domain_stats[domain]["roles"]:
                    domain_stats[domain]["roles"][role] = 0
                domain_stats[domain]["roles"][role] += 1
                
                # Check integrations
                asana_doc = db.collection("asana_users").document(doc.id).get()
                if asana_doc.exists:
                    domain_stats[domain]["integrations"]["asana"] += 1
                
                klaviyo_doc = db.collection("klaviyo_users").document(doc.id).get()
                if klaviyo_doc.exists:
                    domain_stats[domain]["integrations"]["klaviyo"] += 1
        
        # Convert to list and sort by total users
        stats_list = list(domain_stats.values())
        stats_list.sort(key=lambda x: x["total_users"], reverse=True)
        
        return {
            "domains": stats_list,
            "total_domains": len(stats_list),
            "total_users": sum(d["total_users"] for d in stats_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting domain statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))