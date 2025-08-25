#!/usr/bin/env python3
"""
Klaviyo OAuth Flow Diagnostic Tool

This script tests the complete Klaviyo OAuth flow:
1. Checks if OAuth token exists in Secret Manager
2. Tests token validity with Klaviyo API
3. Attempts account discovery
4. Shows current status and next steps
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.secrets import SecretManagerService
from app.services.klaviyo_discovery import KlaviyoDiscoveryService
from google.cloud import firestore
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KlaviyoOAuthDiagnostic:
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        self.secret_manager = SecretManagerService(self.project_id)
        self.discovery_service = KlaviyoDiscoveryService(self.project_id, self.secret_manager)
        self.db = firestore.Client(project=self.project_id)
        
    async def run_diagnostics(self):
        """Run complete OAuth flow diagnostics"""
        print("\n" + "="*60)
        print(f"🔍 KLAVIYO OAUTH DIAGNOSTIC TOOL")
        print(f"📧 User: {self.user_email}")
        print(f"🏗️  Project: {self.project_id}")
        print("="*60 + "\n")
        
        # Step 1: Check OAuth token existence
        print("Step 1: Checking OAuth Token in Secret Manager...")
        print("-" * 50)
        
        token_data = await self.check_oauth_token()
        if not token_data:
            self.print_oauth_instructions()
            return False
            
        # Step 2: Test token with Klaviyo API
        print("\nStep 2: Testing Token with Klaviyo API...")
        print("-" * 50)
        
        api_test = await self.test_klaviyo_api(token_data)
        if not api_test['success']:
            self.print_token_refresh_instructions()
            return False
            
        # Step 3: Attempt account discovery
        print("\nStep 3: Discovering Klaviyo Accounts...")
        print("-" * 50)
        
        discovery = await self.discover_accounts(token_data)
        if not discovery['success']:
            print(f"❌ Discovery failed: {discovery.get('error', 'Unknown error')}")
            return False
            
        # Step 4: Check Firestore data
        print("\nStep 4: Checking Firestore Storage...")
        print("-" * 50)
        
        firestore_status = await self.check_firestore_data()
        
        # Step 5: Show summary and next steps
        print("\n" + "="*60)
        print("📊 DIAGNOSTIC SUMMARY")
        print("="*60)
        self.print_summary(token_data, api_test, discovery, firestore_status)
        
        return True
        
    async def check_oauth_token(self) -> Optional[Dict[str, Any]]:
        """Check if OAuth token exists and get its details"""
        # Try the actual secret name format used by the system
        secret_name = f"oauth-klaviyo-{self.user_email.replace('@', '-').replace('.', '-')}"
        
        try:
            token_json = self.secret_manager.get_secret(secret_name)
            if not token_json:
                print(f"❌ No OAuth token found for {self.user_email}")
                print(f"   Secret name: {secret_name}")
                return None
                
            token_data = json.loads(token_json)
            print(f"✅ OAuth token found!")
            print(f"   Access Token: {token_data.get('access_token', '')[:20]}...")
            print(f"   Refresh Token: {'Yes' if token_data.get('refresh_token') else 'No'}")
            print(f"   Expires: {token_data.get('expires_at', 'Unknown')}")
            
            # Check if expired
            if 'expires_at' in token_data:
                expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
                if expires_at < datetime.now(expires_at.tzinfo):
                    print(f"⚠️  Token is expired! Expired at: {expires_at}")
                else:
                    print(f"✅ Token is valid until: {expires_at}")
                    
            return token_data
            
        except Exception as e:
            print(f"❌ Error accessing token: {e}")
            return None
            
    async def test_klaviyo_api(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test the OAuth token against Klaviyo API"""
        access_token = token_data.get('access_token')
        if not access_token:
            return {'success': False, 'error': 'No access token in data'}
            
        try:
            async with httpx.AsyncClient() as client:
                # Test with Klaviyo accounts endpoint
                response = await client.get(
                    'https://a.klaviyo.com/api/accounts/',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/json',
                        'revision': '2024-07-15'
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get('data', [])
                    print(f"✅ Token is valid! Found {len(accounts)} accounts")
                    
                    # Show account details
                    for acc in accounts[:3]:  # Show first 3
                        attrs = acc.get('attributes', {})
                        print(f"   - {attrs.get('name', 'Unnamed')} ({acc.get('id')})")
                        
                    if len(accounts) > 3:
                        print(f"   ... and {len(accounts) - 3} more")
                        
                    return {
                        'success': True,
                        'accounts': accounts,
                        'count': len(accounts)
                    }
                    
                elif response.status_code == 401:
                    print(f"❌ Token is invalid or expired (401)")
                    return {'success': False, 'error': 'Invalid token', 'status': 401}
                    
                elif response.status_code == 403:
                    print(f"❌ Insufficient permissions (403)")
                    return {'success': False, 'error': 'Insufficient permissions', 'status': 403}
                    
                else:
                    print(f"❌ API returned status {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
                    return {'success': False, 'error': f'Status {response.status_code}', 'status': response.status_code}
                    
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return {'success': False, 'error': str(e)}
            
    async def discover_accounts(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the discovery service"""
        try:
            result = await self.discovery_service.discover_and_store_accounts(self.user_email)
            
            if result['success']:
                accounts = result['data']['accounts']
                print(f"✅ Discovery successful! Found {len(accounts)} accounts")
                
                for acc in accounts[:3]:
                    print(f"   - {acc.get('name', 'Unnamed')} ({acc.get('id')})")
                    print(f"     Email: {acc.get('contact_email', 'N/A')}")
                    print(f"     Linked: {'Yes' if acc.get('is_linked') else 'No'}")
                    
                return {
                    'success': True,
                    'accounts': accounts,
                    'count': len(accounts)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    async def check_firestore_data(self) -> Dict[str, Any]:
        """Check Firestore for discovered accounts"""
        try:
            # Check discovered accounts collection
            doc_ref = self.db.collection('klaviyo_discovered_accounts').document(self.user_email)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                accounts = data.get('accounts', [])
                print(f"✅ Found {len(accounts)} accounts in Firestore")
                print(f"   Last updated: {data.get('last_updated', 'Unknown')}")
                
                # Check for linked accounts
                linked = [a for a in accounts if a.get('linked_client_id')]
                print(f"   Linked accounts: {len(linked)}")
                
                return {
                    'success': True,
                    'accounts': accounts,
                    'linked_count': len(linked)
                }
            else:
                print(f"⚠️  No discovered accounts in Firestore yet")
                return {
                    'success': False,
                    'error': 'No data in Firestore'
                }
                
        except Exception as e:
            print(f"❌ Firestore check failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def print_oauth_instructions(self):
        """Print instructions for connecting OAuth"""
        print("\n" + "="*60)
        print("🔧 HOW TO CONNECT KLAVIYO OAUTH")
        print("="*60)
        print("""
1. Open EmailPilot in your browser:
   http://localhost:8000

2. Log in with your Google account

3. Go to Settings or Integrations

4. Click "Connect Klaviyo" button

5. Authorize access to your Klaviyo accounts

6. Return here and run this script again
""")
        
    def print_token_refresh_instructions(self):
        """Print instructions for refreshing token"""
        print("\n" + "="*60)
        print("🔄 HOW TO REFRESH KLAVIYO TOKEN")
        print("="*60)
        print("""
Your token appears to be invalid or expired.

1. Open EmailPilot: http://localhost:8000

2. Go to Settings/Integrations

3. Click "Disconnect Klaviyo"

4. Click "Connect Klaviyo" again

5. Re-authorize access

6. Run this script again
""")
        
    def print_summary(self, token_data, api_test, discovery, firestore_status):
        """Print diagnostic summary"""
        
        # Overall status
        all_good = (
            token_data is not None and
            api_test.get('success', False) and
            discovery.get('success', False) and
            firestore_status.get('success', False)
        )
        
        if all_good:
            print("\n✅ ALL SYSTEMS OPERATIONAL!")
            print("\nYou can now:")
            print("1. Open http://localhost:8000/static/klaviyo_cors_fixed.html")
            print("2. Use your stored token")
            print("3. Link accounts to clients")
        else:
            print("\n⚠️  SOME ISSUES DETECTED")
            print("\nIssues to resolve:")
            
            if not token_data:
                print("❌ No OAuth token - Connect Klaviyo first")
            elif not api_test.get('success'):
                print("❌ Token invalid - Reconnect Klaviyo")
            elif not discovery.get('success'):
                print("❌ Discovery failed - Check logs")
            elif not firestore_status.get('success'):
                print("⚠️  No data in Firestore - Run discovery")
                
        print("\n" + "="*60)
        print("📝 NEXT STEPS")
        print("="*60)
        
        if not token_data or not api_test.get('success'):
            print("""
1. Connect/Reconnect Klaviyo OAuth:
   - Open http://localhost:8000
   - Go to Settings → Integrations
   - Click "Connect Klaviyo"
   - Authorize access
""")
        elif not discovery.get('success') or not firestore_status.get('success'):
            print("""
1. Run account discovery:
   - Open http://localhost:8000/static/klaviyo_cors_fixed.html
   - Click "Use Stored Token"
   - Click "Discover Accounts"
""")
        else:
            print("""
1. Link accounts to clients:
   - Open http://localhost:8000/static/klaviyo_cors_fixed.html
   - Click "Use Stored Token"
   - Click "Link to Clients"
   - Select accounts and link them
   
2. Or use the main app:
   - Open http://localhost:8000
   - Go to Admin → Clients
   - Manage linked accounts there
""")

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_klaviyo_oauth_flow.py <user_email>")
        print("Example: python test_klaviyo_oauth_flow.py damon@winatecommerce.com")
        sys.exit(1)
        
    user_email = sys.argv[1]
    
    # Set project ID
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"
        
    diagnostic = KlaviyoOAuthDiagnostic(user_email)
    success = await diagnostic.run_diagnostics()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())