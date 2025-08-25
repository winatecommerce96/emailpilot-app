#!/usr/bin/env python3
"""
Test script for Client Linking functionality

This script tests the client linking endpoints to ensure they work correctly.
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.services.client_linking import ClientLinkingService
from app.services.klaviyo_discovery import KlaviyoDiscoveryService
from app.services.secrets import SecretManagerService

async def test_client_linking():
    """Test client linking functionality"""
    
    print("🧪 Testing Client Linking Service")
    print("=" * 50)
    
    # Initialize services
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-app")
    secret_manager = SecretManagerService(project_id)
    linking_service = ClientLinkingService(project_id, secret_manager)
    discovery_service = KlaviyoDiscoveryService(project_id, secret_manager)
    
    test_user_email = "test@emailpilot.ai"
    test_account_id = "test_account_123"
    
    print(f"Test user: {test_user_email}")
    print(f"Test account ID: {test_account_id}")
    print()
    
    # Test 1: Get linkable clients
    print("1. Testing get_user_linkable_clients...")
    try:
        linkable_clients = linking_service.get_user_linkable_clients(test_user_email)
        print(f"   ✅ Found {len(linkable_clients)} linkable clients")
        for client in linkable_clients[:3]:  # Show first 3
            print(f"   - {client['name']} (ID: {client['id']})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 2: Check existing link (should be None for test account)
    print("2. Testing check_existing_link...")
    try:
        existing_link = linking_service.check_existing_link(test_account_id)
        if existing_link:
            print(f"   ✅ Account already linked to: {existing_link['client_name']}")
        else:
            print("   ✅ Account not currently linked")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 3: Auto-match by name/email (mock account data)
    print("3. Testing auto_match_by_name_email...")
    try:
        mock_account_data = {
            "id": test_account_id,
            "name": "Test Company",
            "email": "info@testcompany.com",
            "website": "https://testcompany.com"
        }
        matches = linking_service.auto_match_by_name_email(mock_account_data, test_user_email)
        print(f"   ✅ Found {len(matches)} potential matches")
        for match in matches[:2]:  # Show first 2
            print(f"   - {match['client_name']} (confidence: {match['confidence']}%)")
            print(f"     Reasons: {', '.join(match['match_reasons'])}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 4: Test with mock discovered accounts
    print("4. Testing discovered accounts integration...")
    try:
        mock_discovered_accounts = [
            {
                "id": test_account_id,
                "name": "Test Account",
                "email": "test@example.com",
                "website": "https://example.com",
                "timezone": "UTC",
                "currency": "USD",
                "discovered_at": datetime.now().isoformat(),
                "discovered_by": test_user_email
            }
        ]
        
        # Store mock discovered accounts
        discovery_service.store_discovered_accounts(test_user_email, mock_discovered_accounts)
        print("   ✅ Stored mock discovered accounts")
        
        # Get them back with link status
        accounts_data = discovery_service.get_discovered_accounts(test_user_email)
        print(f"   ✅ Retrieved {len(accounts_data['accounts'])} accounts with link status")
        
        for account in accounts_data['accounts']:
            status = "linked" if account.get('is_linked') else "not linked"
            print(f"   - {account['name']}: {status}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    print("🎉 Client Linking Service tests completed!")
    print()
    print("📝 Available API Endpoints:")
    print("   POST /api/klaviyo/link-account - Link account to existing client")
    print("   POST /api/klaviyo/create-client - Create new client from account")
    print("   DELETE /api/klaviyo/unlink-account/{client_id} - Unlink account")
    print("   GET /api/klaviyo/linkable-clients - Get linkable clients")
    print("   GET /api/klaviyo/account/{account_id}/matches - Get potential matches")

if __name__ == "__main__":
    asyncio.run(test_client_linking())