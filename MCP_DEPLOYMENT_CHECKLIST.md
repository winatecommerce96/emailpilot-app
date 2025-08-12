# 🚀 MCP Management System - Deployment Checklist

## Pre-Deployment Checklist
- [x] Package structure follows EmailPilot guidelines
- [x] Deployment script uses safe template
- [x] No automatic dependency installation
- [x] Documentation included (README.md)
- [x] Compatibility tested locally
- [x] Package ZIP created: `mcp-management-v1.0.0.zip`

## 📦 Package Details
- **Package Name:** MCP Management System
- **Version:** 1.0.0
- **Size:** ~50KB (compressed)
- **Components:**
  - Frontend: MCPManagement.js React component
  - Backend: API routes, services, models, schemas
  - Database: Migration script included
  - Testing: Compatibility test script

## 🔄 Deployment Steps

### 1. Upload Package (5 minutes)
- [ ] Access https://emailpilot.ai/admin
- [ ] Login with admin credentials
- [ ] Navigate to "Package Management"
- [ ] Click "Upload Package"
- [ ] Select `mcp-management-v1.0.0.zip`
- [ ] Enter package name: "MCP Management System"
- [ ] Enter description: "Multi-model AI integration for Klaviyo data analysis"
- [ ] Click "Upload"

### 2. Deploy Package (5 minutes)
- [ ] Find "MCP Management System" in uploaded packages
- [ ] Click "Deploy" button
- [ ] Monitor deployment output
- [ ] Note the integration directory path (e.g., `/integrations/mcp_management_YYYYMMDD_HHMMSS`)

### 3. Manual Backend Integration (15 minutes)
- [ ] SSH or access the server
- [ ] Navigate to integration directory
- [ ] Review INTEGRATION_INSTRUCTIONS.md
- [ ] Copy backend modules:
  ```bash
  # From integration directory
  cp -r api/mcp.py ../../app/api/
  cp -r services/mcp_service.py ../../app/services/
  cp -r services/secret_manager.py ../../app/services/
  cp -r models/mcp_client.py ../../app/models/
  cp -r schemas/mcp_client.py ../../app/schemas/
  cp -r core/auth.py ../../app/core/
  ```
- [ ] Update main.py to include MCP router:
  ```python
  from app.api import mcp
  app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP Management"])
  ```

### 4. Update Dependencies (5 minutes)
- [ ] Edit requirements.txt
- [ ] Add new dependencies:
  ```
  openai>=1.0.0
  anthropic>=0.18.0
  google-generativeai>=0.3.0
  httpx>=0.24.0
  PyJWT>=2.8.0
  ```
- [ ] Install dependencies: `pip install -r requirements.txt`

### 5. Database Migration (5 minutes)
- [ ] Run migration script:
  ```bash
  python migrate_mcp_only.py
  ```
- [ ] Verify tables created:
  - mcp_clients
  - mcp_usage
  - mcp_model_configs

### 6. Configuration (5 minutes)
- [ ] Update app/core/config.py if needed
- [ ] Set environment variables (if not already set):
  - GOOGLE_CLOUD_PROJECT
  - SECRET_KEY
- [ ] Verify Google Secret Manager is accessible

### 7. Restart Application (5 minutes)
- [ ] Via Admin Dashboard: Click "Restart Application"
- [ ] Or via command line:
  ```bash
  gcloud run services update emailpilot-api --region=us-central1
  ```
- [ ] Wait for service to be ready

### 8. Verification (10 minutes)
- [ ] Test health endpoint: `curl https://emailpilot.ai/health`
- [ ] Test MCP API (requires auth token):
  ```bash
  curl https://emailpilot.ai/api/mcp/models \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```
- [ ] Access Admin Dashboard
- [ ] Navigate to Admin > MCP Management
- [ ] Verify UI loads correctly

### 9. Initial Configuration (10 minutes)
- [ ] Add first MCP client:
  - Name: "Test Client"
  - Account ID: "test-001"
  - Klaviyo API Key: (your test key)
  - OpenAI API Key: (optional)
  - Gemini API Key: (optional)
- [ ] Test connection for each configured provider
- [ ] Verify usage tracking works

### 10. Production Testing (10 minutes)
- [ ] Execute a test tool:
  ```json
  POST /api/mcp/execute
  {
    "client_id": "YOUR_CLIENT_ID",
    "tool_name": "get_campaigns",
    "parameters": {"limit": 1},
    "provider": "claude"
  }
  ```
- [ ] Check usage statistics
- [ ] Verify cost tracking
- [ ] Test rate limiting

## 🔍 Post-Deployment Verification

### Success Indicators
- [ ] MCP Management tab visible in Admin interface
- [ ] Can create and edit MCP clients
- [ ] API keys stored securely (not visible in UI)
- [ ] Connection tests pass for configured providers
- [ ] Usage tracking updates after tool execution
- [ ] No errors in application logs

### Monitoring
- [ ] Check Google Cloud Logs for errors
- [ ] Monitor Cloud Run metrics
- [ ] Review Firestore for package deployment record
- [ ] Verify Secret Manager contains API keys

## 🚨 Rollback Plan

If issues occur:

### Quick Rollback (5 minutes)
1. Remove MCP router from main.py
2. Restart application
3. System continues without MCP features

### Full Rollback (15 minutes)
1. Remove copied files:
   ```bash
   rm app/api/mcp.py
   rm app/services/mcp_service.py
   rm app/services/secret_manager.py
   rm app/models/mcp_client.py
   rm app/schemas/mcp_client.py
   rm app/core/auth.py  # Only if it didn't exist before
   ```
2. Remove dependencies from requirements.txt
3. Drop MCP tables (optional):
   ```sql
   DROP TABLE mcp_usage;
   DROP TABLE mcp_clients;
   DROP TABLE mcp_model_configs;
   ```
4. Restart application
5. Remove package record from Firestore

## 📞 Support Contacts

- **Technical Issues:** Check Google Cloud Logs
- **Package Issues:** Review integration directory
- **Database Issues:** Check migration script output
- **UI Issues:** Verify component loaded in browser console

## ✅ Final Confirmation

- [ ] All verification steps passed
- [ ] No errors in logs
- [ ] Feature working as expected
- [ ] Documentation updated
- [ ] Team notified of deployment

## 📝 Notes

**Deployment Date:** _______________
**Deployed By:** _______________
**Integration Directory:** _______________
**Issues Encountered:** _______________
**Resolution:** _______________

---

**Package Ready for Deployment:** ✅

The MCP Management System package is fully prepared and ready for deployment via the EmailPilot Admin Dashboard. Follow this checklist to ensure a smooth deployment process.