#!/usr/bin/env python3
"""
Complete validation script for remote-only Secret Manager integration.
Tests all aspects of the new implementation.
"""
import os
import sys
import json
from typing import Dict, Any

def test_secret_manager():
    """Test Secret Manager integration"""
    print("\n=== Testing Secret Manager ===")
    
    try:
        from app.services.secret_manager import get_secret_strict, get_secret_json_strict, SecretLoadError
        print("✅ Secret Manager module imported")
    except ImportError as e:
        print(f"❌ Failed to import Secret Manager module: {e}")
        return False
    
    # Get project ID
    try:
        from google.auth import default as adc_default
        proj_env = os.getenv("GOOGLE_CLOUD_PROJECT")
        _, proj_adc = adc_default()
        project = proj_env or proj_adc
        
        if not project:
            print("❌ No project ID found. Set GOOGLE_CLOUD_PROJECT or configure ADC.")
            return False
        
        print(f"✅ Using project: {project}")
        print(f"   Transport: {os.getenv('SECRET_MANAGER_TRANSPORT', 'rest')}")
    except Exception as e:
        print(f"❌ Failed to determine project: {e}")
        return False
    
    # Test loading secrets
    secrets_found = {}
    
    # Required secrets
    required = ["emailpilot-firestore-project", "emailpilot-google-credentials", "emailpilot-secret-key"]
    for secret_id in required:
        try:
            if secret_id == "emailpilot-google-credentials":
                value = get_secret_json_strict(project, secret_id)
                secrets_found[secret_id] = isinstance(value, dict)
                print(f"✅ Loaded {secret_id}: JSON with {len(value)} keys")
            else:
                value = get_secret_strict(project, secret_id)
                secrets_found[secret_id] = bool(value)
                if secret_id == "emailpilot-secret-key":
                    print(f"✅ Loaded {secret_id}: {len(value)} chars")
                else:
                    print(f"✅ Loaded {secret_id}: {value}")
        except SecretLoadError as e:
            print(f"❌ Failed to load required secret {secret_id}: {e}")
            return False
    
    # Optional secrets
    optional = ["emailpilot-slack-webhook-url", "emailpilot-gemini-api-key"]
    for secret_id in optional:
        try:
            value = get_secret_strict(project, secret_id, timeout=3.0)
            secrets_found[secret_id] = bool(value)
            print(f"✅ Loaded optional {secret_id}: {'***' + value[-4:] if len(value) > 4 else '***'}")
        except Exception:
            print(f"ℹ️  Optional secret {secret_id} not found (OK)")
    
    return all(secrets_found.get(s) for s in required)

def test_firestore():
    """Test Firestore integration"""
    print("\n=== Testing Firestore ===")
    
    try:
        from app.services import firestore as fs
        from app.services.secret_manager import get_secret_strict, get_secret_json_strict
        print("✅ Firestore module imported")
    except ImportError as e:
        print(f"❌ Failed to import Firestore module: {e}")
        return False
    
    # Get project and credentials
    try:
        from google.auth import default as adc_default
        proj_env = os.getenv("GOOGLE_CLOUD_PROJECT")
        _, proj_adc = adc_default()
        project = proj_env or proj_adc
        
        firestore_project = get_secret_strict(project, "emailpilot-firestore-project")
        sa_json = get_secret_json_strict(project, "emailpilot-google-credentials")
        
        print(f"✅ Firestore project: {firestore_project}")
        print(f"✅ Service account: {sa_json.get('client_email', 'unknown')}")
    except Exception as e:
        print(f"❌ Failed to load Firestore config: {e}")
        return False
    
    # Build client
    try:
        client = fs.build_firestore_client(firestore_project, sa_json)
        print("✅ Firestore client created")
    except Exception as e:
        print(f"❌ Failed to create Firestore client: {e}")
        return False
    
    # Test connectivity
    try:
        fs.ping(client)
        print("✅ Firestore connectivity check passed")
    except Exception as e:
        print(f"❌ Firestore connectivity failed: {e}")
        return False
    
    # Test read/write
    try:
        doc_ref = client.collection("_health").document("validate_test")
        test_data = {"test": True, "timestamp": "test"}
        doc_ref.set(test_data, merge=True)
        
        doc = doc_ref.get()
        if doc.exists and doc.to_dict().get("test") is True:
            print("✅ Firestore write/read test passed")
            # Clean up
            doc_ref.delete()
            return True
        else:
            print("❌ Firestore document verification failed")
            return False
    except Exception as e:
        print(f"❌ Firestore write/read test failed: {e}")
        return False

def test_config():
    """Test the complete config module"""
    print("\n=== Testing Config Module ===")
    
    try:
        from app.core import config
        print("✅ Config module imported")
    except Exception as e:
        print(f"❌ Failed to import config: {e}")
        return False
    
    # Check settings
    try:
        settings = config.settings
        print(f"✅ Settings loaded:")
        print(f"   Project: {settings.project}")
        print(f"   Environment: {settings.environment}")
        print(f"   Secret key: {'*' * 8}... ({len(settings.secret_key)} chars)")
        print(f"   Slack webhook: {'configured' if settings.slack_webhook_url else 'not configured'}")
        print(f"   Gemini API: {'configured' if settings.gemini_api_key else 'not configured'}")
    except Exception as e:
        print(f"❌ Failed to access settings: {e}")
        return False
    
    # Check Firestore client
    try:
        client = config.get_firestore_client()
        if client:
            print("✅ Firestore client accessible from config")
            return True
        else:
            print("❌ Firestore client is None")
            return False
    except Exception as e:
        print(f"❌ Failed to get Firestore client: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Remote-Only Secret Manager Integration Validation")
    print("=" * 60)
    
    # Check environment
    print("\n=== Environment ===")
    print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'not set')}")
    print(f"SECRET_MANAGER_TRANSPORT: {os.getenv('SECRET_MANAGER_TRANSPORT', 'not set (default: rest)')}")
    print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set (default: production)')}")
    
    # Run tests
    results = {
        "Secret Manager": test_secret_manager(),
        "Firestore": test_firestore(),
        "Config": test_config()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Remote-only integration is working.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())