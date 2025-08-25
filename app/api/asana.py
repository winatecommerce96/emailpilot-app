"""
Asana Integration API

Provides basic endpoints to verify connectivity and fetch projects/tasks.
Uses a Personal Access Token stored in Secret Manager (default: `asana-api-token`).

Optional per-client support:
- Store an Asana project link on the client document (`asana_project_link`).
- Future: support per-client `asana_secret_name` for separate PATs.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.asana_client import AsanaClient
from app.services.asana_oauth import AsanaOAuthService
from app.deps import get_secret_manager_service, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/asana", tags=["Asana"])


def _get_asana_token_for_client(client_id: Optional[str] = None) -> str:
    """Resolve Asana token.

    Current strategy:
    - Use global Secret Manager secret `asana-api-token`.
    - Future: if client_id provided, check client doc for `asana_secret_name`.
    """
    sm = get_secret_manager_service()
    # Global PAT
    try:
        token = sm.get_secret("asana-api-token")
        if token:
            return token.strip()
    except Exception as e:
        logger.debug(f"No global Asana token found: {e}")

    # Try client-specific secret name
    if client_id:
        try:
            db = get_db()
            doc = db.collection("clients").document(client_id).get()
            if doc.exists:
                data = doc.to_dict() or {}
                sname = data.get("asana_secret_name")
                if sname:
                    token = sm.get_secret(sname)
                    if token:
                        return token.strip()
        except Exception as e:
            logger.debug(f"Client-specific Asana token resolution failed for {client_id}: {e}")

    raise HTTPException(status_code=400, detail="Asana token not configured in Secret Manager (asana-api-token)")


async def _get_user_token(user_id: str) -> str:
    """Get a valid per-user access token, refreshing if needed."""
    oauth = AsanaOAuthService()
    token = oauth.get_valid_access_token(user_id)
    if token:
        return token
    token = await oauth.refresh_and_get_token(user_id)
    if not token:
        raise HTTPException(status_code=400, detail="User not connected to Asana")
    return token


@router.get("/ping")
async def ping_asana() -> Dict[str, Any]:
    """Verify Asana connectivity by fetching current user."""
    token = _get_asana_token_for_client()
    client = AsanaClient(token)
    me = await client.me()
    user = me.get("data", {})
    return {
        "status": "ok",
        "user": {"gid": user.get("gid"), "name": user.get("name"), "email": user.get("email")},
    }


@router.get("/workspaces")
async def list_workspaces() -> Dict[str, Any]:
    token = _get_asana_token_for_client()
    client = AsanaClient(token)
    workspaces = await client.list_workspaces()
    return {"workspaces": workspaces}


@router.get("/projects")
async def list_projects(workspace_gid: Optional[str] = Query(None)) -> Dict[str, Any]:
    token = _get_asana_token_for_client()
    client = AsanaClient(token)
    projects = await client.list_projects(workspace_gid=workspace_gid)
    return {"projects": projects}


@router.get("/projects/{project_gid}/tasks")
async def list_project_tasks(project_gid: str) -> Dict[str, Any]:
    token = _get_asana_token_for_client()
    client = AsanaClient(token)
    tasks = await client.list_project_tasks(project_gid)
    return {"project_gid": project_gid, "count": len(tasks), "tasks": tasks}


@router.get("/clients/{client_id}/tasks")
async def list_client_asana_tasks(client_id: str) -> Dict[str, Any]:
    """Fetch tasks for the client's configured Asana project link.

    Expects the client document to include `asana_project_link`.
    """
    token = _get_asana_token_for_client(client_id)
    client = AsanaClient(token)

    db = get_db()
    doc = db.collection("clients").document(client_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Client not found")
    data = doc.to_dict() or {}
    link = data.get("asana_project_link")
    if not link:
        raise HTTPException(status_code=400, detail="Client missing asana_project_link")

    project_gid = AsanaClient.parse_project_gid_from_url(link)
    if not project_gid:
        raise HTTPException(status_code=400, detail="Unable to parse project GID from asana_project_link")

    tasks = await client.list_project_tasks(project_gid)
    return {
        "client_id": client_id,
        "project_gid": project_gid,
        "count": len(tasks),
        "tasks": tasks,
    }


@router.post("/users/{user_id}/tasks")
async def create_user_task(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new Asana task in the user’s selected project.

    Expected payload: { name, notes?, due_on?, assignee?, project_gid }
    """
    token = await _get_user_token(user_id)
    client = AsanaClient(token)
    name = payload.get("name")
    project_gid = payload.get("project_gid")
    notes = payload.get("notes")
    due_on = payload.get("due_on")
    assignee = payload.get("assignee")
    custom_fields = payload.get("custom_fields")
    task = await client.create_task(name=name, project_gid=project_gid, notes=notes, due_on=due_on, assignee=assignee, custom_fields=custom_fields)

    # Mirror to Firestore under users/{user_id}/asana/tasks
    db = get_db()
    tdata = task.get("data", {})
    gid = tdata.get("gid")
    if gid:
        db.collection("users").document(user_id).collection("asana").document("data").collection("tasks").document(gid).set({
            "task": tdata,
            "project_gid": project_gid,
            "created_at": tdata.get("created_at"),
            "source": "emailpilot",
        }, merge=True)
    return {"status": "created", "task": tdata}


@router.get("/users/{user_id}/tasks/sync")
async def sync_user_tasks(user_id: str, project_gid: str) -> Dict[str, Any]:
    """Fetch tasks from Asana for the user’s project and store in Firestore.
    Returns number of tasks synced.
    """
    token = await _get_user_token(user_id)
    client = AsanaClient(token)
    tasks = await client.list_project_tasks(project_gid)
    db = get_db()
    base = db.collection("users").document(user_id).collection("asana").document("data").collection("tasks")
    count = 0
    for t in tasks:
        gid = t.get("gid") or (t.get("data") or {}).get("gid")
        if not gid:
            continue
        base.document(gid).set({
            "task": t,
            "project_gid": project_gid,
            "synced_at": None,
            "source": "asana",
        }, merge=True)
        count += 1
    return {"user_id": user_id, "project_gid": project_gid, "synced": count}


@router.get("/users/{user_id}/allowed-projects")
async def get_allowed_projects(user_id: str) -> Dict[str, Any]:
    """Return user’s account management project, client mapping, and available projects list."""
    db = get_db()
    oauth = AsanaOAuthService()
    token = oauth.get_valid_access_token(user_id) or await oauth.refresh_and_get_token(user_id)
    if not token:
        raise HTTPException(status_code=400, detail="User not connected to Asana")
    client = AsanaClient(token)

    # Fetch workspaces and projects
    workspaces = await client.list_workspaces()
    projects: list[Dict[str, Any]] = []
    for ws in workspaces:
        ws_gid = ws.get("gid")
        try:
            ws_projects = await client.list_projects(workspace_gid=ws_gid)
            for p in ws_projects:
                projects.append({
                    "workspace_gid": ws_gid,
                    "workspace_name": ws.get("name"),
                    "project_gid": p.get("gid"),
                    "project_name": p.get("name"),
                })
        except Exception:
            continue

    # Load current selection
    asana_ref = db.collection("users").document(user_id).collection("integrations").document("asana")
    doc = asana_ref.get()
    data = doc.to_dict() if doc.exists else {}
    return {
        "account_management_project_gid": data.get("account_management_project_gid"),
        "client_project_map": data.get("client_project_map", {}),
        "projects": projects,
    }


@router.post("/users/{user_id}/allowed-projects")
async def set_allowed_projects(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Set user’s account management project and per-client project mapping.

    Body can include:
    - account_management_project_gid: str
    - client_project_map: { [client_id]: project_gid }
    """
    db = get_db()
    updates: Dict[str, Any] = {}
    if "account_management_project_gid" in payload:
        updates["account_management_project_gid"] = payload.get("account_management_project_gid")
    if "client_project_map" in payload and isinstance(payload.get("client_project_map"), dict):
        updates["client_project_map"] = payload["client_project_map"]
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    db.collection("users").document(user_id).collection("integrations").document("asana").set(updates, merge=True)
    return {"updated": list(updates.keys())}


@router.get("/users/{user_id}/allowed-projects/supporting/clients")
async def list_active_clients_for_mapping(user_id: str) -> Dict[str, Any]:
    """List active clients for mapping UI convenience."""
    db = get_db()
    docs = list(db.collection("clients").where("is_active", "==", True).stream())
    clients = []
    for d in docs:
        if not d.exists:
            continue
        data = d.to_dict() or {}
        clients.append({"id": d.id, "name": data.get("name")})
    clients.sort(key=lambda c: c.get("name") or "")
    return {"clients": clients}


@router.post("/users/{user_id}/webhooks")
async def create_user_webhook(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create an Asana webhook for a project to receive bi-directional updates.

    Body: { project_gid, target_url }
    The target_url should include the user_id, e.g., http://host/api/asana/webhooks/callback/{user_id}
    """
    project_gid = payload.get("project_gid")
    target_url = payload.get("target_url")
    if not project_gid or not target_url:
        raise HTTPException(status_code=400, detail="project_gid and target_url are required")
    oauth = AsanaOAuthService()
    token = oauth.get_valid_access_token(user_id) or await oauth.refresh_and_get_token(user_id)
    if not token:
        raise HTTPException(status_code=400, detail="User not connected to Asana")
    client = AsanaClient(token)
    webhook = await client.create_webhook(resource_gid=project_gid, target_url=target_url)
    # Store webhook
    db = get_db()
    wdata = webhook.get("data", {})
    gid = wdata.get("gid")
    if gid:
        db.collection("users").document(user_id).collection("asana").document("webhooks").collection("projects").document(gid).set({
            "webhook": wdata,
            "project_gid": project_gid,
            "target_url": target_url,
        }, merge=True)
    return {"webhook": wdata}


@router.delete("/users/{user_id}/webhooks/{webhook_gid}")
async def delete_user_webhook(user_id: str, webhook_gid: str) -> Dict[str, Any]:
    oauth = AsanaOAuthService()
    token = oauth.get_valid_access_token(user_id) or await oauth.refresh_and_get_token(user_id)
    if not token:
        raise HTTPException(status_code=400, detail="User not connected to Asana")
    client = AsanaClient(token)
    await client.delete_webhook(webhook_gid)
    db = get_db()
    db.collection("users").document(user_id).collection("asana").document("webhooks").collection("projects").document(webhook_gid).delete()
    return {"deleted": webhook_gid}


from fastapi import Response, Request

@router.post("/webhooks/callback/{user_id}")
async def asana_webhook_callback(user_id: str, request: Request, response: Response) -> Dict[str, Any]:
    """Handle Asana webhook handshake and events for a specific user.

    Handshake: respond with X-Hook-Secret header received from Asana.
    Events: store in Firestore under users/{user_id}/asana/inbox/events.
    """
    # Handshake header
    hook_secret = request.headers.get("X-Hook-Secret")
    if hook_secret:
        response.headers["X-Hook-Secret"] = hook_secret
    try:
        body = await request.json()
    except Exception:
        body = {}
    # Persist events if present
    events = body.get("events") or []
    if events:
        db = get_db()
        inbox = db.collection("users").document(user_id).collection("asana").document("inbox").collection("events")
        for ev in events:
            gid = ev.get("gid") or ev.get("resource", {}).get("gid") or ev.get("created_at")
            if not gid:
                continue
            inbox.document(str(gid)).set({"event": ev}, merge=True)
    return {"received": len(events)}
