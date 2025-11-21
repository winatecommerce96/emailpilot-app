"""
Admin Asana configuration endpoints using Secret Manager.
Allows setting and validating Asana OAuth app credentials.
Also surfaces aggregate info about connected users.

UPDATED: Now includes calendar integration status and testing endpoints.
"""
from __future__ import annotations
import logging
import os
from typing import Any, Dict, Optional
from google.cloud import firestore, secretmanager

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.secret_manager import SecretManagerService
from app.deps import get_secret_manager_service, get_db
from app.services.asana_client import AsanaClient
from app.services.asana_calendar_integration import (
    ACCOUNT_MANAGEMENT_PROJECT_GID,
    FIGMA_URL_FIELD_NAME,
)

logger = logging.getLogger(__name__)

router = APIRouter()  # Prefix applied in main_firestore.py


async def get_asana_api_token() -> Optional[str]:
    """Get Asana API token from environment variable or Secret Manager

    Following the pattern from asana-brief-creation app:
    1. Check ASANA_ACCESS_TOKEN environment variable first
    2. Fall back to Secret Manager if not found
    """
    # Check environment variable first (same as asana-brief-creation)
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if token:
        logger.info("Using ASANA_ACCESS_TOKEN from environment variable")
        return token.strip()

    # Fall back to Secret Manager
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        secret_service = SecretManagerService(project_id)
        token = secret_service.get_secret("asana-access-token")
        if token:
            logger.info("Using Asana token from Secret Manager")
            return token.strip()
        return None
    except Exception as e:
        logger.warning(f"Could not retrieve Asana token from Secret Manager: {e}")
        return None


class SetAsanaSecretsRequest(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


@router.get("/status")
async def asana_status(secret_manager: SecretManagerService = Depends(get_secret_manager_service)) -> Dict[str, Any]:
    """Returns whether OAuth client creds exist and connected users count."""
    ok_id = False
    ok_secret = False
    try:
        ok_id = bool(secret_manager.get_secret("asana-oauth-client-id"))
    except Exception:
        ok_id = False
    try:
        ok_secret = bool(secret_manager.get_secret("asana-oauth-client-secret"))
    except Exception:
        ok_secret = False

    # Count connected users (best-effort)
    connected_users = 0
    try:
        db = get_db()
        # Firestore has no count queries without aggregation; iterate limited subset
        # For admin visibility, sample first 200 users
        users = list(db.collection("users").limit(200).stream())
        for u in users:
            doc = (
                db.collection("users").document(u.id).collection("integrations").document("asana").get()
            )
            if doc.exists and (doc.to_dict() or {}).get("access_token"):
                connected_users += 1
    except Exception:
        pass

    return {
        "client_id_configured": ok_id,
        "client_secret_configured": ok_secret,
        "connected_users_sample": connected_users,
    }


@router.post("/secrets")
async def set_asana_secrets(payload: SetAsanaSecretsRequest, secret_manager: SecretManagerService = Depends(get_secret_manager_service)) -> Dict[str, Any]:
    """Create or update Asana OAuth client credentials in Secret Manager."""
    try:
        changed = []
        if payload.client_id:
            secret_manager.create_secret("asana-oauth-client-id", payload.client_id, labels={"app": "emailpilot", "type": "asana", "cred": "client_id"})
            changed.append("client_id")
        if payload.client_secret:
            secret_manager.create_secret("asana-oauth-client-secret", payload.client_secret, labels={"app": "emailpilot", "type": "asana", "cred": "client_secret"})
            changed.append("client_secret")
        if not changed:
            raise HTTPException(status_code=400, detail="No values provided")
        return {"updated": changed}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set Asana secrets: {e}")
        raise HTTPException(status_code=500, detail="Failed to set Asana secrets")


# ============================================================================
# Calendar Integration Status and Testing Endpoints
# ============================================================================

@router.get("/calendar/status")
async def get_calendar_integration_status(
    db: firestore.Client = Depends(get_db)
):
    """
    Get status of Asana calendar integration configuration.

    Shows what's configured and what's missing for calendar approval tasks.
    """
    try:
        status_info = {
            "configured": {
                "asana_api_token": False,
                "account_management_project": False,
                "public_base_url": False,
            },
            "values": {},
            "clients_with_asana": 0,
            "clients_without_asana": 0,
            "warnings": [],
        }

        # Check Asana API token
        token = await get_asana_api_token()
        status_info["configured"]["asana_api_token"] = bool(token)
        if not token:
            status_info["warnings"].append("Asana API token (asana-api-token) not configured in Secret Manager")

        # Check Account Management project GID
        status_info["configured"]["account_management_project"] = bool(ACCOUNT_MANAGEMENT_PROJECT_GID)
        status_info["values"]["account_management_project_gid"] = ACCOUNT_MANAGEMENT_PROJECT_GID or "Not set"
        if not ACCOUNT_MANAGEMENT_PROJECT_GID:
            status_info["warnings"].append(
                "ASANA_ACCOUNT_MANAGEMENT_PROJECT_GID not set - tasks won't be multi-homed"
            )

        # Check public base URL
        public_base_url = os.getenv("PUBLIC_BASE_URL")
        status_info["configured"]["public_base_url"] = bool(public_base_url)
        status_info["values"]["public_base_url"] = public_base_url or "Using default (http://localhost:8000)"

        # Count clients with/without Asana links
        clients = db.collection("clients").stream()
        for client_doc in clients:
            client_data = client_doc.to_dict()
            if client_data.get("asana_project_link"):
                status_info["clients_with_asana"] += 1
            else:
                status_info["clients_without_asana"] += 1

        # Overall status
        status_info["ready"] = (
            status_info["configured"]["asana_api_token"] and
            status_info["clients_with_asana"] > 0
        )

        return {
            "success": True,
            "status": status_info
        }

    except Exception as e:
        logger.error(f"Error checking Asana calendar integration status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check status: {str(e)}"
        )


@router.get("/projects")
async def list_asana_projects():
    """
    List all Asana projects accessible with the configured API token.

    Useful for finding the Account Management project GID.
    """
    try:
        token = await get_asana_api_token()
        if not token:
            raise HTTPException(
                status_code=400,
                detail="Asana API token not configured in Secret Manager"
            )

        asana_client = AsanaClient(token)

        # Get workspaces
        workspaces = await asana_client.list_workspaces()
        if not workspaces:
            return {
                "success": True,
                "workspaces": [],
                "message": "No workspaces found"
            }

        # Get projects for each workspace
        results = []
        for workspace in workspaces:
            workspace_gid = workspace.get("gid")
            workspace_name = workspace.get("name")

            projects = await asana_client.list_projects(
                workspace_gid=workspace_gid,
                archived=False
            )

            workspace_projects = []
            for project in projects:
                workspace_projects.append({
                    "gid": project.get("gid"),
                    "name": project.get("name"),
                    "url": f"https://app.asana.com/0/{project.get('gid')}/list",
                })

            results.append({
                "workspace_gid": workspace_gid,
                "workspace_name": workspace_name,
                "projects": workspace_projects,
                "project_count": len(workspace_projects)
            })

        return {
            "success": True,
            "workspaces": results,
            "message": f"Found {sum(w['project_count'] for w in results)} projects across {len(results)} workspaces"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing Asana projects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/project/{project_gid}/fields")
async def get_project_custom_fields(project_gid: str):
    """
    Get custom fields for a specific Asana project.

    Useful for checking if "Figma URL" field exists.
    """
    try:
        token = await get_asana_api_token()
        if not token:
            raise HTTPException(
                status_code=400,
                detail="Asana API token not configured"
            )

        asana_client = AsanaClient(token)
        custom_fields = await asana_client.get_project_custom_fields(project_gid)

        # Find Figma URL field
        figma_field = None
        for field in custom_fields:
            if field.get("name", "").lower() == FIGMA_URL_FIELD_NAME.lower():
                figma_field = field
                break

        return {
            "success": True,
            "project_gid": project_gid,
            "custom_fields": custom_fields,
            "custom_field_count": len(custom_fields),
            "figma_url_field": figma_field,
            "figma_url_configured": bool(figma_field),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting custom fields: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get custom fields: {str(e)}"
        )


@router.post("/test-integration")
async def test_calendar_integration(
    client_id: str,
    db: firestore.Client = Depends(get_db)
):
    """
    Test Asana calendar integration for a specific client.

    Validates configuration and shows what would happen when creating an approval task.
    Does not actually create a task.
    """
    try:
        # Get client data
        client_ref = db.collection("clients").document(client_id)
        client_doc = client_ref.get()

        if not client_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Client {client_id} not found"
            )

        client_data = client_doc.to_dict()
        client_name = client_data.get("name", client_id)
        asana_project_link = client_data.get("asana_project_link")

        # Check prerequisites
        checks = {
            "asana_token_configured": False,
            "client_has_asana_link": bool(asana_project_link),
            "asana_link_parseable": False,
            "account_mgmt_configured": bool(ACCOUNT_MANAGEMENT_PROJECT_GID),
            "figma_field_exists": False,
        }

        issues = []
        project_gid = None

        # Check token
        token = await get_asana_api_token()
        checks["asana_token_configured"] = bool(token)
        if not token:
            issues.append("Asana API token not configured in Secret Manager")
            return {
                "success": False,
                "client_id": client_id,
                "client_name": client_name,
                "checks": checks,
                "issues": issues,
                "message": "Cannot test - Asana token not configured"
            }

        # Check project link
        if not asana_project_link:
            issues.append(f"Client {client_name} does not have asana_project_link configured")
            return {
                "success": False,
                "client_id": client_id,
                "client_name": client_name,
                "checks": checks,
                "issues": issues,
                "message": "Cannot test - no Asana project link"
            }

        # Parse project GID
        asana_client = AsanaClient(token)
        project_gid = asana_client.parse_project_gid_from_url(asana_project_link)
        checks["asana_link_parseable"] = bool(project_gid)

        if not project_gid:
            issues.append(f"Could not parse project GID from URL: {asana_project_link}")
            return {
                "success": False,
                "client_id": client_id,
                "client_name": client_name,
                "checks": checks,
                "issues": issues,
                "message": "Invalid Asana project URL"
            }

        # Check for Figma URL field
        try:
            figma_field = await asana_client.find_custom_field_by_name(project_gid, FIGMA_URL_FIELD_NAME)
            checks["figma_field_exists"] = bool(figma_field)
            if not figma_field:
                issues.append(f"Custom field '{FIGMA_URL_FIELD_NAME}' not found in project")
        except Exception as e:
            issues.append(f"Could not check custom fields: {str(e)}")

        # Check Account Management project
        if not ACCOUNT_MANAGEMENT_PROJECT_GID:
            issues.append("Account Management project GID not configured - task won't be multi-homed")

        # Summary
        will_work = (
            checks["asana_token_configured"] and
            checks["client_has_asana_link"] and
            checks["asana_link_parseable"]
        )

        return {
            "success": True,
            "client_id": client_id,
            "client_name": client_name,
            "asana_project_link": asana_project_link,
            "asana_project_gid": project_gid,
            "checks": checks,
            "issues": issues,
            "will_create_task": will_work,
            "will_be_multihomed": will_work and checks["account_mgmt_configured"],
            "will_set_figma_field": will_work and checks["figma_field_exists"],
            "message": "Integration would work" if will_work else "Integration has issues"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Asana calendar integration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test integration: {str(e)}"
        )


# ============================================================================
# Project Configuration Endpoints (for Configure Projects UI)
# ============================================================================

@router.get("/configuration/clients-and-projects")
async def get_clients_and_projects(db: firestore.Client = Depends(get_db)):
    """
    Get all active clients with their current Asana project mappings.
    Also returns all available Asana projects for selection from ALL workspaces.
    """
    try:
        # Get Asana token
        token = await get_asana_api_token()
        if not token:
            raise HTTPException(
                status_code=400,
                detail="Asana API token not configured in Secret Manager"
            )

        asana_client = AsanaClient(token)

        # Get all workspaces
        workspaces = await asana_client.list_workspaces()
        if not workspaces:
            logger.warning("No workspaces found for current user")
            workspaces = []

        # Get projects from ALL workspaces
        all_projects = []
        for workspace in workspaces:
            workspace_gid = workspace.get("gid")
            workspace_name = workspace.get("name")
            logger.info(f"Fetching projects from workspace: {workspace_name} ({workspace_gid})")

            workspace_projects = await asana_client.list_projects(
                workspace_gid=workspace_gid,
                archived=False  # Only non-archived projects
            )

            # Add workspace info to each project for display
            for project in workspace_projects:
                project["workspace_name"] = workspace_name
                project["workspace_gid"] = workspace_gid

            all_projects.extend(workspace_projects)

        logger.info(f"Found {len(all_projects)} total projects across {len(workspaces)} workspaces")

        # Get all clients from Firestore
        clients_ref = db.collection("clients")
        clients = []

        for client_doc in clients_ref.stream():
            client_data = client_doc.to_dict()
            clients.append({
                "id": client_doc.id,
                "name": client_data.get("name", "Unknown"),
                "client_slug": client_data.get("client_slug", client_doc.id),
                "asana_project_link": client_data.get("asana_project_link"),
                "asana_project_gid": asana_client.parse_project_gid_from_url(client_data.get("asana_project_link", "")) if client_data.get("asana_project_link") else None
            })

        # Sort clients by name
        clients.sort(key=lambda x: x["name"])

        return {
            "success": True,
            "clients": clients,
            "asana_projects": [
                {
                    "gid": p.get("gid"),
                    "name": p.get("name"),
                    "workspace_name": p.get("workspace_name"),
                } for p in all_projects
            ],
            "account_management_project_gid": ACCOUNT_MANAGEMENT_PROJECT_GID,
            "workspace_count": len(workspaces),
            "total_projects": len(all_projects),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clients and projects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get clients and projects: {str(e)}"
        )


class SaveConfigurationRequest(BaseModel):
    """Request to save Asana project configuration"""
    client_mappings: Dict[str, Optional[str]]  # client_id -> project_gid
    account_management_project_gid: Optional[str] = None


@router.post("/configuration/save")
async def save_configuration(
    request: SaveConfigurationRequest,
    db: firestore.Client = Depends(get_db)
):
    """
    Save Asana project configuration:
    - Update client asana_project_link fields in Firestore
    - Update Account Management project GID in environment (requires server restart to take effect)
    """
    try:
        # Get Asana token to validate project GIDs
        token = await get_asana_api_token()
        if not token:
            raise HTTPException(
                status_code=400,
                detail="Asana API token not configured"
            )

        asana_client = AsanaClient(token)
        updated_clients = []
        errors = []

        # Update each client's Asana project link
        for client_id, project_gid in request.client_mappings.items():
            try:
                client_ref = db.collection("clients").document(client_id)
                client_doc = client_ref.get()

                if not client_doc.exists:
                    errors.append(f"Client {client_id} not found")
                    continue

                client_data = client_doc.to_dict()
                client_name = client_data.get("name", client_id)

                if project_gid:
                    # Generate Asana project URL from GID
                    asana_project_link = f"https://app.asana.com/0/{project_gid}/list"

                    # Validate project exists (optional - can be skipped for performance)
                    # try:
                    #     await asana_client.get_project(project_gid)
                    # except Exception:
                    #     errors.append(f"Invalid project GID for {client_name}: {project_gid}")
                    #     continue

                    # Update Firestore
                    client_ref.update({"asana_project_link": asana_project_link})
                    updated_clients.append(client_name)
                    logger.info(f"Updated {client_name} -> project {project_gid}")
                else:
                    # Remove asana_project_link if project_gid is None/empty
                    client_ref.update({"asana_project_link": firestore.DELETE_FIELD})
                    updated_clients.append(f"{client_name} (removed)")
                    logger.info(f"Removed Asana project link for {client_name}")

            except Exception as e:
                logger.error(f"Error updating client {client_id}: {e}")
                errors.append(f"Error updating {client_id}: {str(e)}")

        # Update Account Management project GID in Firestore config
        account_mgmt_message = None
        if request.account_management_project_gid is not None:
            try:
                # Store in Firestore config collection
                config_ref = db.collection("config").document("asana")
                config_ref.set({
                    "account_management_project_gid": request.account_management_project_gid,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)

                account_mgmt_message = f"Account Management project GID updated to {request.account_management_project_gid}"
                logger.info(account_mgmt_message)

            except Exception as e:
                account_mgmt_message = f"Error saving to Firestore: {str(e)}"
                logger.error(account_mgmt_message)
                errors.append(account_mgmt_message)

        return {
            "success": len(errors) == 0,
            "updated_clients": updated_clients,
            "updated_count": len(updated_clients),
            "errors": errors,
            "account_management_message": account_mgmt_message,
            "message": f"Updated {len(updated_clients)} clients" + (f" with {len(errors)} errors" if errors else "")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save configuration: {str(e)}"
        )
