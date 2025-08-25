# 🎯 How the Multi-Agent Orchestrator Actually Works

## Current Architecture

```
┌─────────────────────────────────────────────┐
│            Orchestrator UI (HTML)            │
│         http://localhost:8100/               │
└─────────────────────┬───────────────────────┘
                      │ HTTP + CORS
                      ↓
┌─────────────────────────────────────────────┐
│      Orchestrator API Server (FastAPI)       │
│            Port 8100 (Running ✅)            │
└─────────────────────┬───────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────┐
│         LangGraph Workflow Engine            │
│    (4 Phases with 11 Agent Nodes)           │
└─────────────────────┬───────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   AI Models  │ │Mock Data │ │   External   │
│ (OpenAI/etc) │ │(Built-in)│ │   Services   │
│              │ │   ✅     │ │   (Future)   │
└──────────────┘ └──────────┘ └──────────────┘
```

## What's Currently Working

### ✅ Fully Functional
1. **Orchestrator API** - Running at http://localhost:8100
2. **Web UI** - Available at orchestrator-ui.html
3. **LangGraph Workflow** - Complete 4-phase campaign creation
4. **Mock Data System** - Generates realistic campaign data
5. **Approval Gates** - Human-in-the-loop checkpoints
6. **Artifact Storage** - Saves to `.artifacts/` folder

### 🔄 Optional Integrations (Not Required)
1. **EmailPilot API** - Can connect if running on port 8000
2. **Klaviyo MCP** - Designed for future MCP protocol integration
3. **Firestore** - Falls back to memory if not available
4. **AI Models** - Works with mock responses if no API keys

## How to Use It Right Now

### 1. Simple Demo (No External Services Needed)
```bash
# This works immediately with mock data
python -m apps.orchestrator_service.main demo \
  --month 2024-11 \
  --brand "YourBrand" \
  --auto-approve
```

### 2. Through the Web UI
1. Open `orchestrator-ui.html` in your browser
2. Enter a brand name and month
3. Click "Start Workflow"
4. Watch as it creates a complete campaign package

### 3. Via API
```bash
curl -X POST http://127.0.0.1:8100/runs/start \
  -H "Content-Type: application/json" \
  -d '{
    "brand_id": "acme-corp",
    "selected_month": "2024-11",
    "tenant_id": "pilot-tenant"
  }'
```

## What Each Phase Does

### Phase 1: Calendar Creation 📅
- **Calendar Performance Agent**: Analyzes historical metrics
- **Calendar Strategist Agent**: Plans optimal send times
- **Output**: Campaign calendar with scheduled sends

### Phase 2: Brief Writing 📝
- **Brand Brain Agent**: Creates strategic brief
- **Approval Gate**: Optional human review
- **Output**: Campaign brief with objectives

### Phase 3: Copywriting ✍️
- **Copy Smith Agent**: Generates multiple variants
- **Layout Lab Agent**: Designs email structure
- **Output**: Copy variants and design specs

### Phase 4: Design & QA ✅
- **Gatekeeper Agent**: Quality review
- **Truth Teller Agent**: Analytics setup
- **Output**: QA report and KPI definitions

## The MCP Server Confusion

The `email-sms-mcp-server` you tried to run is a **stdio-based MCP server**, not an HTTP server. It's designed for a future integration where:

1. The orchestrator would spawn it as a subprocess
2. Communicate via stdin/stdout using MCP protocol
3. Access Klaviyo tools through structured messages

**For now**: The orchestrator works perfectly without it using mock data.

## Real vs Mock Data

### Currently Using Mock Data
```python
# In nodes/calendar_performance.py
def fetch_performance(...):
    # Returns simulated metrics
    return PerformanceSlice(
        revenue_total=125000.50,
        conversion_rate=3.2,
        ...
    )
```

### To Use Real Data (Future)
```python
# Would connect to actual services
client = EmailPilotClient(base_url)
real_data = await client.get_metrics(brand_id)
return PerformanceSlice(**real_data)
```

## What You Get

After running a workflow, check:
```
multi-agent/.artifacts/{brand}/{month}/
├── run_state.json         # Complete workflow state
├── performance_slice.json # Historical metrics (mock)
├── campaign_calendar.json # Planned campaigns
├── campaign_brief.json    # Strategic brief
├── copy_variants.json     # Email copy options
├── design_specs.json      # Layout requirements
└── qa_report.json        # Quality review
```

## Try It Now!

The simplest way to see it work:

```bash
# 1. Make sure the server is running
curl http://127.0.0.1:8100/health

# 2. Run a demo
python -m apps.orchestrator_service.main demo \
  --month 2024-12 \
  --brand "TestBrand" \
  --auto-approve

# 3. Check the results
ls -la .artifacts/TestBrand/2024-12/
```

## Adding AI Models (Optional)

To use real AI models instead of mock responses:

1. Edit `.env` file:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

2. The agents will automatically use these models when available.

## Summary

- **The orchestrator is working** ✅
- **The MCP server "hang" is normal** (it's stdio, not HTTP)
- **You don't need external services** to test it
- **Mock data is built-in** and realistic
- **Try the demo command** to see it create a full campaign

The system is designed to be **progressively enhanced**:
1. Start with mock data (works now)
2. Add AI models when ready (optional)
3. Connect real services later (future)