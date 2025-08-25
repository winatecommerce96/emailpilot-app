# OAuth Integration Guide - Asana & Klaviyo

This guide covers the OAuth integration endpoints for Asana and Klaviyo services in EmailPilot.

## Overview

The OAuth integration system allows users to connect their Asana and Klaviyo accounts securely using OAuth 2.0 flows. Tokens are stored securely in Google Secret Manager, while connection metadata is stored in Firestore.

## API Endpoints

All OAuth endpoints are available under `/api/integrations/` and require user authentication.

### Asana Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/integrations/asana/auth` | Initiate Asana OAuth flow |
| `GET` | `/api/integrations/asana/callback` | Handle Asana OAuth callback |
| `GET` | `/api/integrations/asana/status` | Check Asana connection status |
| `POST` | `/api/integrations/asana/disconnect` | Disconnect Asana integration |

### Klaviyo Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/integrations/klaviyo/auth` | Initiate Klaviyo OAuth flow |
| `GET` | `/api/integrations/klaviyo/callback` | Handle Klaviyo OAuth callback |
| `GET` | `/api/integrations/klaviyo/status` | Check Klaviyo connection status |
| `POST` | `/api/integrations/klaviyo/disconnect` | Disconnect Klaviyo integration |

## Configuration Requirements

### 1. Secret Manager Configuration

Set up the following secrets in Google Secret Manager:

```bash
# Asana OAuth credentials
gcloud secrets create asana-client-id --data="your-asana-client-id"
gcloud secrets create asana-client-secret --data="your-asana-client-secret"

# Klaviyo OAuth credentials  
gcloud secrets create klaviyo-client-id --data="your-klaviyo-client-id"
gcloud secrets create klaviyo-client-secret --data="your-klaviyo-client-secret"
```

### 2. OAuth Application Setup

#### Asana Application Setup
1. Go to [Asana Developer Console](https://app.asana.com/0/my-apps)
2. Create a new app or use existing app
3. Set redirect URI to: `http://localhost:8000/api/integrations/asana/callback`
4. Note down Client ID and Client Secret

#### Klaviyo Application Setup
1. Go to [Klaviyo Developer Portal](https://developers.klaviyo.com/en/docs/set_up_oauth)
2. Create a new app or use existing app
3. Set redirect URI to: `http://localhost:8000/api/integrations/klaviyo/callback`
4. Configure required scopes:
   - `lists:read` / `lists:write`
   - `campaigns:read` / `campaigns:write`
   - `flows:read` / `flows:write`
   - `metrics:read`
   - `profiles:read` / `profiles:write`
   - `segments:read`
   - `templates:read` / `templates:write`

## Usage Examples

### Frontend Integration (JavaScript)

```javascript
// Initiate OAuth flow
async function connectAsana() {
    const response = await fetch('/api/integrations/asana/auth', {
        headers: {
            'Authorization': `Bearer ${userToken}`
        }
    });
    
    const data = await response.json();
    if (data.authorization_url) {
        // Open OAuth flow in popup
        window.open(data.authorization_url, 'asana-oauth', 'width=600,height=700');
    }
}

// Check connection status
async function checkAsanaStatus() {
    const response = await fetch('/api/integrations/asana/status', {
        headers: {
            'Authorization': `Bearer ${userToken}`
        }
    });
    
    const status = await response.json();
    console.log('Connected:', status.connected);
}

// Disconnect service
async function disconnectAsana() {
    const response = await fetch('/api/integrations/asana/disconnect', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${userToken}`
        }
    });
    
    const result = await response.json();
    console.log(result.message);
}
```

### Python Client Example

```python
import requests

# Set up headers with authentication
headers = {
    'Authorization': f'Bearer {user_token}',
    'Content-Type': 'application/json'
}

# Check Klaviyo connection status
response = requests.get(
    'http://localhost:8000/api/integrations/klaviyo/status',
    headers=headers
)

if response.ok:
    status = response.json()
    print(f"Klaviyo connected: {status['connected']}")
else:
    print(f"Error: {response.status_code}")
```

## Data Storage

### Firestore Structure

```
users/{user_email}/integrations/{service}
{
    "service": "asana",
    "connected_at": "2024-01-15T10:00:00Z",
    "token_secret_id": "oauth-asana-user-email-com",
    "status": "connected",
    "user_id": "12345",
    "user_name": "John Doe",
    "user_email": "john@example.com"
}
```

### Secret Manager Storage

OAuth tokens are stored in Secret Manager with the naming pattern:
- `oauth-{service}-{user-email-sanitized}`
- Example: `oauth-asana-john-example-com`

Token data includes:
```json
{
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": "default",
    "data": {
        "id": "12345",
        "name": "John Doe",
        "email": "john@example.com"
    }
}
```

## Security Features

1. **CSRF Protection**: State parameter validation prevents CSRF attacks
2. **Secure Storage**: Tokens stored in Google Secret Manager, not database
3. **User Isolation**: Each user's tokens are completely isolated
4. **Popup Flow**: OAuth flows use popup windows to prevent redirect issues
5. **Automatic Cleanup**: Disconnection removes both Firestore data and Secret Manager entries

## Testing

### Test Interface
A test interface is available at: `http://localhost:8000/static/test-oauth.html`

### Command Line Testing
```bash
# Run the test script
python test_service_oauth.py
```

### Manual API Testing
```bash
# Check health
curl http://localhost:8000/health

# Test auth initiation (requires valid JWT token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/integrations/asana/auth

# Check connection status
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/integrations/asana/status
```

## Troubleshooting

### Common Issues

1. **"Client ID not configured"**
   - Ensure secrets are properly set in Secret Manager
   - Check that the service is loading the secrets correctly

2. **"Invalid state parameter"**
   - State parameters expire after OAuth flow completion
   - Ensure popup windows aren't being blocked

3. **"Failed to retrieve access token"**
   - Check OAuth application configuration
   - Verify redirect URIs match exactly
   - Check client credentials are correct

4. **Authentication errors**
   - Ensure valid JWT token is provided
   - Check token hasn't expired

### Debugging

Enable debug logging to see detailed OAuth flow information:
```python
import logging
logging.getLogger('app.api.service_oauth').setLevel(logging.DEBUG)
```

## Production Considerations

1. **Redirect URIs**: Update redirect URIs to production domain
2. **CORS**: Configure CORS properly for production frontend
3. **Token Refresh**: Implement token refresh logic for long-lived integrations
4. **Rate Limiting**: Consider implementing rate limiting for OAuth endpoints
5. **Monitoring**: Add monitoring for OAuth flow success/failure rates

## Next Steps

1. Implement token refresh functionality
2. Add webhook endpoints for service notifications
3. Create service-specific API wrappers using stored tokens
4. Add integration health monitoring
5. Implement bulk operations for connected services