# LangChain Agent System Summary

## Current Status: Fully Operational ✅

### 11 Active Agents

#### Core Agents (4)
1. **rag** - RAG-based question answering
2. **default** - General-purpose task execution  
3. **revenue_analyst** - Revenue data analysis
4. **campaign_planner** - Email campaign planning

#### Email/SMS Specialized Agents (7)
5. **copy_smith** - Copywriting with AIDA/PAS/FOMO frameworks
6. **layout_lab** - Mobile-first responsive design
7. **calendar_strategist** - Campaign timing optimization
8. **brand_brain** - Brand consistency and voice
9. **gatekeeper** - Compliance and regulations
10. **truth_teller** - Performance analytics
11. **audience_architect** - Segmentation strategies

---

## How to Add More Agents

### Quick Method: Edit Registry File

1. Open `/multi-agent/integrations/langchain_core/admin/registry.py`
2. Add your agent in `_initialize_defaults()` method:

```python
self.register_agent({
    "name": "your_new_agent",
    "description": "What it does",
    "default_task": "Task template with {variables}",
    "variables": [
        {"name": "brand", "type": "string", "required": True}
    ],
    "prompt_template": "Your prompt here with {client.name} and other variables"
})
```

3. Save file - server auto-reloads
4. Agent appears in Admin Dashboard → Agent Prompts

---

## Firestore Client Variables (Available Now!)

### ✅ Confirmed Working Variables

When you pass a valid `client_id` (like "christopher-bean-coffee"), these variables are automatically available:

- `{client.name}` - Company name
- `{client.client_id}` - Unique identifier
- `{client.website}` - Company website
- `{client.contact_name}` - Primary contact
- `{client.contact_email}` - Contact email
- `{client.key_growth_objective}` - Growth goals
- `{client.affinity_segment_1_name}` - Segment 1 name
- `{client.affinity_segment_2_name}` - Segment 2 name
- `{client.affinity_segment_3_name}` - Segment 3 name
- `{client.affinity_segment_1_definition}` - Segment 1 details
- `{client.affinity_segment_2_definition}` - Segment 2 details
- `{client.affinity_segment_3_definition}` - Segment 3 details
- `{client.is_active}` - Active status
- `{client.created_at}` - Creation date
- `{client.updated_at}` - Last update
- Plus many more custom fields per client

### How to Use Client Variables

#### In Agent Prompts (Admin Dashboard)
1. Go to Admin Dashboard → Agent Prompts
2. Select any agent
3. In your prompt template, use:
```
Analyzing data for {client.name}
Website: {client.website}
Key Goal: {client.key_growth_objective}
```

#### When Running Agents
Pass a valid client ID (use their slug, not "rogue-creamery" but actual ID):
```bash
# Get valid client IDs first
curl http://localhost:8000/api/clients/

# Use the ID (like "christopher-bean-coffee")
curl -X POST http://localhost:8000/api/admin/langchain/agents/copy_smith/runs \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "christopher-bean-coffee",
    "task": "Create holiday email"
  }'
```

#### View All Variables for a Client
```bash
# See all 58+ variables for a specific client
curl "http://localhost:8000/api/admin/langchain/orchestration/variables/all?client_id=christopher-bean-coffee&include_firestore=true"
```

---

## Admin Dashboard Access

### View and Edit Agent Prompts
1. Navigate to: http://localhost:8000/admin-dashboard
2. Click "Agent Prompts" tab
3. Features available:
   - View all 11 agents
   - Edit prompt templates
   - Test with sample data
   - Save changes instantly
   - Variable Explorer (shows client variables when client_id provided)

### Variable Explorer
- Shows 58+ variables when a valid client is selected
- Categories: Firestore (client data), MCP (performance), System (date/user)
- Click any variable to insert into prompt
- Live preview with actual data

---

## Quick Test URLs

- **Admin Dashboard**: http://localhost:8000/admin-dashboard
- **Agent Prompts Direct**: http://localhost:8000/static/admin/langchain/prompts.html
- **Test All Agents**: http://localhost:8000/test_all_agents.html
- **Test Prompts Panel**: http://localhost:8000/test_agent_prompts_final.html

---

## API Endpoints

### List All Agents
```bash
curl http://localhost:8000/api/admin/langchain/agents
```

### Get Agent Prompt
```bash
curl http://localhost:8000/api/admin/langchain/agents/copy_smith/prompt
```

### Update Agent Prompt
```bash
curl -X PUT http://localhost:8000/api/admin/langchain/agents/copy_smith/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt_template": "New prompt template..."}'
```

### Run Agent
```bash
curl -X POST http://localhost:8000/api/admin/langchain/agents/copy_smith/runs \
  -H "Content-Type: application/json" \
  -d '{"brand": "christopher-bean-coffee", "task": "Create email"}'
```

---

## Important Notes

1. **Use Valid Client IDs**: Get them from `/api/clients/` endpoint
2. **Client Variables Load Automatically**: When you pass a valid client_id/brand
3. **All 11 Agents Are Active**: Visible in Admin Dashboard
4. **MCP Agents Deprecated**: Removed in favor of LangChain agents
5. **Variables Include**: Client data (Firestore), Performance (MCP), System context

---

## Next Steps

To add a new agent:
1. Edit `/multi-agent/integrations/langchain_core/admin/registry.py`
2. Add agent definition with variables and prompt
3. Save and let server reload
4. Test in Admin Dashboard

To use client variables:
1. Pass valid client_id when running agents
2. Use `{client.field_name}` syntax in prompts
3. Variables auto-populate from Firestore

The system is fully operational with 11 agents and 58+ dynamic variables per client!