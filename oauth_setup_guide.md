# OAuth Integration Setup Guide

## Overview
EmailPilot now supports OAuth integration with Asana and Klaviyo. This guide provides the complete setup process and troubleshooting steps.

## Quick Start

### 1. Test the Integration
```bash
# Start the server
uvicorn main_firestore:app --port 8000 --host localhost --reload

# Open the test page
open http://localhost:8000/oauth_integration_test.html
```

### 2. OAuth Flow
1. Click "Test Guest Login" to authenticate
2. Click "Connect Asana" or "Connect Klaviyo"
3. Complete OAuth in the popup window
4. Connection status updates automatically

## Configuration Requirements

### Asana OAuth Setup

1. **Create Asana App**
   - Visit: https://app.asana.com/0/developer-console
   - Create new app
   - Set OAuth callback URL: `http://localhost:8000/api/integrations/asana/callback`

2. **Configure Secrets**
   ```bash
   # Store in Google Secret Manager
   gcloud secrets create asana-client-id --data-file=- <<< "YOUR_ASANA_CLIENT_ID"
   gcloud secrets create asana-client-secret --data-file=- <<< "YOUR_ASANA_CLIENT_SECRET"
   ```

### Klaviyo OAuth Setup

1. **Create Klaviyo App**
   - Visit: https://www.klaviyo.com/oauth/client
   - Create new OAuth app
   - Set redirect URI: `http://localhost:8000/api/integrations/klaviyo/callback`

2. **App Configuration**
   - **App Name**: EmailPilot AI - Campaign Automation Platform
   - **Description**: AI-powered email campaign automation and performance optimization
   - **OAuth Installation URL**: `http://localhost:8000/api/integrations/klaviyo/auth`
   - **Settings URL**: `http://localhost:8000/settings/integrations`
   - **Scopes Required**:
     - campaigns:read
     - campaigns:write
     - flows:read
     - flows:write
     - metrics:read
     - profiles:read
     - templates:read
     - lists:read

3. **Configure Secrets**
   ```bash
   gcloud secrets create klaviyo-client-id --data-file=- <<< "YOUR_KLAVIYO_CLIENT_ID"
   gcloud secrets create klaviyo-client-secret --data-file=- <<< "YOUR_KLAVIYO_CLIENT_SECRET"
   ```

## API Endpoints

### Authentication Flow
- `GET /api/integrations/{service}/auth` - Initiate OAuth flow
- `GET /api/integrations/{service}/callback` - OAuth callback handler
- `GET /api/integrations/{service}/status` - Check connection status
- `POST /api/integrations/{service}/disconnect` - Disconnect service

### Supported Services
- `asana` - Project management integration
- `klaviyo` - Email marketing platform

## Frontend Integration

### Using LinkServiceModal Component
```javascript
import LinkServiceModal from '/static/dist/LinkServiceModal.js';

// In your React component
<LinkServiceModal
    userId={currentUser.email}
    currentConnections={{
        asana: false,
        klaviyo: false
    }}
    onClose={() => setShowModal(false)}
    onConnectionUpdate={(connections) => {
        console.log('Updated connections:', connections);
    }}
/>
```

### Direct OAuth Integration
```javascript
// Get authorization URL
const response = await fetch('/api/integrations/klaviyo/auth', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

const { authorization_url } = await response.json();

// Open OAuth popup
const popup = window.open(authorization_url, 'OAuth', 'width=600,height=700');

// Listen for completion
window.addEventListener('message', (event) => {
    if (event.data.success && event.data.service === 'klaviyo') {
        console.log('Klaviyo connected successfully!');
    }
});
```

## Security Considerations

### Token Storage
- OAuth tokens stored in Google Secret Manager
- Secret naming: `oauth-{service}-{user-email-sanitized}`
- Connection metadata stored in Firestore

### CSRF Protection
- State parameter generated for each OAuth request
- State verified on callback
- Timeout after 5 minutes

### Permissions
- User must be authenticated to EmailPilot
- Each user's OAuth connections are isolated
- Tokens encrypted at rest

## Troubleshooting

### Common Issues

1. **"Not authenticated" error**
   - Ensure user is logged into EmailPilot first
   - Check JWT token in localStorage

2. **Redirect URI mismatch**
   - Verify callback URL in OAuth provider settings
   - Must match exactly: `http://localhost:8000/api/integrations/{service}/callback`

3. **Popup blocked**
   - Enable popups for localhost:8000
   - Check browser popup blocker settings

4. **CORS errors**
   - Server must run on `localhost` (not 127.0.0.1)
   - Use: `uvicorn main_firestore:app --host localhost`

### Debug Tools

1. **Test Page**: `oauth_integration_test.html`
   - Complete testing workflow
   - Debug console
   - Test results tracking

2. **Simple Test**: `test_oauth_flow.html`
   - Basic OAuth flow testing
   - Manual step-by-step process

3. **Check Logs**
   ```bash
   # Server logs
   tail -f .app_uvicorn.out
   
   # Browser console
   # Open DevTools > Console to see detailed errors
   ```

## Production Deployment

### Update Redirect URIs
```python
# app/core/settings.py
asana_redirect_uri: str = "https://emailpilot.ai/api/integrations/asana/callback"
klaviyo_redirect_uri: str = "https://emailpilot.ai/api/integrations/klaviyo/callback"
```

### Update OAuth Providers
1. Update redirect URIs in Asana app settings
2. Update redirect URIs in Klaviyo app settings
3. Ensure production domain is verified

### Environment Variables
```bash
export GOOGLE_CLOUD_PROJECT=emailpilot-production
export ENVIRONMENT=production
export SECRET_MANAGER_ENABLED=true
```

## Klaviyo App Store Listing

### App Titles (65 characters max)
1. **EmailPilot: AI-Powered Campaign Automation & Audit Platform**
2. **EmailPilot: Smart Performance Audits for Klaviyo Success**
3. **EmailPilot: Automate, Analyze & Optimize Email Campaigns**
4. **EmailPilot: Your AI Copilot for Klaviyo Marketing**
5. **EmailPilot: Revenue-Driven Email Optimization Suite**

### App Description
EmailPilot is an AI-powered automation platform that supercharges your Klaviyo email marketing with intelligent campaign management, automated performance audits, and real-time optimization recommendations. 

Key features:
- **Automated Performance Audits**: Daily analysis of campaign metrics with actionable insights
- **AI Campaign Planning**: Smart calendar with drag-and-drop scheduling and content suggestions
- **Revenue Optimization**: Identify and fix underperforming flows and segments
- **Multi-Client Management**: Manage multiple Klaviyo accounts from one dashboard
- **Real-Time Alerts**: Instant notifications for critical performance issues
- **Goal Tracking**: Set and monitor KPIs with automated progress reports

Perfect for agencies, e-commerce teams, and marketing professionals who want to maximize their Klaviyo ROI through intelligent automation and data-driven insights.

## Support

For issues or questions:
- GitHub Issues: https://github.com/emailpilot/emailpilot-app/issues
- Documentation: https://docs.emailpilot.ai
- Support Email: support@emailpilot.ai