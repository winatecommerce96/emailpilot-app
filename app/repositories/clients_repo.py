"""
Client Repository
Manages client data in Firestore with OAuth integration support
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import firestore

from app.services.klaviyo_oauth_service import KlaviyoAccount, OAuthToken

logger = logging.getLogger(__name__)


class Client:
    """Client data model"""
    
    def __init__(self, **kwargs):
        self.client_id = kwargs.get("client_id") or str(uuid.uuid4())
        self.created_at = kwargs.get("created_at") or datetime.utcnow()
        self.updated_at = kwargs.get("updated_at") or datetime.utcnow()
        self.owner_user_id = kwargs.get("owner_user_id")
        self.source = kwargs.get("source", "klaviyo")
        self.display_name = kwargs.get("display_name", "")
        self.status = kwargs.get("status", "active")
        self.tags = kwargs.get("tags", [])
        
        # Klaviyo-specific data
        self.klaviyo = kwargs.get("klaviyo", {})
        
        # OAuth data
        self.oauth = kwargs.get("oauth", {})
        
        # Additional fields for compatibility with existing admin UI
        self.name = self.display_name  # Alias for compatibility
        self.description = kwargs.get("description", "")
        self.is_active = self.status == "active"
        self.contact_email = kwargs.get("contact_email", "")
        self.contact_name = kwargs.get("contact_name", "")
        self.website = kwargs.get("website", "")
        self.metric_id = kwargs.get("metric_id", "")
        self.klaviyo_api_key = kwargs.get("klaviyo_api_key", "")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert client to dictionary for Firestore"""
        return {
            "client_id": self.client_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "owner_user_id": self.owner_user_id,
            "source": self.source,
            "display_name": self.display_name,
            "status": self.status,
            "tags": self.tags,
            "klaviyo": self.klaviyo,
            "oauth": self.oauth,
            # Compatibility fields
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "website": self.website,
            "metric_id": self.metric_id,
            "klaviyo_api_key": self.klaviyo_api_key
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Client":
        """Create client from Firestore document"""
        return cls(**data)


class ClientsRepository:
    """Repository for managing clients in Firestore"""
    
    def __init__(self, db: firestore.Client):
        """
        Initialize repository
        
        Args:
            db: Firestore client instance
        """
        self.db = db
        self.collection = "clients"
    
    async def find_by_owner_and_klaviyo_account(
        self,
        user_id: str,
        account_id: str
    ) -> Optional[Client]:
        """
        Find client by owner and Klaviyo account ID
        
        Args:
            user_id: Owner user ID
            account_id: Klaviyo account ID
            
        Returns:
            Client if found, None otherwise
        """
        try:
            # Query for matching client
            query = (
                self.db.collection(self.collection)
                .where("owner_user_id", "==", user_id)
                .where("klaviyo.account_id", "==", account_id)
                .limit(1)
            )
            
            docs = query.stream()
            for doc in docs:
                return Client.from_dict(doc.to_dict())
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding client: {e}")
            return None
    
    async def upsert_client_from_klaviyo(
        self,
        user_id: str,
        account: KlaviyoAccount,
        token: OAuthToken,
        encrypted_tokens: Dict[str, str]
    ) -> Client:
        """
        Create or update client from Klaviyo OAuth data
        
        Args:
            user_id: Owner user ID
            account: Klaviyo account information
            token: OAuth token data
            encrypted_tokens: Encrypted access and refresh tokens
            
        Returns:
            Created or updated Client
        """
        try:
            # Check if client already exists
            existing_client = await self.find_by_owner_and_klaviyo_account(
                user_id,
                account.id
            )
            
            if existing_client:
                # Update existing client
                client_id = existing_client.client_id
                
                # Update client data
                update_data = {
                    "updated_at": datetime.utcnow(),
                    "display_name": account.name,
                    "status": "active",
                    "klaviyo": {
                        "account_id": account.id,
                        "account_name": account.name,
                        "email_domain": account.email_domain,
                        "company_id": account.company_id,
                        "contact_email": account.contact_email,
                        "lists_count": account.lists_count,
                        "segments_count": account.segments_count,
                        "test_account": account.test_account,
                        "metadata": account.metadata
                    },
                    "oauth": {
                        "provider": "klaviyo",
                        "access_token": encrypted_tokens["access_token"],
                        "refresh_token": encrypted_tokens.get("refresh_token"),
                        "expires_at": token.expires_at,
                        "scopes": token.scope.split(" ") if token.scope else [],
                        "last_refreshed": datetime.utcnow()
                    },
                    # Update compatibility fields
                    "name": account.name,
                    "contact_email": account.contact_email or "",
                    "is_active": True
                }
                
                # Preserve existing tags but ensure "oauth" is included
                if "oauth" not in existing_client.tags:
                    update_data["tags"] = existing_client.tags + ["oauth"]
                
                # Update in Firestore
                self.db.collection(self.collection).document(client_id).update(update_data)
                
                logger.info(f"Updated client {client_id} for user {user_id}")
                
                # Return updated client
                updated_doc = self.db.collection(self.collection).document(client_id).get()
                return Client.from_dict(updated_doc.to_dict())
                
            else:
                # Create new client
                client_id = str(uuid.uuid4())
                
                client_data = {
                    "client_id": client_id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "owner_user_id": user_id,
                    "source": "klaviyo",
                    "display_name": account.name,
                    "status": "active",
                    "tags": ["new", "oauth"],
                    "klaviyo": {
                        "account_id": account.id,
                        "account_name": account.name,
                        "email_domain": account.email_domain,
                        "company_id": account.company_id,
                        "contact_email": account.contact_email,
                        "lists_count": account.lists_count,
                        "segments_count": account.segments_count,
                        "test_account": account.test_account,
                        "metadata": account.metadata
                    },
                    "oauth": {
                        "provider": "klaviyo",
                        "access_token": encrypted_tokens["access_token"],
                        "refresh_token": encrypted_tokens.get("refresh_token"),
                        "expires_at": token.expires_at,
                        "scopes": token.scope.split(" ") if token.scope else [],
                        "connected_at": datetime.utcnow()
                    },
                    # Compatibility fields for existing admin UI
                    "name": account.name,
                    "description": f"Auto-created from Klaviyo OAuth for account {account.id}",
                    "is_active": True,
                    "contact_email": account.contact_email or "",
                    "contact_name": "",
                    "website": "",
                    "metric_id": "",
                    "klaviyo_api_key": "",  # OAuth tokens are used instead
                    # Brand Manager fields
                    "client_voice": "",
                    "client_background": "",
                    # Project Management
                    "asana_project_link": "",
                    # Affinity Segments
                    "affinity_segment_1_name": "",
                    "affinity_segment_1_definition": "",
                    "affinity_segment_2_name": "",
                    "affinity_segment_2_definition": "",
                    "affinity_segment_3_name": "",
                    "affinity_segment_3_definition": "",
                    # Growth
                    "key_growth_objective": "subscriptions",
                    "timezone": account.metadata.get("timezone", "UTC")
                }
                
                # Create in Firestore
                self.db.collection(self.collection).document(client_id).set(client_data)
                
                logger.info(f"Created new client {client_id} for user {user_id}")
                
                return Client.from_dict(client_data)
                
        except Exception as e:
            logger.error(f"Error upserting client: {e}")
            raise
    
    async def get_client(self, client_id: str) -> Optional[Client]:
        """
        Get client by ID
        
        Args:
            client_id: Client ID
            
        Returns:
            Client if found, None otherwise
        """
        try:
            doc = self.db.collection(self.collection).document(client_id).get()
            if doc.exists:
                return Client.from_dict(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting client {client_id}: {e}")
            return None
    
    async def list_clients(
        self,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Client]:
        """
        List clients with optional filters
        
        Args:
            user_id: Filter by owner user ID
            source: Filter by source (e.g., "klaviyo")
            status: Filter by status (e.g., "active")
            limit: Maximum number of results
            
        Returns:
            List of clients
        """
        try:
            query = self.db.collection(self.collection)
            
            if user_id:
                query = query.where("owner_user_id", "==", user_id)
            if source:
                query = query.where("source", "==", source)
            if status:
                query = query.where("status", "==", status)
            
            query = query.limit(limit)
            
            clients = []
            for doc in query.stream():
                clients.append(Client.from_dict(doc.to_dict()))
            
            return clients
            
        except Exception as e:
            logger.error(f"Error listing clients: {e}")
            return []
    
    async def update_oauth_tokens(
        self,
        client_id: str,
        encrypted_tokens: Dict[str, str],
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Update OAuth tokens for a client
        
        Args:
            client_id: Client ID
            encrypted_tokens: New encrypted tokens
            expires_at: Token expiration time
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "updated_at": datetime.utcnow(),
                "oauth.access_token": encrypted_tokens["access_token"],
                "oauth.last_refreshed": datetime.utcnow()
            }
            
            if encrypted_tokens.get("refresh_token"):
                update_data["oauth.refresh_token"] = encrypted_tokens["refresh_token"]
            
            if expires_at:
                update_data["oauth.expires_at"] = expires_at
            
            self.db.collection(self.collection).document(client_id).update(update_data)
            
            logger.info(f"Updated OAuth tokens for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating OAuth tokens for client {client_id}: {e}")
            return False