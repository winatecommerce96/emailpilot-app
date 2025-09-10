# Authentication V2 Migration Guide

## Overview

EmailPilot has been upgraded with a modern authentication system that addresses the shortcomings of the previous OAuth implementation. The new system provides:

- ✅ **Clerk Integration** - Modern SSO provider with better performance
- ✅ **Multi-tenant Support** - Organizations can have isolated data
- ✅ **Refresh Tokens** - Automatic token renewal without re-login
- ✅ **API Key Management** - Programmatic access for services
- ✅ **Enhanced Security** - Token revocation, session management
- ✅ **Better Performance** - No more timeout issues

## What's Changed

### Previous Issues (Fixed)
- 🟥 Google OAuth timeouts (2+ second delays)
- 🟥 No refresh token support
- 🟥 Single-tenant only
- 🟥 No API key authentication
- 🟥 Complex secret management

### New Features
- ✅ Sub-second authentication responses
- ✅ Automatic token refresh
- ✅ Multi-organization support
- ✅ API keys with scopes
- ✅ Clerk SSO integration

## Migration Steps

### 1. Install Dependencies

```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
source .venv/bin/activate
pip install -r requirements.txt  # Updated with clerk-backend-api
```

### 2. Configure Clerk (Optional but Recommended)

Create a Clerk account at https://clerk.com and get your keys:

```bash
# Add to Google Secret Manager
gcloud secrets create clerk-secret-key --data-file=- <<< "sk_test_YOUR_CLERK_SECRET_KEY"
gcloud secrets create clerk-frontend-api --data-file=- <<< "YOUR_CLERK_FRONTEND_API"
gcloud secrets create clerk-webhook-secret --data-file=- <<< "whsec_YOUR_WEBHOOK_SECRET"
```

### 3. Test New Endpoints

Start the server:
```bash
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

Test authentication endpoints:

```bash
# Health check
curl http://localhost:8000/api/auth/v2/auth/me

# Register new user
curl -X POST http://localhost:8000/api/auth/v2/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "name": "Test User",
    "company": "Test Company"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@emailpilot.ai",
    "password": "demo"
  }'

# Refresh token
curl -X POST http://localhost:8000/api/auth/v2/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'

# Create API key (requires authentication)
curl -X POST http://localhost:8000/api/auth/v2/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "scopes": ["read", "write"],
    "expires_in_days": 90
  }'
```

### 4. Frontend Integration

The new authentication system includes React components:

```html
<!DOCTYPE html>
<html>
<head>
    <title>EmailPilot Login V2</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div id="root"></div>
    
    <!-- Load Auth Provider -->
    <script src="/static/dist/components/AuthV2Provider.js"></script>
    
    <!-- Load Login Component -->
    <script src="/static/dist/components/LoginV2.js"></script>
    
    <script>
        // Initialize app with auth provider
        const App = () => {
            return React.createElement(AuthV2Provider, null,
                React.createElement(LoginV2)
            );
        };
        
        ReactDOM.render(
            React.createElement(App),
            document.getElementById('root')
        );
    </script>
</body>
</html>
```

### 5. API Usage Examples

#### Using Access Tokens

```javascript
// Authenticated fetch with automatic refresh
const { authenticatedFetch } = useAuthV2();

const response = await authenticatedFetch('/api/calendar/clients');
const data = await response.json();
```

#### Using API Keys

```bash
# Use API key in header
curl http://localhost:8000/api/calendar/clients \
  -H "X-API-Key: ek_live_YOUR_API_KEY_HERE"

# Or in Python
import requests

headers = {
    'X-API-Key': 'ek_live_YOUR_API_KEY_HERE'
}

response = requests.get(
    'http://localhost:8000/api/calendar/clients',
    headers=headers
)
```

### 6. Multi-Tenant Usage

#### Create a Tenant

```javascript
const response = await authenticatedFetch('/api/auth/v2/tenants', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        name: 'Acme Corporation',
        domain: 'acme.com',
        settings: {
            theme: 'blue',
            features: ['calendar', 'reports']
        }
    })
});
```

#### Switch Tenants

```javascript
const { switchTenant } = useAuthV2();

await switchTenant('acme-corporation');
// User now operating in Acme Corporation context
```

## Migration Timeline

### Phase 1: Parallel Operation (Current)
- Both `/api/auth` (v1) and `/api/auth/v2` endpoints are active
- Existing sessions continue to work
- New features only in v2

### Phase 2: Soft Migration (Week 1-2)
- Update frontend to use v2 endpoints
- Migrate existing users to new system
- Keep v1 as fallback

### Phase 3: Deprecation (Week 3-4)
- Mark v1 endpoints as deprecated
- Show migration warnings
- Final user migration

### Phase 4: Removal (Week 5+)
- Remove v1 endpoints
- Clean up old auth code
- Full v2 operation

## Testing Checklist

- [ ] Register new user
- [ ] Login with email/password
- [ ] Login with Clerk SSO
- [ ] Login with Google OAuth (legacy)
- [ ] Refresh expired token
- [ ] Create API key
- [ ] Use API key for requests
- [ ] Create tenant
- [ ] Switch between tenants
- [ ] Revoke API key
- [ ] Logout and clear sessions

## Troubleshooting

### Common Issues

1. **Clerk not configured**
   - Error: "Clerk is not configured"
   - Solution: Add Clerk keys to Secret Manager (optional, system works without it)

2. **Token expired**
   - Error: "Token has expired"
   - Solution: Use refresh token endpoint or re-login

3. **Tenant access denied**
   - Error: "Access denied to this tenant"
   - Solution: Ensure user is member of tenant

4. **API key invalid**
   - Error: "Invalid API key"
   - Solution: Check key format (ek_live_* or ek_test_*)

### Debug Mode

Enable debug logging:
```python
# In main_firestore.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check auth headers:
```bash
curl -v http://localhost:8000/api/auth/v2/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Security Best Practices

1. **Store tokens securely**
   - Use httpOnly cookies for web apps
   - Use secure storage for mobile apps
   - Never log tokens

2. **Rotate API keys regularly**
   - Set expiration dates
   - Monitor usage
   - Revoke unused keys

3. **Implement rate limiting**
   - Already configured in middleware
   - Adjust limits as needed

4. **Use HTTPS in production**
   - Required for Clerk SSO
   - Protects tokens in transit

## Support

For issues or questions:
- Check logs: `tail -f logs/emailpilot_app.log`
- Test endpoints: Use the curl commands above
- Review code: `/app/api/auth_v2.py`

## Benefits Summary

The new authentication system provides:

1. **Better Performance**: No more 2+ second timeouts
2. **Enhanced Security**: Token revocation, API keys, session management
3. **Multi-tenant**: Isolated data per organization
4. **Developer Friendly**: API keys, refresh tokens, clear documentation
5. **Future Proof**: Ready for Auth0, Okta, or other providers

---

*Authentication V2 - Built for scale, security, and simplicity*