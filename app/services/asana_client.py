from __future__ import annotations
from typing import Any, Dict, List, Optional
import re
import logging
import httpx

logger = logging.getLogger(__name__)

ASANA_API_URL = "https://app.asana.com/api/1.0"


class AsanaClient:
    """Lightweight Asana API client using PAT (Personal Access Token).

    Notes:
    - Uses Bearer token from Secret Manager (stored as `asana-access-token`).
    - Minimal helpers for common list operations with pagination.
    """

    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("Asana access token is required")
        self.access_token = access_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = path if path.startswith("http") else f"{ASANA_API_URL}{path}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=8.0)) as client:
            r = await client.get(url, headers=self._headers(), params=params or {})
            if r.status_code >= 400:
                detail = r.text
                logger.error(f"Asana GET {url} failed {r.status_code}: {detail}")
                r.raise_for_status()
            return r.json()

    async def _post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = path if path.startswith("http") else f"{ASANA_API_URL}{path}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=8.0)) as client:
            r = await client.post(url, headers=self._headers(), json=json or {})
            if r.status_code >= 400:
                detail = r.text
                logger.error(f"Asana POST {url} failed {r.status_code}: {detail}")
                r.raise_for_status()
            return r.json()

    @staticmethod
    def parse_project_gid_from_url(url: str) -> Optional[str]:
        """Extract Asana project GID from a project URL.

        Examples:
        - https://app.asana.com/0/123456789012345/board
        - https://app.asana.com/0/123456789012345/list
        - https://app.asana.com/0/123456789012345
        - https://app.asana.com/0/project/123456789012345
        """
        if not url:
            return None
        # Common patterns: /0/<gid> or /project/<gid>
        m = re.search(r"/(?:project/)?(\d{5,})", url)
        if m:
            return m.group(1)
        # Fallback: split by '/' and find the first 12+ digit token
        tokens = re.split(r"[/#?]", url)
        for t in tokens:
            if t.isdigit() and len(t) >= 10:
                return t
        return None

    async def me(self) -> Dict[str, Any]:
        return await self._get("/users/me")

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        data = await self._get("/workspaces")
        return data.get("data", [])

    async def list_projects(self, workspace_gid: Optional[str] = None, archived: Optional[bool] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if workspace_gid:
            params["workspace"] = workspace_gid
        if archived is not None:
            params["archived"] = str(bool(archived)).lower()

        # Asana pagination via "next_page": {"offset": ...}
        projects: List[Dict[str, Any]] = []
        next_offset: Optional[str] = None
        while True:
            if next_offset:
                params["offset"] = next_offset
            page = await self._get("/projects", params=params)
            items = page.get("data", [])
            projects.extend(items)
            next_page = page.get("next_page") or {}
            next_offset = next_page.get("offset")
            if not next_offset:
                break
        return projects

    async def list_project_tasks(
        self,
        project_gid: str,
        completed_since: Optional[str] = None,
        opt_fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not project_gid:
            return []
        params: Dict[str, Any] = {}
        if completed_since is not None:
            params["completed_since"] = completed_since
        if opt_fields:
            params["opt_fields"] = opt_fields
        else:
            params["opt_fields"] = "name,completed,assignee,assignee.name,assignee.email,due_on,permalink_url,modified_at"

        tasks: List[Dict[str, Any]] = []
        next_offset: Optional[str] = None
        while True:
            if next_offset:
                params["offset"] = next_offset
            page = await self._get(f"/projects/{project_gid}/tasks", params=params)
            items = page.get("data", [])
            tasks.extend(items)
            next_page = page.get("next_page") or {}
            next_offset = next_page.get("offset")
            if not next_offset:
                break
        return tasks

    async def create_task(
        self,
        name: str,
        project_gid: str,
        notes: Optional[str] = None,
        due_on: Optional[str] = None,
        assignee: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        projects: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create an Asana task in the specified project.

        Args:
            name: Task name
            project_gid: Primary project GID (for backwards compatibility)
            notes: Task description
            due_on: Due date (YYYY-MM-DD format)
            assignee: Assignee GID
            custom_fields: Custom field values (dict of field_gid: value)
            projects: List of project GIDs to multi-home the task (overrides project_gid if provided)
        """
        if not name or not project_gid:
            raise ValueError("Task name and project_gid are required")

        # Use projects list if provided, otherwise use single project_gid
        project_list = projects if projects else [project_gid]

        payload = {
            "data": {
                "name": name,
                "projects": project_list,
            }
        }
        if notes:
            payload["data"]["notes"] = notes
        if due_on:
            payload["data"]["due_on"] = due_on
        if assignee:
            payload["data"]["assignee"] = assignee
        if custom_fields:
            payload["data"]["custom_fields"] = custom_fields
        return await self._post("/tasks", json=payload)

    async def create_webhook(self, resource_gid: str, target_url: str) -> Dict[str, Any]:
        if not resource_gid or not target_url:
            raise ValueError("resource_gid and target_url are required to create webhook")
        payload = {"data": {"resource": resource_gid, "target": target_url}}
        return await self._post("/webhooks", json=payload)

    async def delete_webhook(self, webhook_gid: str) -> Dict[str, Any]:
        if not webhook_gid:
            raise ValueError("webhook_gid is required")
        url = f"{ASANA_API_URL}/webhooks/{webhook_gid}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=8.0)) as client:
            r = await client.delete(url, headers=self._headers())
            if r.status_code >= 400:
                logger.error(f"Asana DELETE {url} failed {r.status_code}: {r.text}")
                r.raise_for_status()
            return {"ok": True}

    async def get_task(self, task_gid: str, opt_fields: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if opt_fields:
            params["opt_fields"] = opt_fields
        return await self._get(f"/tasks/{task_gid}", params=params)

    async def get_project_custom_fields(self, project_gid: str) -> List[Dict[str, Any]]:
        """Get custom fields for a project.

        Returns list of custom field objects with 'gid', 'name', 'type', etc.
        """
        if not project_gid:
            raise ValueError("project_gid is required")

        data = await self._get(f"/projects/{project_gid}", params={"opt_fields": "custom_field_settings.custom_field"})
        custom_field_settings = data.get("data", {}).get("custom_field_settings", [])

        return [setting.get("custom_field", {}) for setting in custom_field_settings]

    async def find_custom_field_by_name(self, project_gid: str, field_name: str) -> Optional[Dict[str, Any]]:
        """Find a custom field in a project by name (case-insensitive).

        Returns the custom field object if found, None otherwise.
        """
        custom_fields = await self.get_project_custom_fields(project_gid)

        for field in custom_fields:
            if field.get("name", "").lower() == field_name.lower():
                return field

        return None

    async def get_project(self, project_gid: str, opt_fields: Optional[str] = None) -> Dict[str, Any]:
        """Get project details.

        Args:
            project_gid: Project GID
            opt_fields: Optional fields to include in response
        """
        if not project_gid:
            raise ValueError("project_gid is required")

        params: Dict[str, Any] = {}
        if opt_fields:
            params["opt_fields"] = opt_fields

        return await self._get(f"/projects/{project_gid}", params=params)

    async def get_workspace_projects(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all projects in a workspace.

        Args:
            workspace_gid: Workspace GID (optional, will fetch from /me if not provided)

        Returns:
            List of project objects
        """
        # If no workspace GID provided, get it from /me
        if not workspace_gid:
            me = await self.me()
            workspaces = me.get("data", {}).get("workspaces", [])
            if not workspaces:
                logger.warning("No workspaces found for current user")
                return []
            workspace_gid = workspaces[0].get("gid")
            logger.info(f"Using workspace {workspace_gid}")

        # Get all projects with pagination
        projects: List[Dict[str, Any]] = []
        next_offset: Optional[str] = None
        params: Dict[str, Any] = {
            "workspace": workspace_gid,
            "opt_fields": "gid,name,archived"
        }

        while True:
            if next_offset:
                params["offset"] = next_offset
            page = await self._get("/projects", params=params)
            items = page.get("data", [])
            projects.extend(items)
            next_page = page.get("next_page") or {}
            next_offset = next_page.get("offset")
            if not next_offset:
                break

        logger.info(f"Found {len(projects)} projects in workspace")
        return projects

    async def get_project_sections(self, project_gid: str) -> List[Dict[str, Any]]:
        """Get all sections for a project.

        Args:
            project_gid: Project GID

        Returns:
            List of section objects with 'gid' and 'name'
        """
        if not project_gid:
            raise ValueError("project_gid is required")

        data = await self._get(f"/projects/{project_gid}/sections")
        sections = data.get("data", [])

        logger.info(f"Found {len(sections)} sections in project {project_gid}")
        return sections
