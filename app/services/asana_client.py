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
    - Uses Bearer token from Secret Manager (typically stored as `asana-api-token`).
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
    ) -> Dict[str, Any]:
        """Create an Asana task in the specified project."""
        if not name or not project_gid:
            raise ValueError("Task name and project_gid are required")
        payload = {
            "data": {
                "name": name,
                "projects": [project_gid],
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
