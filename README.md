# EmailPilot App - AI Agent Orchestration & Model Management

[![Smoke Tests](https://github.com/OWNER/REPO/actions/workflows/smoke.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/smoke.yml)

EmailPilot is a Klaviyo automation and planning platform with **Centralized AI Orchestrator**, **Multi-Agent AI Orchestration** and **Dynamic Model Selection** capabilities. It features a lightweight frontend served from `frontend/public` and a Python backend under `app/`.

## 🆕 Latest Updates (October 2025)

### 📅 Calendar UI/UX Enhancements

Major improvements to the Calendar Master interface for better usability and information density:

#### **Enhanced Campaign Display**
- **Channel-Specific Emojis**: Campaigns now show 📧 (Email), 📱 (SMS), or 💻 (Push) instead of text labels
- **Audience Segment Badges**: Replaced redundant "EMAIL" labels with actual audience segments (🎯 prefix)
- **Expanded Single Events**: Single campaigns expand to fill the entire calendar day for better visibility
- **Multi-Line Names**: Campaign names wrap up to 2 lines instead of truncating
- **Smart Space Utilization**: Better use of vertical space within calendar cells

#### **Improved Calendar Layout**
- **Full Month View**: Optimized sizing fits entire month without scrolling
- **Compact Design**: Reduced day height (140px → 110px) with maintained readability
- **Enhanced Grid Borders**: More defined borders (15% opacity + shadow) for better visual separation
- **Responsive Spacing**: Tighter margins while maintaining clean design

#### **Holiday & Event Display**
- **Full Names Visible**: Holiday/event names wrap to 2 lines instead of cutting off at 15 characters
- **Scrollable Headers**: Multiple holidays scroll within constrained space
- **Smart Truncation**: Shows up to 2 lines with ellipsis for longer names
- **Persistent Emojis**: Holiday emojis always visible as visual indicators

#### **Comprehensive Detail Modal**
- **7+ Information Sections**: Status, details, audience, metrics, content, goals, tags
- **Color-Coded Status Bar**: Visual indicators for Draft/Scheduled/Sent campaigns
- **Performance Metrics**: Large, prominent display of open rate, click rate, revenue
- **Direct Actions**: Edit, Duplicate, Delete buttons within modal
- **Rich Content Preview**: Subject line, preview text, full description

#### **List View Transformation**
- **Drag-and-Drop Scheduling**: Move campaigns between weeks by dragging
- **Rich Information Cards**: Expanded metrics, audience size, status indicators
- **Collapsible Details**: Smooth animations for showing/hiding campaign details
- **Sort & Filter Controls**: Sort by Date/Name/Revenue/Type, filter by channel or type
- **View Persistence**: Stays in list view after delete/duplicate actions
- **Icon-Based Actions**: Info (ℹ️), Duplicate (📋), Edit (✏️), Delete (🗑️) buttons

#### **Error Handling & Performance**
- **Graceful API Failures**: Silent fallbacks for missing endpoints
- **Clean Console**: Debug-level logging for expected failures
- **Browser Extension Compatibility**: Suppressed connection errors
- **Initial Render Guarantee**: Calendar displays immediately on page load

All enhancements maintain backward compatibility with existing functionality.

## Previous Updates (2025-08-29)

### ✨ New Features

- **📊 Klaviyo Data Backfill System**: Comprehensive historical data synchronization
  - Day-by-day backfill for campaigns, flows, and granular order data
  - Real-time progress tracking with resume capability  
  - Web management interface at `/static/backfill_manager.html`
  - Processes complete order details including items, UTM parameters, and customer info
  - Tested with Rogue Creamery, ready for all connected clients
  - [Full Documentation](./BACKFILL_SYSTEM_DOCUMENTATION.md)

## Previous Updates (2025-08-27)

### ✨ Features
- **🎯 Workflow Manager**: Advanced workflow visualization and management system at `/static/workflow_manager.html`
  - Interactive execution flow diagrams with dependency visualization
  - Click-to-edit agents within workflows
  - Real-time workflow status and execution tracking
  - Modern glass morphism UI with smooth animations
  
- **🤖 Enhanced Calendar Workflow Integration**: Multi-agent system for AI-powered campaign planning
  - Brand Calendar Agent for client-specific configurations
  - Historical Analyst for performance analysis
  - Segment Strategist for audience targeting
  - Content Optimizer for campaign content
  - Calendar Orchestrator for final assembly

- **📊 Centralized LLM Configuration**: Updated to latest models (Dec 2024)
  - **OpenAI**: GPT-4o Mini (Good), GPT-4o (Better), O1 Preview (Best)
  - **Anthropic**: Claude 3.5 Haiku (Good), Claude 3.5 Sonnet (Better/Best)
  - **Google**: Gemini 1.5 Flash (Good), Gemini 1.5 Pro (Better), Gemini 2.0 Flash Experimental (Best)

### 🔧 Fixes & Improvements
- **✅ Claude API Integration**: Fixed authentication and model configuration
  - Proper Secret Manager integration for API keys
  - Support for all Claude 3.5 models
  - Resolved credit and authentication issues
  
- **✅ Workflow Builder AI**: Fixed hanging issues and API errors
  - Corrected model ID handling in workflow generation
  - Improved error reporting and debugging
  - Fixed API key passing for all LLM providers
  
- **✅ Workflow Management UI**: Complete functionality restored
  - Fixed edit capabilities for all workflows including Revenue Performance Analyzer
  - Corrected LangGraph Studio link
  - Fixed execution counter persistence
  - Agent editing now works across all workflows

### 🚀 Quick Access
- **Backfill Manager**: `http://localhost:8000/static/backfill_manager.html` 🆕
- **Workflow Manager**: `http://localhost:8000/static/workflow_manager.html`
- **Workflow Builder AI**: `http://localhost:8000/static/workflow_builder_ai.html`
- **Calendar Master**: `http://localhost:8000/static/calendar_master.html`
- **Agent Creator Pro**: `http://localhost:8000/static/agent_creator_enhanced.html`

## 🎨 Workflow Management System

The EmailPilot workflow system provides comprehensive management of AI agent workflows with visual execution tracking and real-time editing capabilities.

### Key Components

#### 1. **Workflow Manager** (`/static/workflow_manager.html`)
- **Visual Execution Flow**: Interactive diagrams showing agent dependencies and execution order
- **Live Agent Editing**: Click any agent to modify prompts and configurations
- **Workflow Categories**: Marketing, Analytics, and Automation workflows
- **Execution Tracking**: Real-time status updates and execution statistics

#### 2. **Available Workflows**
- **📅 Calendar Planning Workflow**: 5-agent system for campaign calendar generation
- **✉️ Email Campaign Generator**: End-to-end email creation with 4 specialized agents
- **💰 Revenue Performance Analyzer**: 2-agent system for revenue analysis

#### 3. **Agent Registry System**
- **Dynamic Configuration**: Agents loaded from Firestore or registry
- **Dependency Management**: Automatic handling of agent dependencies
- **Role-Based Organization**: Each agent has a specific role in the workflow
- **Version Control**: Track and manage agent versions

### Workflow API Endpoints
```
GET  /api/workflow-agents/workflows              # List all workflows
GET  /api/workflow-agents/workflow/{id}          # Get workflow details
GET  /api/workflow-agents/workflow/{id}/execution-graph  # Get execution graph
GET  /api/workflow-agents/agent/{name}           # Get agent details
POST /api/workflow-agents/agent/{name}/update    # Update agent configuration
POST /api/workflow/generate                      # Generate new workflow from prompt
```

### Backfill API Endpoints
```
POST /api/backfill/start/{client_id}             # Start backfill for a client
GET  /api/backfill/status/{client_id}            # Check backfill status
GET  /api/backfill/status                        # Get all backfill statuses
POST /api/backfill/start-all                     # Start backfill for all clients
GET  /api/backfill/data/{client_id}/summary      # Get backfilled data summary
GET  /api/backfill/data/{client_id}/orders       # Get backfilled order data
DELETE /api/backfill/clear/{client_id}           # Clear backfill status
```

## 🚀 NEW: LangGraph Studio + LangSmith Integration

**Full integration with LangGraph Studio for visual debugging and LangSmith for production tracing.**

### Quick Start
```bash
# Setup integration
./scripts/setup_langgraph_integration.sh dev

# Open Hub Dashboard
open http://localhost:8000/hub/
```

### Integration Documentation
- **[📚 Integration Guide](./LANGGRAPH_INTEGRATION.md)** - Complete integration plan and specifications
- **[🔧 Troubleshooting](./LANGGRAPH_TROUBLESHOOTING.md)** - Common issues and solutions
- **[⚙️ Environment Setup](./.env.langgraph.example)** - Configuration reference
- **[🎯 Hub Dashboard](http://localhost:8000/static/hub_dashboard_spec.html)** - Unified control center mockup

### Key Integration Features
- 🎨 **LangGraph Studio** - Visual workflow design and debugging
- 📊 **LangSmith** - Production tracing and monitoring  
- 🏠 **Hub Dashboard** - Unified launcher with deep-links
- 📝 **Workflow Editor** - Schema management and code generation
- 🔍 **End-to-end tracing** - Complete visibility from Studio to production

## 🎯 Quick Links for Developers

### **[📖 UI Development Guide](docs/UI_DEVELOPMENT_GUIDE.md)** - How to add ANY UI feature to EmailPilot
- 3-step process to expose backend features in the UI
- Complete checklist for adding components
- Troubleshooting guide for common issues
- **Required reading before adding UI features**

### **[⚡ Quick Reference Card](docs/UI_QUICK_REFERENCE.md)** - One-page cheat sheet
- Essential commands and file locations
- Copy-paste examples
- Common issues & fixes

### **[🛠️ Developer Tools](http://localhost:8000/admin)** - Access all hidden features
- Click "Developer Tools" in Quick Actions
- Browse and test 200+ backend endpoints
- No need to use Postman or curl

### **[🤖 Machine-Readable Manifest](ui-manifest.json)** - For tools and automation
- JSON specification of UI system
- Parseable by other tools
- Complete component registry

## 📊 Admin Interface

The EmailPilot admin section features an enhanced **collapsible sidebar navigation** system for improved organization and usability:

### Key Features:
- **🎯 Collapsible Sidebar**: Toggle between compact (64px) and expanded (256px) views
- **📁 Organized Groups**: Logical grouping of admin functions
- **🔔 Visual Indicators**: Badge counters for alerts, status indicators for system health
- **📱 Responsive Design**: Mobile-friendly drawer overlay on small screens
- **⌨️ Accessibility**: Full keyboard navigation support with ARIA labels

### Admin Menu Structure:
```
├── 🏠 Core
│   ├── Overview - System dashboard and quick actions
│   ├── Users - User management and permissions
│   └── Clients - Enhanced client management with secure API storage
├── 📅 Planning
│   ├── Goals - Company goals and KPIs
│   └── Alerts - Order and revenue alerts
├── 🤖 AI & Automation
│   ├── MCP - Model Context Protocol management
│   ├── Chat - Klaviyo AI chat interface
│   ├── Models - AI model configuration
│   └── Prompts - Prompt designer
├── 🔌 Integrations
│   ├── Slack - Slack webhook configuration
│   └── OAuth - Service OAuth settings
└── ⚙️ System
    ├── Environment - Environment variables
    ├── Ops & Logs - Operations and logging
    ├── Diagnostics - System health checks
    └── Packages - Package upload and deployment
```

### Accessing the Admin Section:
Navigate to `http://localhost:8000/admin` after logging in. The sidebar will appear on the left side of the screen.

### Global Theme System:
- **🌓 Dark/Light Mode**: Global theme system applies to entire application
- **🎨 Theme Toggle**: Available in main navigation bar, affects all pages
- **💾 Persistence**: Theme preference saved and restored on reload
- **🖥️ System Detection**: Auto-detects and respects OS dark mode preference
- **⚡ No Flash**: Theme applied early to prevent flash of wrong theme
- **📱 Mobile Support**: Updates browser theme-color for mobile UI
- **Full Documentation**: See [Theme System Guide](docs/THEME_SYSTEM.md) for details

### Logo & Branding:
- **EmailPilot Logo**: Displayed in navigation bar and admin sidebar
- **Adaptive Styling**: Logo brightness adjusts for optimal visibility in each theme
- **Click Navigation**: Logo click returns to dashboard from any page

## 🎯 AI System Architecture (Updated 2025-08-22)

### 🆕 LangGraph Visual Workflows
**LangGraph Studio provides visual workflow orchestration:**
- Browser-based editor at `https://smith.langchain.com/studio/`
- Campaign planning graph with Klaviyo integration
- Full LangSmith tracing and debugging
- See [LangGraph README](emailpilot_graph/README.md) for setup

### LangChain Multi-Agent System
**LangChain provides text-based AI orchestration:**
- Multi-agent orchestration with specialized roles
- RAG (Retrieval Augmented Generation) capabilities
- Flexible provider support (OpenAI, Claude, Gemini)
- Production-ready agent workflows

See [Migration Guide](LANGGRAPH_MIGRATION.md) for transition details.

### Legacy AI Orchestrator (Archived)
The previous AI Orchestrator system has been replaced by LangChain. Legacy documentation available at [docs/ARCHIVED_AI_ORCHESTRATOR.md](docs/ARCHIVED_AI_ORCHESTRATOR.md).

## 🚨 CRITICAL: AI Agent & Model Setup Instructions

This document provides complete setup instructions to get AI Agents and Model Selection working correctly. If agents are detected but not invoked, or if no models appear in dropdowns, follow the steps below.

## Key Documentation
- **🆕 LangGraph Studio**: [LangGraph Setup](emailpilot_graph/README.md) - Visual workflow orchestration
- **📋 Migration Guide**: [LangGraph Migration](LANGGRAPH_MIGRATION.md) - Transition from MCP agents
- **🤖 LangChain Integration**: [LangChain Summary](LANGCHAIN_INTEGRATION_SUMMARY.md) - Multi-agent orchestration
- **📊 Test Results**: Successfully retrieving and analyzing $14,138.83 in 7-day revenue for Rogue Creamery
- Changelog & Legacy Map: `docs/CHANGELOG_AND_LEGACY.md`
- Rollout & Deployment Checklist: `docs/ROLLOUT_CHECKLIST.md`
 - Preflight Runner: `scripts/preflight_checklist.py` (use `--write` to auto-check items)
- Services Catalog: `docs/services_catalog.md` (JSON for Admin UI at `docs/services_catalog.json`)

## 🚀 Quick Start - Complete AI Setup

### Prerequisites
1. **Python 3.11+** with pip
2. **Google Cloud Project** with Firestore and Secret Manager enabled
3. **Node.js 16+** for frontend build
4. **API Keys** for AI providers (OpenAI, Claude, Gemini)

### Step 1: Environment Setup
```bash
# Clone the repository
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # IMPORTANT: Use .venv, NOT conda

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export GOOGLE_CLOUD_PROJECT="emailpilot-438321"  # or your project ID
export SECRET_MANAGER_TRANSPORT="rest"  # Use REST transport for Secret Manager
export ENVIRONMENT="development"
```

### Step 2: Configure AI Provider API Keys

**CRITICAL**: The AI models won't work without API keys configured in Google Secret Manager.

```bash
# Option A: Use gcloud CLI to create secrets
gcloud secrets create openai-api-key --data-file=- <<< "sk-your-openai-key-here"
gcloud secrets create gemini-api-key --data-file=- <<< "your-gemini-key-here"
gcloud secrets create emailpilot-claude --data-file=- <<< "your-claude-key-here"

# Option B: Use the Admin UI (after starting the server)
# Navigate to http://localhost:8000/admin/ai-models
# Click on each provider and add API keys through the UI
```

### Step 3: Verify Agent Configuration Files
```bash
# Check that agent config exists (REQUIRED)
ls -la email-sms-mcp-server/agents_config.json
# This file MUST exist - it's already in the repo

# Optional: Create custom instructions for agent behavior
cat > email-sms-mcp-server/custom_instructions.json << 'EOF'
{
  "agents": {
    "content_strategist": {
      "preferred_provider": "openai",
      "preferred_model": "gpt-4",
      "fallback_providers": ["gemini", "claude"]
    },
    "copywriter": {
      "preferred_provider": "claude",
      "preferred_model": "claude-3-sonnet",
      "fallback_providers": ["openai", "gemini"]
    }
  }
}
EOF
```

### Step 4: Start the Application
```bash
# CRITICAL: Must use --host localhost (NOT 127.0.0.1 or 0.0.0.0)
uvicorn main_firestore:app --port 8000 --host localhost --reload

# Alternative using make
make dev  # Ensure Makefile uses --host localhost
```

## Frontend Recovery and Build (Standardized)

The frontend now relies on precompiled assets served from `/static/dist`, which maps to `frontend/dist` in the repo. A stable build script and Makefile target are provided.

### Build the Frontend

```bash
# One command
make build

# Or directly run the script
bash scripts/build_frontend.sh
```

What it does:
- Compiles JSX components with esbuild to `frontend/dist`
- Generates or copies CSS to `frontend/dist/styles.css`
- Mirrors outputs to `frontend/public/dist` for compatibility
- Assets served by FastAPI under `/static/dist/*`

### Smoke Test (local)

```bash
# Start backend
make dev

# In another terminal, verify:
curl -sI http://localhost:8000/ | head -n1            # 200 OK
curl -sI http://localhost:8000/admin | head -n1       # 200 OK
curl -sI http://localhost:8000/admin-dashboard | head -n1  # 200 OK

# Check key assets
curl -sI http://localhost:8000/static/dist/app.js | head -n1
curl -sI http://localhost:8000/static/dist/styles.css | head -n1

# Check core APIs
curl -sI http://localhost:8000/health | head -n1
curl -sI http://localhost:8000/api/admin/system/status | head -n1
curl -sI http://localhost:8000/api/auth/google/status | head -n1
```

### Best Practice: Use `/static/dist`

- Server mounts: `/static` → `frontend/public` and `/static/dist` → `frontend/dist`.
- The build outputs to `frontend/dist`. Do not point new features to other locations.
- The script mirrors outputs to `frontend/public/dist` to support existing HTML during transition.

### Modern Authentication with Clerk (NEW - Recommended)

EmailPilot now supports **Clerk** for modern, secure authentication with SSO, multi-tenant support, and refresh tokens.

#### Setting up Clerk Authentication:

1. **Create a Clerk account** at https://dashboard.clerk.com
2. **Get your API keys** from the Clerk dashboard
3. **Store keys in Google Secret Manager**:
   ```bash
   # Store Clerk keys (already done - keys are in Secret Manager)
   gcloud secrets versions list CLERK_SECRET_KEY
   gcloud secrets versions list NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
   ```

4. **Test the new auth endpoints**:
   ```bash
   # Check auth status
   curl -s http://localhost:8000/api/auth/v2/auth/me
   
   # Login with email/password
   curl -X POST http://localhost:8000/api/auth/v2/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"demo@emailpilot.ai","password":"demo"}'
   
   # Create API key (requires auth)
   curl -X POST http://localhost:8000/api/auth/v2/auth/api-keys \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"My API Key","scopes":["read","write"]}'
   ```

5. **Access the test dashboard**:
   ```
   http://localhost:8000/static/test-auth-v2.html
   ```

#### Features of the New Auth System:
- ✅ **Multi-tenant support** - Isolate data per organization
- ✅ **Refresh tokens** - Automatic token renewal
- ✅ **API key management** - Programmatic access
- ✅ **SSO with Clerk** - Enterprise-grade authentication
- ✅ **No timeouts** - Fixed the 2+ second OAuth delays

See [AUTH_V2_MIGRATION_GUIDE.md](AUTH_V2_MIGRATION_GUIDE.md) for complete migration instructions.

### Google OAuth Login (Legacy - Being Replaced)

Status endpoints to confirm wiring:

```bash
curl -s http://localhost:8000/api/auth/google/status | jq .
curl -sI http://localhost:8000/api/auth/me  # 401 when not logged in
```

To enable Google OAuth end-to-end, set these env vars (and corresponding credentials in GCP Console):

```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/google/callback"
```

Then restart the server and perform the login flow from the Admin UI or the dedicated login page (`frontend/public/debug-login.html`).

### Backup and Archival

- A timestamped backup of a working frontend snapshot is written to `backups/working_frontend_YYYYmmdd_HHMMSS.tgz` after successful recovery.
- Legacy frontend folders are preserved under `archive/legacy/` (e.g., early SPA deployments), keeping the repo clean while retaining history.

### Troubleshooting

- If `/static/dist/*` returns 404, rebuild (`make build`) and confirm `frontend/dist` has outputs.
- If Tailwind CLI is unavailable, the build script falls back to copying `frontend/public/styles/main.css` to `styles.css`.
- If admin pages show minimal styling with the template system, functionality can still be tested via links and APIs. Styling can be improved later without affecting endpoints.

### Step 5: Verify Services Are Running
```bash
# Check health
curl -s http://localhost:8000/health | jq .

# Start MCP Services (for Klaviyo data)
cd services/klaviyo_revenue_api
uvicorn main:app --port 9090 --reload &

# Check MCP health
curl -s http://localhost:9090/healthz | jq .

# Test LangChain Integration
python rogue_creamery_production.py
# Should retrieve and analyze Klaviyo data successfully
```

## 🤖 LangChain Multi-Agent System - How It Works

### Architecture Overview
1. **LangChain Core** (`multi-agent/integrations/langchain_core/`)
   - Multi-agent orchestration framework
   - Tool execution via MCP (Model Context Protocol)
   - RAG capabilities for document-based Q&A
   - Flexible provider support (OpenAI, Claude, Gemini)

2. **MCP Services** (Deterministic Tool Execution)
   - **Klaviyo Revenue API** (`services/klaviyo_revenue_api/`) - Port 9090
   - **Performance API** (`services/performance_api/`) - Port 9091
   - Provides reliable data retrieval and job execution

3. **Integration Layer**
   - LangChain agents call MCP tools for data
   - AI analysis performed on retrieved data
   - Results saved to Firestore and JSON reports

### Why Agents Might Not Be Working

**Problem 1: No API Keys Configured**
- **Symptom**: Agents detected but return simulated responses
- **Fix**: Add API keys to Secret Manager (see Step 2 above)

**Problem 2: Wrong Host Configuration**
- **Symptom**: CORS errors, connection refused
- **Fix**: Always use `--host localhost` when starting server

**Problem 3: Missing Agent Prompts in Firestore**
- **Symptom**: Agents use generic prompts instead of specialized ones
- **Fix**: Create agent-specific prompts via Admin UI

```bash
# Create agent prompt via API
curl -X POST http://localhost:8000/api/ai-models/prompts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "content_strategist_prompt",
    "description": "Campaign strategy development prompt",
    "prompt_template": "You are a content strategist. Given: {request_data}, create a comprehensive campaign strategy.",
    "model_provider": "openai",
    "model_name": "gpt-4",
    "category": "agent",
    "variables": ["request_data"],
    "metadata": {"agent_type": "content_strategist"}
  }'
```

## 🎯 LangChain Integration Examples

### Working Example: Rogue Creamery Analysis

```bash
# Start MCP server for Klaviyo data
cd services/klaviyo_revenue_api
uvicorn main:app --port 9090 --reload &

# Run production analysis
python rogue_creamery_production.py

# Results:
# - Total Revenue: $14,138.83
# - Campaign Revenue: $10,351.66 (73.2%)
# - Flow Revenue: $3,787.17 (26.8%)
# - Total Orders: 105
# - Average Order Value: $134.66
```

### MCP Tool Endpoints

```bash
# Get 7-day revenue for a client
curl "http://localhost:9090/clients/by-slug/rogue-creamery/revenue/last7?timeframe_key=last_7_days"

# Get weekly metrics bundle
curl "http://localhost:9090/clients/by-slug/rogue-creamery/weekly/metrics"
```

## 📊 AI Model Selection - Configuration Guide

### Available Providers and Models

**OpenAI**
- Models: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`
- Secret Name: `openai-api-key`

**Gemini (Google)**
- Models: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-pro-002`, `gemini-1.5-flash-002`
- Secret Name: `gemini-api-key`

**Claude (Anthropic)**
- Models: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-haiku-20240307`
- Secret Name: `claude-api-key` or `emailpilot-claude`

### Admin UI - AI Models Management

Navigate to: **http://localhost:8000/admin/ai-models**

1. **Providers Tab**: Configure API keys
2. **Prompts Tab**: Create/edit prompt templates
3. **Agent Config Tab**: Map agents to prompts and models
4. **Test Console**: Test prompts with live models

### Testing LangChain Integration

```python
# Production-ready test script
from rogue_creamery_production import KlaviyoAnalyzer

# Initialize analyzer
analyzer = KlaviyoAnalyzer("rogue-creamery")

# Fetch data from MCP
data = analyzer.fetch_revenue_data()
# Returns: {'total': 14138.83, 'campaign_total': 10351.66, ...}

# Analyze with AI
analysis = analyzer.analyze_performance()
# Generates insights and recommendations

# Display and save results
analyzer.display_results()
analyzer.save_report("report.json")
```

## 🔧 Troubleshooting Guide

### Issue: "No AI models in dropdown"

**Diagnosis Steps:**
1. Check API keys are configured:
   ```bash
   curl http://localhost:8000/api/ai-models/providers | jq '.providers[] | {name, has_key}'
   ```

2. Verify Secret Manager access:
   ```bash
   gcloud secrets list --project=$GOOGLE_CLOUD_PROJECT
   ```

3. Check service account permissions:
   ```bash
   gcloud projects get-iam-policy $GOOGLE_CLOUD_PROJECT \
     --flatten="bindings[].members" \
     --filter="bindings.role:roles/secretmanager.secretAccessor"
   ```

**Solution:**
- Add API keys via Admin UI or gcloud CLI
- Grant Secret Manager access to service account
- Restart the server after adding keys

### Issue: "Agents detected but not invoked"

**Diagnosis Steps:**
1. Check agent service is loaded:
   ```bash
   curl http://localhost:8000/api/agent-config/agents | jq .
   ```

2. Verify orchestrator files exist:
   ```bash
   ls -la email-sms-mcp-server/{server.py,agents_config.json}
   ```

3. Check logs for errors:
   ```bash
   tail -f logs/emailpilot_app.log | grep -E "agent|orchestrator"
   ```

**Solution:**
- Ensure `email-sms-mcp-server/` directory exists with required files
- Check Python path includes the MCP server directory
- Reload agents after configuration changes:
  ```bash
  curl -X POST http://localhost:8000/api/agent-config/agents/reload
  ```

### Issue: "CORS errors when calling AI services"

**Solution:**
- Always start server with `--host localhost` (not 127.0.0.1)
- Check CORS configuration in environment:
  ```bash
  export CORS_ALLOW_ALL=true  # For development only
  # OR
  export CORS_ORIGINS="http://localhost:8000,http://localhost:3000"
  ```

### Issue: "Timeout errors when invoking agents"

**Solution:**
- Increase timeout for AI model calls
- Use fallback providers for resilience
- Check network connectivity to AI provider APIs

## 💬 Model Chat - Interactive AI Testing

### Overview
The Model Chat feature provides a direct chat interface to test AI models and agent behaviors without writing code. Access it via **Admin → AI Models → Model Chat**.

### Features
- **Multi-Provider Support**: Chat with OpenAI, Claude, or Gemini models
- **Agent Integration**: Optionally use agent system prompts for specialized responses
- **Configurable Parameters**: Adjust temperature and max tokens in real-time
- **Token Usage Tracking**: See input/output token counts for each response
- **Session Management**: Clear chat history with "Reset Session"

### How to Use Model Chat

1. **Navigate to Model Chat**:
   ```
   http://localhost:8000/admin/ai-models
   → Click "Model Chat" tab
   ```

2. **Select Provider and Model**:
   - Choose from configured providers (OpenAI, Claude, Gemini)
   - Select specific model (e.g., gpt-4, claude-3-sonnet, gemini-1.5-pro)

3. **Optional Agent Selection**:
   - Choose an agent to use its specialized prompt
   - Agents include: copywriter, content_strategist, designer, etc.

4. **Configure Parameters**:
   - **Temperature** (0.0-2.0): Controls randomness (0=deterministic, 2=creative)
   - **Max Tokens** (1-4096): Maximum response length

5. **Start Chatting**:
   - Type your message
   - Press Send or Ctrl+Enter (Cmd+Enter on Mac)
   - View responses with provider/model info and token usage

### API Testing with cURL

Test the Model Chat endpoints directly:

```bash
# List available models for a provider
curl -s "http://localhost:8000/api/ai-models/models?provider=openai" | jq .

# Simple chat completion (no agent)
curl -s -X POST http://localhost:8000/api/ai-models/chat/complete \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4",
    "messages": [{"role":"user","content":"Write a haiku about coffee"}],
    "temperature": 0.7,
    "max_tokens": 100
  }' | jq .

# Chat with agent context
curl -s -X POST http://localhost:8000/api/ai-models/chat/complete \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "claude",
    "model": "claude-3-sonnet",
    "messages": [{"role":"user","content":"Create an email subject line"}],
    "temperature": 0.8,
    "max_tokens": 150,
    "agent_type": "copywriter"
  }' | jq .
```

### Response Format

Successful response:
```json
{
  "ok": true,
  "output_message": {
    "role": "assistant",
    "content": "Model's response text here..."
  },
  "usage": {
    "input_tokens": 25,
    "output_tokens": 50,
    "total_tokens": 75,
    "provider_raw": {...}
  }
}
```

Error response:
```json
{
  "ok": false,
  "error": {
    "message": "Error description",
    "provider": "openai",
    "code": "invalid_model"
  }
}
```

### Troubleshooting Model Chat

**Issue: "No providers available"**
- Ensure API keys are configured in Secret Manager
- Check `/api/ai-models/providers` shows `"has_key": true`

**Issue: "Model not responding"**
- Verify API key is valid for the provider
- Check network connectivity to provider APIs
- Review logs: `tail -f logs/emailpilot_app.log`

**Issue: "Agent not affecting responses"**
- Ensure agent prompts are configured in Firestore
- Check agent is mapped to a prompt template
- Verify with: `curl http://localhost:8000/api/agent-config/agents`

## 🎯 Klaviyo MCP Enhanced - Advanced Analytics & 18+ Tool Categories

### 🚀 NEW: Enhanced MCP Integration (August 2025)
EmailPilot now features the **Klaviyo MCP Server Enhanced** with comprehensive API coverage and advanced capabilities:

#### Key Features
- **18 Tool Categories**: Profiles, Lists, Segments, Campaigns, Metrics, Flows, Templates, Catalogs, Tags, Webhooks, Data Privacy, Coupons, Forms, Reviews, Images, Reporting, Events, Attribution
- **Advanced Analytics**: Campaign performance metrics, revenue attribution, custom metric aggregation
- **Intelligent Gateway**: Routes to Enhanced MCP (primary) or Python MCP (fallback)
- **Dynamic API Keys**: Automatic retrieval from Secret Manager via Firestore references
- **Full Integration**: Works with LangChain, LangGraph, and Calendar Planning

#### Architecture
```
EmailPilot → MCP Gateway → Enhanced MCP (Node.js, Port 9095)
                        ↘ Fallback MCP (Python, Port 9090)
```

### Starting Enhanced MCP Services
```bash
# Start Enhanced MCP Server (Node.js)
cd services/klaviyo_mcp_enhanced
npm start  # Runs on port 9095

# Start Fallback Python MCP (automatic fallback)
uvicorn services.klaviyo_api.main:app --host 127.0.0.1 --port 9090

# Or use the convenience script
./scripts/start_mcp_enhanced.sh
```

### Admin Dashboard
Access the Enhanced MCP management interface:
```
http://localhost:8000/mcp_enhanced_admin.html
```

Features:
- Real-time service status monitoring
- 18 tool category overview
- Client API key validation
- Tool testing interface
- Gateway routing control

### API Key Management
The Enhanced MCP Gateway automatically:
1. Reads client documents from Firestore
2. Retrieves `klaviyo_api_key_secret` field
3. Fetches actual API key from Secret Manager
4. Injects key into Enhanced MCP requests
5. Falls back to Python MCP if Enhanced fails

No manual API key configuration needed!

### ClientKeyResolver - Centralized API Key Resolution

**IMPORTANT**: All new code accessing Klaviyo API keys MUST use the `ClientKeyResolver` service instead of direct Secret Manager or Firestore access.

#### Overview
The `ClientKeyResolver` (`app/services/client_key_resolver.py`) provides a centralized, intelligent service for resolving Klaviyo API keys with comprehensive fallback handling.

#### Features
- **Automatic Secret Manager Integration**: Seamlessly fetches keys from Google Secret Manager
- **Intelligent Name Mapping**: Generates secret names from client names (e.g., "Consumer Law Attorneys" → "klaviyo-api-consumer-law-attorneys")
- **Field Standardization**: Uses `klaviyo_api_key_secret` as the standard field (with backward compatibility for `klaviyo_secret_name`)
- **Legacy Support**: Falls back to plaintext fields (`klaviyo_api_key`, `klaviyo_private_key`) when needed
- **Automatic Migration**: Migrates legacy plaintext keys to Secret Manager on first access
- **Development Mode**: Supports environment variable fallbacks for local development

#### Usage in FastAPI Endpoints

```python
from fastapi import Depends
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver

@router.get("/endpoint")
async def your_endpoint(
    client_id: str,
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
):
    # Get the API key for a client
    api_key = await key_resolver.get_client_klaviyo_key(client_id)
    
    if not api_key:
        raise HTTPException(status_code=404, detail="No API key found")
    
    # Use the API key...
    return {"status": "success"}
```

#### Usage in Non-FastAPI Code

```python
from app.services.client_key_resolver import ClientKeyResolver
from app.services.secrets import SecretManagerService
from google.cloud import firestore

# Initialize dependencies
db = firestore.Client(project="emailpilot-438321")
secret_manager = SecretManagerService("emailpilot-438321")
resolver = ClientKeyResolver(db=db, secret_manager=secret_manager)

# Get API key
api_key = await resolver.get_client_klaviyo_key("client-id")
```

#### Fallback Order
1. **Primary**: `klaviyo_api_key_secret` field → Secret Manager
2. **Legacy Field**: `klaviyo_secret_name` field → Secret Manager (backward compatibility)
3. **Generated Name**: Auto-generated from client name → Secret Manager
4. **Legacy Plaintext**: `klaviyo_api_key` or `klaviyo_private_key` fields (with auto-migration)
5. **Environment Variables**: Development mode fallback (e.g., `KLAVIYO_API_KEY_CLIENT_SLUG`)

#### Field Naming Standard
- **Use**: `klaviyo_api_key_secret` in Firestore documents
- **Avoid**: `klaviyo_secret_name` (deprecated but supported)
- **Never**: Store raw API keys in `klaviyo_api_key` or `klaviyo_private_key` (auto-migrated)

#### Benefits
- **Single Source of Truth**: All API key logic centralized in one place
- **Automatic Handling**: Manages Secret Manager access, fallbacks, and migrations
- **Security**: Ensures keys are stored securely and never exposed in logs
- **Consistency**: Standardizes field naming across the entire codebase
- **Dependency Injection**: Works seamlessly with FastAPI's dependency system

## 📝 Configuration Files Reference

### Required Files
- `services/klaviyo_mcp_enhanced/` - Enhanced MCP server (Node.js)
- `app/api/mcp_gateway.py` - Gateway service for routing
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (includes MCP settings)

### Optional Files
- `docs/services_catalog.json` - Service registry for Admin UI
- Custom agent configurations in Firestore

## 🔄 Development Workflow

1. **Start with environment setup** (Step 1)
2. **Configure API keys** (Step 2)
3. **Start the server** (Step 4)
4. **Test agent invocation** (Testing section)
5. **Configure prompts via Admin UI** as needed
6. **Monitor logs** for issues: `tail -f logs/*.log`

## 🏢 Enhanced Client Management System

EmailPilot features a comprehensive client management system with secure API key handling and unified data storage.

### Key Features
- **Unified Firestore Storage**: Single document per client with 25+ configurable fields
- **Secure API Key Management**: Integration with Google Secret Manager for encrypted storage
- **Client Slug Generation**: Auto-generated slugs from client names for consistent identification
- **LangChain Variable Integration**: Client data automatically available to AI agents
- **Development Mode Fallback**: Graceful handling when Secret Manager is unavailable

### Client Data Structure
Each client document in Firestore contains:
- **Basic Info**: `client_name`, `client_slug`, `industry`, `company_size`
- **Contact Details**: `primary_contact_name`, `primary_contact_email`, `account_manager`
- **Klaviyo Configuration**: `klaviyo_account_id`, `klaviyo_company_id`, metric IDs
- **API Security**: `klaviyo_api_key_secret` (Secret Manager reference)
- **Campaign Settings**: `timezone`, `currency`, segment configurations
- **Goals & Metrics**: Revenue targets, conversion goals, custom KPIs

### Secret Manager Integration
- **Naming Convention**: API keys stored as `klaviyo-api-{client_slug}`
- **Automatic Resolution**: System automatically maps client slugs to Secret Manager entries
- **Secure Access**: Uses Google Cloud IAM for encrypted storage and retrieval
- **Development Mode**: Falls back to plaintext storage when Secret Manager unavailable

### Client Slug System
- **Auto-Generation**: Slugs created from client names (e.g., "Rogue Creamery" → "rogue-creamery")
- **Consistent Identification**: Used across API endpoints, MCP tools, and agent references
- **Migration Complete**: All legacy random IDs standardized to human-readable slugs
- **API Compatibility**: Both `/clients/{client_id}` and `/clients/by-slug/{slug}` endpoints supported

### Testing & Development Tools
- **Client Validation**: `/api/admin/clients/validate` endpoint for configuration testing
- **API Key Testing**: Built-in Klaviyo API connectivity validation
- **Bulk Operations**: Import/export client configurations
- **Development Helpers**: Mock data generation and testing utilities

### Example Usage
```bash
# Get client by slug
curl "http://localhost:8000/api/clients/by-slug/rogue-creamery"

# Test Klaviyo connectivity
curl "http://localhost:8000/api/admin/clients/rogue-creamery/test-klaviyo"

# Get revenue data (uses client slug internally)
curl "http://localhost:9090/clients/by-slug/rogue-creamery/revenue/last7"
```

## 📚 Additional Resources

- [AgentService.md](AgentService.md) - Detailed agent service documentation
- [docs/AGENT_MCP_REVIEW_AND_FIXES.md](docs/AGENT_MCP_REVIEW_AND_FIXES.md) - Review and fixes
- [email-sms-mcp-server/README.md](email-sms-mcp-server/README.md) - MCP server details

## ⚠️ Important Notes

1. **Security**: Never commit API keys to the repository. Use Secret Manager.
2. **Development**: Use `--host localhost` to avoid CORS issues
3. **Production**: Configure proper CORS origins and disable `CORS_ALLOW_ALL`
4. **Monitoring**: Check logs regularly: `logs/emailpilot_app.log` and `logs/agent_orchestrator.log`
5. **Updates**: After changing agent configs, reload: `POST /api/agent-config/agents/reload`

---

## Legacy Quick Start (for reference)
- Frontend (static):
  - Build (optional): `npm run build`
  - Serve locally: `npm run serve` then open http://localhost:8080/
- Backend (FastAPI/Uvicorn): see `EMAILPILOT_SETUP.md` and `main_firestore.py`.
 - Health: backend exposes `GET /health` for probes.

## Preflight Checklist (Optional)
- Report-only: `python scripts/preflight_checklist.py`
- Update docs/ROLLOUT_CHECKLIST.md: `python scripts/preflight_checklist.py --write`

UX/UI Guidelines
For consistent, world‑class visuals across the app, follow the design system documented here:

- UX/UI guidelines: [EMAILPILOT_UX_UI_GUIDELINES.md](EMAILPILOT_UX_UI_GUIDELINES.md)
  - Shadow policy (bold shadow on login + popovers only)
  - Primary button style (`.ep-btn-primary`) and how to force apply
  - Login layout, microcopy, and divider naming
  - Theme enhancer behavior (`frontend/public/dist/brand-theme.js`)
  - AI implementation checklist and accessibility notes

Project Docs
- Deployment and system docs live alongside the codebase (search for `*_README.md`).
- Calendar and integration notes: see `EMAILPILOT_CALENDAR_FINAL.md`, `EMAILPILOT_SETUP.md`.
- Refactoring summary: [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)
- Agent service details: [AgentService.md](AgentService.md)
- **Calendar Planning AI**: [CALENDAR_PLANNING_AI.md](CALENDAR_PLANNING_AI.md) - AI-powered calendar generation with MCP integration

## Dev Notes → Typing

**Postponed Annotations Pattern**: This codebase uses `from __future__ import annotations` and `TYPE_CHECKING` guards to avoid import-time circular dependencies and NameError issues in FastAPI applications. Heavy service classes (e.g., `SecretManagerService`, `AIModelsService`, `KlaviyoClient`) are imported under `if TYPE_CHECKING:` blocks and referenced as forward refs (`"ClassName"`) in function signatures. This ensures clean module loading at runtime while maintaining full static type checking support. See Python 3.12+ documentation on postponed evaluation of annotations for details.

Admin Ops Endpoints (for UI)
- `GET /api/admin/ops/logs/large?threshold=500M` – list large log files (`logs/*`, `*.log`, `*.out`).
- `POST /api/admin/ops/logs/cleanup` – body `{ "mode": "list|truncate|delete", "threshold": "500M" }` to act on large logs.
- `GET /api/admin/ops/files/big?threshold=200M` – list large non‑log files to review.
- `GET /api/admin/revenue/status?base=http://127.0.0.1:9090&origin=http://localhost:3000` – probe Revenue API health and CORS preflight, returns headers.
- `POST /api/admin/klaviyo/start` – body `{ "host": "127.0.0.1", "port": 9090 }` to start local Klaviyo API (dev), logs at `logs/klaviyo_api_uvicorn.out`.
- `POST /api/admin/revenue/stop` – stop the background Revenue API process started via the admin endpoint.
- `GET /api/admin/services` – wrapped services catalog (with count, last_modified).
- `GET /api/admin/services/catalog` – raw JSON array from `docs/services_catalog.json`.

Navigation & URL Structure
EmailPilot uses client-side routing with real URLs for all sections, making it easy to bookmark, share, and directly access any part of the application.

**Available URLs:**
- `/` or `/dashboard` - Main dashboard
- `/dashboard/metrics` - Dashboard with metrics focus
- `/dashboard/reports` - Dashboard with reports focus
- `/reports` - Reports overview
- `/reports/performance` - Performance reports
- `/reports/revenue` - Revenue reports
- `/goals` - Goals dashboard
- `/goals/{clientId}` - Specific client goals (e.g., `/goals/rogue-creamery`)
- `/calendar` - Calendar view
- `/calendar/month` - Monthly calendar view
- `/calendar/week` - Weekly calendar view
- `/admin` - Admin panel (defaults to system status)
- `/admin/system` - System status
- `/admin/agents` - Agent management
- `/admin/clients` - Client management
- `/admin/mcp` - MCP management
- `/admin/secrets` - Secrets management
- `/admin/packages` - Package upload
- `/admin/environment` - Environment variables

**Programmatic Navigation:**
The app provides a global `nav` helper for navigation:
```javascript
// Navigate to specific sections
window.nav.toDashboard();           // Go to dashboard
window.nav.toReports('performance'); // Go to performance reports
window.nav.toGoals('client-123');    // Go to specific client goals
window.nav.toAdmin('agents');        // Go to admin agents section

// Direct navigation with router
window.EmailPilotRouter.navigate('/admin/system');
```

**Deep Linking:**
All URLs are directly accessible and bookmarkable. You can share links like:
- `http://localhost:8000/admin/system` - Direct link to System Status
- `http://localhost:8000/reports/performance` - Direct link to Performance Reports
- `http://localhost:8000/goals/rogue-creamery` - Direct link to client goals

Contributing
- Keep UI changes aligned with the guidelines above.
- Prefer `data-ep-primary` for primary buttons.
- Use `ep-shadow-heavy` only for login and dialogs/popovers.
- When adding new sections, update the router configuration in `app.js`
- Use the navigation helper (`window.nav`) for programmatic navigation

Documentation Policy
- Any change to service structure, new services, or endpoint reshuffling must update both:
  - `docs/services_catalog.md` (human-readable table)
  - `docs/services_catalog.json` (machine-readable for Admin UI)
- PRs that add/modify services should include these docs updates; the Admin UI consumes `/api/admin/services/catalog` for live catalogs.

Using the AI Agent System
To use the AI agent system, send a POST request to the `/api/agents/invoke` endpoint. The request body should be a JSON object containing the data you want to process. For example:
```json
{
  "client_id": "your_client_id",
  "campaign_brief": "Create a campaign for a new product launch."
}
```
The response will be a JSON object containing the results of the agent orchestration.

For setup, usage, and troubleshooting guidance, see [AgentService.md](AgentService.md).

**Note on Agent Configuration**: Changes made to agent instructions in the admin panel are applied automatically and immediately. There is no need to restart the server.

**Note on Adding New Agents**: When a new agent is added via the admin panel, its configuration is saved. However, to make the agent fully functional, a developer must update the `MultiAgentOrchestrator` in `email-sms-mcp-server/server.py` to include the new agent in the orchestration logic.

MCP Klaviyo Tool Integration
- Service: Klaviyo API service under `services/klaviyo_api/` (legacy folder `services/revenue_api/` retained for reference)
  - GET `/healthz` – health check
  - GET `/clients/{client_id}/revenue/last7?timeframe_key=last_7_days&tz=` – sums Klaviyo Campaign + Flow conversion_value for the client's Placed Order metric
  - GET `/clients/by-slug/{slug}/revenue/last7?timeframe_key=...` – same, resolves by slug
  - Reads Klaviyo API key from Secret Manager; resolves metric_id from Firestore (or auto-detects)
  - Cache TTL via `REVENUE_CACHE_TTL` (default 300s)
  - Weekly metrics bundle: `GET /clients/{client_id}/weekly/metrics` and `/clients/by-slug/{slug}/weekly/metrics` (campaign/flow totals + order counts) — new
- OpenAPI MCP wrapper:
  - `npx @modelcontextprotocol/openapi --spec services/klaviyo_api/openapi.yaml --server.url http://localhost:9090`
  - AgentService should call the MCP tool mapped to GET `/clients/{client_id}/revenue/last7` or `/clients/{client_id}/weekly/metrics`
  - Instruction: “When asked for revenue based on ‘Placed Order’, call the revenue tool. Do not use metric-aggregates for attribution.”

Admin – MCP Management (Frontend)
- Add a tab to Admin for MCP Management that surfaces:
  - Tool registry (from OpenAPI MCP), health, and version
  - Revenue service health, Klaviyo connectivity, Firestore/Secrets checks
  - Configuration: default timeframe key, cache TTL, auto-detect metric toggle, lock metric per client
  - Client controls: lookup by slug or ID; recompute, clear cache, detect metric, save metric
  - Logs: recent requests, last Klaviyo error detail
  - Wrapper controls: show URL, status, restart, validate tool call

Firestore Client IDs ✅ COMPLETED
- ✅ **COMPLETED**: All `clients` document IDs standardized to human-readable slugs (e.g., `rogue-creamery`)
- Migration script: `scripts/migrate_client_ids.py` (completed - shallow copy + tombstone)

MCP Revenue Service – Full Context and Decisions
- Objective: Reliably answer “How much revenue do we have for the last 7 days based on the Placed Order metric?” quickly and accurately, then generalize for flexible timeframes and MCP integration.
- Early failures and root causes:
  - Using `/api/metric-aggregates` with `measurement=sum` or `sum($value)` undercounted or returned 404/400 due to:
    - Missing trailing slash and missing `content-type` header.
    - Wrong filter grammar: Klaviyo expects function style filters and unquoted timestamps; timeframe is not supported on that endpoint as used.
    - More importantly, metric-aggregates total ≠ email-attributed revenue (Campaign + Flow). It sums raw event values, not marketing attribution.
  - Correct endpoint family for attribution: values reports by channel
    - `/api/campaign-values-reports/` and `/api/flow-values-reports/`
    - data.type MUST be endpoint-specific: `campaign-values-report` or `flow-values-report`.
    - attribution “revenue” comes from `statistics: ["conversions", "conversion_value"]` (not `value_statistics`).
    - timeframe MUST be `{ "key": "…" }`, e.g. `{ "key": "last_7_days" }`.
- Implemented solution (services/revenue_api):
  - Endpoints:
    - GET `/healthz` – health check.
    - GET `/clients/{client_id}/revenue/last7` – compute attribution totals for the client.
    - GET `/clients/by-slug/{slug}/revenue/last7` – same, resolves client doc by `client_slug`.
  - Query params (flexible timeframe):
    - `timeframe_key`: one of `last_7_days` (default), `last_30_days`, `last_90_days`, `yesterday`, `last_24_hours`.
    - `start`, `end`: ISO8601 bounds (optional). If both provided, they override `timeframe_key`.
    - `timeframe`: URL-encoded JSON object for full control (e.g., `{ "key": "last_7_days" }` or `{ "start": "…", "end": "…" }`).
    - `tz`: reserved for future per-zone handling; values-reports accept only `key` or start/end.
    - `recompute`: boolean to bypass cache for one request.
  - Output: `{ client_id, metric_id, campaign_total, flow_total, total, timeframe }`.
  - Secret resolution (Klaviyo key): supports full resource path, project-local secret names, base64-encoded raw keys, and raw fallback (`klaviyo_api_key`). Convention fallback `klaviyo-api-{client_slug}` also supported.
  - Metric resolution (Placed Order): reads any of `placed_order_metric_id`, `metrics.placed_order_metric_id`, or `klaviyo_placed_order_metric_id`; if absent, auto-discovers the best “Placed Order” variant by probing candidates and choosing the one with non-zero activity for the current timeframe.
  - Caching: in-memory, default TTL 300s (env `REVENUE_CACHE_TTL`). Cache key includes client identifier, timeframe, and tz.
  - Admin/diagnostics endpoints:
    - POST `/admin/cache/clear?client_id=&timeframe_key=&tz=&metric_name=` → `{ removed }`.
    - POST `/admin/metric/detect?client_id=` → `{ client_id, detected_metric_id }`.
    - POST `/admin/metric/lock` JSON `{ client_id, metric_id }` → writes to Firestore and evicts cache.
  - Verified result (Rogue Creamery): metric `TPWsCU`, `campaign_total ≈ 26,159.68`, `flow_total ≈ 6,291.95`, `total ≈ 32,451.63`, timeframe `last_7_days`.

OpenAPI MCP Wrapper and Agent Integration
- Wrapper command (stdio MCP):
  - `npx @modelcontextprotocol/openapi --spec services/klaviyo_api/openapi.yaml --server.url http://localhost:9090`
- Tools exposed (derived from OpenAPI):
  - GET `/clients/{client_id}/revenue/last7` with query params `timeframe_key`, `tz`, `start`, `end`, `timeframe`, `recompute`.
  - GET `/clients/by-slug/{slug}/revenue/last7` with identical query params.
- Agent instruction update:
  - “When asked for revenue based on ‘Placed Order’, call the Revenue MCP tool with the client slug (or doc ID during migration) and pass a timeframe as either `timeframe_key` (e.g., last_7_days, last_30_days, month_to_date → map to start/end) or explicit `start`/`end` ISO strings. Do not use metric-aggregates for attribution; the tool already sums Campaign + Flow conversion_value.”
- Common timeframe mappings:
  - last_7_days → `timeframe_key=last_7_days`.
  - last_30_days → `timeframe_key=last_30_days`.
  - month_to_date → pass explicit `start` = first day of month 00:00:00Z and `end` = now; or map to a supported key if available.
  - yesterday → `timeframe_key=yesterday`.
  - last_24_hours → `timeframe_key=last_24_hours`.

Admin – MCP Management (Frontend Spec)
- Routes to call from Admin UI (all under Revenue API base URL):
  - `GET /healthz`: show status and project.
  - `GET /clients/{client_id}/revenue/last7?timeframe_key=…&tz=&start=&end=&timeframe=&recompute=`: compute totals by doc ID.
  - `GET /clients/by-slug/{slug}/revenue/last7?...`: compute totals by slug.
  - `POST /admin/cache/clear?client_id=&timeframe_key=&tz=&metric_name=`: clear cache entries.
  - `POST /admin/metric/detect?client_id=`: auto-detect best placed order metric for this client.
  - `POST /admin/metric/lock` JSON `{ client_id, metric_id }`: lock metric ID to Firestore.
- UI panels:
  - Tool Registry: show MCP OpenAPI wrapper tools and health; enable/disable (local config), show spec.
  - Service Health: revenue API health and quick attribution check latency.
  - Configuration: default timeframe, `REVENUE_CACHE_TTL`, auto-detect toggle.
  - Client Controls: lookup by slug/ID, recompute, clear cache, detect best metric, lock metric; display totals and cache status.
  - Logs: recent request metrics; last Klaviyo error detail.
  - MCP Wrapper Controls: wrapper URL, status, restart, validate MCP tool call.

Firestore Client IDs – Migration ✅ COMPLETED
- ✅ **COMPLETED**: All `clients` docs migrated from random IDs to human-readable slugs
- ✅ **COMPLETED**: Document IDs now use slug format (e.g., `rogue-creamery`) for readability
- ✅ **COMPLETED**: API usage standardized with consistent slug-based calls
- Script: `scripts/migrate_client_ids.py` – migration completed successfully

Key Klaviyo API Notes
- values-reports usage for attribution:
  - Endpoints: `/api/campaign-values-reports/`, `/api/flow-values-reports/`.
  - data.type: `campaign-values-report` or `flow-values-report` (endpoint-specific).
  - attributes.statistics MUST include `"conversions"` and `"conversion_value"`.
  - attributes.timeframe MUST be `{ "key": "…" }` or an object with `start`/`end` ISO8601 values.
- metric-aggregates caveats:
  - Do not use for email-attributed revenue. It sums raw event values (total), not marketing attribution by channel.
  - If used for control checks, ensure: trailing slash, `content-type` header, and filter grammar: `and(greater-or-equal(datetime,YYYY-MM-DDTHH:MM:SSZ),less-than(datetime,YYYY-MM-DDTHH:MM:SSZ))` with unquoted timestamps.




# Klaviyo API Service (Test)

Previously referred to as the "Revenue API"; the active implementation lives under `services/klaviyo_api` (the legacy `services/revenue_api` folder is retained for reference).

A small FastAPI service that returns email-attributed revenue for the last 7 days by summing Klaviyo Campaign and Flow "conversion_value" for the client's "Placed Order" metric.

- Endpoint: `GET /clients/{client_id}/revenue/last7`
- Auth: Uses Secret Manager to resolve the client-specific Klaviyo API key.
- Client config: Reads from Firestore `clients/{client_id}`.
- Timeframe: `last_7_days` (matches Klaviyo UI boundaries/timezone).
- Output: `{ client_id, metric_id, campaign_total, flow_total, total, timeframe }`

Notes
- Metric ID per client: The service reads `placed_order_metric_id` from Firestore if present (`placed_order_metric_id`, `metrics.placed_order_metric_id`, or `klaviyo_placed_order_metric_id`). If missing, it discovers the best "Placed Order" metric by probing candidates and selects the one with non-zero activity.
- Secret resolution: The service supports these patterns for the key:
  - `klaviyo_api_key_secret`: Secret Manager name (e.g., `klaviyo-api-rogue-creamery`), or full resource path `projects/.../secrets/.../versions/...`.
  - `api_key_encrypted`: If base64 encoded and decodes to a value that looks like a key (e.g., starts with `pk_`), it is used as a raw API key. Otherwise, it is treated like a secret name.
  - Fallback to `klaviyo_api_key` when secret references are not available.

Client Management Status ✅ COMPLETED
- ✅ **COMPLETED**: All Firestore document IDs standardized to human-readable slugs
- ✅ **COMPLETED**: Client slugs (e.g., `rogue-creamery`) now used as document IDs
- ✅ **COMPLETED**: Enhanced client management with Secret Manager integration
- ✅ **COMPLETED**: 25+ client fields supported with unified storage system

Local run
- `export GOOGLE_CLOUD_PROJECT=emailpilot-438321`
- `uvicorn services.klaviyo_api.main:app --host 0.0.0.0 --port 9090`
- `curl http://localhost:9090/healthz`
- `curl "http://localhost:9090/clients/<client_doc_id>/revenue/last7"`


  # Refactoring Summary: Centralized Dependency Injection

This document outlines the recent refactoring effort to centralize dependency injection for services like settings management and database connections.

## Key Changes

-   **Deleted Modules**: The following modules have been deleted and their functionality replaced:
    -   `app/core/config.py`
    -   `app/services/secret_manager.py`
    -   `app/services/firestore_client.py`

-   **New Modules**:
    -   `app/core/settings.py`: Manages application settings using Pydantic's `BaseSettings`.
    -   `app/services/secrets.py`: A new `SecretManagerService` for interacting with Google Secret Manager.
    -   `app/deps/`: A new package for centralized dependency injection functions.
        -   `app/deps/firestore.py`: Provides the `get_db` dependency for Firestore.
        -   `app/deps/secrets.py`: Provides the `get_secret_manager_service` dependency.

## How to Use the New System

To access application settings, the Firestore database, or the Secret Manager service, use the `Depends` function from FastAPI with the appropriate dependency function.

### Example: Accessing Settings

```python
from fastapi import APIRouter, Depends
from app.core.settings import Settings, get_settings

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(settings: Settings = Depends(get_settings)):
    # Use the settings object
    print(settings.google_cloud_project)
```

### Example: Accessing the Database

```python
from fastapi import APIRouter, Depends
from google.cloud import firestore
from app.deps import get_db

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(db: firestore.Client = Depends(get_db)):
    # Use the db object
    docs = db.collection("my-collection").stream()
```

### Example: Accessing the Secret Manager

```python
from fastapi import APIRouter, Depends
from app.services.secrets import SecretManagerService
from app.deps import get_secret_manager_service

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(secret_manager: SecretManagerService = Depends(get_secret_manager_service)):
    # Use the secret_manager object
    my_secret = secret_manager.get_secret("my-secret")
```
Scheduled Performance Jobs (Weekly/Monthly)
- Service: `services/performance_api/`
  - GET `/healthz`
  - POST `/jobs/weekly?client_id=...|slug=...` → computes last 7 days via Revenue API, writes to `clients/{id}/performance/weekly-YYYY-MM-DD`.
  - POST `/jobs/monthly?client_id=...|slug=...&month=YYYY-MM` → computes month-to-date (default) or specific month; reads goal from `clients/{id}/goals/{YYYY-MM}` and stores `{goal, progress_percent}`.
- Env: `KLAVIYO_API_BASE` (default `http://localhost:9090`, `REVENUE_API_BASE` still supported).
- OpenAPI MCP wrapper (optional): `services/performance_api/openapi.yaml` – expose `/jobs/weekly` and `/jobs/monthly` as MCP tools for scheduling/ops.
- Suggested scheduling:
  - Cloud Scheduler → HTTPS call to `/jobs/weekly` (daily) and `/jobs/monthly` (daily and first of month for last month snapshot).
- Firestore writes (examples):
  - `clients/{id}/performance/weekly-2025-08-16` → { scope: "weekly", timeframe: {start,end}, campaign_total, flow_total, total, created_at }
  - `clients/{id}/performance/monthly-2025-08` → { scope: "monthly", timeframe, goal, progress_percent, totals, created_at }

Prompt Management API (for Admin UI)
- Endpoints (Revenue API):
  - `GET /admin/prompts` → list {items:[{name, description, variables, enabled, updated_at, tool, defaults, tags}]}
  - `GET /admin/prompts/{name}` → full prompt {name, description, content, variables, tool, defaults, enabled, tags, updated_at}
  - `POST /admin/prompts` → upsert prompt body {name, description?, content, variables?, tool?, defaults?, enabled?, tags?}
  - `DELETE /admin/prompts/{name}` → delete prompt
  - `POST /admin/prompts/{name}/test` → render + test: body { client_id|slug, params:{timeframe_key|start|end|timeframe|tz|recompute, ...}, variables? } → returns { rendered_prompt, tool, tool_args, tool_result, latency_ms }
- Storage: Firestore collection `mcp_prompts`.
- Template engine: minimal `{{ var }}` replacement (safe for quick iteration).

Admin MCP Management UI – Frontend Wiring
- Location: Admin → MCP Management. Provide the following panels: Status, MCP Test Console, Prompts, Clients, Jobs.

- Fix 500 import error: ensure Admin imports resolve correctly (avoid absolute `/components/...` imports unless your dev server serves that path). Prefer relative imports (e.g., `../components/MCPFirestoreSync`).

- Status panel
  - Show wrapper status and start/stop controls.
  - Endpoints:
    - GET `/admin/mcp/status`
    - POST `/admin/mcp/start` body `{ "kind": "openapi_revenue" | "performance_openapi" | "firebase" }`
    - POST `/admin/mcp/stop` body `{ "kind": "..." }`

- MCP Test Console
  - Lets Admin call any MCP tool and see raw JSON. Also add an “Explain with AgentService” button.
  - Endpoints:
    - POST `/admin/mcp/tools/smart_call` body `{ "name": "<tool>", "arguments": { ... }, "prefer"?: "openapi_revenue"|"performance_openapi"|"firebase" }`
    - Optional: POST `/admin/mcp/call` with `{ "kind":"...", "request":{ "jsonrpc":"2.0","id":1,"method":"tools/list","params":{} } }` to fetch tools dynamically.
  - Example React snippet:
    ```tsx
    import { useEffect, useState } from 'react'

    function MCPConsole() {
      const [status, setStatus] = useState({})
      const [tool, setTool] = useState('GET /clients/{client_id}/revenue/last7')
      const [args, setArgs] = useState('{"client_id":"test-client","timeframe_key":"last_7_days","recompute":true}')
      const [result, setResult] = useState<any>(null)
      const [explanation, setExplanation] = useState('')

      useEffect(() => {
        fetch('/admin/mcp/status').then(r=>r.json()).then(setStatus)
      }, [])

      const callTool = async () => {
        const body = { name: tool, arguments: JSON.parse(args) }
        const r = await fetch('/admin/mcp/tools/smart_call', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) })
        const json = await r.json()
        setResult(json)
      }

      const explain = async () => {
        // Example AgentService call – adjust to your endpoint
        const r = await fetch('/api/agents/invoke', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
          prompt: 'Summarize this MCP result for a business user',
          context: { mcp_result: result }
        }) })
        const json = await r.json()
        setExplanation(json.summary || JSON.stringify(json))
      }

      return (
        <div>
          <h3>MCP Status</h3>
          <pre>{JSON.stringify(status,null,2)}</pre>

          <h3>MCP Test Console</h3>
          <select value={tool} onChange={e=>setTool(e.target.value)}>
            <option>GET /clients/{'{client_id}'}/revenue/last7</option>
            <option>GET /clients/by-slug/{'{slug}'}/revenue/last7</option>
            <option>POST /jobs/weekly</option>
            <option>POST /jobs/monthly</option>
          </select>
          <textarea value={args} onChange={e=>setArgs(e.target.value)} rows={8} style={{width:'100%'}} />
          <button onClick={callTool}>Call Tool</button>
          <button onClick={explain} disabled={!result}>Explain with AgentService</button>
          <h4>Result</h4>
          <pre>{JSON.stringify(result,null,2)}</pre>
          <h4>Explanation</h4>
          <pre>{explanation}</pre>
        </div>
      )
    }
    ```

- Prompts panel
  - List/edit/test prompts.
  - Endpoints:
    - GET `/admin/prompts`
    - GET `/admin/prompts/{name}`
    - POST `/admin/prompts` (upsert) body `{ name, description?, content, variables?, tool?, defaults?, enabled?, tags? }`
    - DELETE `/admin/prompts/{name}`
    - POST `/admin/prompts/{name}/test` body `{ client_id|slug, params:{ timeframe_key|start|end|timeframe|tz|recompute, ...}, variables? }`

- Clients panel
  - Quick fetch revenue, detect/lock metric, clear cache.
  - Endpoints:
    - GET `/clients/{client_id}/revenue/last7?timeframe_key=last_7_days&recompute=true`
    - GET `/clients/by-slug/{slug}/revenue/last7?timeframe_key=last_7_days&recompute=true`
    - POST `/admin/metric/detect?client_id=...`
    - POST `/admin/metric/lock` body `{ "client_id": "...", "metric_id": "..." }`
    - POST `/admin/cache/clear?client_id=...&timeframe_key=last_7_days`

- Jobs panel
  - Trigger weekly/monthly jobs and show last write.
  - Endpoints:
    - POST `/jobs/weekly?client_id=... | slug=...`
    - POST `/jobs/monthly?client_id=... | slug=... [&month=YYYY-MM]`

- Timeframe input (flexible)
  - Allow presets (timeframe_key: last_7_days, last_30_days, last_90_days, yesterday, last_24_hours) and custom absolute (`start`+`end` ISO).
  - Expose advanced JSON input (`timeframe` object) and `recompute` toggle.

## Operational Learnings: Runaway Agent Sanity Log + CORS (2025‑08‑17)

- Symptom: Disk space dropped rapidly and some app pages showed CORS errors.
- Finding: A background Python process was writing continuously to `.agent_sanity.out`, which grew to ~643GB. The process was listening on `localhost:8099` and repeatedly invoked agents, producing massive logs.
- Root cause: The multi‑agent orchestrator allowed back‑and‑forth "ping‑pong" between agents (e.g., `designer` ↔ `copywriter`) without a hard stop, and the process’s stdout/stderr were redirected to a flat file in the repo root.
- Immediate remediation: Killed the writer process and removed `.agent_sanity.out`, reclaiming space.
- Fixes applied (code):
  - `email-sms-mcp-server/server.py`: Added safety guards — a max step cap and simple ping‑pong detection — to prevent infinite/long loops and log spam.
  - `services/revenue_api/main.py`: Added FastAPI `CORSMiddleware` with common localhost origins (8000/8080/3000/5173) to resolve dev CORS errors when the frontend calls the Revenue API.
- Prevention and guidance:
  - Avoid redirecting long‑running server output to ad‑hoc files (e.g., `> .agent_sanity.out`). Prefer structured logging with rotation (Python `logging.handlers.RotatingFileHandler`) or keep logs in a `logs/` directory already covered by `.gitignore`.
  - Use sensible log levels; do not log large agent contexts on every step in tight loops.
  - For multi‑service local dev across ports, ensure CORS is configured on each service (backend app has CORS; Revenue API now does as well).
  - If a runaway log happens again, identify and stop the writer before deleting the file to free space.
- Quick commands (macOS):
  - Check disk: `df -h .`
  - Identify biggest files (example): `du -h -d 2 . | sort -h | tail`
  - Find writer of a file: `lsof | grep -F ".agent_sanity.out"`
  - Stop process: `kill <pid>` or `kill -9 <pid>` as last resort

## Maintenance & Ops Commands

- Log rotation: enabled for app, agent orchestrator, and revenue API. Logs write under `logs/` with rotation (5 MB x 5).
- Clean up large logs:
  - On-demand: `make logs-clean SIZE=1G MODE=truncate YES=yes`
  - Script direct: `./scripts/cleanup_large_files.sh -t 1G --truncate --yes`
  - Cron example (daily at 2:30 AM): `30 2 * * * cd /path/to/emailpilot-app && SIZE=1G make cron-clean-logs >/dev/null 2>&1`
- Inspect large non-log files: `make bigfiles`
- Revenue API CORS checks:
  - Start and probe locally: `make quick-check-revenue` (starts on `127.0.0.1:9090`, preflight tests, then stops)
- Probe an existing instance (no start): `make status-revenue` (set `KLAVIYO_API_BASE` if not default)
- Simple backend smoke test (no GCP deps): `make quick-check-simple`

Environment variables of interest
- `KLAVIYO_API_BASE`: Base URL for Klaviyo API (default `http://127.0.0.1:9090`; `REVENUE_API_BASE` supported for back-compat).
- `ORIGIN`: Origin to use for CORS preflight during `status-revenue` (default `http://localhost:3000`).
- `LOG_DIR`: Optional override for log output directory (default `logs/`).
- `LOG_FORMAT`: `json` for Cloud Run-friendly JSON logs; default `text`.
- `TRUSTED_HOSTS`: Comma-separated list of allowed hosts for TrustedHostMiddleware.
- `CORS_ALLOW_ALL`: `true` to allow all origins (dev only); otherwise define `CORS_ORIGINS`.
- `CORS_ORIGINS`: Comma-separated whitelist of allowed origins. Used if `CORS_ALLOW_ALL` is not true.

Admin UI Aids
- Ops & Logs tab shows count badge of logs > 1G and provides one‑click “Truncate >1G Now”.
- Overview displays a warning banner when logs > 1G are detected with a button to jump to Ops & Logs.
- Overview tab shows a red badge (count) when any components report non‑operational status; a Problems card lists failing components with quick links to the relevant admin tab (e.g., MCP, AI Models, Slack, Environment).

Local Development
- Prereqs: Python 3.11+, pip, Docker (optional), Google Cloud SDK (for Cloud Run deploys).
- Env: set `GOOGLE_CLOUD_PROJECT` for services that use Secret Manager/Firestore.
- Start backend locally: `make dev` (default localhost:8000; health at `/health`).
- Smoke tests (no GCP): `make test-smoke`.

Container + Cloud Run
- Build image: `make docker-build-app` (uses Dockerfile → `uvicorn main_firestore:app`).
- Run locally: `make docker-run-app` then browse http://localhost:8080/health.
- Deploy (example):
  - `gcloud builds submit --tag gcr.io/$PROJECT_ID/emailpilot-app:latest`
  - `gcloud run deploy emailpilot-app --image gcr.io/$PROJECT_ID/emailpilot-app:latest --platform managed --region us-central1 --allow-unauthenticated`

Status Checks
- Quick status: `make status` (basic)
- Extended status: `make status-all`
  - Probes `/health`, `/api/admin/system/status`, `/api/auth/google/status`, unauth `/api/auth/me`, and optional Revenue API health/CORS if running locally on 9090.

CI Badge Setup
- Replace `OWNER/REPO` in the badge URL above with your GitHub org/repo once this repo is on GitHub and you want the badge to reflect workflow status.

Preflight Deploy (CI)
- Manual workflow: “Preflight Deploy to Cloud Run (Manual)” in GitHub Actions
  - Inputs: confirm (type “yes”), service, region (defaults provided)
  - Runs smoke tests before building and deploying

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Workflow Builder AI Hanging
- **Issue**: Page loads but workflow generation doesn't work
- **Solution**: 
  - Ensure server is running: `uvicorn main_firestore:app --port 8000 --host localhost --reload`
  - Check API keys are in Secret Manager: `emailpilot-claude`, `openai-api-key`, `emailpilot-gemini-api-key`
  - Verify model selection matches available models in dropdown

#### Claude API Errors
- **Issue**: "ACCESS_TOKEN_SCOPE_INSUFFICIENT" or authentication errors
- **Solution**:
  - API key is stored as `emailpilot-claude` in Secret Manager (not `anthropic-api-key`)
  - Run test: `python test_claude_api.py` (if available)
  - Check credits at: https://console.anthropic.com/settings/billing

#### Workflow Management Issues
- **Issue**: Can't edit agents or workflows don't load
- **Solution**:
  - Clear browser cache and reload
  - Check Firestore connection is working
  - Verify agents are properly registered in `/api/workflow-agents/workflows`

#### LangGraph Studio Link
- **Issue**: Link doesn't open or shows 404
- **Solution**: Correct URL is `https://smith.langchain.com/` (not `/studio/`)

#### Execution Counter Issues
- **Issue**: "Executions Today" number changes on refresh
- **Solution**: This is now fixed with sessionStorage persistence. Clear browser storage if seeing old behavior.

### Required Environment Variables
```bash
# In .env file or Secret Manager
GOOGLE_CLOUD_PROJECT=emailpilot-438321
USE_SECRET_MANAGER=true
ANTHROPIC_SECRET_NAME=emailpilot-claude
OPENAI_SECRET_NAME=openai-api-key
GEMINI_SECRET_NAME=emailpilot-gemini-api-key
```

### API Key Configuration
All API keys should be stored in Google Secret Manager:
- **OpenAI**: `openai-api-key`
- **Anthropic/Claude**: `emailpilot-claude`
- **Google/Gemini**: `emailpilot-gemini-api-key`

To add/update keys:
```bash
gcloud secrets create {secret-name} --data-file=- <<< "your-api-key-here"
```

## 📚 Architecture Notes

Prompt Systems: MCP vs AI Models
- MCP (Model Context Protocol): deterministic tool execution over a defined interface. In EmailPilot, we wrap HTTP services (e.g., Klaviyo API and Performance API) via OpenAPI MCP, exposing tools like `GET /clients/{client_id}/revenue/last7` and `/jobs/weekly`. Use MCP when you need reliable data retrieval or to run jobs/ops with predictable inputs/outputs.
- AI Models Service: prompt and provider management for generative tasks. Centralizes prompts in Firestore, selects providers (Gemini/Claude/OpenAI), and executes text generation. Use AI Models when you need analysis, summarization, or content (e.g., weekly insights, copy suggestions). It can call MCP tools as part of a workflow but focuses on prompt-driven outputs.
- Together: weekly insights use MCP to fetch metrics (`services/klaviyo_api` weekly/full endpoints), then run prompts through the AI Models Service (if configured) to produce human‑readable insights and Slack summaries.

## 📅 Calendar System Architecture

### Overview
The EmailPilot Calendar is a shared planning interface accessible across multiple services in the EmailPilot ecosystem. The calendar is served from the orchestrator service but uses a shared client library for consistency.

### Architecture Components

#### 1. Calendar UI Location
- **Service**: EmailPilot Orchestrator (`/emailpilot-orchestrator/`)
- **URL**: `https://app.emailpilot.ai/calendar`
- **File**: `calendar_master.html` (root of orchestrator directory)
- **Route**: `/calendar` endpoint in `main_fastapi.py`

#### 2. Shared Client Library
- **Service**: EmailPilot Orchestrator
- **URL**: `https://app.emailpilot.ai/api/clients`
- **Purpose**: Single source of truth for all client data across services
- **Data**: Returns all 11 clients as direct JSON array

#### 3. Calendar Events API
- **Service**: EmailPilot App (`/emailpilot-app/`)
- **URL**: `https://emailpilot-app-p3cxgvcsla-uc.a.run.app/api/calendar/events`
- **File**: `app/api/calendar.py`
- **Purpose**: CRUD operations for calendar events stored in Firestore
- **Authentication**: **NO CLERK AUTH** - Calendar HTML has no authentication context

### Service Relationships

```
┌─────────────────────────────────────────────────────────────┐
│  app.emailpilot.ai (EmailPilot Orchestrator)                │
│  ┌──────────────────┐        ┌─────────────────────────┐   │
│  │  /calendar       │        │  /api/clients            │   │
│  │  (HTML UI)       │───────>│  (Shared Client Library) │   │
│  └──────────────────┘        └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                │
                │ Fetches events from
                ↓
┌─────────────────────────────────────────────────────────────┐
│  emailpilot-app-p3cxgvcsla-uc.a.run.app                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /api/calendar/events                                 │   │
│  │  (Calendar Events CRUD - Firestore)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

#### Why Split Architecture?
1. **Shared Client Library**: Orchestrator serves `api/clients` endpoint used by multiple services
2. **Single Calendar UI**: One canonical calendar interface instead of duplicates
3. **Distributed Events**: Calendar events stored in Firestore, accessed via emailpilot-app service

#### Why No Authentication on Calendar Events?
- Calendar HTML served from orchestrator has no Clerk authentication context
- Events API must be publicly accessible (within private network)
- Removed `Depends(verify_clerk_session)` from calendar.py endpoints (lines 743-759)

### Deployment Locations

#### EmailPilot Orchestrator
- **Repository**: `/klaviyo-audit-automation/emailpilot-orchestrator/`
- **Deploy Script**: `./deploy-cloud-run.sh`
- **Main File**: `main_fastapi.py`
- **Dockerfile**: `Dockerfile.cloudrun`
- **Domain**: `app.emailpilot.ai`

#### EmailPilot App
- **Repository**: `/klaviyo-audit-automation/emailpilot-app/`
- **Deploy Config**: `cloudbuild.yaml`
- **Main File**: `app/main.py`
- **Service**: `emailpilot-app` on Cloud Run
- **Direct URL**: `https://emailpilot-app-p3cxgvcsla-uc.a.run.app`

### API Endpoints Reference

#### Client Library
```
GET https://app.emailpilot.ai/api/clients
Response: Array of 11 client objects
```

#### Calendar Events
```
GET https://emailpilot-app-p3cxgvcsla-uc.a.run.app/api/calendar/events
Parameters:
  - client_id: string (required)
  - start_date: string (optional, YYYY-MM-DD)
  - end_date: string (optional, YYYY-MM-DD)
Response: { events: [...] }
```

### Testing & Verification

#### Test Calendar Access
```bash
# Calendar UI should load
curl -s "https://app.emailpilot.ai/calendar" | head -20

# Should contain HTML with calendar interface
```

#### Test Client Library
```bash
# Should return all 11 clients
curl -s "https://app.emailpilot.ai/api/clients" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"

# Expected output: 11
```

#### Test Events API
```bash
# Test Rogue Creamery October 2025 events
curl -s "https://emailpilot-app-p3cxgvcsla-uc.a.run.app/api/calendar/events?client_id=rogue-creamery&start_date=2025-10-01&end_date=2025-10-31"

# Should return events array for October 2025
```

### Troubleshooting

#### Calendar Shows 404
- **Issue**: `https://app.emailpilot.ai/calendar` returns 404
- **Solution**: Redeploy orchestrator with `./deploy-cloud-run.sh` from `/emailpilot-orchestrator/`

#### No Clients Loading
- **Issue**: Calendar shows empty client list
- **Solution**: Check `https://app.emailpilot.ai/api/clients` returns 11 clients
- **Debug**: Verify orchestrator service is running and domain mapping is correct

#### No Events Loading
- **Issue**: Events API returns "Authorization header required"
- **Solution**: Verify `current_user: dict = Depends(verify_clerk_session)` removed from calendar.py:743-759
- **Redeploy**: Run `gcloud builds submit --config=cloudbuild.yaml .` from `/emailpilot-app/`

#### Events Return Empty Array
- **Issue**: API works but no events for client/date range
- **Solution**: Verify events exist in Firestore `calendar_events` collection
- **Check**: Use Firestore console to confirm events for client_id and date range

### File Locations Quick Reference

```
/klaviyo-audit-automation/
├── emailpilot-orchestrator/
│   ├── main_fastapi.py         # Add /calendar route here (line 288)
│   ├── calendar_master.html    # Calendar UI (root level)
│   ├── deploy-cloud-run.sh     # Deploy orchestrator
│   └── Dockerfile.cloudrun
│
└── emailpilot-app/
    ├── app/main.py             # App main file
    ├── app/api/calendar.py     # Calendar events API (remove auth lines 743-759)
    ├── cloudbuild.yaml         # Build config for emailpilot-app
    └── frontend/public/
        └── calendar_master.html  # Source calendar (copy to orchestrator)
```

### Migration Notes

If you need to move calendar to a different service:
1. Copy `calendar_master.html` to new service
2. Update `/calendar` route in service main file
3. Update calendar HTML to fetch from correct API endpoints
4. Redeploy both services
5. Update documentation and DNS if needed

