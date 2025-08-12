# 🧪 MCP Management System - Production Testing Guide

## Overview
This guide provides step-by-step instructions for testing the MCP (Model Context Protocol) Management System in production after successful deployment.

## 🔍 Phase 1: Verify Deployment

### 1.1 Check Package Deployment Status
```bash
# SSH into production or use Cloud Shell
gcloud run services describe emailpilot-api --region=us-central1 --format="value(status.url)"

# Check deployment logs
gcloud run logs read --service=emailpilot-api --region=us-central1 --limit=50 | grep -i "mcp"
```

### 1.2 Verify Frontend Components
1. Navigate to https://emailpilot.ai/admin
2. Login with admin credentials
3. Check if "MCP Management" appears in the admin menu
4. If not visible, check browser console for errors

### 1.3 Verify API Endpoints
```bash
# Get auth token first (replace with actual login)
TOKEN=$(curl -X POST https://emailpilot.ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' | jq -r '.access_token')

# Test MCP endpoints
curl -X GET https://emailpilot.ai/api/mcp/models \
  -H "Authorization: Bearer $TOKEN"

curl -X GET https://emailpilot.ai/api/mcp/clients \
  -H "Authorization: Bearer $TOKEN"
```

## 🎯 Phase 2: Functional Testing

### 2.1 Create Test MCP Client

1. **Via Admin UI**:
   - Go to https://emailpilot.ai/admin
   - Navigate to MCP Management
   - Click "Add New Client"
   - Enter test data:
     ```
     Name: Test Production Client
     Account ID: test-prod-001
     Klaviyo API Key: [Use a valid test key]
     OpenAI API Key: [Optional - for testing OpenAI]
     Gemini API Key: [Optional - for testing Gemini]
     Default Provider: claude
     Rate Limit: 60 req/min
     Token Limit: 100000/day
     ```
   - Click "Save"

2. **Via API**:
   ```bash
   curl -X POST https://emailpilot.ai/api/mcp/clients \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test API Client",
       "account_id": "test-api-001",
       "klaviyo_api_key": "pk_test_key",
       "enabled": true,
       "read_only": true,
       "default_model_provider": "claude",
       "rate_limit_requests_per_minute": 60,
       "rate_limit_tokens_per_day": 100000
     }'
   ```

### 2.2 Test Connection to Each Provider

#### Test Claude (Klaviyo Integration)
```bash
CLIENT_ID="[client-id-from-step-2.1]"

curl -X POST https://emailpilot.ai/api/mcp/clients/$CLIENT_ID/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_provider": "claude",
    "test_query": "List available Klaviyo tools"
  }'
```

#### Test OpenAI
```bash
curl -X POST https://emailpilot.ai/api/mcp/clients/$CLIENT_ID/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_provider": "openai",
    "test_query": "Describe the MCP system"
  }'
```

#### Test Gemini
```bash
curl -X POST https://emailpilot.ai/api/mcp/clients/$CLIENT_ID/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_provider": "gemini",
    "test_query": "What tools are available?"
  }'
```

### 2.3 Execute MCP Tools

#### Get Campaigns (Real Klaviyo Data)
```bash
curl -X POST https://emailpilot.ai/api/mcp/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "'$CLIENT_ID'",
    "tool_name": "get_campaigns",
    "parameters": {"limit": 5},
    "provider": "claude",
    "model": "claude-3-sonnet"
  }'
```

#### Get Flows
```bash
curl -X POST https://emailpilot.ai/api/mcp/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "'$CLIENT_ID'",
    "tool_name": "get_flows",
    "parameters": {"limit": 5},
    "provider": "openai",
    "model": "gpt-4-turbo"
  }'
```

### 2.4 Test Usage Tracking

1. **Check Usage Stats**:
   ```bash
   curl -X GET https://emailpilot.ai/api/mcp/usage/$CLIENT_ID/stats?period=daily \
     -H "Authorization: Bearer $TOKEN"
   ```

2. **View Usage History**:
   ```bash
   curl -X GET https://emailpilot.ai/api/mcp/usage/$CLIENT_ID?limit=10 \
     -H "Authorization: Bearer $TOKEN"
   ```

## 🔄 Phase 3: Integration Testing

### 3.1 Test with Existing EmailPilot Features

1. **Klaviyo Audit Integration**:
   - Run an audit for a client configured with MCP
   - Verify MCP enhances audit results
   - Check if AI-powered insights appear

2. **Performance Analysis**:
   - Generate performance report
   - Verify MCP provides additional analysis
   - Compare results across different models

### 3.2 Multi-Model Comparison

```bash
# Compare responses from different models
PROMPT="Analyze the performance of this Klaviyo campaign"

# Claude
curl -X POST https://emailpilot.ai/api/mcp/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "'$CLIENT_ID'",
    "tool_name": "analyze_campaign",
    "parameters": {"campaign_id": "test-campaign"},
    "provider": "claude",
    "model": "claude-3-opus"
  }' > claude_response.json

# OpenAI
curl -X POST https://emailpilot.ai/api/mcp/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "'$CLIENT_ID'",
    "tool_name": "analyze_campaign",
    "parameters": {"campaign_id": "test-campaign"},
    "provider": "openai",
    "model": "gpt-4-turbo"
  }' > openai_response.json

# Compare results
jq '.result' claude_response.json
jq '.result' openai_response.json
```

## 🛡️ Phase 4: Security & Performance Testing

### 4.1 Rate Limiting Test
```bash
# Attempt to exceed rate limit
for i in {1..100}; do
  curl -X POST https://emailpilot.ai/api/mcp/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "client_id": "'$CLIENT_ID'",
      "tool_name": "get_campaigns",
      "parameters": {"limit": 1},
      "provider": "claude"
    }' &
done

# Should see rate limiting errors after 60 requests/minute
```

### 4.2 API Key Security
1. Verify API keys are NOT returned in any responses
2. Check Google Secret Manager for encrypted storage:
   ```bash
   gcloud secrets list --project=emailpilot-438321 | grep mcp
   ```

### 4.3 Performance Metrics
```bash
# Measure response times
time curl -X POST https://emailpilot.ai/api/mcp/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "'$CLIENT_ID'",
    "tool_name": "get_campaigns",
    "parameters": {"limit": 10},
    "provider": "claude"
  }'

# Expected: < 3 seconds for simple queries
```

## 📊 Phase 5: Admin Dashboard Testing

### 5.1 UI Functionality
1. **Client Management**:
   - ✅ Add new client
   - ✅ Edit existing client
   - ✅ Delete client
   - ✅ Enable/disable client
   - ✅ Toggle read-only mode

2. **Connection Testing**:
   - ✅ Test each provider connection
   - ✅ View test results
   - ✅ See error messages for failures

3. **Usage Analytics**:
   - ✅ View usage statistics
   - ✅ See cost breakdown
   - ✅ Track top tools used
   - ✅ Monitor success rates

### 5.2 Data Validation
```javascript
// In browser console at admin page
// Check if MCP component loaded
console.log(window.MCPManagement ? "✅ MCP Component Loaded" : "❌ Component Missing");

// Test API connectivity
fetch('/api/mcp/models', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
})
.then(r => r.json())
.then(data => console.log("Models:", data));
```

## 🔍 Phase 6: Monitoring & Logs

### 6.1 Check Application Logs
```bash
# View recent MCP-related logs
gcloud run logs read --service=emailpilot-api --region=us-central1 \
  --format="table(timestamp,severity,textPayload)" \
  --limit=100 | grep -i mcp

# Check for errors
gcloud run logs read --service=emailpilot-api --region=us-central1 \
  --format="table(timestamp,severity,textPayload)" \
  --filter="severity>=ERROR" \
  --limit=50
```

### 6.2 Database Verification
```python
# Run this in a Python environment with Firestore access
from google.cloud import firestore
db = firestore.Client(project='emailpilot-438321')

# Check MCP clients
clients = db.collection('mcp_clients').stream()
for doc in clients:
    print(f"Client: {doc.id} - {doc.to_dict().get('name')}")

# Check usage records
usage = db.collection('mcp_usage').limit(10).stream()
for doc in usage:
    data = doc.to_dict()
    print(f"Usage: {data.get('tool_name')} - {data.get('provider')} - {data.get('success')}")
```

## ✅ Testing Checklist

### Basic Functionality
- [ ] Package deployed successfully
- [ ] Frontend component visible in admin
- [ ] API endpoints accessible
- [ ] Can create new MCP client
- [ ] Can edit existing client
- [ ] Can delete client

### Provider Integration
- [ ] Claude/Klaviyo connection works
- [ ] OpenAI connection works (if key provided)
- [ ] Gemini connection works (if key provided)
- [ ] Tool execution returns results
- [ ] Error handling works properly

### Advanced Features
- [ ] Usage tracking records data
- [ ] Rate limiting enforces limits
- [ ] Cost calculation accurate
- [ ] Multi-model comparison works
- [ ] Webhook notifications sent (if configured)

### Security & Performance
- [ ] API keys stored securely
- [ ] Authentication required for all endpoints
- [ ] Response times acceptable (< 3s)
- [ ] No sensitive data in logs
- [ ] Graceful error handling

## 🚨 Common Issues & Solutions

### Issue: MCP Management not visible in admin
**Solution**: 
1. Clear browser cache
2. Check if MCPManagement.js loaded: `Network tab → Filter: MCPManagement`
3. Verify component registration in admin dashboard

### Issue: API endpoints return 404
**Solution**:
1. Check if main_firestore.py includes MCP router
2. Restart application: `gcloud run services update emailpilot-api --region=us-central1`
3. Verify deployment completed successfully

### Issue: Connection tests fail
**Solution**:
1. Verify API keys are correct format (pk_ for Klaviyo, sk- for OpenAI)
2. Check Google Secret Manager permissions
3. Review error logs for specific failure reason

### Issue: Rate limiting not working
**Solution**:
1. Check Redis/memory cache configuration
2. Verify rate limit values in database
3. Test with lower limits (e.g., 5 req/min)

## 📈 Success Metrics

After successful testing, you should see:
1. ✅ All test clients can connect to their configured providers
2. ✅ Tool execution completes in < 3 seconds
3. ✅ Usage tracking shows accurate data
4. ✅ Cost calculations match expected values
5. ✅ No errors in production logs
6. ✅ Admin UI fully functional
7. ✅ Rate limiting prevents abuse
8. ✅ Multi-model comparison provides varied insights

## 🎯 Next Steps

Once testing is complete:
1. Document any issues found
2. Create production MCP clients for real use
3. Train team on using MCP features
4. Monitor usage and costs
5. Gather feedback for improvements
6. Plan additional tool integrations

## 📞 Support

If you encounter issues:
1. Check logs: `gcloud run logs read`
2. Review this testing guide
3. Check INTEGRATION_INSTRUCTIONS.md
4. Contact development team with:
   - Error messages
   - Steps to reproduce
   - Expected vs actual behavior