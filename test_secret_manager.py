#!/usr/bin/env python3
"""
Test script to verify Secret Manager integration is working
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Set environment to use Secret Manager
os.environ["SECRET_MANAGER_ENABLED"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"

from app.services.secret_manager import get_secret_manager
from app.core.config import settings

def test_secret_manager():
    """Test Secret Manager functionality"""
    
    print("🧪 Testing Secret Manager Integration")
    print("=" * 50)
    
    # Check if Secret Manager is enabled
    print(f"✅ Secret Manager Enabled: {settings.secret_manager_enabled}")
    print(f"📁 Project ID: {settings.google_cloud_project}")
    print()
    
    # Test direct Secret Manager access
    print("Testing Direct Secret Manager Access:")
    print("-" * 40)
    
    secret_manager = get_secret_manager()
    
    secrets_to_test = [
        ("emailpilot-database-url", "Database URL"),
        ("emailpilot-secret-key", "Secret Key"),
        ("emailpilot-klaviyo-api-key", "Klaviyo API Key"),
        ("emailpilot-gemini-api-key", "Gemini API Key"),
        ("emailpilot-slack-webhook-url", "Slack Webhook")
    ]
    
    for secret_id, name in secrets_to_test:
        try:
            value = secret_manager.get_secret(secret_id)
            if value:
                masked = value[:4] + "*" * 10 + value[-4:] if len(value) > 8 else "*" * len(value)
                print(f"✅ {name}: {masked}")
            else:
                print(f"❌ {name}: Not found")
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)}")
    
    print()
    print("Testing Configuration Loading:")
    print("-" * 40)
    
    # Test configuration loading
    config_values = [
        ("database_url", "Database URL"),
        ("secret_key", "Secret Key"),
        ("klaviyo_api_key", "Klaviyo API Key"),
        ("gemini_api_key", "Gemini API Key"),
        ("slack_webhook_url", "Slack Webhook")
    ]
    
    for attr, name in config_values:
        value = getattr(settings, attr, None)
        if value:
            masked = value[:4] + "*" * 10 + value[-4:] if len(value) > 8 else "*" * len(value)
            print(f"✅ {name}: {masked}")
        else:
            print(f"❌ {name}: Not loaded")
    
    print()
    print("=" * 50)
    print("🎉 Secret Manager integration test complete!")
    
    # List all secrets with emailpilot label
    print("\n📋 All EmailPilot secrets in Secret Manager:")
    try:
        all_secrets = secret_manager.list_secrets(filter_str="labels.app=emailpilot")
        for secret in all_secrets:
            print(f"  • {secret}")
    except Exception as e:
        print(f"  Error listing secrets: {e}")

if __name__ == "__main__":
    test_secret_manager()