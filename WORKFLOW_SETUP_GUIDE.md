# Workflow Setup Guide - EmailPilot

Welcome to the EmailPilot Workflow Management System! This guide will help you create, manage, and deploy workflows for email marketing automation using real-time Klaviyo data.

## 🚀 Quick Start

### 1. Start the System
```bash
# Start all services
make dev

# In another terminal, start Enhanced MCP
cd services/klaviyo_mcp_enhanced
node src/simple-http-wrapper.js
```

### 2. Open Workflow Hub
```bash
make workflow-hub
```
This opens the central dashboard where you can access all workflow tools.

### 3. Create Your First Workflow
```bash
make workflow-new
```
Follow the step-by-step wizard to create a workflow in minutes!

## 📚 Table of Contents

1. [Overview](#overview)
2. [Web-Based Tools](#web-based-tools)
3. [Creating Workflows](#creating-workflows)
4. [Managing Agents](#managing-agents)
5. [Testing Workflows](#testing-workflows)
6. [Available Commands](#available-commands)
7. [Troubleshooting](#troubleshooting)

## Overview

The EmailPilot Workflow System combines:
- **Visual Workflow Designer** - Drag-and-drop interface
- **AI Agents** - 9 specialized agents with Enhanced MCP
- **Real Klaviyo Data** - 26 tools for accessing live data
- **Step-by-Step Wizard** - Perfect for beginners

## 🌐 Web-Based Tools

All tools are accessible from the central hub at `http://localhost:8000/static/workflow_hub.html`

### Workflow Hub (Central Dashboard)
- **URL**: `/static/workflow_hub.html`
- **Purpose**: Central access point for all tools
- **Features**: 
  - Quick status overview
  - Links to all tools
  - Recent workflows
  - System health monitoring

### Workflow Builder
- **URL**: `/static/workflow_builder.html`
- **Purpose**: Visual workflow design
- **Features**:
  - Drag-and-drop Enhanced MCP tools
  - Visual node connections
  - Real-time code generation
  - Save/load workflows

### Agent Editor
- **URL**: `/static/agent_editor.html`
- **Purpose**: Configure AI agents
- **Features**:
  - Edit agent prompts
  - Assign Enhanced MCP tools
  - Test with real data
  - Version control

### Workflow Wizard
- **URL**: `/static/workflow_wizard.html`
- **Purpose**: Guided workflow creation
- **Features**:
  - 5-step process
  - Template selection
  - Automatic tool recommendations
  - Perfect for beginners

### Calendar Planner
- **URL**: `/static/calendar_planner.html`
- **Purpose**: Plan email campaigns
- **Features**:
  - Monthly calendar view
  - AI recommendations
  - Drag-drop scheduling
  - Historical analysis

## 🛠️ Creating Workflows

### Method 1: Using the Wizard (Recommended for Beginners)

1. **Open the wizard**:
   ```bash
   make workflow-new
   ```

2. **Follow the 5 steps**:
   - Step 1: Choose a template
   - Step 2: Select client
   - Step 3: Choose Enhanced MCP tools
   - Step 4: Set schedule
   - Step 5: Review and create

3. **Test before deploying**:
   - The wizard automatically offers to test your workflow
   - Uses real Klaviyo data from rogue-creamery

### Method 2: Visual Builder (For Advanced Users)

1. **Open the builder**:
   ```bash
   open http://localhost:8000/static/workflow_builder.html
   ```

2. **Design your workflow**:
   - Drag tools from the left palette
   - Connect nodes to create flow
   - Configure properties on the right
   - View generated code in real-time

3. **Save and deploy**:
   - Click "Save" to store locally
   - Click "Test" to validate
   - Click "Deploy" to activate

### Method 3: Code-Based (For Developers)

Create a Python file with your workflow:

```python
from langgraph.graph import StateGraph
from multi-agent.integrations.langchain_core.adapters.enhanced_mcp_adapter import get_enhanced_mcp_adapter

# Get Enhanced MCP adapter
adapter = get_enhanced_mcp_adapter()

# Define your workflow
class WorkflowState(TypedDict):
    client_id: str
    results: dict

# Create workflow
workflow = StateGraph(WorkflowState)

# Add nodes with Enhanced MCP tools
def analyze_campaigns(state):
    tools = adapter.get_tools_for_agent("campaign_analyzer", state["client_id"])
    # Your logic here
    return state

workflow.add_node("analyze", analyze_campaigns)

# Compile and run
app = workflow.compile()
```

## 🤖 Managing Agents

### Available Agents

View all agents:
```bash
make agent-list
```

**High Priority Agents**:
- `monthly_goals_generator_v3` - Revenue goal planning
- `calendar_planner` - Campaign scheduling  
- `ab_test_coordinator` - A/B test management

**Medium Priority Agents**:
- `revenue_analyst` - Financial analysis
- `campaign_strategist` - Strategy planning
- `audience_architect` - Segmentation
- `compliance_checker` - Regulatory compliance
- `engagement_optimizer` - Engagement optimization
- `performance_analyst` - Performance metrics

### Editing Agents

1. **Open Agent Editor**:
   ```bash
   open http://localhost:8000/static/agent_editor.html
   ```

2. **Select an agent** from the left panel

3. **Edit the prompt** in the center editor

4. **Assign Enhanced MCP tools** from the right panel

5. **Test with real data** in the console

6. **Save changes**

## 🧪 Testing Workflows

### Quick Test
```bash
make workflow-test
```

This runs a comprehensive test of:
- Enhanced MCP connection
- All 9 agents
- Real Klaviyo data access

### Test Individual Workflows

1. Open the Testing Lab (coming soon)
2. Select your workflow
3. Choose test data (use rogue-creamery)
4. Run and view results

### Manual Testing

Test Enhanced MCP directly:
```bash
curl -X POST http://localhost:8000/api/mcp/gateway/invoke \
  -H "Content-Type: application/json" \
  -d '{"client_id": "rogue-creamery", "tool_name": "campaigns.list", "use_enhanced": true}'
```

## 📋 Available Commands

### Workflow Management
- `make workflow-hub` - Open central dashboard
- `make workflow-new` - Create new workflow
- `make workflow-test` - Test workflows
- `make agent-list` - List all agents
- `make calendar-plan` - Plan email calendar
- `make tools-available` - Show Enhanced MCP tools

### Development
- `make dev` - Start development server
- `make test` - Run tests
- `make build` - Build production assets

## 🔧 Enhanced MCP Tools

The system includes 26 tools for accessing Klaviyo data:

### Campaign Tools
- `campaigns.list` - List all campaigns
- `campaigns.get` - Get specific campaign
- `campaign_messages.list` - Campaign messages

### Metrics Tools  
- `metrics.aggregate` - Aggregate metrics
- `reporting.revenue` - Revenue reports
- `metrics.timeline` - Timeline data

### Audience Tools
- `segments.list` - List segments
- `profiles.get` - Profile data
- `segments.get_profiles` - Segment profiles

### View all tools:
```bash
make tools-available
```

## 🐛 Troubleshooting

### Services Not Running

Check service status:
```bash
make status
```

Start required services:
```bash
# Terminal 1
make dev

# Terminal 2  
cd services/klaviyo_mcp_enhanced
node src/simple-http-wrapper.js

# Terminal 3 (optional)
cd emailpilot_graph
langgraph dev --port 2024
```

### No Klaviyo Data

1. Ensure using `rogue-creamery` client (has API keys)
2. Check Enhanced MCP is running on port 9095
3. Verify MCP Gateway status:
   ```bash
   curl http://localhost:8000/api/mcp/gateway/status
   ```

### Workflow Not Working

1. Check all services are running
2. Verify Enhanced MCP tools are available
3. Test with rogue-creamery client
4. Check browser console for errors

### Common Issues

**Port conflicts**:
- Main app: 8000 (change with `--port`)
- Enhanced MCP: 9095
- LangGraph: 2024

**Missing dependencies**:
```bash
pip install -r requirements.txt
cd services/klaviyo_mcp_enhanced
npm install
```

**API key issues**:
- Use rogue-creamery for testing
- Check Secret Manager configuration
- Verify GOOGLE_CLOUD_PROJECT is set

## 📖 Best Practices

1. **Always test with rogue-creamery** - It has working API keys
2. **Start with templates** - Use the wizard for quick setup
3. **Test before deploying** - Use the test lab
4. **Monitor performance** - Check workflow execution logs
5. **Version your workflows** - Save configurations regularly

## 🎯 Example Workflows

### Monthly Campaign Planning
```bash
1. make workflow-new
2. Select "Campaign Planning" template
3. Choose "rogue-creamery" client
4. Tools auto-selected: campaigns, metrics, segments
5. Set to run monthly
6. Create and test
```

### Revenue Goal Generation
```bash
1. Open Agent Editor
2. Select "monthly_goals_generator_v3"
3. Ensure has tools: metrics_aggregate, reporting_revenue
4. Test with: "Generate Q1 2025 goals for rogue-creamery"
5. View results
```

### A/B Test Coordination
```bash
1. Use Workflow Builder
2. Drag "ab_test_coordinator" agent
3. Add "campaigns.list" tool
4. Add "metrics.aggregate" tool
5. Connect nodes
6. Save and test
```

## 🚢 Deployment

Once tested, deploy your workflow:

1. **Local deployment**:
   ```bash
   make deploy
   ```

2. **Cloud deployment**:
   ```bash
   gcloud run deploy emailpilot-workflows \
     --source . \
     --port 8000
   ```

3. **Schedule with cron**:
   - Add to crontab for regular execution
   - Use Cloud Scheduler for managed scheduling

## 📞 Support

- **Documentation**: This guide
- **Issues**: Check Troubleshooting section
- **Logs**: `tail -f logs/workflow.log`
- **Status**: `make status`

## 🎉 Next Steps

1. Create your first workflow with `make workflow-new`
2. Test with real data using rogue-creamery
3. Explore the visual builder
4. Configure agents for your needs
5. Deploy to production

Happy workflow building! 🚀