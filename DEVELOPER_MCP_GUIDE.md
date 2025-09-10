# 🚨 MANDATORY: How to Add New MCP Tools 🚨

## ⛔ STOP! READ THIS FIRST ⛔

**ALL new MCP integrations MUST use the Universal MCP Registry. Direct MCP implementations are FORBIDDEN.**

### ❌ What NOT to Do

**DO NOT:**
- Create new files like `mcp_stripe.py`, `mcp_salesforce.py`, etc.
- Write custom MCP wrappers or handlers
- Bypass the Universal MCP Registry
- Directly implement MCP functionality

**These actions will be BLOCKED by the enforcement system.**

### ✅ The ONLY Approved Way to Add MCPs

## Step 1: Use the Web Interface (Recommended)

1. Navigate to: `http://localhost:8000/static/mcp_tools.html`
2. Click on "Universal MCP Registry" tab
3. Fill in the registration form:
   - Tool Name (e.g., "Stripe Payments")
   - Base URL (e.g., "https://api.stripe.com/v1")
   - Service Type (financial, marketing, etc.)
   - Authentication Type
   - Example Queries
4. Click "Register MCP"

**That's it! The system automatically:**
- Creates an AI wrapper
- Generates a LangChain agent
- Enables natural language queries
- Sets up learning capabilities

## Step 2: Use the API (For Programmatic Registration)

```python
import httpx

async def register_new_mcp():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/mcp/register",
            json={
                "name": "Stripe Payments",
                "base_url": "https://api.stripe.com/v1",
                "service_type": "financial",
                "auth_type": "bearer",
                "description": "Stripe payment processing",
                "example_queries": [
                    "List all transactions",
                    "Show revenue for last month",
                    "Get customer payment history"
                ]
            }
        )
        result = response.json()
        print(f"✅ MCP registered: {result['wrapper_endpoint']}")
```

## Step 3: Use Your New MCP

### Natural Language Query
```python
# Query your MCP with natural language
response = await client.post(
    f"/api/mcp/stripe_payments/query",
    json={
        "query": "Show me failed payments from last week",
        "optimization": "balanced"
    }
)
```

### Direct Tool Invocation (If Needed)
```python
# Directly invoke a specific tool
response = await client.post(
    f"/api/mcp/stripe_payments/invoke",
    json={
        "tool_name": "list_transactions",
        "params": {"limit": 100}
    }
)
```

## Why This System Is Mandatory

1. **Automatic AI Enhancement**: Every MCP gets intelligent query processing
2. **Self-Learning**: System improves over time
3. **Standardization**: Consistent interface for all MCPs
4. **No Code Maintenance**: Add MCPs without writing code
5. **Optimal LLM Selection**: Automatic model selection based on task
6. **Built-in Retry Logic**: Multiple fallback strategies
7. **Performance Tracking**: Automatic metrics and monitoring

## Enforcement System

The system ACTIVELY PREVENTS bypass attempts:

```python
# This will FAIL - enforcement blocks it
from app.api import mcp_stripe  # ❌ BLOCKED

# This will FAIL - pattern blocked
class NewMCPHandler:  # ❌ BLOCKED
    pass

# This will SUCCEED - using registry
from app.services.mcp_registry import UniversalMCPRegistry  # ✅ ALLOWED
```

## For Legacy MCP Migration

If you have an existing MCP that predates the registry:

1. **Export its configuration**:
```python
legacy_config = {
    "name": "Legacy MCP",
    "endpoints": [...],  # Your existing endpoints
    "auth_type": "api_key"
}
```

2. **Register it through the Universal Registry**:
```python
await registry.register_new_mcp(legacy_config)
```

3. **Update references to use registry endpoints**:
```python
# Old way (deprecated)
result = await legacy_mcp.query(...)  # ❌

# New way (required)
result = await client.post(
    "/api/mcp/legacy_mcp/query",  # ✅
    json={"query": "..."}
)
```

## Examples of Registered MCPs

### Marketing Tools
- Klaviyo (email marketing)
- Mailchimp (campaigns)
- HubSpot (CRM + marketing)

### Financial Tools
- Stripe (payments)
- Square (transactions)
- QuickBooks (accounting)

### Analytics Tools
- Google Analytics (web analytics)
- Mixpanel (product analytics)
- Amplitude (user behavior)

### E-commerce Tools
- Shopify (store management)
- WooCommerce (WordPress commerce)
- BigCommerce (enterprise e-commerce)

## Testing Your MCP

After registration, test your MCP:

1. **Via UI**: Use the test interface in Universal MCP Registry tab
2. **Via API**: Use the test endpoint
3. **Via Workflow**: Integrate with calendar or other workflows

```python
# Test endpoint
response = await client.post(
    f"/api/mcp/{mcp_id}/test",
    json={
        "query": "test query",
        "use_cache": False
    }
)
```

## Monitoring and Metrics

View your MCP's performance:

```python
# Get metrics
response = await client.get(f"/api/mcp/{mcp_id}")
metrics = response.json()["metrics"]

print(f"Total Queries: {metrics['total_queries']}")
print(f"Success Rate: {metrics['success_rate']}")
print(f"Patterns Learned: {metrics['patterns_learned']}")
```

## Support and Documentation

- **Full Documentation**: See `SMART_MCP_GATEWAY.md`
- **UI Access**: `http://localhost:8000/static/mcp_tools.html`
- **API Reference**: `http://localhost:8000/docs#/MCP%20Universal%20Management`

## Remember

🎯 **One Rule**: ALL MCPs go through the Universal Registry. No exceptions.

The enforcement system will:
- ✅ Guide you to the correct approach
- ⚠️ Warn about deprecated patterns
- ❌ Block bypass attempts
- 📊 Track all MCP usage

---

**Last Updated**: 2025-08-28  
**Status**: MANDATORY for all new MCP integrations  
**Enforcement**: ACTIVE