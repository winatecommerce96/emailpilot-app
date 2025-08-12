#!/usr/bin/env python3
"""
Script to migrate existing secrets from .env file to Google Secret Manager
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import secretmanager
from google.api_core import exceptions

# Add the app directory to the Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.services.secret_manager import SecretManagerService

# Load .env file
load_dotenv()

# Secret mappings
SECRET_MAPPINGS = {
    "DATABASE_URL": "emailpilot-database-url",
    "SECRET_KEY": "emailpilot-secret-key",
    "KLAVIYO_API_KEY": "emailpilot-klaviyo-api-key",
    "SLACK_WEBHOOK_URL": "emailpilot-slack-webhook-url",
    "GEMINI_API_KEY": "emailpilot-gemini-api-key",
}

def migrate_secrets():
    """Migrate secrets from environment variables to Secret Manager"""
    
    print("🚀 Starting secret migration to Google Secret Manager")
    print("=" * 50)
    
    # Initialize Secret Manager
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
    secret_manager = SecretManagerService(project_id=project_id)
    
    print(f"📁 Project ID: {project_id}")
    print()
    
    migrated = []
    skipped = []
    errors = []
    
    for env_key, secret_id in SECRET_MAPPINGS.items():
        value = os.getenv(env_key)
        
        if not value:
            print(f"⏭️  Skipping {env_key}: No value found")
            skipped.append(env_key)
            continue
        
        try:
            # Check if secret already exists
            existing_value = secret_manager.get_secret(secret_id)
            
            if existing_value == value:
                print(f"✅ {env_key}: Already up-to-date in Secret Manager")
                migrated.append(env_key)
            else:
                # Update the secret
                secret_manager.create_secret(
                    secret_id=secret_id,
                    secret_value=value,
                    labels={"app": "emailpilot", "type": "config", "key": env_key}
                )
                print(f"🔄 {env_key}: Updated in Secret Manager")
                migrated.append(env_key)
                
        except Exception as e:
            print(f"❌ {env_key}: Error - {str(e)}")
            errors.append(f"{env_key}: {str(e)}")
    
    print()
    print("=" * 50)
    print("📊 Migration Summary:")
    print(f"  ✅ Migrated: {len(migrated)} secrets")
    print(f"  ⏭️  Skipped: {len(skipped)} secrets (no value)")
    print(f"  ❌ Errors: {len(errors)}")
    
    if errors:
        print("\n⚠️  Errors encountered:")
        for error in errors:
            print(f"  • {error}")
    
    # Update .env file to enable Secret Manager
    env_file = Path(".env")
    if env_file.exists():
        print("\n📝 Updating .env file...")
        
        # Read current .env
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Filter out sensitive values and update SECRET_MANAGER_ENABLED
        new_lines = []
        secret_manager_found = False
        
        for line in lines:
            # Skip sensitive values
            if any(line.startswith(f"{key}=") for key in SECRET_MAPPINGS.keys()):
                continue
            
            # Update SECRET_MANAGER_ENABLED if found
            if line.startswith("SECRET_MANAGER_ENABLED="):
                new_lines.append("SECRET_MANAGER_ENABLED=true\n")
                secret_manager_found = True
            else:
                new_lines.append(line)
        
        # Add SECRET_MANAGER_ENABLED if not found
        if not secret_manager_found:
            new_lines.append("\n# Secret Manager Configuration\n")
            new_lines.append("SECRET_MANAGER_ENABLED=true\n")
            new_lines.append(f"GOOGLE_CLOUD_PROJECT={project_id}\n")
        
        # Write back to .env
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
        
        print("✅ .env file updated (sensitive values removed)")
    
    print("\n🎉 Migration completed!")
    print("\n📌 Next steps:")
    print("  1. Test the application locally to ensure secrets are loaded correctly")
    print("  2. Deploy to Cloud Run using: ./deploy_with_secrets.sh")
    print("  3. Verify the deployment at the admin panel")

if __name__ == "__main__":
    try:
        migrate_secrets()
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        print("\nPlease ensure:")
        print("  1. Google Cloud SDK is installed and configured")
        print("  2. You have the necessary permissions for Secret Manager")
        print("  3. GOOGLE_APPLICATION_CREDENTIALS is set correctly")
        sys.exit(1)