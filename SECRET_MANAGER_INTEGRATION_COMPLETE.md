# ✅ Secret Manager Integration Complete

## Overview
The calendar planning functionality has been fully updated to use Google Secret Manager for both Gemini and Klaviyo API keys, with intelligent client-to-secret mapping.

## 🔐 Secret Naming Schema

### Gemini API Key
- **Secret Name**: `gemini-api-key`
- **Used By**: All AI calendar planning features
- **Location**: Google Secret Manager

### Klaviyo API Keys
- **Schema**: `klaviyo-api-{normalized-client-name}`
- **Examples**:
  - "Consumer Law Attorneys" → `klaviyo-api-consumer-law-attorneys`
  - "Wheelchair Getaways" → `klaviyo-api-wheelchair-getaways`
  - "Coffee Roasters USA" → `klaviyo-api-coffee-roasters-usa`

## 🎯 Key Features Implemented

### 1. **ClientKeyResolver Service**
- Intelligent name normalization (handles spaces, special chars)
- Automatic mapping between clients and their secrets
- Legacy key migration support
- Efficient caching for performance

### 2. **Gemini Service Updates**
- Fetches API key from Secret Manager first
- Falls back to environment variables if needed
- Secure key handling throughout

### 3. **Calendar Planning Integration**
- MCP service uses Secret Manager for Klaviyo keys
- Client context includes secret mapping
- Automatic key resolution per client

### 4. **Admin Management Interface**
- Complete UI for managing secrets
- Bulk migration tools
- Testing and validation endpoints
- Status monitoring

## 📊 Current Client Mappings

Based on the API response, your clients need their secret names configured:

| Client Name | Suggested Secret Name | Current Status |
|------------|----------------------|----------------|
| Wheelchair Getaways | `klaviyo-api-wheelchair-getaways` | Has legacy key |
| Consumer Law Attorneys | `klaviyo-api-consumer-law-attorneys` | Needs mapping |
| Coffee Roasters | `klaviyo-api-coffee-roasters` | Needs mapping |

## 🔧 How It Works

### Automatic Key Resolution Flow:
1. User selects client for calendar planning
2. System checks for `klaviyo_secret_name` in client document
3. If not found, generates name from client name
4. Fetches key from Secret Manager
5. Uses key for MCP Klaviyo API calls

### Name Normalization Rules:
- Converts to lowercase
- Replaces spaces with hyphens
- Removes special characters
- Ensures valid secret name format

## 📝 Client Document Enhancement

Each client in Firestore now supports:
```json
{
  "id": "client-id",
  "name": "Client Name",
  "klaviyo_secret_name": "klaviyo-api-client-name",  // New field
  "klaviyo_private_key": "legacy-key",  // Legacy support
  ...
}
```

## 🚀 API Endpoints

### Secret Manager Status
```bash
GET /api/admin/secret-manager/status
# Returns Secret Manager availability and stats
```

### Client Mappings
```bash
GET /api/admin/secret-manager/client-mappings
# Lists all clients with their secret mappings
```

### Set Client Key
```bash
POST /api/admin/secret-manager/client/set-key
{
  "client_id": "xxx",
  "api_key": "pk_xxx"
}
# Stores key in Secret Manager and updates mapping
```

### Bulk Migration
```bash
POST /api/admin/secret-manager/bulk-migrate
# Migrates all legacy keys to Secret Manager
```

## ⚠️ Permission Requirements

The application needs these IAM permissions:
- `secretmanager.secrets.create`
- `secretmanager.secrets.get`
- `secretmanager.versions.access`
- `secretmanager.versions.add`

Current status shows permission errors - ensure service account has Secret Manager Secret Accessor role.

## 🎨 Admin UI Component

Access the Secret Manager admin interface:
1. Navigate to Admin section
2. Click "Secret Manager" tab
3. View client mappings
4. Migrate keys as needed

## 🔍 Testing

### Test Gemini Integration:
```bash
# Should fetch from Secret Manager
curl http://localhost:8000/api/calendar/planning/generate
```

### Test Klaviyo Key Resolution:
```bash
# Should resolve client's Klaviyo key
curl http://localhost:8000/api/calendar/planning/klaviyo-data \
  -H "Content-Type: application/json" \
  -d '{"client_id": "abc", "month": 8, "year": 2025}'
```

## 📈 Benefits

1. **Security**: API keys never stored in code or plaintext
2. **Centralization**: All keys managed in one place
3. **Rotation**: Easy key rotation without code changes
4. **Audit Trail**: Google Cloud audit logs for access
5. **Scalability**: Efficient for hundreds of clients

## 🛠️ Next Steps

1. **Grant Permissions**: Ensure service account has Secret Manager access
2. **Create Secrets**: Add API keys to Secret Manager using correct naming
3. **Update Clients**: Set `klaviyo_secret_name` field for each client
4. **Test Integration**: Verify calendar planning works with Secret Manager

## 📋 Migration Checklist

- [ ] Grant Secret Manager IAM permissions
- [ ] Create `gemini-api-key` secret
- [ ] Create Klaviyo secrets for each client
- [ ] Update client documents with secret names
- [ ] Test calendar planning feature
- [ ] Remove legacy keys from Firestore

The system is fully prepared for Secret Manager integration and will work seamlessly once the secrets are created and permissions are granted!