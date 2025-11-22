"""
Klaviyo Account Discovery Service

Discovers Klaviyo accounts that a user has access to via their OAuth token
and stores them in Firestore for client linking.
"""

import httpx
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.secret_manager import SecretManagerService, SecretNotFoundError
from app.services.firestore import build_firestore_client
from google.cloud import firestore

logger = logging.getLogger(__name__)

KLAVIYO_API_URL = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2024-07-15"  # Updated to latest revision for accounts endpoint

class KlaviyoDiscoveryService:
    """Service for discovering Klaviyo accounts using OAuth tokens"""
    
    def __init__(self, project_id: str, secret_manager: SecretManagerService = None):
        self.project_id = project_id
        self.secret_manager = secret_manager or SecretManagerService(project_id)
        self.firestore_client = None
        
    def _get_firestore_client(self) -> firestore.Client:
        """Get or create Firestore client"""
        if not self.firestore_client:
            self.firestore_client = build_firestore_client(self.project_id)
        return self.firestore_client
    
    def _get_oauth_token(self, user_email: str) -> str:
        """Get OAuth token for user from Secret Manager"""
        import json
        
        try:
            # Try the format used by the OAuth callback
            secret_name = f"oauth-klaviyo-{user_email.replace('@', '-').replace('.', '-')}"
            token_json = self.secret_manager.get_secret(secret_name)
            
            if token_json:
                # Parse the JSON to get the access token
                token_data = json.loads(token_json)
                access_token = token_data.get("access_token")
                if access_token:
                    return access_token
                else:
                    raise ValueError("No access_token in stored OAuth data")
            else:
                raise ValueError(f"No Klaviyo OAuth token found for user {user_email}")
                
        except SecretNotFoundError:
            raise ValueError(f"No Klaviyo OAuth token found for user {user_email}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OAuth token JSON for {user_email}: {e}")
            raise ValueError(f"Invalid OAuth token format")
        except Exception as e:
            logger.error(f"Failed to get OAuth token for {user_email}: {e}")
            raise ValueError(f"Failed to get OAuth token: {str(e)}")
    
    async def _call_klaviyo_api(self, oauth_token: str, endpoint: str, retry_count: int = 3) -> Dict[str, Any]:
        """Make authenticated API call to Klaviyo with retry logic for rate limits"""
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "accept": "application/json",
            "revision": KLAVIYO_REVISION,
        }
        
        url = f"{KLAVIYO_API_URL}{endpoint}"
        
        for attempt in range(retry_count):
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
                try:
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 429:
                        # Rate limited - wait and retry
                        retry_after = 1  # Default to 1 second
                        
                        # Try to get retry-after from response
                        try:
                            error_data = response.json()
                            if error_data.get("errors"):
                                detail = error_data["errors"][0].get("detail", "")
                                # Extract seconds from "Expected available in X second(s)"
                                import re
                                match = re.search(r'in (\d+) second', detail)
                                if match:
                                    retry_after = int(match.group(1))
                        except:
                            pass
                        
                        if attempt < retry_count - 1:
                            logger.info(f"Rate limited, waiting {retry_after} seconds before retry...")
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise ValueError(f"Rate limited after {retry_count} attempts")
                    
                    elif response.status_code == 401:
                        raise ValueError("Invalid or expired OAuth token")
                    elif response.status_code == 403:
                        raise ValueError("Insufficient permissions to access Klaviyo accounts")
                    elif response.status_code >= 400:
                        logger.error(f"Klaviyo API error {response.status_code}: {response.text}")
                        response.raise_for_status()
                    
                    return response.json()
                    
                except httpx.RequestError as e:
                    logger.error(f"Network error calling Klaviyo API: {e}")
                    raise ValueError(f"Network error: {str(e)}")
    
    async def discover_accounts(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Discover Klaviyo accounts the user has access to
        
        Args:
            user_email: Email of the authenticated user
            
        Returns:
            List of account dictionaries with id, name, and other details
        """
        try:
            # Get OAuth token for user
            oauth_token = self._get_oauth_token(user_email)
            
            # Call Klaviyo accounts API
            accounts_data = await self._call_klaviyo_api(oauth_token, "/accounts/")
            
            # Extract account information
            accounts = []
            for account_data in accounts_data.get("data", []):
                account_id = account_data.get("id")
                attributes = account_data.get("attributes", {})
                
                account_info = {
                    "id": account_id,
                    "name": attributes.get("name", f"Account {account_id}"),
                    "email": attributes.get("contact_information", {}).get("default_sender_email"),
                    "website": attributes.get("contact_information", {}).get("organization_website"),
                    "timezone": attributes.get("timezone"),
                    "currency": attributes.get("currency"),
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "discovered_by": user_email
                }
                
                # Remove None values
                account_info = {k: v for k, v in account_info.items() if v is not None}
                accounts.append(account_info)
            
            logger.info(f"Discovered {len(accounts)} Klaviyo accounts for {user_email}")
            return accounts
            
        except Exception as e:
            logger.error(f"Failed to discover accounts for {user_email}: {e}")
            raise
    
    def store_discovered_accounts(self, user_email: str, accounts: List[Dict[str, Any]]) -> None:
        """
        Store discovered accounts in Firestore
        
        Args:
            user_email: Email of the user who discovered the accounts
            accounts: List of account dictionaries
        """
        try:
            db = self._get_firestore_client()
            
            # Store in user-specific collection
            user_accounts_ref = db.collection("klaviyo_discovered_accounts").document(user_email)
            
            # Update document with discovered accounts
            account_data = {
                "user_email": user_email,
                "accounts": accounts,
                "last_discovery": datetime.now(timezone.utc),
                "total_accounts": len(accounts)
            }
            
            user_accounts_ref.set(account_data)
            
            logger.info(f"Stored {len(accounts)} discovered accounts for {user_email}")
            
        except Exception as e:
            logger.error(f"Failed to store discovered accounts for {user_email}: {e}")
            raise ValueError(f"Failed to store accounts: {str(e)}")
    
    def get_discovered_accounts(self, user_email: str) -> Dict[str, Any]:
        """
        Get discovered accounts for a user with their linking status
        
        Args:
            user_email: Email of the user
            
        Returns:
            Dictionary with accounts and their link status
        """
        try:
            db = self._get_firestore_client()
            
            # Get discovered accounts
            user_accounts_ref = db.collection("klaviyo_discovered_accounts").document(user_email)
            doc = user_accounts_ref.get()
            
            if not doc.exists:
                return {
                    "user_email": user_email,
                    "accounts": [],
                    "total_accounts": 0,
                    "last_discovery": None
                }
            
            discovered_data = doc.to_dict()
            accounts = discovered_data.get("accounts", [])
            
            # Check linking status for each account
            clients_ref = db.collection("clients")
            linked_accounts = set()
            
            # Get all clients to check which accounts are already linked
            for client_doc in clients_ref.stream():
                client_data = client_doc.to_dict()
                # Check both old and new field names for backward compatibility
                klaviyo_account_id = client_data.get("klaviyo_oauth_account_id") or client_data.get("klaviyo_account_id")
                if klaviyo_account_id:
                    linked_accounts.add(klaviyo_account_id)
            
            # Add link status to each account
            for account in accounts:
                account["is_linked"] = account["id"] in linked_accounts
                
                # Find client name if linked
                if account["is_linked"]:
                    for client_doc in clients_ref.stream():
                        client_data = client_doc.to_dict()
                        # Check both old and new field names for backward compatibility
                        client_account_id = client_data.get("klaviyo_oauth_account_id") or client_data.get("klaviyo_account_id")
                        if client_account_id == account["id"]:
                            account["linked_client_name"] = client_data.get("name")
                            account["linked_client_id"] = client_doc.id
                            break
            
            discovered_data["accounts"] = accounts
            return discovered_data
            
        except Exception as e:
            logger.error(f"Failed to get discovered accounts for {user_email}: {e}")
            raise ValueError(f"Failed to get accounts: {str(e)}")
    
    async def discover_and_store_accounts(self, user_email: str) -> Dict[str, Any]:
        """
        Discover accounts and store them in one operation
        
        Args:
            user_email: Email of the authenticated user
            
        Returns:
            Dictionary with discovery results
        """
        try:
            # Discover accounts
            accounts = await self.discover_accounts(user_email)
            
            # Store discovered accounts
            self.store_discovered_accounts(user_email, accounts)
            
            # Get accounts with link status
            result = self.get_discovered_accounts(user_email)
            
            logger.info(f"Successfully discovered and stored {len(accounts)} accounts for {user_email}")
            
            return {
                "success": True,
                "message": f"Discovered {len(accounts)} Klaviyo accounts",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Failed to discover and store accounts for {user_email}: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }