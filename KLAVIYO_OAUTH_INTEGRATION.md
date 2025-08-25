# Klaviyo OAuth Integration & Auto-Client Creation

## Overview

EmailPilot now supports Klaviyo OAuth authentication with automatic client creation in the Enhanced Client Management system. When users connect their Klaviyo accounts via OAuth, the system automatically creates or updates client records with all necessary metadata.

## Features

- **OAuth 2.0 Authentication**: Secure authorization flow with PKCE (Proof Key for Code Exchange)
- **Auto-Client Creation**: Automatically creates client records upon successful OAuth connection
- **Token Management**: Secure encryption and storage of OAuth tokens
- **Token Refresh**: Automatic token refresh before expiration
- **Idempotent Operations**: Re-authentication updates existing clients without creating duplicates
- **Real-time UI Updates**: Admin interface reflects new clients immediately

## Setup

### 1. Prerequisites

- Klaviyo OAuth application (create at https://www.klaviyo.com/oauth/client-management)
- Google Cloud Project with Firestore and Secret Manager enabled
- Python 3.11+ environment

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required Klaviyo OAuth settings
KLAVIYO_OAUTH_CLIENT_ID=your-klaviyo-oauth-client-id
KLAVIYO_OAUTH_CLIENT_SECRET=your-klaviyo-oauth-client-secret
KLAVIYO_OAUTH_REDIRECT_URI=http://localhost:8000/api/integrations/klaviyo/oauth/callback
KLAVIYO_OAUTH_SCOPES=accounts:read,campaigns:read,flows:read,lists:read,metrics:read,profiles:read,segments:read

# Encryption settings
ENCRYPTION_KEY=your-base64-encryption-key  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Feature flag
FEATURE_KLAVIYO_OAUTH=true
```

### 3. Start the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

## Usage

### Connecting a Klaviyo Account

1. Navigate to **Admin → Clients** (`http://localhost:8000/admin/clients`)
2. Click the **🔗 Connect Klaviyo** button in the top toolbar
3. Authorize the application in Klaviyo's consent screen
4. Upon successful authorization, you'll be redirected back to the clients page
5. The new client will appear in the clients list automatically

### Client Data Model

When a Klaviyo account is connected, the following client record is created:

```javascript
{
  "client_id": "uuid-v4",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "owner_user_id": "user@example.com",
  "source": "klaviyo",
  "display_name": "Account Name from Klaviyo",
  "status": "active",
  "tags": ["new", "oauth"],
  "klaviyo": {
    "account_id": "kl_123",
    "account_name": "Account Name",
    "email_domain": "example.com",
    "company_id": "comp_123",
    "contact_email": "contact@example.com",
    "lists_count": 10,
    "segments_count": 5,
    "test_account": false,
    "metadata": {
      "timezone": "America/New_York",
      "preferred_currency": "USD",
      "locale": "en-US"
    }
  },
  "oauth": {
    "provider": "klaviyo",
    "access_token": "encrypted_token",
    "refresh_token": "encrypted_refresh",
    "expires_at": "2024-01-15T11:30:00Z",
    "scopes": ["accounts:read", "lists:read"],
    "connected_at": "2024-01-15T10:30:00Z"
  }
}
```

## API Endpoints

### Start OAuth Flow
```http
GET /api/integrations/klaviyo/oauth/start?redirect_path=/admin/clients
```
Initiates the OAuth flow and redirects to Klaviyo consent page.

### OAuth Callback
```http
GET /api/integrations/klaviyo/oauth/callback?code=AUTH_CODE&state=STATE
```
Handles the OAuth callback, exchanges code for tokens, and creates/updates the client.

### Refresh Token
```http
POST /api/integrations/klaviyo/oauth/refresh/{client_id}
```
Manually refresh OAuth tokens for a specific client.

### Check OAuth Status
```http
GET /api/integrations/klaviyo/status
```
Returns the current user's Klaviyo OAuth connection status and linked accounts.

## Security

### Token Encryption
- All OAuth tokens are encrypted using Fernet symmetric encryption
- Encryption keys are stored in environment variables or Secret Manager
- Tokens are encrypted before storage in Firestore

### PKCE Protection
- The OAuth flow uses PKCE (RFC 7636) for enhanced security
- Code verifier and challenge are generated for each authorization request
- Protects against authorization code interception attacks

### State Parameter
- Random state parameter generated for CSRF protection
- State is validated on callback to ensure request integrity

## Error Handling

### OAuth Errors
- **Invalid State**: Returns user to clients page with error message
- **Token Exchange Failure**: Logs error and shows user-friendly message
- **API Unavailable**: Implements retry logic with exponential backoff

### User Experience
- All errors display non-blocking toast notifications
- Users can retry connection immediately
- URL parameters are cleaned up after processing

## Testing

Run the test suite:

```bash
# Unit tests
pytest tests/repositories/test_clients_repo.py -v

# Integration tests
pytest tests/integrations/test_klaviyo_oauth_flow.py -v

# All tests
pytest tests/ -v
```

## Manual Testing

1. **Happy Path**:
   - Click "Connect Klaviyo"
   - Complete OAuth consent
   - Verify new client appears in list
   - Check client details match Klaviyo account

2. **Idempotency**:
   - Connect same Klaviyo account again
   - Verify no duplicate clients created
   - Check `updated_at` timestamp changed

3. **Token Refresh**:
   - Wait for token to near expiration
   - Make an API call requiring authentication
   - Verify token refreshes automatically

4. **Error Scenarios**:
   - Cancel OAuth consent → verify error message
   - Use invalid state → verify CSRF protection
   - Disconnect network during callback → verify error handling

## Troubleshooting

### Common Issues

1. **"Klaviyo OAuth not configured" error**
   - Ensure `KLAVIYO_OAUTH_CLIENT_ID` and `KLAVIYO_OAUTH_CLIENT_SECRET` are set
   - Check environment variables are loaded correctly

2. **Redirect URI mismatch**
   - Verify redirect URI in `.env` matches Klaviyo OAuth app settings
   - Ensure using correct protocol (http/https) and port

3. **Tokens not encrypting**
   - Check `ENCRYPTION_KEY` is set and valid
   - Verify `cryptography` package is installed

4. **Client not appearing after OAuth**
   - Check browser console for JavaScript errors
   - Verify Firestore permissions allow write access
   - Check server logs for client creation errors

## Architecture

### Components

1. **OAuth Service** (`app/services/klaviyo_oauth_service.py`)
   - Handles OAuth flow mechanics
   - Token exchange and refresh
   - Account metadata retrieval

2. **OAuth Router** (`app/api/integrations/klaviyo_oauth.py`)
   - FastAPI endpoints for OAuth flow
   - Session management and state validation
   - Client creation orchestration

3. **Clients Repository** (`app/repositories/clients_repo.py`)
   - Firestore CRUD operations
   - Idempotent upsert logic
   - Client data mapping

4. **Crypto Service** (`app/services/crypto_service.py`)
   - Token encryption/decryption
   - Key derivation and management
   - Secure token storage

5. **Frontend Integration** (`frontend/public/components/AdminClientManagement.js`)
   - Connect button UI
   - OAuth callback handling
   - Real-time client list updates

## Future Enhancements

- [ ] WebSocket/SSE for real-time client updates
- [ ] Bulk OAuth connection for multiple accounts
- [ ] OAuth connection health monitoring
- [ ] Automatic token refresh scheduling
- [ ] Client data enrichment from Klaviyo API
- [ ] OAuth audit logging
- [ ] Multi-user client sharing

## Migration Notes

For existing clients with API keys:
- OAuth clients coexist with API key clients
- OAuth takes precedence when both exist
- API keys remain functional for backward compatibility
- Migration tool available to convert API key clients to OAuth

## Changelog

### v1.0.0 (2024-01-15)
- Initial implementation of Klaviyo OAuth integration
- Auto-client creation upon successful authorization
- Token encryption and secure storage
- PKCE support for enhanced security
- Idempotent client upsert operations
- Frontend integration with Connect button
- Comprehensive test coverage