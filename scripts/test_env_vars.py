#!/usr/bin/env python3
"""
Test script to verify environment variables for Firestore emulator mode
"""
import os
import sys

def test_env_vars():
    """Test that required environment variables are set for emulator mode"""
    
    print("🔍 Testing environment variables for Firestore emulator mode")
    print("=" * 60)
    
    # Required environment variables for emulator mode
    required_vars = {
        'FIRESTORE_EMULATOR_HOST': '127.0.0.1:8080',
        'GOOGLE_CLOUD_PROJECT': 'emailpilot-dev',
        'FIREBASE_PROJECT_ID': 'emailpilot-dev'
    }
    
    all_good = True
    
    for var_name, expected_value in required_vars.items():
        actual_value = os.getenv(var_name)
        
        if actual_value:
            if actual_value == expected_value:
                print(f"✅ {var_name} = {actual_value}")
            else:
                print(f"⚠️  {var_name} = {actual_value} (expected: {expected_value})")
                all_good = False
        else:
            print(f"❌ {var_name} = NOT SET (expected: {expected_value})")
            all_good = False
    
    print()
    
    # Test Firebase detection
    try:
        from google.cloud import firestore
        print("📦 google.cloud.firestore imported successfully")
        
        # Try to create a client (this should work with emulator)
        if os.getenv('FIRESTORE_EMULATOR_HOST'):
            try:
                db = firestore.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))
                print("✅ Firestore client created (emulator mode)")
            except Exception as e:
                print(f"⚠️  Firestore client creation failed: {e}")
        else:
            print("ℹ️  FIRESTORE_EMULATOR_HOST not set - production mode")
            
    except ImportError:
        print("❌ google.cloud.firestore not available")
        print("   Install with: pip install google-cloud-firestore")
        all_good = False
    
    print()
    
    if all_good:
        print("🎉 Environment variables correctly configured for emulator mode!")
        return 0
    else:
        print("⚠️  Some environment variables need attention")
        return 1

if __name__ == "__main__":
    sys.exit(test_env_vars())