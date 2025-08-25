# LangChain Agent Creation Guide

## How to Add New Agents

### Method 1: Add to Registry (Recommended for Permanent Agents)

Edit the file: `/multi-agent/integrations/langchain_core/admin/registry.py`

In the `_initialize_defaults()` method, add your new agent after the existing ones:

```python
# Example: Adding a new "email_optimizer" agent
self.register_agent({
    "name": "email_optimizer",
    "description": "Optimizes email content for engagement",
    "version": "1.0",
    "status": "active",
    "default_task": "Optimize email for {brand} targeting {segment}",
    "policy": {
        "max_tool_calls": 10,
        "timeout_seconds": 45,
        "allowed_tools": ["klaviyo_api", "firestore_ro", "analyze"]
    },
    "variables": [
        {
            "name": "brand",
            "type": "string",
            "required": True,
            "description": "Brand to optimize for"
        },
        {
            "name": "segment",
            "type": "string",
            "required": True,
            "description": "Target segment"
        },
        {
            "name": "goal",
            "type": "string",
            "default": "engagement",
            "allowed_values": ["engagement", "conversion", "retention"],
            "description": "Optimization goal"
        }
    ],
    "prompt_template": """You are an email optimization specialist.
    
Your task is to optimize email content for maximum {goal}.
Brand: {brand}
Target Segment: {segment}
Client Context: {client}

Analyze and optimize for:
1. Subject line effectiveness
2. Preview text optimization
3. Content structure
4. CTA placement and copy
5. Personalization opportunities

Provide specific recommendations with expected impact."""
})
```

After adding, restart the server and the agent will appear in the Admin Dashboard.

### Method 2: Dynamic Registration via API (For Testing)

You can also add agents dynamically through the API:

```bash
curl -X POST http://localhost:8000/api/admin/langchain/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "seasonal_planner",
    "description": "Plans seasonal campaigns",
    "version": "1.0",
    "status": "active",
    "default_task": "Plan {season} campaign for {brand}",
    "variables": [
      {"name": "brand", "type": "string", "required": true},
      {"name": "season", "type": "string", "required": true}
    ],
    "prompt_template": "Plan a seasonal campaign..."
  }'
```

### Method 3: Create Custom Node Implementation

For complex agents with custom logic, create a node implementation:

1. Create file: `/multi-agent/apps/orchestrator_service/nodes/your_agent.py`

```python
from typing import Dict, Any
from ..state import MessageState

async def your_agent(state: MessageState) -> MessageState:
    """Your agent implementation."""
    # Custom logic here
    response = await process_with_llm(state.messages[-1])
    state.messages.append(response)
    return state
```

2. Register in `__init__.py`
3. Add to registry.py as shown in Method 1

---

## Accessing Firestore Client Variables

### Available Client Variables (53+ Total)

The Firestore client collection provides rich context about each client. These variables are automatically available in agent prompts:

#### Basic Client Information
- `{client.name}` - Client company name
- `{client.id}` - Unique client identifier
- `{client.klaviyo_account_id}` - Klaviyo account ID
- `{client.klaviyo_public_key}` - Public API key
- `{client.industry}` - Industry vertical
- `{client.timezone}` - Client timezone
- `{client.website}` - Client website URL
- `{client.logo_url}` - Brand logo URL

#### Business Context
- `{client.key_growth_objective}` - Primary growth goal
- `{client.monthly_revenue_goal}` - Revenue target
- `{client.avg_order_value}` - Average order value
- `{client.customer_lifetime_value}` - CLV metric
- `{client.primary_audience}` - Main target audience
- `{client.unique_selling_proposition}` - USP

#### Segmentation Data
- `{client.affinity_segment_1_name}` - Segment 1 name
- `{client.affinity_segment_1_description}` - Segment 1 details
- `{client.affinity_segment_2_name}` - Segment 2 name
- `{client.affinity_segment_2_description}` - Segment 2 details
- `{client.affinity_segment_3_name}` - Segment 3 name
- `{client.affinity_segment_3_description}` - Segment 3 details

#### Campaign Preferences
- `{client.email_frequency}` - Sending frequency
- `{client.best_send_times}` - Optimal send times
- `{client.content_preferences}` - Content types
- `{client.brand_voice}` - Brand tone/voice
- `{client.color_palette}` - Brand colors
- `{client.font_family}` - Brand typography

#### Integration Settings
- `{client.slack_webhook}` - Slack notifications
- `{client.asana_project_id}` - Asana integration
- `{client.google_analytics_id}` - GA tracking
- `{client.facebook_pixel_id}` - FB pixel

#### Metadata
- `{client.created_at}` - Account creation date
- `{client.updated_at}` - Last update
- `{client.is_active}` - Active status
- `{client.subscription_tier}` - Plan level

### How to Use Client Variables in Agent Prompts

#### 1. In the Admin Dashboard

Go to Admin Dashboard → Agent Prompts → Select any agent:

1. Click "Explore Variables" to see all available variables
2. Search for "client" to filter client-specific variables
3. Click any variable to insert it at cursor position
4. The variable will be replaced with actual data at runtime

#### 2. In Agent Prompt Templates

```python
"prompt_template": """You are analyzing data for {client.name}.

Industry: {client.industry}
Website: {client.website}
Growth Objective: {client.key_growth_objective}
Monthly Revenue Goal: ${client.monthly_revenue_goal}

Key Segments:
1. {client.affinity_segment_1_name}: {client.affinity_segment_1_description}
2. {client.affinity_segment_2_name}: {client.affinity_segment_2_description}
3. {client.affinity_segment_3_name}: {client.affinity_segment_3_description}

Brand Voice: {client.brand_voice}
USP: {client.unique_selling_proposition}

Task: {task}
"""
```

#### 3. Accessing Variables Programmatically

```python
# In your agent code
from app.services.firestore import get_db

async def get_client_context(client_id: str) -> dict:
    """Get all client variables from Firestore."""
    db = get_db()
    client_doc = db.collection("clients").document(client_id).get()
    
    if client_doc.exists:
        client_data = client_doc.to_dict()
        # Prefix all keys with "client."
        return {f"client.{k}": v for k, v in client_data.items()}
    return {}
```

### Variable Discovery API

To see all available variables for a specific client:

```bash
# Get all variables including client data
curl http://localhost:8000/api/admin/langchain/orchestration/variables/all?client_id=YOUR_CLIENT_ID

# Response includes:
{
  "variables": [
    {
      "name": "client.name",
      "value": "Rogue Creamery",
      "source": "firestore",
      "description": "Client company name"
    },
    {
      "name": "client.industry",
      "value": "Food & Beverage",
      "source": "firestore",
      "description": "Industry vertical"
    },
    // ... 50+ more variables
  ]
}
```

### Dynamic Variable Injection

Variables are automatically injected when running agents:

```python
# When you run an agent
POST /api/admin/langchain/agents/copy_smith/runs
{
  "brand": "rogue-creamery",  # This triggers client data loading
  "task": "Create email copy"
}

# The system automatically:
# 1. Loads client data from Firestore
# 2. Injects all client.* variables
# 3. Adds system variables (date, user, etc.)
# 4. Includes MCP server data if available
# 5. Passes everything to the agent prompt
```

---

## Quick Reference: Adding a New Agent

### Step 1: Define the Agent
```python
# In registry.py
self.register_agent({
    "name": "your_agent_name",
    "description": "What this agent does",
    "variables": [
        {"name": "brand", "type": "string", "required": True}
    ],
    "prompt_template": "Your prompt with {client.name} and other {variables}"
})
```

### Step 2: Restart Server
```bash
# The server will auto-reload if using --reload flag
# Or manually restart:
pkill -f uvicorn && uvicorn main_firestore:app --port 8000 --host localhost --reload
```

### Step 3: Test in Admin Dashboard
1. Go to http://localhost:8000/admin-dashboard
2. Click "Agent Prompts" tab
3. Find your new agent in the list
4. Edit and test the prompt
5. Use Variable Explorer to add client context

### Step 4: Run the Agent
```bash
curl -X POST http://localhost:8000/api/admin/langchain/agents/your_agent_name/runs \
  -H "Content-Type: application/json" \
  -d '{"brand": "rogue-creamery", "task": "Your task here"}'
```

---

## Best Practices

1. **Always include client context**: Use `{client.*}` variables for personalization
2. **Define clear variables**: Specify types, defaults, and validation
3. **Set appropriate policies**: Configure timeout and tool access
4. **Test with real data**: Use actual client IDs to verify variable injection
5. **Document your agents**: Include clear descriptions and examples
6. **Use Variable Explorer**: Test prompts with live data before deploying

## Troubleshooting

### Agent Not Appearing
- Check server logs for registration errors
- Ensure agent name is unique
- Verify JSON syntax in registration

### Variables Not Loading
- Confirm client exists in Firestore
- Check client_id is being passed correctly
- Verify Firestore permissions

### Prompt Errors
- Use Variable Explorer to validate all variables exist
- Check for typos in variable names
- Ensure required variables are provided

## Summary

- **11 agents currently active** (4 core + 7 Email/SMS specialized)
- **53+ variables available** from Firestore, MCP, and system
- **Easy to add new agents** via registry.py
- **Full client context** automatically injected
- **Admin Dashboard UI** for prompt editing and testing
- **Variable Explorer** shows all available data

Your agents have full access to rich client data from Firestore, making them context-aware and capable of personalized responses!