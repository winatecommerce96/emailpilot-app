# MCP Cloud Function Frontend Update - Deployment Checklist

## Pre-Deployment Verification

### 1. Cloud Functions Status Check
- [ ] Cloud Functions are deployed and accessible
  - Health: https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health
  - Models: https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models  
  - Clients: https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients

### 2. Test Endpoints Before Deployment
- [ ] Open `test_cloud_function_endpoints.html` in browser
- [ ] Click "Test All Endpoints" button
- [ ] Verify all endpoints show ✅ Success status
- [ ] If any fail, fix Cloud Functions before deploying frontend

### 3. Package Contents Verification
- [ ] `frontend/components/mcp-config.js` - Configuration file
- [ ] `frontend/components/MCPManagement.js` - Updated management component
- [ ] `frontend/components/MCPTestingInterface.js` - Updated testing interface
- [ ] `deploy_to_emailpilot.sh` - Deployment script
- [ ] `rollback_script.sh` - Rollback capability
- [ ] `README.md` - Documentation

## Deployment Process

### 1. Create ZIP Package
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
zip -r mcp-cloud-function-frontend-update.zip mcp-cloud-function-frontend-update/
```

### 2. Upload to EmailPilot
- [ ] Go to https://emailpilot.ai/admin
- [ ] Navigate to Package Management
- [ ] Upload `mcp-cloud-function-frontend-update.zip`
- [ ] Package name: "MCP Cloud Function Frontend Update v1.0.0"
- [ ] Description: "Updates frontend to use Cloud Function endpoints instead of local /api/mcp/*"

### 3. Deploy Package
- [ ] Click "Deploy" button for the uploaded package
- [ ] Monitor deployment output for success messages
- [ ] Verify no error messages in deployment log
- [ ] Check that backup was created successfully

## Post-Deployment Verification

### 1. Initial System Check
- [ ] Go to EmailPilot Admin Dashboard
- [ ] Navigate to MCP Management section
- [ ] Verify "🟢 Cloud Functions Connected" status appears at top
- [ ] Check that endpoint URL shows Cloud Function address

### 2. Basic Functionality Test
- [ ] Can load list of MCP clients (or shows empty state if none exist)
- [ ] Can click "Add New Client" without errors
- [ ] Interface loads without JavaScript errors in browser console
- [ ] No 404 errors in network tab

### 3. Production Testing Interface
- [ ] Click "Production Testing" button (if available)
- [ ] Run "Quick Test (2 min)" 
- [ ] Verify Cloud Function connection status shows green
- [ ] Check that test phases complete successfully
- [ ] Export test results to verify functionality

### 4. Full CRUD Operations Test
- [ ] Create a test MCP client
- [ ] Edit the test client
- [ ] Test client connections
- [ ] Delete the test client
- [ ] All operations should use Cloud Function URLs

## Troubleshooting

### If Deployment Fails
- [ ] Check deployment logs in EmailPilot admin dashboard
- [ ] Verify package structure and file permissions
- [ ] Ensure deployment script is executable
- [ ] Contact support with error details

### If Cloud Functions Don't Work After Deployment
- [ ] Check browser console for CORS errors
- [ ] Verify Cloud Functions are still accessible directly
- [ ] Check if authentication token is being sent correctly
- [ ] Try refreshing the browser cache

### If System Becomes Unusable
- [ ] Run rollback script immediately:
  ```bash
  /app/staged_packages/mcp_cloud_function_update_*/rollback_script.sh
  ```
- [ ] Or manually restore from backup:
  ```bash
  cp /app/frontend/public/components/backups/[timestamp]/*.backup /app/frontend/public/components/
  rm /app/frontend/public/components/mcp-config.js
  ```

## Success Criteria

### ✅ Deployment is Successful When:
1. **No 404 Errors**: MCP system no longer returns 404 errors
2. **Cloud Function Connectivity**: Status shows "🟢 Cloud Functions Connected"
3. **API Operations Work**: Can create, read, update, delete MCP clients
4. **Testing Passes**: Production testing interface shows all green results
5. **Performance**: Cloud Function calls complete within reasonable time
6. **Error Handling**: Proper error messages for failed Cloud Function calls

### 📊 Monitoring Points
- Browser console should show no JavaScript errors
- Network tab should show calls to `us-central1-emailpilot-438321.cloudfunctions.net`
- Response times should be under 5 seconds for most operations
- CORS headers should be present in responses

## Rollback Plan

### Automatic Rollback
- Use included `rollback_script.sh` to restore previous components
- Removes mcp-config.js and restores original component files
- Safe to run without data loss

### Manual Rollback
1. Restore original components from backup directory
2. Remove `mcp-config.js` file
3. Clear browser cache
4. Test original functionality works

## Support Information

- **Package Version**: v1.0.0
- **Cloud Function Project**: emailpilot-438321
- **Cloud Function Region**: us-central1
- **Endpoints Updated**: 3 components + 1 configuration file
- **Deployment Type**: Frontend-only update (no backend changes)
- **Reversible**: Yes, with included rollback script

---

**Final Check**: After deployment, the MCP system should work seamlessly with Cloud Functions and users should notice no difference except that 404 errors are resolved.