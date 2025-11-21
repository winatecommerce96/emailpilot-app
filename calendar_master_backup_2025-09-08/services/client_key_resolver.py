"""
Client Key Resolution Service for Secret Manager Integration

This service provides a centralized way to resolve Klaviyo API keys for clients,
mapping client names to their corresponding Secret Manager secret names.
"""

import logging
import re
from typing import Optional, Dict, Any
from google.cloud import firestore
from fastapi import Depends
from app.deps.firestore import get_db
from app.services.secret_manager import SecretManagerService, SecretNotFoundError
from app.deps import get_secret_manager_service

logger = logging.getLogger(__name__)

class ClientKeyResolver:
    """
    Resolves client Klaviyo API keys using Secret Manager with intelligent name mapping
    """
    
    def __init__(self, db: firestore.Client, secret_manager: SecretManagerService):
        self.db = db
        self.secret_manager = secret_manager
        self._client_cache = {}  # Simple cache for client data
    
    def normalize_client_name(self, client_name: str) -> str:
        """
        Normalize client name for secret name generation
        
        Examples:
        - "Consumer Law Attorneys" -> "consumer-law-attorneys"
        - "The Widget Company, LLC" -> "the-widget-company-llc"
        - "Acme Corp (NYC)" -> "acme-corp-nyc"
        """
        # Convert to lowercase
        normalized = client_name.lower()
        
        # Remove common business suffixes and punctuation
        normalized = re.sub(r'\b(llc|inc|corp|ltd|company|co\.?)\b', '', normalized)
        normalized = re.sub(r'[^\w\s-]', '', normalized)  # Keep only alphanumeric, spaces, hyphens
        normalized = re.sub(r'\s+', '-', normalized.strip())  # Replace spaces with hyphens
        normalized = re.sub(r'-+', '-', normalized)  # Remove duplicate hyphens
        normalized = normalized.strip('-')  # Remove leading/trailing hyphens
        
        return normalized
    
    def generate_secret_name(self, client_name: str, client_id: str = None) -> str:
        """
        Generate a secret name for a client
        
        Priority:
        1. Use normalized client name if unique
        2. Fall back to client_id if provided
        3. Use a combination if needed
        """
        normalized_name = self.normalize_client_name(client_name)
        
        if normalized_name:
            return f"klaviyo-api-{normalized_name}"
        elif client_id:
            return f"klaviyo-api-{client_id}"
        else:
            # Last resort - use a sanitized version of the original name
            fallback = re.sub(r'[^a-zA-Z0-9-]', '-', client_name.lower())
            return f"klaviyo-api-{fallback}"
    
    async def get_client_klaviyo_key(self, client_id: str) -> Optional[str]:
        """
        Get Klaviyo API key for a client using Secret Manager with intelligent mapping
        
        Steps:
        1. Check if client document has klaviyo_secret_name field
        2. If not, generate secret name based on client name
        3. Try to fetch from Secret Manager
        4. Fall back to legacy fields if Secret Manager fails
        5. Update client document with secret mapping for future use
        """
        try:
            # Get client document
            client_doc = self.db.collection('clients').document(client_id).get()
            if not client_doc.exists:
                logger.error(f"Client {client_id} not found")
                return None
            
            client_data = client_doc.to_dict()
            client_name = client_data.get('name', '')
            
            # Check if client already has a secret name mapping
            # Priority: klaviyo_api_key_secret > klaviyo_secret_name (backward compat)
            existing_secret_name = client_data.get('klaviyo_api_key_secret') or client_data.get('klaviyo_secret_name')
            
            if existing_secret_name:
                # Try to get key from existing secret name
                try:
                    key = self.secret_manager.get_secret(existing_secret_name)
                    if key:
                        return key.strip()
                    else:
                        logger.warning(f"Secret {existing_secret_name} exists in client doc but not in Secret Manager")
                except Exception as e:
                    logger.warning(f"Failed to get secret {existing_secret_name}: {e}")
            
            # Generate secret name based on client name
            if client_name:
                generated_secret_name = self.generate_secret_name(client_name, client_id)
                
                # Try to get key from generated secret name
                logger.info(f"Attempting to fetch secret with generated name: {generated_secret_name}")
                try:
                    key = self.secret_manager.get_secret(generated_secret_name)
                    if key:
                        # Update client document with the working secret name
                        await self._update_client_secret_mapping(client_id, generated_secret_name)
                        return key.strip()
                except Exception as e:
                    logger.debug(f"Secret {generated_secret_name} not found: {e}")
            
            # Fall back to legacy fields
            legacy_key = client_data.get('klaviyo_api_key') or client_data.get('klaviyo_private_key')
            if legacy_key:
                logger.warning(f"Client {client_id} using legacy plaintext key - consider migrating to Secret Manager")
                
                # If we have a legacy key, migrate it to Secret Manager
                if client_name:
                    await self._migrate_legacy_key_to_secret_manager(client_id, client_name, legacy_key.strip())
                
                return legacy_key.strip()
            
            logger.error(f"No Klaviyo API key found for client {client_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Klaviyo key for client {client_id}: {e}")
            return None
    
    async def set_client_klaviyo_key(self, client_id: str, api_key: str) -> bool:
        """
        Set Klaviyo API key for a client in Secret Manager
        
        Steps:
        1. Get client name
        2. Generate appropriate secret name
        3. Store in Secret Manager
        4. Update client document with secret mapping
        5. Clean up legacy fields
        """
        try:
            # Get client document
            client_doc = self.db.collection('clients').document(client_id).get()
            if not client_doc.exists:
                logger.error(f"Client {client_id} not found")
                return False
            
            client_data = client_doc.to_dict()
            client_name = client_data.get('name', '')
            
            if not client_name:
                logger.error(f"Client {client_id} has no name - cannot generate secret name")
                return False
            
            # Generate secret name
            secret_name = self.generate_secret_name(client_name, client_id)
            
            # Store in Secret Manager
            try:
                self.secret_manager.create_or_update_secret(
                    secret_id=secret_name,
                    secret_value=api_key,
                    labels={
                        "client_id": client_id,
                        "client_name": self.normalize_client_name(client_name),
                        "type": "klaviyo_api_key",
                        "app": "emailpilot"
                    }
                )
                
                # Update client document
                await self._update_client_secret_mapping(client_id, secret_name, cleanup_legacy=True)
                
                logger.info(f"Successfully stored Klaviyo key for client {client_id} as {secret_name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to store secret {secret_name}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting Klaviyo key for client {client_id}: {e}")
            return False
    
    async def _update_client_secret_mapping(self, client_id: str, secret_name: str, cleanup_legacy: bool = False):
        """Update client document with secret name mapping"""
        try:
            client_ref = self.db.collection('clients').document(client_id)
            update_data = {
                'klaviyo_api_key_secret': secret_name,  # Use standard field name
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if cleanup_legacy:
                # Remove legacy plaintext fields
                update_data['klaviyo_api_key'] = firestore.DELETE_FIELD
                update_data['klaviyo_private_key'] = firestore.DELETE_FIELD
            
            client_ref.update(update_data)
            
        except Exception as e:
            logger.error(f"Failed to update client {client_id} secret mapping: {e}")
    
    async def _migrate_legacy_key_to_secret_manager(self, client_id: str, client_name: str, api_key: str):
        """Migrate legacy plaintext key to Secret Manager"""
        try:
            secret_name = self.generate_secret_name(client_name, client_id)
            
            # Store in Secret Manager
            self.secret_manager.create_or_update_secret(
                secret_id=secret_name,
                secret_value=api_key,
                labels={
                    "client_id": client_id,
                    "client_name": self.normalize_client_name(client_name),
                    "type": "klaviyo_api_key",
                    "app": "emailpilot",
                    "migrated_from": "legacy"
                }
            )
            
            # Update client document
            await self._update_client_secret_mapping(client_id, secret_name, cleanup_legacy=True)
            
            logger.info(f"Migrated legacy key for client {client_id} to Secret Manager as {secret_name}")
            
        except Exception as e:
            logger.error(f"Failed to migrate legacy key for client {client_id}: {e}")
    
    def list_client_secret_mappings(self) -> Dict[str, Any]:
        """
        List all clients and their secret name mappings for debugging
        """
        try:
            clients = self.db.collection('clients').stream()
            mappings = {}
            
            for client_doc in clients:
                client_data = client_doc.to_dict()
                client_id = client_doc.id
                
                mappings[client_id] = {
                    'name': client_data.get('name', ''),
                    'klaviyo_secret_name': client_data.get('klaviyo_secret_name'),
                    'has_legacy_key': bool(client_data.get('klaviyo_api_key') or client_data.get('klaviyo_private_key')),
                    'suggested_secret_name': self.generate_secret_name(client_data.get('name', ''), client_id) if client_data.get('name') else None
                }
            
            return mappings
            
        except Exception as e:
            logger.error(f"Failed to list client secret mappings: {e}")
            return {}


def get_client_key_resolver(
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service),
) -> ClientKeyResolver:
    """Get ClientKeyResolver instance with proper dependency injection"""
    return ClientKeyResolver(db=db, secret_manager=secret_manager)