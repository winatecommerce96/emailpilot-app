"""
Klaviyo Account Discovery API

Endpoints for discovering and managing Klaviyo accounts that users have access to
via their OAuth tokens.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import os

from app.services.klaviyo_discovery import KlaviyoDiscoveryService
from app.services.client_linking import ClientLinkingService
from app.services.secrets import SecretManagerService
from app.services.auth import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

def get_current_user_flexible(request: Request) -> Dict[str, Any]:
    """Get current user from session OR bearer token"""
    # First try session
    user = request.session.get("user")
    if user:
        return user
    
    # Then try bearer token using JWT decoding
    try:
        from app.services.auth import verify_token
        import jwt
        from app.core.settings import get_settings
        
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            settings = get_settings()
            # Decode the JWT token
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
            if payload:
                return {"email": payload.get("email"), "sub": payload.get("sub")}
    except:
        pass
    
    raise HTTPException(status_code=401, detail="Authentication required")

def get_klaviyo_discovery_service() -> KlaviyoDiscoveryService:
    """Get Klaviyo discovery service instance"""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-app")
    secret_manager = SecretManagerService(project_id)
    return KlaviyoDiscoveryService(project_id, secret_manager)

def get_client_linking_service() -> ClientLinkingService:
    """Get client linking service instance"""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-app")
    secret_manager = SecretManagerService(project_id)
    return ClientLinkingService(project_id, secret_manager)

# Pydantic models for request validation
class LinkAccountRequest(BaseModel):
    account_id: str
    client_id: str

class CreateClientRequest(BaseModel):
    account_id: str
    client_name: Optional[str] = None
    description: Optional[str] = None
    contact_name: Optional[str] = None
    website: Optional[str] = None
    client_voice: Optional[str] = None
    client_background: Optional[str] = None
    key_growth_objective: Optional[str] = None

@router.post("/discover-accounts")
async def discover_klaviyo_accounts(
    request: Request,
    discovery_service: KlaviyoDiscoveryService = Depends(get_klaviyo_discovery_service)
) -> JSONResponse:
    """
    Discover Klaviyo accounts that the authenticated user has access to
    via their OAuth token and store them in Firestore.
    
    This endpoint:
    1. Gets the user's OAuth token from Secret Manager
    2. Calls Klaviyo API to fetch available accounts
    3. Stores discovered accounts in Firestore
    4. Returns accounts with their current link status
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400, 
                detail="User email not found in session"
            )
        
        logger.info(f"Starting account discovery for user: {user_email}")
        
        # Discover and store accounts
        result = await discovery_service.discover_and_store_accounts(user_email)
        
        if not result["success"]:
            # Return specific error messages for common issues
            error_message = result["error"]
            
            if "No Klaviyo OAuth token found" in error_message:
                raise HTTPException(
                    status_code=404,
                    detail="No Klaviyo OAuth token found. Please connect your Klaviyo account first."
                )
            elif "Invalid or expired OAuth token" in error_message:
                raise HTTPException(
                    status_code=401,
                    detail="Klaviyo OAuth token is invalid or expired. Please reconnect your account."
                )
            elif "Insufficient permissions" in error_message:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions to access Klaviyo accounts."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Account discovery failed: {error_message}"
                )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": result["message"],
                "accounts": result["data"]["accounts"],
                "total_accounts": result["data"]["total_accounts"],
                "last_discovery": result["data"]["last_discovery"],
                "user_email": user_email
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in discover_klaviyo_accounts: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during account discovery"
        )

@router.get("/available-accounts")
async def get_available_klaviyo_accounts(
    request: Request,
    discovery_service: KlaviyoDiscoveryService = Depends(get_klaviyo_discovery_service)
) -> JSONResponse:
    """
    Get discovered Klaviyo accounts for the authenticated user with their link status.
    
    Returns previously discovered accounts from Firestore, including:
    - Account details (id, name, email, etc.)
    - Link status (whether account is already linked to a client)
    - Linked client information (if applicable)
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        logger.info(f"Getting available accounts for user: {user_email}")
        
        # Get discovered accounts with link status
        accounts_data = discovery_service.get_discovered_accounts(user_email)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "accounts": accounts_data["accounts"],
                "total_accounts": accounts_data["total_accounts"],
                "last_discovery": accounts_data["last_discovery"],
                "user_email": user_email
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting available accounts for {user_email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available accounts: {str(e)}"
        )

@router.get("/account/{account_id}/status")
async def get_account_link_status(
    account_id: str,
    request: Request,
    discovery_service: KlaviyoDiscoveryService = Depends(get_klaviyo_discovery_service)
) -> JSONResponse:
    """
    Get the link status of a specific Klaviyo account.
    
    Args:
        account_id: Klaviyo account ID to check
        
    Returns:
        Link status and client information if linked
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        # Get all discovered accounts for the user
        accounts_data = discovery_service.get_discovered_accounts(user_email)
        
        # Find the specific account
        account_info = None
        for account in accounts_data["accounts"]:
            if account["id"] == account_id:
                account_info = account
                break
        
        if not account_info:
            raise HTTPException(
                status_code=404,
                detail=f"Account {account_id} not found in discovered accounts"
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "account_id": account_id,
                "account_name": account_info.get("name"),
                "is_linked": account_info.get("is_linked", False),
                "linked_client_id": account_info.get("linked_client_id"),
                "linked_client_name": account_info.get("linked_client_name")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account status for {account_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get account status: {str(e)}"
        )

@router.delete("/clear-discovered")
async def clear_discovered_accounts(
    request: Request,
    discovery_service: KlaviyoDiscoveryService = Depends(get_klaviyo_discovery_service)
) -> JSONResponse:
    """
    Clear discovered accounts for the authenticated user.
    
    This is useful when users want to re-discover accounts or 
    clean up old discovery data.
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        # Clear discovered accounts by storing empty data
        discovery_service.store_discovered_accounts(user_email, [])
        
        logger.info(f"Cleared discovered accounts for user: {user_email}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Discovered accounts cleared successfully",
                "user_email": user_email
            }
        )
        
    except Exception as e:
        logger.error(f"Error clearing discovered accounts for {user_email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear discovered accounts: {str(e)}"
        )

# Client Linking Endpoints

@router.post("/link-account")
async def link_account_to_client(
    link_request: LinkAccountRequest,
    request: Request,
    linking_service: ClientLinkingService = Depends(get_client_linking_service)
) -> JSONResponse:
    """
    Link a discovered Klaviyo account to an existing EmailPilot client.
    
    Args:
        link_request: Contains account_id and client_id to link
        
    Returns:
        Success/failure status with details
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        logger.info(f"Linking account {link_request.account_id} to client {link_request.client_id} for user {user_email}")
        
        # Perform the linking
        result = linking_service.link_account_to_existing_client(
            user_email=user_email,
            account_id=link_request.account_id,
            client_id=link_request.client_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": result["message"],
                "client_id": result["client_id"],
                "client_name": result["client_name"],
                "account_id": result["account_id"],
                "account_name": result["account_name"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking account {link_request.account_id} to client {link_request.client_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to link account to client: {str(e)}"
        )

@router.post("/create-client")
async def create_client_from_account(
    create_request: CreateClientRequest,
    request: Request,
    linking_service: ClientLinkingService = Depends(get_client_linking_service)
) -> JSONResponse:
    """
    Create a new EmailPilot client from a discovered Klaviyo account.
    
    Args:
        create_request: Contains account_id and optional client data
        
    Returns:
        Success/failure status with new client details
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        logger.info(f"Creating client from account {create_request.account_id} for user {user_email}")
        
        # Prepare additional data
        additional_data = {}
        if create_request.client_name:
            # Override the account name if provided
            additional_data["name"] = create_request.client_name
        if create_request.description:
            additional_data["description"] = create_request.description
        if create_request.contact_name:
            additional_data["contact_name"] = create_request.contact_name
        if create_request.website:
            additional_data["website"] = create_request.website
        if create_request.client_voice:
            additional_data["client_voice"] = create_request.client_voice
        if create_request.client_background:
            additional_data["client_background"] = create_request.client_background
        if create_request.key_growth_objective:
            additional_data["key_growth_objective"] = create_request.key_growth_objective
        
        # Create the client
        result = linking_service.create_client_from_account(
            user_email=user_email,
            account_id=create_request.account_id,
            additional_data=additional_data if additional_data else None
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": result["message"],
                "client_id": result["client_id"],
                "client_name": result["client_name"],
                "account_id": result["account_id"],
                "account_name": result["account_name"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client from account {create_request.account_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create client from account: {str(e)}"
        )

@router.delete("/unlink-account/{client_id}")
async def unlink_account_from_client(
    client_id: str,
    request: Request,
    linking_service: ClientLinkingService = Depends(get_client_linking_service)
) -> JSONResponse:
    """
    Unlink a Klaviyo account from an EmailPilot client.
    
    Args:
        client_id: ID of the client to unlink account from
        
    Returns:
        Success/failure status with details
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        logger.info(f"Unlinking account from client {client_id} for user {user_email}")
        
        # Perform the unlinking
        result = linking_service.unlink_account_from_client(
            user_email=user_email,
            client_id=client_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": result["message"],
                "client_id": result["client_id"],
                "client_name": result["client_name"],
                "account_id": result["account_id"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking account from client {client_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unlink account from client: {str(e)}"
        )

@router.get("/linkable-clients")
async def get_linkable_clients(
    request: Request,
    linking_service: ClientLinkingService = Depends(get_client_linking_service)
) -> JSONResponse:
    """
    Get list of clients that can be linked to Klaviyo accounts.
    
    Returns clients that don't already have OAuth accounts linked.
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        logger.info(f"Getting linkable clients for user {user_email}")
        
        # Get linkable clients
        clients = linking_service.get_user_linkable_clients(user_email)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "clients": clients,
                "total_clients": len(clients),
                "user_email": user_email
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting linkable clients for {user_email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get linkable clients: {str(e)}"
        )

@router.get("/account/{account_id}/matches")
async def get_potential_client_matches(
    account_id: str,
    request: Request,
    linking_service: ClientLinkingService = Depends(get_client_linking_service),
    discovery_service: KlaviyoDiscoveryService = Depends(get_klaviyo_discovery_service)
) -> JSONResponse:
    """
    Get potential client matches for a discovered Klaviyo account based on name/email similarity.
    
    Args:
        account_id: Klaviyo account ID to find matches for
        
    Returns:
        List of potential client matches with confidence scores
    """
    try:
        # Get authenticated user
        user = get_current_user_flexible(request)
        user_email = user.get("email")
        
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="User email not found in session"
            )
        
        logger.info(f"Getting potential matches for account {account_id} for user {user_email}")
        
        # Get the account data first
        accounts_data = discovery_service.get_discovered_accounts(user_email)
        account_info = None
        
        for account in accounts_data["accounts"]:
            if account["id"] == account_id:
                account_info = account
                break
        
        if not account_info:
            raise HTTPException(
                status_code=404,
                detail=f"Account {account_id} not found in discovered accounts"
            )
        
        # Get potential matches
        matches = linking_service.auto_match_by_name_email(account_info, user_email)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "account_id": account_id,
                "account_name": account_info.get("name"),
                "matches": matches,
                "total_matches": len(matches)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting matches for account {account_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get potential matches: {str(e)}"
        )