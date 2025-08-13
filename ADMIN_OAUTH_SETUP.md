# EmailPilot Admin OAuth Setup Guide

This guide walks you through setting up Google OAuth with Admin-only access for EmailPilot.

## 🎯 Overview

The OAuth system provides:
- **Admin-only access** - Only whitelisted emails can login
- **Secret Manager integration** - OAuth credentials stored securely
- **JWT sessions** - Secure token-based authentication
- **Firestore admin management** - Admin users stored in Firestore
- **Auto-initialization** - First admin user setup

## 🚀 Quick Setup

### 1. Prerequisites

Ensure you have:
- Google Cloud Project with Firestore and Secret Manager enabled
- Authentication configured (`gcloud auth application-default login`)
- EmailPilot server can access Google Cloud services

### 2. Configure Google OAuth

Create OAuth 2.0 credentials in Google Cloud Console:

1. Go to [Google Cloud Console > APIs & Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Application type: "Web application"
4. Authorized redirect URIs: `http://localhost:8000/api/auth/google/callback`
5. Note down the Client ID and Client Secret

### 3. Run Setup Script

```bash
cd /path/to/emailpilot-app
python setup_admin_oauth.py
```

The script will:
- Test Firestore and Secret Manager access
- Store OAuth credentials in Secret Manager
- Create the first admin user
- Generate JWT secret key

### 4. Start Server

```bash
uvicorn main_firestore:app --reload --port 8000
```

### 5. Login

Navigate to: `http://localhost:8000/api/auth/google/login`

## 📁 Implementation Files

### New Files Created:
- `/app/services/auth.py` - JWT authentication service
- `/setup_admin_oauth.py` - Setup script for initial configuration
- `/test_admin_oauth.py` - Test suite for OAuth functionality

### Modified Files:
- `/app/api/auth_google.py` - Enhanced with Secret Manager & admin checks
- `/app/core/auth.py` - Updated with compatibility imports

## 🔐 Security Features

### Admin Whitelist System
- Only emails in Firestore `admins` collection can login
- First user becomes admin automatically
- Existing admins can add new admins

### Secret Manager Integration
- OAuth credentials stored securely in Google Secret Manager
- JWT secret keys auto-generated and stored
- No sensitive data in environment variables

### Session Management
- JWT tokens with 24-hour expiration
- Sessions tracked in Firestore
- Secure HTTP-only cookies
- Proper logout with session invalidation

## 🛠 API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/google/login` | Redirect to Google OAuth | No |
| GET | `/api/auth/google/callback` | Handle OAuth callback | No |
| GET | `/api/auth/google/status` | Check OAuth configuration | No |
| DELETE | `/api/auth/google/logout` | Logout and clear session | No |

### Admin Management Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/auth/google/admins` | List admin users | Admin |
| POST | `/api/auth/google/admins` | Add new admin user | Admin |
| POST | `/api/auth/google/oauth-config` | Update OAuth credentials | Admin |

### Example Admin API Usage

```bash
# Get OAuth status
curl http://localhost:8000/api/auth/google/status

# List admin users (requires admin token)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/auth/google/admins

# Add new admin (requires admin token)
curl -X POST \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"email": "newadmin@example.com"}' \
     http://localhost:8000/api/auth/google/admins
```

## 🔍 Testing

Run the test suite to verify everything works:

```bash
python test_admin_oauth.py
```

Tests include:
- ✅ Firestore connection
- ✅ Secret Manager access  
- ✅ Admin user functions
- ✅ JWT functionality
- ✅ OAuth endpoints

## 📊 Firestore Collections

### `admins` Collection
```json
{
  "email": "admin@example.com",
  "created_at": "2025-08-12T10:00:00Z",
  "is_active": true,
  "created_by": "system"
}
```

### `users` Collection
```json
{
  "email": "admin@example.com", 
  "name": "Admin User",
  "picture": "https://avatar.url",
  "google_id": "google_user_id",
  "role": "admin",
  "last_login": "2025-08-12T10:00:00Z",
  "session_id": "session_123"
}
```

### `sessions` Collection
```json
{
  "user_email": "admin@example.com",
  "role": "admin", 
  "created_at": "2025-08-12T10:00:00Z",
  "expires_at": "2025-08-13T10:00:00Z",
  "is_active": true
}
```

## 🔧 Configuration

### Environment Variables (Optional)
```bash
# Google Cloud Project (auto-detected)
export GOOGLE_CLOUD_PROJECT=your-project-id

# Custom Firestore emulator (development only)
export FIRESTORE_EMULATOR_HOST=localhost:8080
```

### Secret Manager Secrets
- `google-oauth-client-id` - Google OAuth Client ID
- `google-oauth-client-secret` - Google OAuth Client Secret  
- `google-oauth-redirect-uri` - OAuth redirect URI
- `jwt-secret-key` - JWT signing secret (auto-generated)

## 🚨 Troubleshooting

### Common Issues

**"OAuth not configured" error:**
```bash
# Run setup script to configure OAuth
python setup_admin_oauth.py
```

**"Admin access only" error:**
```bash
# Check if your email is in admin list
# First user becomes admin automatically
# Contact existing admin to add you
```

**Firestore connection issues:**
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set project ID
export GOOGLE_CLOUD_PROJECT=your-project-id
```

**Secret Manager access denied:**
```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Check IAM permissions
gcloud projects get-iam-policy PROJECT_ID
```

### Debug Mode

Enable debug logging in your application:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Migration from Environment Variables

If you previously used environment variables for OAuth:

1. Run setup script to migrate to Secret Manager
2. Remove old environment variables:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET` 
   - `GOOGLE_REDIRECT_URI`
3. Restart server

## 🛡 Security Considerations

### Production Deployment
- Set `secure=True` for cookies (HTTPS only)
- Use proper domain for redirect URI
- Enable audit logging in Secret Manager
- Regular rotation of JWT secrets
- Monitor admin user additions

### Access Control
- Admin users should use strong Google accounts with 2FA
- Regular review of admin user list
- Session timeout enforcement
- Rate limiting on auth endpoints

## 📞 Support

For issues with the OAuth implementation:
1. Run `python test_admin_oauth.py` for diagnostics
2. Check application logs for detailed error messages
3. Verify Google Cloud permissions and API enablement
4. Ensure Firestore and Secret Manager are properly configured