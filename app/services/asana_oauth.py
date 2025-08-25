from __future__ import annotations
import logging
from typing import Dict, Optional
import time
import urllib.parse
import httpx

from app.deps import get_secret_manager_service, get_db

logger = logging.getLogger(__name__)

ASANA_AUTH_URL = "https://app.asana.com/-/oauth_authorize"
ASANA_TOKEN_URL = "https://app.asana.com/-/oauth_token"


class AsanaOAuthService:
    """Handles Asana OAuth authorization code flow and token refresh.

    Stores app client credentials in Secret Manager:
    - asana-oauth-client-id
    - asana-oauth-client-secret

    Stores per-user tokens in Firestore under:
    users/{user_id}/integrations/asana
    { access_token, refresh_token, expires_at, workspace_gid?, default_project_gid? }
    """

    def __init__(self):
        self.sm = get_secret_manager_service()
        self.db = get_db()

    def get_client_credentials(self) -> Dict[str, str]:
        client_id = self.sm.get_secret("asana-oauth-client-id")
        client_secret = self.sm.get_secret("asana-oauth-client-secret")
        if not client_id or not client_secret:
            raise RuntimeError("Asana OAuth client credentials not configured in Secret Manager")
        return {"client_id": client_id.strip(), "client_secret": client_secret.strip()}

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        creds = self.get_client_credentials()
        params = {
            "client_id": creds["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "default",
            "state": state,
        }
        return f"{ASANA_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, str]:
        creds = self.get_client_credentials()
        data = {
            "grant_type": "authorization_code",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "redirect_uri": redirect_uri,
            "code": code,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            r = await client.post(ASANA_TOKEN_URL, data=data)
            r.raise_for_status()
            return r.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        creds = self.get_client_credentials()
        data = {
            "grant_type": "refresh_token",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            r = await client.post(ASANA_TOKEN_URL, data=data)
            r.raise_for_status()
            return r.json()

    def _user_integration_ref(self, user_id: str):
        return (
            self.db.collection("users")
            .document(user_id)
            .collection("integrations")
            .document("asana")
        )

    def store_tokens(self, user_id: str, token_data: Dict[str, str]) -> None:
        """Persist tokens for a user in Firestore."""
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")  # seconds
        token_type = token_data.get("token_type")

        expires_at = int(time.time()) + int(expires_in or 3600)
        doc = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at,
            "updated_at": int(time.time()),
        }
        self._user_integration_ref(user_id).set(doc, merge=True)

    def get_valid_access_token(self, user_id: str) -> Optional[str]:
        doc = self._user_integration_ref(user_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_at = int(data.get("expires_at") or 0)
        now = int(time.time())
        if access_token and now < (expires_at - 60):  # small buffer
            return access_token
        if refresh_token:
            # We cannot await in sync function; caller should use refresh_and_get_token
            return None
        return None

    async def refresh_and_get_token(self, user_id: str) -> Optional[str]:
        doc = self._user_integration_ref(user_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            return None
        tokens = await self.refresh_access_token(refresh_token)
        self.store_tokens(user_id, tokens)
        return tokens.get("access_token")

