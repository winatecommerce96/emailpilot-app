# MCP-to-Agent Orchestration Guide

## Overview
The LangChain Orchestration system enables seamless data flow from MCP (Model Context Protocol) servers to LangChain agents, with dynamic variable discovery from multiple sources including Firestore collections.

## Key Features

### 1. Dynamic Variable Discovery
The system automatically discovers variables from:
- **Firestore Collections** - Client data, goals, performance metrics
- **MCP Servers** - Revenue data, campaign metrics, email/SMS statistics  
- **System Context** - Current date, user info, environment variables

### 2. Enhanced Prompt Editor
Access via: **Admin Dashboard → Agent Prompts**

#### New Capabilities:
- **Variable Explorer** - Click "Explore Variables" to see all 50+ available variables
- **Smart Search** - Filter variables by name or description
- **One-Click Insert** - Click any variable to insert at cursor position
- **Live Preview** - See prompt with sample data in real-time

#### Available Variable Categories:

**Client Variables** (from Firestore):
- `{client.name}` - Client company name
- `{client.klaviyo_account_id}` - Klaviyo account identifier
- `{client.timezone}` - Client timezone
- `{client.industry}` - Industry vertical
- `{client.key_growth_objective}` - Primary growth goal
- `{client.affinity_segment_1_name}` - Customer segment names
- Plus 20+ more client fields

**Performance Metrics**:
- `{performance.mtd_revenue}` - Month-to-date revenue
- `{performance.open_rate}` - Current email open rate
- `{performance.click_rate}` - Current click rate
- `{performance.avg_order_value}` - Average order value

**MCP Data Sources**:
- `{mcp.revenue_7d}` - 7-day revenue from Klaviyo
- `{mcp.top_campaigns}` - Best performing campaigns
- `{mcp.campaign_roi}` - Campaign return on investment
- `{mcp.scheduled_campaigns}` - Upcoming campaigns

## Setting Up MCP-to-Agent Orchestration

### Step 1: Access Orchestration API
The orchestration API is available at:
```
/api/admin/langchain/orchestration
```

### Step 2: Create an Orchestration

**Example: Revenue Drop Alert**
```json
POST /api/admin/langchain/orchestration/orchestrations
{
  "name": "Revenue Drop Alert",
  "description": "Triggers revenue analysis when daily revenue drops significantly",
  "mcp_server": "klaviyo_revenue",
  "agent_id": "revenue_analyst",
  "trigger_type": "event",
  "trigger_config": {
    "event": "revenue_check",
    "frequency": "daily",
    "condition": "revenue_change < -20"
  },
  "data_mapping": {
    "brand": "client.name",
    "month": "system.current_month",
    "comparison_period": "previous_day"
  },
  "filters": [
    {"field": "revenue_7d", "operator": ">", "value": 0}
  ],
  "transformations": [
    {
      "type": "calculate",
      "operation": "percentage_change",
      "old_field": "revenue_yesterday",
      "new_field": "revenue_today",
      "output_field": "revenue_change"
    }
  ],
  "enabled": true
}
```

### Step 3: Data Flow Configuration

#### Data Mapping
Maps MCP output fields to agent input variables:
```json
"data_mapping": {
  "brand": "client.name",           // Agent expects 'brand', gets client name
  "revenue": "mcp.revenue_7d",      // Agent gets 7-day revenue
  "month": "system.current_month"   // Agent gets current month
}
```

#### Filters
Only trigger when conditions are met:
```json
"filters": [
  {"field": "revenue_7d", "operator": ">", "value": 1000},
  {"field": "client.is_active", "operator": "==", "value": true}
]
```

#### Transformations
Process data before sending to agent:
```json
"transformations": [
  {
    "type": "calculate",
    "operation": "percentage_change",
    "old_field": "last_month_revenue",
    "new_field": "this_month_revenue",
    "output_field": "revenue_growth"
  }
]
```

## Trigger Types

### 1. **Event-Based**
Triggered by specific events:
```json
"trigger_type": "event",
"trigger_config": {
  "event": "campaign_complete",
  "source": "klaviyo"
}
```

### 2. **Schedule-Based**
Run on a schedule:
```json
"trigger_type": "schedule",
"trigger_config": {
  "cron": "0 9 * * *",  // Daily at 9 AM
  "timezone": "America/New_York"
}
```

### 3. **Webhook-Based**
External webhook triggers:
```json
"trigger_type": "webhook",
"trigger_config": {
  "endpoint": "/webhooks/klaviyo-alert",
  "method": "POST",
  "auth_type": "bearer"
}
```

### 4. **Manual**
Triggered manually via API or UI:
```json
"trigger_type": "manual",
"trigger_config": {
  "require_confirmation": true
}
```

## Testing Orchestrations

### Test with Sample Data
```bash
curl -X POST http://localhost:8000/api/admin/langchain/orchestration/orchestrations/{id}/test \
  -H "Content-Type: application/json" \
  -d '{
    "revenue_7d": 15000,
    "orders_7d": 150,
    "brand": "rogue-creamery"
  }'
```

### Response Shows:
- Input data from MCP
- Mapped data for agent
- Whether trigger conditions are met
- Which agent would be invoked

## Pre-Built Templates

Access templates via:
```
GET /api/admin/langchain/orchestration/orchestrations/templates
```

Available templates:
- **Revenue Drop Alert** - Monitors revenue changes
- **Campaign Performance Review** - Post-campaign analysis
- **List Growth Monitor** - Track subscriber growth
- **Engagement Alert** - Monitor open/click rates

## Best Practices

### 1. Variable Naming
- Use descriptive names: `{client.monthly_revenue_goal}` not `{mrg}`
- Follow dot notation: `{source.field}` format
- Keep consistent across agents

### 2. Data Validation
- Always include filters to validate data quality
- Check for required fields before triggering
- Handle missing data gracefully

### 3. Performance
- Limit transformation complexity
- Cache frequently used variables
- Batch similar orchestrations

### 4. Error Handling
- Set up fallback values for missing data
- Log all orchestration executions
- Monitor failure rates

## API Endpoints

### Variable Discovery
```
GET /api/admin/langchain/orchestration/variables/{context}
  ?client_id={id}        # Optional: Get client-specific variables
  &include_mcp=true      # Include MCP server variables
  &include_firestore=true # Include Firestore variables
```

### Orchestration Management
```
GET    /api/admin/langchain/orchestration/orchestrations       # List all
POST   /api/admin/langchain/orchestration/orchestrations       # Create new
GET    /api/admin/langchain/orchestration/orchestrations/{id}  # Get details
PUT    /api/admin/langchain/orchestration/orchestrations/{id}  # Update
DELETE /api/admin/langchain/orchestration/orchestrations/{id}  # Delete
POST   /api/admin/langchain/orchestration/orchestrations/{id}/test # Test
```

## Integration with Prompt Editor

The enhanced prompt editor now shows:
1. **All Available Variables** - 50+ variables from all sources
2. **Variable Categories** - Grouped by source (client, mcp, system, etc.)
3. **Smart Search** - Find variables quickly
4. **One-Click Insert** - Click to add to prompt
5. **Live Preview** - See how prompts render with data

## Example: Complete Revenue Analysis Flow

1. **MCP Server** (`klaviyo_revenue`) fetches latest revenue data
2. **Orchestration** checks if revenue dropped > 20%
3. **Data Mapping** enriches with client context from Firestore
4. **Agent Trigger** invokes `revenue_analyst` with full context
5. **Agent Execution** analyzes using enriched prompt with all variables
6. **Result** delivered with insights and recommendations

## Troubleshooting

### Variables Not Appearing
- Check Firestore connection
- Verify MCP servers are running
- Ensure proper permissions

### Orchestration Not Triggering
- Verify trigger conditions
- Check filter criteria
- Review logs for errors

### Data Mapping Issues
- Confirm source fields exist
- Check variable names match exactly
- Validate data types

## Summary

The orchestration system provides:
- **50+ Dynamic Variables** from multiple sources
- **Visual Variable Explorer** in prompt editor
- **Flexible Data Flow** from MCP to agents
- **Smart Transformations** for data processing
- **Multiple Trigger Types** for automation
- **Complete Testing Tools** for validation

This enables sophisticated automation where MCP servers can intelligently trigger agents with full context from your entire data ecosystem.