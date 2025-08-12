#!/usr/bin/env python3
"""
Test script for MCP Firestore synchronization
Tests the integration between local MCP clients and Firestore
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_firestore_sync():
    """Test the Firestore synchronization functionality"""
    
    # Import after path is set
    from app.services.mcp_firestore_sync import mcp_firestore_sync
    from app.core.database import SessionLocal, engine, Base
    
    # Import all models to avoid circular dependencies
    from app.models.client import Client
    from app.models.calendar import CalendarEvent
    from app.models.mcp_client import MCPClient
    from app.models.goal import Goal
    from app.models.report import Report
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Check if Firestore sync is enabled
        logger.info(f"Firestore sync enabled: {mcp_firestore_sync.sync_enabled}")
        logger.info(f"Firestore connected: {mcp_firestore_sync.db is not None}")
        
        if not mcp_firestore_sync.sync_enabled:
            logger.warning("Firestore sync is disabled. Set up Firebase credentials to enable.")
            logger.info("To enable Firestore sync:")
            logger.info("1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
            logger.info("2. Or ensure you're running on Google Cloud with proper permissions")
            return
        
        # Create some test MCP clients if none exist
        existing_clients = db.query(MCPClient).all()
        
        if not existing_clients:
            logger.info("Creating test MCP clients...")
            
            test_clients = [
                {
                    "id": "mcp-client-1",
                    "name": "Test MCP Client 1",
                    "account_id": "test-account-1",
                    "klaviyo_api_key_secret_id": "test-klaviyo-key-1",
                    "openai_api_key_secret_id": None,
                    "gemini_api_key_secret_id": None,
                    "enabled": True,
                    "read_only": False,
                    "default_model_provider": "claude",
                    "rate_limit_requests_per_minute": 60,
                    "rate_limit_tokens_per_day": 1000000
                },
                {
                    "id": "mcp-client-2",
                    "name": "Test MCP Client 2",
                    "account_id": "test-account-2",
                    "klaviyo_api_key_secret_id": "test-klaviyo-key-2",
                    "openai_api_key_secret_id": "test-openai-key-2",
                    "gemini_api_key_secret_id": None,
                    "enabled": True,
                    "read_only": True,
                    "default_model_provider": "openai",
                    "rate_limit_requests_per_minute": 30,
                    "rate_limit_tokens_per_day": 500000
                }
            ]
            
            for client_data in test_clients:
                client = MCPClient(**client_data)
                db.add(client)
            
            db.commit()
            logger.info(f"Created {len(test_clients)} test MCP clients")
        
        # Test syncing to Firestore
        logger.info("\n=== Testing sync to Firestore ===")
        result = await mcp_firestore_sync.sync_all_mcp_clients_to_firestore(db)
        logger.info(f"Sync result: {json.dumps(result, indent=2)}")
        
        # Test fetching from Firestore
        logger.info("\n=== Testing fetch from Firestore ===")
        firestore_clients = await mcp_firestore_sync.get_firestore_mcp_clients()
        logger.info(f"Found {len(firestore_clients)} clients in Firestore")
        for client in firestore_clients:
            logger.info(f"  - {client.get('name')} (ID: {client.get('account_id')})")
        
        # Test importing from Firestore
        logger.info("\n=== Testing import from Firestore ===")
        import_result = await mcp_firestore_sync.import_mcp_clients_from_firestore(db)
        logger.info(f"Import result: {json.dumps(import_result, indent=2)}")
        
        # List all local MCP clients after sync
        logger.info("\n=== Local MCP clients after sync ===")
        all_clients = db.query(MCPClient).all()
        for client in all_clients:
            logger.info(f"  - {client.name} (Account: {client.account_id}, Enabled: {client.enabled})")
        
        logger.info("\n✅ Firestore sync test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_firestore_sync())