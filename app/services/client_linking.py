"""
Client Linking Service

Service for linking discovered Klaviyo accounts to EmailPilot clients.
Handles creating new clients from discovered accounts, linking to existing clients,
and managing OAuth connection metadata.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from google.cloud import firestore
from app.services.firestore import build_firestore_client
from app.services.secrets import SecretManagerService

logger = logging.getLogger(__name__)

class ClientLinkingService:
    """Service for linking Klaviyo accounts to EmailPilot clients"""
    
    def __init__(self, project_id: str, secret_manager: SecretManagerService = None):
        self.project_id = project_id
        self.secret_manager = secret_manager or SecretManagerService(project_id)
        self.firestore_client = None
        
    def _get_firestore_client(self) -> firestore.Client:
        """Get or create Firestore client"""
        if not self.firestore_client:
            self.firestore_client = build_firestore_client(self.project_id)
        return self.firestore_client
    
    def _validate_user_owns_account(self, user_email: str, account_id: str) -> Dict[str, Any]:
        """
        Validate that the user owns the discovered account
        
        Args:
            user_email: Email of the user trying to link
            account_id: Klaviyo account ID to validate
            
        Returns:
            Dictionary with validation result and account data if valid
            
        Raises:
            ValueError: If user doesn't own the account
        """
        try:
            db = self._get_firestore_client()
            
            # Get user's discovered accounts
            user_accounts_ref = db.collection("klaviyo_discovered_accounts").document(user_email)
            doc = user_accounts_ref.get()
            
            if not doc.exists:
                raise ValueError(f"No discovered accounts found for user {user_email}")
            
            discovered_data = doc.to_dict()
            accounts = discovered_data.get("accounts", [])
            
            # Find the specific account
            account_data = None
            for account in accounts:
                if account.get("id") == account_id:
                    account_data = account
                    break
            
            if not account_data:
                raise ValueError(f"Account {account_id} not found in user's discovered accounts")
            
            # Validate ownership
            if account_data.get("discovered_by") != user_email:
                raise ValueError(f"User {user_email} does not own account {account_id}")
            
            return {
                "valid": True,
                "account_data": account_data
            }
            
        except Exception as e:
            logger.error(f"Error validating account ownership: {e}")
            raise ValueError(f"Failed to validate account ownership: {str(e)}")
    
    def check_existing_link(self, account_id: str) -> Optional[Dict[str, str]]:
        """
        Check if a Klaviyo account is already linked to a client
        
        Args:
            account_id: Klaviyo account ID to check
            
        Returns:
            Dictionary with client info if linked, None if not linked
        """
        try:
            db = self._get_firestore_client()
            
            # Search for existing client with this account ID
            clients_query = db.collection("clients").where("klaviyo_oauth_account_id", "==", account_id).limit(1)
            clients = list(clients_query.stream())
            
            if clients:
                client_doc = clients[0]
                client_data = client_doc.to_dict()
                return {
                    "client_id": client_doc.id,
                    "client_name": client_data.get("name", "Unknown"),
                    "linked_by": client_data.get("oauth_connected_by"),
                    "linked_at": client_data.get("oauth_connected_at")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking existing link for account {account_id}: {e}")
            raise ValueError(f"Failed to check existing link: {str(e)}")
    
    def auto_match_by_name_email(self, account_data: Dict[str, Any], user_email: str) -> List[Dict[str, Any]]:
        """
        Auto-match discovered account to existing clients by name/email similarity
        
        Args:
            account_data: Discovered account data
            user_email: Email of the user who discovered the account
            
        Returns:
            List of potential client matches with confidence scores
        """
        try:
            db = self._get_firestore_client()
            
            account_name = account_data.get("name", "").lower().strip()
            account_email = account_data.get("email", "").lower().strip()
            account_website = account_data.get("website", "").lower().strip()
            
            # Get all existing clients for the user
            # For now, we'll search all clients - in the future we could filter by user
            clients_query = db.collection("clients").where("is_active", "==", True)
            clients = list(clients_query.stream())
            
            matches = []
            
            for client_doc in clients:
                client_data = client_doc.to_dict()
                client_name = client_data.get("name", "").lower().strip()
                client_email = client_data.get("contact_email", "").lower().strip()
                client_website = client_data.get("website", "").lower().strip()
                
                # Skip if already has a Klaviyo account linked
                if client_data.get("klaviyo_oauth_account_id"):
                    continue
                
                confidence = 0
                match_reasons = []
                
                # Name matching (highest weight)
                if account_name and client_name:
                    if account_name == client_name:
                        confidence += 50
                        match_reasons.append("Exact name match")
                    elif account_name in client_name or client_name in account_name:
                        confidence += 30
                        match_reasons.append("Partial name match")
                
                # Email matching
                if account_email and client_email:
                    if account_email == client_email:
                        confidence += 40
                        match_reasons.append("Exact email match")
                    elif account_email.split("@")[1] == client_email.split("@")[1]:
                        confidence += 20
                        match_reasons.append("Same domain")
                
                # Website matching
                if account_website and client_website:
                    # Clean up URLs for comparison
                    account_domain = account_website.replace("https://", "").replace("http://", "").replace("www.", "")
                    client_domain = client_website.replace("https://", "").replace("http://", "").replace("www.", "")
                    
                    if account_domain == client_domain:
                        confidence += 30
                        match_reasons.append("Website match")
                
                # Only include matches with reasonable confidence
                if confidence >= 30:
                    matches.append({
                        "client_id": client_doc.id,
                        "client_name": client_data.get("name"),
                        "client_email": client_data.get("contact_email"),
                        "client_website": client_data.get("website"),
                        "confidence": confidence,
                        "match_reasons": match_reasons,
                        "created_at": client_data.get("created_at"),
                        "description": client_data.get("description", "")
                    })
            
            # Sort by confidence score (highest first)
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            
            logger.info(f"Found {len(matches)} potential matches for account {account_data.get('id')}")
            return matches
            
        except Exception as e:
            logger.error(f"Error auto-matching account: {e}")
            return []
    
    def link_account_to_existing_client(
        self, 
        user_email: str, 
        account_id: str, 
        client_id: str
    ) -> Dict[str, Any]:
        """
        Link a discovered Klaviyo account to an existing EmailPilot client
        
        Args:
            user_email: Email of the user performing the link
            account_id: Klaviyo account ID to link
            client_id: Existing client ID to link to
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate user owns the account
            validation = self._validate_user_owns_account(user_email, account_id)
            account_data = validation["account_data"]
            
            # Check if account is already linked
            existing_link = self.check_existing_link(account_id)
            if existing_link:
                raise ValueError(
                    f"Account {account_id} is already linked to client "
                    f"{existing_link['client_name']} ({existing_link['client_id']})"
                )
            
            db = self._get_firestore_client()
            
            # Verify client exists
            client_ref = db.collection("clients").document(client_id)
            client_doc = client_ref.get()
            
            if not client_doc.exists:
                raise ValueError(f"Client {client_id} not found")
            
            client_data = client_doc.to_dict()
            
            # Check if client already has a different Klaviyo account linked
            if client_data.get("klaviyo_oauth_account_id"):
                raise ValueError(
                    f"Client {client_data.get('name')} is already linked to "
                    f"Klaviyo account {client_data.get('klaviyo_oauth_account_id')}"
                )
            
            # Update client with OAuth connection info
            update_data = {
                "klaviyo_oauth_account_id": account_id,
                "oauth_connection_type": "discovered",
                "oauth_connected_by": user_email,
                "oauth_connected_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Add account metadata to client
                "klaviyo_account_name": account_data.get("name"),
                "klaviyo_account_email": account_data.get("email"),
                "klaviyo_account_timezone": account_data.get("timezone"),
                "klaviyo_account_currency": account_data.get("currency")
            }
            
            client_ref.update(update_data)
            
            logger.info(f"Successfully linked account {account_id} to client {client_id} by user {user_email}")
            
            return {
                "success": True,
                "message": f"Successfully linked Klaviyo account to client {client_data.get('name')}",
                "client_id": client_id,
                "client_name": client_data.get("name"),
                "account_id": account_id,
                "account_name": account_data.get("name")
            }
            
        except Exception as e:
            logger.error(f"Error linking account {account_id} to client {client_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_client_from_account(
        self, 
        user_email: str, 
        account_id: str, 
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new EmailPilot client from a discovered Klaviyo account
        
        Args:
            user_email: Email of the user creating the client
            account_id: Klaviyo account ID to create client from
            additional_data: Optional additional client data
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate user owns the account
            validation = self._validate_user_owns_account(user_email, account_id)
            account_data = validation["account_data"]
            
            # Check if account is already linked
            existing_link = self.check_existing_link(account_id)
            if existing_link:
                raise ValueError(
                    f"Account {account_id} is already linked to client "
                    f"{existing_link['client_name']} ({existing_link['client_id']})"
                )
            
            db = self._get_firestore_client()
            
            # Prepare client data from account info
            account_name = account_data.get("name", f"Account {account_id}")
            
            # Check for name conflicts
            existing_name_query = db.collection("clients").where("name", "==", account_name).limit(1)
            if list(existing_name_query.stream()):
                # Add suffix to make name unique
                counter = 1
                base_name = account_name
                while True:
                    new_name = f"{base_name} ({counter})"
                    check_query = db.collection("clients").where("name", "==", new_name).limit(1)
                    if not list(check_query.stream()):
                        account_name = new_name
                        break
                    counter += 1
            
            client_data = {
                "name": account_name,
                "description": f"Auto-created from Klaviyo account {account_data.get('name', account_id)}",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # OAuth connection info
                "klaviyo_oauth_account_id": account_id,
                "oauth_connection_type": "discovered",
                "oauth_connected_by": user_email,
                "oauth_connected_at": datetime.now(timezone.utc).isoformat(),
                # Account metadata
                "klaviyo_account_name": account_data.get("name"),
                "klaviyo_account_email": account_data.get("email"),
                "klaviyo_account_timezone": account_data.get("timezone"),
                "klaviyo_account_currency": account_data.get("currency"),
                # Default values
                "metric_id": "",
                "contact_email": account_data.get("email", ""),
                "contact_name": "",
                "website": account_data.get("website", ""),
                "timezone": account_data.get("timezone", "UTC"),
                "key_growth_objective": "subscriptions"
            }
            
            # Merge any additional data provided
            if additional_data:
                # Only allow safe fields to be overridden
                safe_fields = {
                    "description", "contact_name", "website", "client_voice", 
                    "client_background", "key_growth_objective"
                }
                for field, value in additional_data.items():
                    if field in safe_fields and value is not None:
                        client_data[field] = value
            
            # Create the client
            doc_ref = db.collection("clients").add(client_data)
            new_client_id = doc_ref[1].id
            
            logger.info(f"Successfully created client {new_client_id} from account {account_id} by user {user_email}")
            
            return {
                "success": True,
                "message": f"Successfully created client '{account_name}' from Klaviyo account",
                "client_id": new_client_id,
                "client_name": account_name,
                "account_id": account_id,
                "account_name": account_data.get("name")
            }
            
        except Exception as e:
            logger.error(f"Error creating client from account {account_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def unlink_account_from_client(self, user_email: str, client_id: str) -> Dict[str, Any]:
        """
        Unlink a Klaviyo account from an EmailPilot client
        
        Args:
            user_email: Email of the user performing the unlink
            client_id: Client ID to unlink account from
            
        Returns:
            Dictionary with operation result
        """
        try:
            db = self._get_firestore_client()
            
            # Get client data
            client_ref = db.collection("clients").document(client_id)
            client_doc = client_ref.get()
            
            if not client_doc.exists:
                raise ValueError(f"Client {client_id} not found")
            
            client_data = client_doc.to_dict()
            account_id = client_data.get("klaviyo_oauth_account_id")
            
            if not account_id:
                raise ValueError(f"Client {client_data.get('name')} has no linked Klaviyo account")
            
            # Validate user has permission to unlink
            # For now, allow any authenticated user to unlink - in the future we might add ownership checks
            connected_by = client_data.get("oauth_connected_by")
            if connected_by and connected_by != user_email:
                logger.warning(f"User {user_email} unlinking account connected by {connected_by}")
            
            # Remove OAuth connection info from client
            update_data = {
                "klaviyo_oauth_account_id": firestore.DELETE_FIELD,
                "oauth_connection_type": firestore.DELETE_FIELD,
                "oauth_connected_by": firestore.DELETE_FIELD,
                "oauth_connected_at": firestore.DELETE_FIELD,
                "klaviyo_account_name": firestore.DELETE_FIELD,
                "klaviyo_account_email": firestore.DELETE_FIELD,
                "klaviyo_account_timezone": firestore.DELETE_FIELD,
                "klaviyo_account_currency": firestore.DELETE_FIELD,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "oauth_disconnected_by": user_email,
                "oauth_disconnected_at": datetime.now(timezone.utc).isoformat()
            }
            
            client_ref.update(update_data)
            
            logger.info(f"Successfully unlinked account {account_id} from client {client_id} by user {user_email}")
            
            return {
                "success": True,
                "message": f"Successfully unlinked Klaviyo account from client {client_data.get('name')}",
                "client_id": client_id,
                "client_name": client_data.get("name"),
                "account_id": account_id
            }
            
        except Exception as e:
            logger.error(f"Error unlinking account from client {client_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_linkable_clients(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Get list of clients that the user can link accounts to
        
        Args:
            user_email: Email of the user
            
        Returns:
            List of client dictionaries that don't already have OAuth accounts linked
        """
        try:
            db = self._get_firestore_client()
            
            # Get all active clients without OAuth links
            # For now, we'll show all clients - in the future we might filter by user ownership
            clients_query = (
                db.collection("clients")
                .where("is_active", "==", True)
            )
            
            linkable_clients = []
            
            for client_doc in clients_query.stream():
                client_data = client_doc.to_dict()
                
                # Skip clients that already have OAuth accounts linked
                if client_data.get("klaviyo_oauth_account_id"):
                    continue
                
                linkable_clients.append({
                    "id": client_doc.id,
                    "name": client_data.get("name"),
                    "description": client_data.get("description", ""),
                    "contact_email": client_data.get("contact_email", ""),
                    "website": client_data.get("website", ""),
                    "created_at": client_data.get("created_at"),
                    "has_klaviyo_key": bool(client_data.get("klaviyo_secret_name") or client_data.get("klaviyo_api_key"))
                })
            
            # Sort by name
            linkable_clients.sort(key=lambda x: x["name"])
            
            return linkable_clients
            
        except Exception as e:
            logger.error(f"Error getting linkable clients for user {user_email}: {e}")
            return []