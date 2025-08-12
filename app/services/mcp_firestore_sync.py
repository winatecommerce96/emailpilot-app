"""
MCP Client Firestore Synchronization Service
Handles real-time synchronization between MCP clients and Firebase Firestore
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin
from sqlalchemy.orm import Session
from app.models.mcp_client import MCPClient
from app.core.database import get_db
import asyncio

logger = logging.getLogger(__name__)

class MCPFirestoreSync:
    """Service for syncing MCP clients between local database and Firestore"""
    
    def __init__(self):
        self.db = None
        self._initialize_firebase()
        self.sync_enabled = os.getenv('MCP_FIRESTORE_SYNC_ENABLED', 'true').lower() == 'true'
    
    def _initialize_firebase(self):
        """Initialize Firebase connection if not already initialized"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Try to get service account from environment or file
                service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'emailpilot-438321')
                
                if service_account_path and os.path.exists(service_account_path):
                    # Use service account file
                    cred = credentials.Certificate(service_account_path)
                    initialize_app(cred, {'projectId': project_id})
                else:
                    # Use default credentials (for Cloud Run, etc.)
                    try:
                        initialize_app(options={'projectId': project_id})
                    except Exception:
                        logger.warning("Firebase not initialized - MCP sync will be disabled")
                        self.sync_enabled = False
                        return
                
                logger.info(f"Firebase initialized for MCP sync - project: {project_id}")
            
            self.db = firestore.client()
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase for MCP sync: {e}")
            self.sync_enabled = False
    
    async def sync_mcp_client_to_firestore(self, mcp_client: MCPClient) -> bool:
        """Sync a single MCP client to Firestore"""
        if not self.sync_enabled or not self.db:
            return False
            
        try:
            # Prepare client data for Firestore
            client_data = {
                'id': mcp_client.id,
                'name': mcp_client.name,
                'account_id': mcp_client.account_id,
                'enabled': mcp_client.enabled,
                'read_only': mcp_client.read_only,
                'default_model_provider': mcp_client.default_model_provider,
                'rate_limit_requests_per_minute': mcp_client.rate_limit_requests_per_minute,
                'rate_limit_tokens_per_day': mcp_client.rate_limit_tokens_per_day,
                'total_requests': mcp_client.total_requests,
                'total_tokens_used': mcp_client.total_tokens_used,
                'webhook_url': mcp_client.webhook_url,
                'custom_settings': mcp_client.custom_settings or {},
                'has_klaviyo_key': bool(mcp_client.klaviyo_api_key_secret_id),
                'has_openai_key': bool(mcp_client.openai_api_key_secret_id),
                'has_gemini_key': bool(mcp_client.gemini_api_key_secret_id),
                'is_active': True,  # MCP clients are always active when enabled
                'type': 'mcp',  # Mark as MCP client
                'synced_at': firestore.SERVER_TIMESTAMP,
                'updated_at': mcp_client.updated_at.isoformat() if mcp_client.updated_at else None,
                'created_at': mcp_client.created_at.isoformat() if mcp_client.created_at else None
            }
            
            # Use account_id as the document ID for consistency
            doc_ref = self.db.collection('clients').document(mcp_client.account_id)
            doc_ref.set(client_data, merge=True)
            
            logger.info(f"Synced MCP client {mcp_client.name} to Firestore")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing MCP client to Firestore: {e}")
            return False
    
    async def sync_all_mcp_clients_to_firestore(self, db: Session) -> Dict[str, Any]:
        """Sync all MCP clients from local database to Firestore"""
        if not self.sync_enabled or not self.db:
            return {"success": False, "message": "Firestore sync is disabled"}
            
        try:
            # Get all MCP clients from local database
            mcp_clients = db.query(MCPClient).all()
            
            success_count = 0
            error_count = 0
            
            for client in mcp_clients:
                if await self.sync_mcp_client_to_firestore(client):
                    success_count += 1
                else:
                    error_count += 1
            
            return {
                "success": True,
                "synced": success_count,
                "errors": error_count,
                "total": len(mcp_clients)
            }
            
        except Exception as e:
            logger.error(f"Error syncing all MCP clients: {e}")
            return {"success": False, "message": str(e)}
    
    async def import_mcp_clients_from_firestore(self, db: Session) -> Dict[str, Any]:
        """Import MCP clients from Firestore to local database"""
        if not self.sync_enabled or not self.db:
            return {"success": False, "message": "Firestore sync is disabled"}
            
        try:
            # Query Firestore for MCP clients
            docs = self.db.collection('clients').where('type', '==', 'mcp').stream()
            
            imported_count = 0
            updated_count = 0
            error_count = 0
            
            for doc in docs:
                try:
                    client_data = doc.to_dict()
                    
                    # Check if client already exists in local database
                    existing_client = db.query(MCPClient).filter(
                        MCPClient.account_id == client_data.get('account_id')
                    ).first()
                    
                    if existing_client:
                        # Update existing client
                        for key, value in client_data.items():
                            if hasattr(existing_client, key) and key not in ['id', 'created_at', 'synced_at']:
                                setattr(existing_client, key, value)
                        existing_client.updated_at = datetime.utcnow()
                        updated_count += 1
                    else:
                        # Create new client
                        new_client = MCPClient(
                            id=client_data.get('id'),
                            name=client_data.get('name'),
                            account_id=client_data.get('account_id'),
                            enabled=client_data.get('enabled', True),
                            read_only=client_data.get('read_only', True),
                            default_model_provider=client_data.get('default_model_provider', 'claude'),
                            rate_limit_requests_per_minute=client_data.get('rate_limit_requests_per_minute', 60),
                            rate_limit_tokens_per_day=client_data.get('rate_limit_tokens_per_day', 1000000),
                            total_requests=client_data.get('total_requests', 0),
                            total_tokens_used=client_data.get('total_tokens_used', 0),
                            webhook_url=client_data.get('webhook_url'),
                            custom_settings=client_data.get('custom_settings', {})
                        )
                        db.add(new_client)
                        imported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error importing client {doc.id}: {e}")
                    error_count += 1
            
            db.commit()
            
            return {
                "success": True,
                "imported": imported_count,
                "updated": updated_count,
                "errors": error_count
            }
            
        except Exception as e:
            logger.error(f"Error importing MCP clients from Firestore: {e}")
            db.rollback()
            return {"success": False, "message": str(e)}
    
    def setup_realtime_sync(self, db_session_factory):
        """Setup real-time listeners for Firestore changes"""
        if not self.sync_enabled or not self.db:
            logger.warning("Firestore real-time sync not enabled")
            return
            
        def on_snapshot(doc_snapshot, changes, read_time):
            """Handle Firestore document changes"""
            for change in changes:
                try:
                    if change.type.name == 'ADDED' or change.type.name == 'MODIFIED':
                        doc_data = change.document.to_dict()
                        
                        # Only process MCP clients
                        if doc_data.get('type') != 'mcp':
                            continue
                        
                        # Create a new database session
                        db = db_session_factory()
                        
                        try:
                            # Update or create client in local database
                            existing_client = db.query(MCPClient).filter(
                                MCPClient.account_id == doc_data.get('account_id')
                            ).first()
                            
                            if existing_client:
                                # Update existing client
                                for key, value in doc_data.items():
                                    if hasattr(existing_client, key) and key not in ['id', 'created_at', 'synced_at', 'type']:
                                        setattr(existing_client, key, value)
                                existing_client.updated_at = datetime.utcnow()
                            else:
                                # Create new client
                                new_client = MCPClient(
                                    id=doc_data.get('id'),
                                    name=doc_data.get('name'),
                                    account_id=doc_data.get('account_id'),
                                    enabled=doc_data.get('enabled', True),
                                    read_only=doc_data.get('read_only', True),
                                    default_model_provider=doc_data.get('default_model_provider', 'claude'),
                                    rate_limit_requests_per_minute=doc_data.get('rate_limit_requests_per_minute', 60),
                                    rate_limit_tokens_per_day=doc_data.get('rate_limit_tokens_per_day', 1000000),
                                    webhook_url=doc_data.get('webhook_url'),
                                    custom_settings=doc_data.get('custom_settings', {})
                                )
                                db.add(new_client)
                            
                            db.commit()
                            logger.info(f"Synced MCP client {doc_data.get('name')} from Firestore")
                            
                        finally:
                            db.close()
                    
                    elif change.type.name == 'REMOVED':
                        # Handle deletion if needed
                        pass
                        
                except Exception as e:
                    logger.error(f"Error processing Firestore change: {e}")
        
        # Start listening to MCP clients collection
        try:
            query = self.db.collection('clients').where('type', '==', 'mcp')
            query.on_snapshot(on_snapshot)
            logger.info("Real-time Firestore sync listener started for MCP clients")
        except Exception as e:
            logger.error(f"Failed to setup real-time sync: {e}")
    
    async def get_firestore_mcp_clients(self) -> List[Dict]:
        """Get all MCP clients directly from Firestore"""
        if not self.sync_enabled or not self.db:
            return []
            
        try:
            docs = self.db.collection('clients').where('type', '==', 'mcp').stream()
            
            clients = []
            for doc in docs:
                client_data = doc.to_dict()
                client_data['firestore_id'] = doc.id
                clients.append(client_data)
            
            return clients
            
        except Exception as e:
            logger.error(f"Error fetching MCP clients from Firestore: {e}")
            return []

# Initialize the sync service
mcp_firestore_sync = MCPFirestoreSync()