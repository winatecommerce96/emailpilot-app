#!/usr/bin/env python3
"""
Setup script for EmailPilot Admin OAuth Configuration
This script helps initialize the first admin user and configure Google OAuth credentials.
"""
import os
import sys
import asyncio
from datetime import datetime
from app.deps.firestore import get_db
from app.services.secret_manager import get_secret_manager
from app.services.auth import initialize_admin_user

def setup_oauth_secrets():
    """Setup Google OAuth credentials in Secret Manager"""
    secret_manager = get_secret_manager()
    
    print("🔐 Setting up Google OAuth credentials in Secret Manager...")
    print("You'll need to get these from Google Cloud Console:")
    print("https://console.cloud.google.com/apis/credentials")
    print()
    
    # Get OAuth credentials from user
    client_id = input("Enter Google OAuth Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required")
        return False
        
    client_secret = input("Enter Google OAuth Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required")
        return False
    
    redirect_uri = input("Enter Redirect URI (or press Enter for default): ").strip()
    if not redirect_uri:
        redirect_uri = "http://localhost:8000/api/auth/google/callback"
    
    try:
        # Store credentials in Secret Manager
        secret_manager.create_secret("google-oauth-client-id", client_id)
        print("✅ Stored google-oauth-client-id")
        
        secret_manager.create_secret("google-oauth-client-secret", client_secret)
        print("✅ Stored google-oauth-client-secret")
        
        secret_manager.create_secret("google-oauth-redirect-uri", redirect_uri)
        print("✅ Stored google-oauth-redirect-uri")
        
        # Also store JWT secret if not exists
        jwt_secret = secret_manager.get_secret("jwt-secret-key")
        if not jwt_secret:
            import secrets
            jwt_secret = secrets.token_urlsafe(32)
            secret_manager.create_secret("jwt-secret-key", jwt_secret)
            print("✅ Generated and stored jwt-secret-key")
        
        print("\n🎉 OAuth credentials successfully configured in Secret Manager!")
        return True
        
    except Exception as e:
        print(f"❌ Error storing OAuth credentials: {e}")
        return False

async def setup_first_admin():
    """Setup the first admin user"""
    print("\n👤 Setting up first admin user...")
    
    admin_email = input("Enter admin email address: ").strip()
    if not admin_email:
        print("❌ Admin email is required")
        return False
        
    if "@" not in admin_email:
        print("❌ Please enter a valid email address")
        return False
    
    try:
        db = get_db()
        
        # Check if admin already exists
        admin_doc = db.collection("admins").document(admin_email).get()
        if admin_doc.exists:
            print(f"ℹ️  Admin user {admin_email} already exists")
            return True
        
        # Initialize admin user
        success = await initialize_admin_user(admin_email, db)
        
        if success:
            print(f"✅ Successfully initialized admin user: {admin_email}")
            print(f"🔗 They can now login at: http://localhost:8000/api/auth/google/login")
            return True
        else:
            print("❌ Failed to initialize admin user")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up admin user: {e}")
        return False

def check_firestore_connection():
    """Check Firestore connection"""
    try:
        db = get_db()
        # Try to access a collection to test connection
        test_doc = db.collection("test").limit(1).get()
        print("✅ Firestore connection successful")
        return True
    except Exception as e:
        print(f"❌ Firestore connection failed: {e}")
        print("Make sure you have:")
        print("1. Set GOOGLE_CLOUD_PROJECT environment variable")
        print("2. Authenticated with Google Cloud (gcloud auth application-default login)")
        print("3. Or set GOOGLE_APPLICATION_CREDENTIALS to your service account key")
        return False

def check_secret_manager_access():
    """Check Secret Manager access"""
    try:
        secret_manager = get_secret_manager()
        # Try to list secrets to test access
        secrets = secret_manager.list_secrets()
        print("✅ Secret Manager access successful")
        return True
    except Exception as e:
        print(f"❌ Secret Manager access failed: {e}")
        print("Make sure you have Secret Manager API enabled and proper permissions")
        return False

async def main():
    """Main setup function"""
    print("🚀 EmailPilot Admin OAuth Setup")
    print("=" * 40)
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    if not check_firestore_connection():
        return
        
    if not check_secret_manager_access():
        return
    
    print("\n✅ All prerequisites met!")
    
    # Setup OAuth credentials
    print("\n" + "=" * 40)
    oauth_setup = setup_oauth_secrets()
    
    if not oauth_setup:
        print("❌ OAuth setup failed. Please try again.")
        return
    
    # Setup first admin
    print("\n" + "=" * 40)
    admin_setup = await setup_first_admin()
    
    if not admin_setup:
        print("❌ Admin setup failed. Please try again.")
        return
    
    print("\n" + "=" * 40)
    print("🎉 Setup Complete!")
    print("\nNext steps:")
    print("1. Start the server: uvicorn main_firestore:app --reload --port 8000")
    print("2. Navigate to: http://localhost:8000/api/auth/google/login")
    print("3. Login with the admin email you configured")
    print("4. You'll be redirected to the admin dashboard")
    print("\nAdmin management endpoints:")
    print("- GET /api/auth/google/status - Check OAuth config")
    print("- GET /api/auth/google/admins - List admin users")
    print("- POST /api/auth/google/admins - Add new admin")
    print("- POST /api/auth/google/oauth-config - Update OAuth config")

if __name__ == "__main__":
    asyncio.run(main())