# EmailPilot Auth V2 Implementation

## Overview
Modern authentication system with Clerk integration support, multi-tenant capabilities, refresh tokens, and API key management.

## Current Status ✅
- **Backend API**: Fully functional (auth_v2_lite.py)
- **Frontend Components**: React components ready
- **Test Interface**: Available at `/test-auth-v2-final.html`
- **Clerk Integration**: Ready (keys in Secret Manager)

## Quick Start

### 1. Access Test Interface
```bash
# Open in browser
http://localhost:8000/static/test-auth-v2-final.html
```

### 2. Available Endpoints

#### Authentication
- `POST /api/auth/v2/auth/login` - Email/password login
- `POST /api/auth/v2/auth/register` - New user registration
- `POST /api/auth/v2/auth/refresh` - Refresh access token
- `POST /api/auth/v2/auth/logout` - Logout user
- `GET /api/auth/v2/auth/me` - Get current user info

#### SSO (Single Sign-On)
- `GET /api/auth/v2/auth/sso/clerk` - Clerk SSO login
- `GET /api/auth/v2/auth/sso/google` - Google SSO (legacy)
- `GET /api/auth/v2/auth/callback` - SSO callback handler

#### API Keys
- `GET /api/auth/v2/auth/api-keys` - List API keys
- `POST /api/auth/v2/auth/api-keys` - Create new API key
- `DELETE /api/auth/v2/auth/api-keys/{key_id}` - Revoke API key

#### Multi-Tenant
- `GET /api/auth/v2/tenants` - List available tenants
- `POST /api/auth/v2/tenants/{tenant_id}/switch` - Switch tenant

## Implementation Details

### Backend Structure
```
app/api/
├── auth_v2.py          # Full implementation (with Clerk SDK)
├── auth_v2_lite.py     # Lightweight version (no SDK dependency)
└── main_firestore.py   # Router registration
```

### Frontend Components
```
frontend/public/dist/components/
├── AuthV2Provider.js   # React context provider
└── LoginV2.js          # Login UI component
```

### Secret Manager Configuration
```
CLERK_SECRET_KEY                        # Clerk backend secret
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY      # Clerk frontend key
```

## Features

### 1. JWT Token Management
- **Access Token**: 15-minute expiration
- **Refresh Token**: 30-day expiration
- **Automatic Refresh**: Built into AuthV2Provider

### 2. Multi-Tenant Support
- Organization-level isolation
- Tenant switching without re-login
- Role-based permissions per tenant

### 3. API Key Management
- Scoped API keys (read, write, admin)
- Configurable expiration
- Usage tracking
- Prefix-based identification

### 4. SSO Integration
- Clerk integration (ready to activate)
- Google OAuth (legacy support)
- Automatic user provisioning

## Usage Examples

### JavaScript/React
```javascript
// Using AuthV2Provider
import { AuthV2Provider, useAuthV2 } from './components/AuthV2Provider';

function App() {
  return (
    <AuthV2Provider>
      <YourApp />
    </AuthV2Provider>
  );
}

// Inside component
function YourComponent() {
  const { 
    user, 
    login, 
    logout, 
    authenticatedFetch 
  } = useAuthV2();
  
  // Login
  await login('user@example.com', 'password');
  
  // Make authenticated API call
  const response = await authenticatedFetch('/api/calendar/events');
}
```

### Python/Backend
```python
from app.api.auth_v2_lite import get_current_user, require_auth

@router.get("/protected")
@require_auth
async def protected_route(user = Depends(get_current_user)):
    return {"message": f"Hello {user.email}"}
```

### cURL Examples
```bash
# Login
curl -X POST http://localhost:8000/api/auth/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@emailpilot.com","password":"admin123"}'

# Use access token
curl http://localhost:8000/api/auth/v2/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Refresh token
curl -X POST http://localhost:8000/api/auth/v2/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"YOUR_REFRESH_TOKEN"}'
```

## Migration from V1

### Key Differences
1. **Token-based**: No more session cookies
2. **Refresh tokens**: Automatic token renewal
3. **Multi-tenant**: Built-in organization support
4. **API keys**: Programmatic access support

### Migration Steps
1. Update frontend to use `AuthV2Provider`
2. Replace session checks with token validation
3. Update API calls to include Bearer token
4. Migrate user data to include tenant info

## Troubleshooting

### Common Issues

#### 1. Module Import Errors
- **Problem**: `ModuleNotFoundError: clerk_backend_api`
- **Solution**: Using auth_v2_lite.py (no SDK dependency)

#### 2. Token Expiration
- **Problem**: 401 errors after 15 minutes
- **Solution**: AuthV2Provider handles automatic refresh

#### 3. CORS Issues
- **Problem**: Cross-origin requests blocked
- **Solution**: Ensure using localhost:8000 (not 127.0.0.1)

#### 4. Static File 404
- **Problem**: Components not loading
- **Solution**: Files must be in `frontend/public/dist/`

## Security Considerations

1. **Token Storage**: Uses localStorage (consider httpOnly cookies for production)
2. **Secret Management**: All keys in Google Secret Manager
3. **Rate Limiting**: Implement on login/register endpoints
4. **Password Policy**: Enforce strong passwords
5. **Token Rotation**: Automatic with refresh tokens

## Next Steps

### To Enable Clerk SSO:
1. Ensure Clerk keys are in Secret Manager ✅
2. Configure Clerk dashboard with redirect URLs
3. Test SSO flow with test-auth-v2-final.html
4. Update user onboarding flow

### To Add Auth0:
1. Add Auth0 credentials to Secret Manager
2. Implement Auth0 endpoints in auth_v2.py
3. Add Auth0 button to LoginV2 component
4. Configure Auth0 dashboard

## Support

For issues or questions:
1. Check test interface: http://localhost:8000/static/test-auth-v2-final.html
2. Review logs: `uvicorn` output
3. Verify Secret Manager: `gcloud secrets list`
4. Test endpoints: Use cURL examples above