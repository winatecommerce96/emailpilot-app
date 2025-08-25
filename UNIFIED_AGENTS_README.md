# Unified AI Agents System

**Single Source of Truth for AI Agent Management in EmailPilot**

## Overview

The Unified AI Agents System consolidates all AI agent definitions into a single, coherent system, replacing the previous fragmented approach with three competing definitions:

1. ~~The "Prompts" section in `/api/ai-models`~~ **DEPRECATED**
2. ~~The "Available AI Agents" list in the copywriting tool~~ **MIGRATED** 
3. ~~The "Agents" section in admin dashboard~~ **REPLACED**

## 🎯 Single Source of Truth (SSOT)

**Location**: `/api/agents/` endpoints backed by Firestore `agents` collection

**Schema**: Each agent includes:
```json
{
  "agent_id": "copywriter",
  "display_name": "Expert Copywriter", 
  "role": "copywriter",
  "default_provider": "claude",
  "default_model_id": "claude-3-5-sonnet-20241022",
  "prompt_template": "You are an expert email copywriter...",
  "capabilities": ["email_copy", "subject_lines", "cta_creation"],
  "active": true,
  "description": "Expert in email copy and messaging",
  "version": 1,
  "variables": ["brand_voice", "target_audience"],
  "created_at": "2025-08-19T11:09:29.847Z",
  "updated_at": "2025-08-19T11:09:29.847Z",
  "metadata": {
    "source": "copywriting_tool",
    "category": "marketing"
  }
}
```

## 📡 API Endpoints

### Core CRUD Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/agents/` | List all agents (with filters) |
| `GET` | `/api/agents/{agent_id}` | Get specific agent |
| `POST` | `/api/agents/` | Create new agent |
| `PUT` | `/api/agents/{agent_id}` | Update existing agent |
| `DELETE` | `/api/agents/{agent_id}` | Delete agent (soft delete) |

### Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/agents/stats` | Get collection statistics |
| `POST` | `/api/agents/{agent_id}/invoke` | Invoke agent (connects to AI Orchestrator) |
| `POST` | `/api/agents/migrate-from-prompts` | Migrate data from old prompts system |
| `POST` | `/api/agents/seed-default-agents` | Seed with standard marketing agents |

### Query Parameters

```bash
# Filter agents
GET /api/agents/?active_only=true&role=copywriter&capability=email_copy

# Get statistics  
GET /api/agents/stats

# Create agent
POST /api/agents/
Content-Type: application/json
{
  "display_name": "SEO Specialist",
  "role": "seo",
  "prompt_template": "You are an SEO specialist...",
  "default_provider": "openai",
  "capabilities": ["seo_optimization", "keyword_research"]
}
```

## 🔄 Migration Status

### ✅ Completed Migrations

1. **Prompts Collection** → **Agents Collection**
   - Agent-category prompts migrated to unified schema
   - 3 agents migrated: `content_strategist`, `segmentation_expert`, `ab_test_coordinator`

2. **Copywriting Tool** → **API-Driven**
   - Hardcoded agents list removed
   - Now fetches from `/api/agents/` endpoint
   - 4 agents seeded: `copywriter`, `designer`, `brand_specialist`, `performance_analyst`

3. **Admin Dashboard** → **Unified Management**
   - New `/admin/ai-models.html` interface
   - Full CRUD operations for agents
   - Migration tools included

### 📊 Migration Results

- **Total Unified Agents**: 7
- **Prompts Migrated**: 3  
- **Copywriting Agents Seeded**: 4
- **Migration Log**: Stored in `migration_logs` Firestore collection

## 🖥️ User Interfaces

### Primary: Admin AI Models Page
**URL**: `http://localhost:8000/admin/ai-models.html`

**Tabs**:
- **Agents (SSOT)** - Full agent management interface
- **Prompts (Deprecated)** - Shows deprecation notice + migration tools
- **Model Configuration** - Provider and model settings  
- **Migration Tools** - Run migrations and view logs

### Secondary: Admin Dashboard
**URL**: `http://localhost:8000/static/admin-dashboard.html` 

The "AI Agents" tab now uses the unified system via `UnifiedAgentsPanel.js`.

### Integration: Copywriting Tool  
**URL**: `http://localhost:8002`

The copywriting tool now fetches agents from the unified API instead of hardcoded lists.

## 📝 Example Usage

### JavaScript (Frontend)
```javascript
// Fetch all active agents
const response = await fetch('/api/agents/?active_only=true');
const data = await response.json();
console.log(`Found ${data.total} active agents`);

// Create new agent
const newAgent = {
  display_name: "Social Media Specialist",
  role: "social_media", 
  prompt_template: "You are a social media marketing expert...",
  default_provider: "openai",
  capabilities: ["social_copy", "hashtag_strategy"]
};

const response = await fetch('/api/agents/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(newAgent)
});
```

### Python (Backend)
```python
import httpx

# Get agents for copywriting
async def get_copywriting_agents():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/agents/",
            params={"role": "copywriter", "active_only": True}
        )
        return response.json()

# Invoke agent
async def invoke_agent(agent_id: str, context: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/api/agents/{agent_id}/invoke",
            json=context
        )
        return response.json()
```

## 🚨 Breaking Changes & Migration Path

### For Applications Using Old APIs

#### 1. Replace Prompts API Calls
```python
# OLD (deprecated)
response = requests.get("/api/ai-models/prompts?category=agent")

# NEW (unified)
response = requests.get("/api/agents/?role=copywriter")
```

#### 2. Update Agent References
```python
# OLD (copywriting tool hardcoded)
agents = [
    {"id": "copywriter", "name": "Copywriter"},
    {"id": "designer", "name": "Designer"}
]

# NEW (API-driven)
response = requests.get("/api/agents/")
agents = response.json()["agents"]
```

#### 3. Schema Changes
```python
# OLD prompt schema
{
  "id": "prompt_123",
  "name": "Content Strategist",
  "prompt_template": "...",
  "model_provider": "claude"
}

# NEW agent schema  
{
  "agent_id": "content_strategist",
  "display_name": "Content Strategist", 
  "prompt_template": "...",
  "default_provider": "claude",
  "role": "strategist",
  "capabilities": ["strategy", "planning"]
}
```

## 🛠️ Development & Maintenance

### Adding New Agents

1. **Via API** (Recommended):
```bash
curl -X POST http://localhost:8000/api/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Email Automation Specialist",
    "role": "automation",
    "prompt_template": "You are an expert in email automation...",
    "default_provider": "gemini",
    "capabilities": ["automation_workflows", "trigger_setup"]
  }'
```

2. **Via Admin UI**: 
   - Visit `http://localhost:8000/admin/ai-models.html`
   - Go to "Agents (SSOT)" tab
   - Click "Create New Agent"

### Running Migrations

Execute migration script:
```bash
cd /path/to/emailpilot-app
python migrate_agents_to_unified.py
```

Or use admin interface:
- Visit `http://localhost:8000/admin/ai-models.html` 
- Go to "Migration Tools" tab
- Click migration buttons

### Monitoring

- **Agent Stats**: `GET /api/agents/stats`
- **Migration Logs**: Firestore `migration_logs` collection
- **Health Check**: `GET /health` (main app status)

## 🎯 Benefits of Unified System

### ✅ Eliminated Duplication
- **Before**: 3 different agent definitions across the app
- **After**: 1 unified agents collection

### ✅ Centralized Management  
- **Before**: Edit agents in multiple places
- **After**: Single admin interface for all agents

### ✅ API Consistency
- **Before**: Different endpoints return different schemas
- **After**: Consistent `/api/agents/*` endpoints

### ✅ Better Integration
- **Before**: Copywriting tool had hardcoded agents
- **After**: All tools consume from unified API

### ✅ Version Control
- **Before**: No version tracking for agent changes
- **After**: Version field tracks agent updates

### ✅ Metadata & Capabilities
- **Before**: Limited agent information  
- **After**: Rich metadata, capabilities, and role-based filtering

## 🔮 Future Enhancements

1. **Agent Invocation Integration**
   - Connect `/api/agents/{id}/invoke` to AI Orchestrator
   - Add execution history and performance tracking

2. **Advanced Filtering**
   - Search agents by capability
   - Filter by provider/model availability 
   - Tag-based organization

3. **Agent Templates**
   - Pre-built agent templates for common roles
   - Industry-specific agent collections

4. **Performance Analytics**
   - Track agent usage and effectiveness
   - A/B testing for agent prompts
   - Cost optimization recommendations

5. **Access Control**
   - Role-based permissions for agent management
   - Approval workflows for agent changes

---

## 📋 Checklist: Verifying Migration Success

- [ ] `/api/agents/` returns all migrated agents
- [ ] Copywriting tool fetches agents from API (not hardcoded)
- [ ] Admin UI uses `UnifiedAgentsPanel.js` component
- [ ] Old prompts endpoint returns deprecation notice
- [ ] Migration logs exist in Firestore
- [ ] No references to old agent systems remain in codebase
- [ ] Agent stats endpoint returns correct counts
- [ ] All agents have proper schema (agent_id, role, capabilities, etc.)

---

**Status**: ✅ **MIGRATION COMPLETE** - Unified AI Agents System Active

**Contact**: System implemented as part of EmailPilot Agent Unification Project  
**Documentation**: This README serves as the primary reference for the unified system