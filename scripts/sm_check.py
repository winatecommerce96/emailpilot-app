#!/usr/bin/env python3
"""
Secret Manager validation script - tests connectivity and secret access.
Run this before starting the app to verify configuration.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_environment():
    """Check environment variables are set"""
    print("=" * 60)
    print("ENVIRONMENT CHECK")
    print("=" * 60)
    
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "Not set")
    transport = os.getenv("SECRET_MANAGER_TRANSPORT", "rest")
    auth_type = "ADC" if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") else "Service Account"
    
    print(f"PROJECT: {project}")
    print(f"TRANSPORT: {transport}")
    print(f"AUTH TYPE: {auth_type}")
    
    if project == "Not set":
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT not set")
        print("   Run: export GOOGLE_CLOUD_PROJECT=your-project-id")
        return False
    
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not Path(creds_path).exists():
            print(f"❌ ERROR: Service account file not found: {creds_path}")
            return False
        print(f"✅ Service account file exists: {creds_path}")
    else:
        print("ℹ️  Using Application Default Credentials (ADC)")
        print("   Make sure you've run: gcloud auth application-default login")
    
    print()
    return True

def check_secrets():
    """Test loading secrets from Secret Manager"""
    print("=" * 60)
    print("SECRET MANAGER CHECK")
    print("=" * 60)
    
    try:
        from app.services.secret_manager import get_secret_strict, SecretLoadError
        
        # Required secrets
        required_secrets = [
            ("emailpilot-database-url", "DATABASE_URL"),
            ("emailpilot-secret-key", "SECRET_KEY")
        ]
        
        # Optional secrets
        optional_secrets = [
            ("emailpilot-slack-webhook-url", "SLACK_WEBHOOK_URL"),
            ("emailpilot-gemini-api-key", "GEMINI_API_KEY"),
            ("emailpilot-google-credentials", "GOOGLE_CREDENTIALS")
        ]
        
        all_good = True
        
        # Check required secrets
        print("\nRequired Secrets:")
        print("-" * 40)
        for secret_id, name in required_secrets:
            try:
                value = get_secret_strict(secret_id, timeout=4.0, max_attempts=2)
                print(f"✅ {name:25} OK (length: {len(value)})")
                
                # Additional validation
                if name == "DATABASE_URL" and value.startswith("sqlite:"):
                    print(f"   ⚠️  WARNING: Using SQLite - not for production!")
                if name == "SECRET_KEY" and len(value) < 32:
                    print(f"   ⚠️  WARNING: Key shorter than recommended (32+ chars)")
                    
            except SecretLoadError as e:
                print(f"❌ {name:25} FAILED")
                print(f"   Error: {e}")
                all_good = False
            except Exception as e:
                print(f"❌ {name:25} UNEXPECTED ERROR")
                print(f"   Error: {e}")
                all_good = False
        
        # Check optional secrets
        print("\nOptional Secrets:")
        print("-" * 40)
        for secret_id, name in optional_secrets:
            try:
                value = get_secret_strict(secret_id, timeout=2.0, max_attempts=1)
                print(f"✅ {name:25} OK (length: {len(value)})")
            except SecretLoadError:
                print(f"ℹ️  {name:25} Not configured (optional)")
            except Exception as e:
                print(f"⚠️  {name:25} Error: {e}")
        
        print()
        return all_good
        
    except ImportError as e:
        print(f"❌ ERROR: Cannot import secret manager module: {e}")
        print("   Make sure you're in the correct directory and dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_config():
    """Test loading the full configuration"""
    print("=" * 60)
    print("CONFIGURATION CHECK")
    print("=" * 60)
    
    try:
        from app.core.config import settings
        
        print("✅ Configuration loaded successfully!")
        print(f"   Environment: {settings.environment}")
        print(f"   Project: {settings.google_cloud_project}")
        print(f"   Debug: {settings.debug}")
        
        # Check database
        if hasattr(settings, 'database_url'):
            if settings.database_url.startswith("postgresql"):
                print("✅ Using PostgreSQL database")
            elif settings.database_url.startswith("mysql"):
                print("✅ Using MySQL database")
            elif settings.database_url.startswith("sqlite"):
                print("⚠️  Using SQLite database (development only)")
            else:
                print(f"ℹ️  Database type: {settings.database_url.split(':')[0]}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Cannot load configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all checks"""
    print("\n" + "=" * 60)
    print("SECRET MANAGER VALIDATION SCRIPT")
    print("=" * 60)
    print()
    
    # Track overall status
    all_passed = True
    
    # Run checks
    if not check_environment():
        all_passed = False
    
    if not check_secrets():
        all_passed = False
    
    if not check_config():
        all_passed = False
    
    # Final summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nYou can now start the application:")
        print("  uvicorn main_firestore:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(0)
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before starting the application.")
        print("\nCommon fixes:")
        print("1. Set GOOGLE_CLOUD_PROJECT:")
        print("   export GOOGLE_CLOUD_PROJECT=your-project-id")
        print("\n2. Authenticate with Google Cloud:")
        print("   gcloud auth application-default login")
        print("\n3. Use REST transport to avoid DNS issues:")
        print("   export SECRET_MANAGER_TRANSPORT=rest")
        print("\n4. Ensure secrets exist in Secret Manager:")
        print("   - emailpilot-database-url")
        print("   - emailpilot-secret-key")
        print("\n5. Grant Secret Manager permissions:")
        print("   gcloud projects add-iam-policy-binding YOUR_PROJECT \\")
        print("     --member='user:your-email@domain.com' \\")
        print("     --role='roles/secretmanager.secretAccessor'")
        sys.exit(1)

if __name__ == "__main__":
    main()