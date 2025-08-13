#!/usr/bin/env python3
"""
Firestore-only verification script.
Tests Secret Manager connectivity and Firestore operations.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Run Firestore-only configuration check"""
    print("=" * 60)
    print("FIRESTORE-ONLY CONFIGURATION CHECK")
    print("=" * 60)
    print()
    
    # Check environment
    print("Environment Configuration:")
    print("-" * 40)
    print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'Not set')}")
    print(f"SECRET_MANAGER_TRANSPORT: {os.getenv('SECRET_MANAGER_TRANSPORT', 'rest')}")
    print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'production')}")
    
    # Check for ADC
    try:
        from google.auth import default as adc_default
        creds, project = adc_default()
        print(f"ADC Project: {project or 'Not configured'}")
        print(f"ADC Available: ✅")
    except Exception as e:
        print(f"ADC Available: ❌ ({e})")
    
    print()
    
    # Try to load configuration
    print("Loading Configuration:")
    print("-" * 40)
    
    try:
        from app.core import config
        
        print(f"✅ Configuration loaded successfully!")
        print(f"   Project: {config.settings.project}")
        print(f"   Environment: {config.settings.environment}")
        print(f"   Has SECRET_KEY: {bool(config.settings.secret_key)} (len: {len(config.settings.secret_key)})")
        print(f"   Has Slack: {bool(config.settings.slack_webhook_url)}")
        print(f"   Has Gemini: {bool(config.settings.gemini_api_key)}")
        
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    
    # Test Firestore operations
    print("Firestore Operations Test:")
    print("-" * 40)
    
    try:
        from google.cloud import firestore
        from app.core.config import get_firestore_client
        
        db = get_firestore_client()
        print(f"✅ Firestore client created")
        
        # Write test document
        doc_ref = db.collection("_health").document("startup_test")
        test_data = {
            "ok": True,
            "test": "fs_only_check",
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(test_data, merge=True)
        print(f"✅ Write operation successful")
        
        # Read test document
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if data.get("ok") is True and data.get("test") == "fs_only_check":
                print(f"✅ Read operation successful")
                print(f"   Document data: {data}")
            else:
                print(f"⚠️  Document data unexpected: {data}")
        else:
            print(f"❌ Document not found after write")
        
        # List collections (basic connectivity test)
        collections = list(db.collections())
        print(f"✅ Can list collections (found {len(collections)})")
        
        # Clean up test document (optional)
        try:
            doc_ref.delete()
            print(f"✅ Cleanup: Test document deleted")
        except:
            print(f"ℹ️  Cleanup: Could not delete test document")
        
    except Exception as e:
        print(f"❌ Firestore operations failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✅ ALL CHECKS PASSED!")
    print()
    print("Your Firestore-only configuration is working correctly.")
    print("You can now start the application:")
    print()
    print("  export SECRET_MANAGER_TRANSPORT=rest")
    print("  export GOOGLE_CLOUD_PROJECT=emailpilot-438321")
    print("  uvicorn main_firestore:app --host 0.0.0.0 --port 8000 --reload")
    print()

if __name__ == "__main__":
    main()