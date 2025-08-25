"""
Klaviyo OAuth Service
Handles OAuth authentication flow, token management, and account metadata retrieval
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OAuthToken(BaseModel):
    """OAuth token data model"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    token_type: str = "Bearer"


class KlaviyoAccount(BaseModel):
    """Klaviyo account data model"""
    id: str
    name: str
    email_domain: Optional[str] = None
    company_id: Optional[str] = None
    contact_email: Optional[str] = None
    lists_count: Optional[int] = None
    segments_count: Optional[int] = None
    profiles_count: Optional[int] = None
    test_account: bool = False
    metadata: Dict[str, Any] = {}


class KlaviyoOAuthService:
    """Service for handling Klaviyo OAuth operations"""
    
    OAUTH_BASE_URL = "https://www.klaviyo.com/oauth"
    API_BASE_URL = "https://a.klaviyo.com/api"
    TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/token"
    AUTHORIZE_ENDPOINT = f"{OAUTH_BASE_URL}/authorize"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None
    ):
        """
        Initialize Klaviyo OAuth service
        
        Args:
            client_id: Klaviyo OAuth client ID
            client_secret: Klaviyo OAuth client secret
            redirect_uri: OAuth callback URL
            scopes: List of required OAuth scopes
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or [
            "accounts:read",
            "campaigns:read",
            "flows:read",
            "lists:read",
            "metrics:read",
            "profiles:read",
            "segments:read"
        ]
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge for enhanced security
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate a code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        # Generate code challenge using SHA256
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(
            challenge_bytes
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def build_auth_url(
        self,
        state: str,
        code_challenge: Optional[str] = None
    ) -> str:
        """
        Build Klaviyo OAuth authorization URL
        
        Args:
            state: CSRF protection state parameter
            code_challenge: PKCE code challenge (optional but recommended)
            
        Returns:
            Authorization URL string
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state
        }
        
        # Add PKCE challenge if provided
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        
        return f"{self.AUTHORIZE_ENDPOINT}?{urlencode(params)}"
    
    async def exchange_code_for_token(
        self,
        code: str,
        code_verifier: Optional[str] = None
    ) -> OAuthToken:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier (if PKCE was used)
            
        Returns:
            OAuthToken object with access token and metadata
            
        Raises:
            Exception: If token exchange fails
        """
        try:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri
            }
            
            # Add PKCE verifier if provided
            if code_verifier:
                data["code_verifier"] = code_verifier
            
            response = await self.http_client.post(
                self.TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                logger.error(f"Token exchange failed: {response.status_code} - {error_data}")
                raise Exception(f"Token exchange failed: {error_data.get('error', 'Unknown error')}")
            
            token_data = response.json()
            
            # Calculate expiration time
            expires_at = None
            if token_data.get("expires_in"):
                expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            
            return OAuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in"),
                expires_at=expires_at,
                scope=token_data.get("scope"),
                token_type=token_data.get("token_type", "Bearer")
            )
            
        except httpx.RequestError as e:
            logger.error(f"Network error during token exchange: {e}")
            raise Exception(f"Network error during token exchange: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            raise
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """
        Refresh an expired access token
        
        Args:
            refresh_token: Refresh token from previous OAuth flow
            
        Returns:
            New OAuthToken object
            
        Raises:
            Exception: If token refresh fails
        """
        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token
            }
            
            response = await self.http_client.post(
                self.TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                logger.error(f"Token refresh failed: {response.status_code} - {error_data}")
                raise Exception(f"Token refresh failed: {error_data.get('error', 'Unknown error')}")
            
            token_data = response.json()
            
            # Calculate expiration time
            expires_at = None
            if token_data.get("expires_in"):
                expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            
            return OAuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                expires_in=token_data.get("expires_in"),
                expires_at=expires_at,
                scope=token_data.get("scope"),
                token_type=token_data.get("token_type", "Bearer")
            )
            
        except httpx.RequestError as e:
            logger.error(f"Network error during token refresh: {e}")
            raise Exception(f"Network error during token refresh: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise
    
    async def get_account_profile(self, access_token: str) -> KlaviyoAccount:
        """
        Fetch Klaviyo account metadata using access token
        
        Args:
            access_token: Valid OAuth access token
            
        Returns:
            KlaviyoAccount object with account details
            
        Raises:
            Exception: If API call fails
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "revision": "2024-10-15"  # Use latest Klaviyo API revision
            }
            
            # Fetch account information
            account_response = await self.http_client.get(
                f"{self.API_BASE_URL}/accounts",
                headers=headers
            )
            
            if account_response.status_code != 200:
                logger.error(f"Failed to fetch account info: {account_response.status_code}")
                raise Exception(f"Failed to fetch account information: {account_response.status_code}")
            
            account_data = account_response.json()
            
            # Extract account information (Klaviyo returns array of accounts)
            if not account_data.get("data"):
                raise Exception("No accounts found for this OAuth token")
            
            # Use the first account (typically there's only one)
            account = account_data["data"][0]
            account_attrs = account.get("attributes", {})
            
            # Optionally fetch additional metadata (lists, segments counts)
            lists_count = None
            segments_count = None
            
            try:
                # Fetch lists count
                lists_response = await self.http_client.get(
                    f"{self.API_BASE_URL}/lists?page[size]=1",
                    headers=headers
                )
                if lists_response.status_code == 200:
                    lists_data = lists_response.json()
                    lists_count = lists_data.get("meta", {}).get("total_count", 0)
            except Exception as e:
                logger.warning(f"Failed to fetch lists count: {e}")
            
            try:
                # Fetch segments count
                segments_response = await self.http_client.get(
                    f"{self.API_BASE_URL}/segments?page[size]=1",
                    headers=headers
                )
                if segments_response.status_code == 200:
                    segments_data = segments_response.json()
                    segments_count = segments_data.get("meta", {}).get("total_count", 0)
            except Exception as e:
                logger.warning(f"Failed to fetch segments count: {e}")
            
            return KlaviyoAccount(
                id=account["id"],
                name=account_attrs.get("account_name", "Unknown Account"),
                email_domain=account_attrs.get("email_domain"),
                company_id=account_attrs.get("company_id"),
                contact_email=account_attrs.get("contact_email"),
                lists_count=lists_count,
                segments_count=segments_count,
                test_account=account_attrs.get("test_account", False),
                metadata={
                    "timezone": account_attrs.get("timezone", "UTC"),
                    "industry": account_attrs.get("industry"),
                    "public_api_key": account_attrs.get("public_api_key"),
                    "locale": account_attrs.get("locale", "en-US"),
                    "preferred_currency": account_attrs.get("preferred_currency", "USD")
                }
            )
            
        except httpx.RequestError as e:
            logger.error(f"Network error fetching account profile: {e}")
            raise Exception(f"Network error fetching account profile: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching account profile: {e}")
            raise
    
    async def validate_token(self, access_token: str) -> bool:
        """
        Validate if an access token is still valid
        
        Args:
            access_token: Access token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "revision": "2024-10-15"
            }
            
            # Try a simple API call to validate token
            response = await self.http_client.get(
                f"{self.API_BASE_URL}/accounts",
                headers=headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client connection"""
        await self.http_client.aclose()