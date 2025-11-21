#!/usr/bin/env python3
"""
Script to check Klaviyo OAuth client credentials in Google Secret Manager.
Validates that klaviyo_client_id and klaviyo_client_secret are properly configured.
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to sys.path so we can import modules
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

def mask_credential(value):
    """Mask credential showing only first and last 3 characters"""
    if not value or len(value) < 6:
        return "••••••••"
    return f"{value[:3]}...{value[-3:]}"

def check_klaviyo_secrets():
    """Check Klaviyo OAuth credentials using app's settings"""
    print("🔍 Checking Klaviyo OAuth Credentials...")
    print("=" * 50)
    
    # Check environment variable
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT environment variable not set")
        return False
    
    print(f"📋 Google Cloud Project: {project_id}")
    print()
    
    try:
        # Import after setting up path
        from app.services.secret_manager import SecretManagerService, SecretNotFoundError, SecretError
        
        # Initialize SecretManager directly
        secret_manager = SecretManagerService(project_id=project_id)
        print("✅ SecretManagerService initialized successfully")
        
        # Check if secrets exist in Google Secret Manager
        secrets_to_check = [
            ("klaviyo-client-id", "Klaviyo Client ID"),
            ("klaviyo-client-secret", "Klaviyo Client Secret")
        ]
        
        results = {}
        print("\n🔐 Checking secrets in Google Secret Manager:")
        print("-" * 45)
        
        for secret_id, display_name in secrets_to_check:
            try:
                value = secret_manager.get_secret(secret_id)
                if value and len(value.strip()) > 0:
                    results[secret_id] = value
                    print(f"✅ {display_name}: {mask_credential(value)}")
                else:
                    results[secret_id] = None
                    print(f"❌ {display_name}: Empty or None")
            except SecretNotFoundError:
                results[secret_id] = None
                print(f"❌ {display_name}: Secret not found")
            except SecretError as e:
                results[secret_id] = None
                print(f"❌ {display_name}: Error - {e}")
        
        # Try to load settings using app's method
        print("\n⚙️  Loading settings using app's configuration:")
        print("-" * 45)
        
        try:
            from app.core.settings import get_settings
            settings = get_settings()
            
            print(f"✅ Settings loaded successfully")
            print(f"   Klaviyo Client ID: {mask_credential(settings.klaviyo_client_id) if settings.klaviyo_client_id else 'None'}")
            print(f"   Klaviyo Client Secret: {mask_credential(settings.klaviyo_client_secret) if settings.klaviyo_client_secret else 'None'}")
            print(f"   Klaviyo Redirect URI: {settings.klaviyo_redirect_uri}")
            
            # Validate configuration
            config_valid = True
            if not settings.klaviyo_client_id:
                print("❌ klaviyo_client_id is None or empty")
                config_valid = False
            if not settings.klaviyo_client_secret:
                print("❌ klaviyo_client_secret is None or empty")
                config_valid = False
                
            if config_valid:
                print("✅ All Klaviyo OAuth credentials are properly configured")
            else:
                print("❌ Klaviyo OAuth credentials are missing or incomplete")
                
        except Exception as e:
            print(f"❌ Failed to load settings: {e}")
            config_valid = False
        
        # Summary
        print("\n📊 Summary:")
        print("-" * 20)
        
        secret_manager_status = all(results[key] is not None for key in results.keys())
        
        if secret_manager_status and config_valid:
            print("✅ All checks passed - Klaviyo OAuth is properly configured")
            return True
        else:
            print("❌ Configuration issues detected:")
            if not secret_manager_status:
                print("   - Secrets missing or empty in Google Secret Manager")
            if not config_valid:
                print("   - App settings not loading credentials properly")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        print("   Make sure you're running from the correct directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def list_all_secrets():
    """List all secrets in the project for debugging"""
    try:
        from app.services.secret_manager import SecretManagerService
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            print("❌ GOOGLE_CLOUD_PROJECT not set")
            return
            
        secret_manager = SecretManagerService(project_id=project_id)
        secrets = secret_manager.list_secrets()
        
        print(f"\n📋 All secrets in project '{project_id}':")
        print("-" * 40)
        klaviyo_secrets = [s for s in secrets if 'klaviyo' in s.lower()]
        
        if klaviyo_secrets:
            print("Klaviyo-related secrets:")
            for secret in klaviyo_secrets:
                print(f"  - {secret}")
        else:
            print("No Klaviyo-related secrets found")
            
        print(f"\nTotal secrets: {len(secrets)}")
        
    except Exception as e:
        print(f"❌ Failed to list secrets: {e}")

if __name__ == "__main__":
    # Suppress verbose logging
    logging.getLogger('google').setLevel(logging.ERROR)
    
    success = check_klaviyo_secrets()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list-all":
        list_all_secrets()
    
    sys.exit(0 if success else 1)