# EmailPilot LangGraph Integration

## Overview

This repository contains the LangGraph integration for EmailPilot, a comprehensive FastAPI-based platform for automating Klaviyo email marketing campaigns with advanced AI orchestration using LangGraph visual workflows.

## 🚀 Key Features

### LangGraph Visual Workflows
- **Visual Studio Interface**: Browser-based drag-and-drop workflow editor at `https://smith.langchain.com/studio/`
- **Campaign Planning Graph**: Intelligent email campaign planning with Klaviyo integration
- **Full Observability**: LangSmith tracing for debugging and monitoring all workflow executions
- **Hot Reload**: Real-time updates as you modify workflows

### Architecture Highlights
- **Unified Workflow System**: Single graph replaces multiple separate MCP agents
- **State Management**: Built-in state handling for complex multi-step workflows
- **Tool Integration**: Seamless connection to Klaviyo API and other services
- **Production Ready**: Enterprise-grade monitoring, error handling, and scaling

## 📁 Project Structure

```
emailpilot-app/
├── emailpilot_graph/           # LangGraph implementation
│   ├── agent.py               # Campaign planning graph
│   ├── langgraph.json         # Configuration
│   └── README.md              # Detailed documentation
├── app/                       # FastAPI backend
│   ├── api/                   # API endpoints
│   └── services/              # Business logic
├── frontend/                  # React frontend
├── multi-agent/               # LangChain multi-agent system
└── services/                  # MCP data services
```

## 🎯 Current Implementation Status (August 2025)

### ✅ Completed
- LangGraph server running on port 2024
- Studio UI integration complete
- Campaign planning graph with 3 specialized tools
- LangSmith tracing to "emailpilot-calendar" project
- Hub dashboard for unified access
- Full API documentation at `/docs`

### 🔧 Available Tools
1. **analyze_klaviyo_metrics**: Analyzes email metrics for brands
2. **generate_campaign_calendar**: Creates optimized campaign schedules
3. **optimize_send_times**: ML-based send time optimization

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 16+
- Google Cloud Project with Firestore
- API Keys (OpenAI, Claude, Gemini)

### Installation

1. **Clone the repository**
```bash
git clone [repository-url]
cd emailpilot-app
```

2. **Set up Python environment**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export OPENAI_API_KEY="sk-..."
export LANGSMITH_API_KEY="lsv2_..."
```

4. **Start LangGraph server**
```bash
cd emailpilot_graph
langgraph dev --port 2024
```

5. **Start main application**
```bash
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

6. **Access the applications**
- Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
- Main App: `http://localhost:8000`
- Hub Dashboard: `http://localhost:8000/hub/`

## 📊 AI Architecture

### LangGraph (Primary - Visual Workflows)
- Visual workflow orchestration for campaign planning
- Browser-based Studio interface
- Full LangSmith integration
- Located in `emailpilot_graph/`

### LangChain Multi-Agent (Text-Based Interface)
- RAG capabilities for document Q&A
- Revenue analysis agents
- Specialized copywriting agents
- Located in `multi-agent/`

### MCP Data Services (Deterministic Operations)
- Klaviyo Revenue API (port 9090)
- Performance API (port 9091)
- Located in `services/`

## 🔄 Migration from MCP

The system has migrated from MCP-based agents to LangGraph:

| Old System | New System | Status |
|------------|------------|--------|
| MCP Email/SMS Agents | LangGraph Campaign Planning | ✅ Migrated |
| Individual agent files | Unified graph in agent.py | ✅ Consolidated |
| Manual workflow coding | Visual Studio editor | ✅ Enhanced |
| Limited observability | Full LangSmith tracing | ✅ Upgraded |

## 📚 Documentation

### Core Documentation
- [LangGraph Integration Guide](LANGGRAPH_INTEGRATION.md) - Complete integration specifications
- [Migration Guide](LANGGRAPH_MIGRATION.md) - Transition from MCP to LangGraph
- [Troubleshooting](LANGGRAPH_TROUBLESHOOTING.md) - Common issues and solutions
- [Workflow System](LANGGRAPH_WORKFLOW_SYSTEM.md) - Detailed workflow documentation

### Calendar & Planning
- [Calendar Planning AI](CALENDAR_PLANNING_AI.md) - AI-powered calendar generation
- [Calendar Technical Guide](CALENDAR_PLANNER_TECHNICAL_GUIDE.md) - Technical implementation
- [Calendar Integration](CALENDAR_INTEGRATION_COMPLETE.md) - Integration details

### Development Guides
- [README](README.md) - Main project documentation
- [Agent Service](AgentService.md) - Agent service documentation
- [LangChain Integration](LANGCHAIN_INTEGRATION_SUMMARY.md) - Multi-agent orchestration

## 🛠 Development

### Adding New Tools

Edit `emailpilot_graph/agent.py`:

```python
@tool
def your_new_tool(param: str) -> str:
    """Tool description"""
    return "result"

# Add to tools list
tools = [...existing_tools, your_new_tool]
```

### Testing

```bash
# Test LangGraph API
curl http://127.0.0.1:2024/assistants/agent

# Test campaign planning
curl -X POST http://127.0.0.1:2024/threads \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"role": "user", "content": "Plan campaigns for next month"}]
    }
  }'
```

## 🔐 Security

- API keys stored in Google Secret Manager
- JWT authentication for admin access
- Role-based access control
- Encrypted storage for sensitive data

## 📈 Monitoring

- **LangSmith**: Full tracing at [smith.langchain.com](https://smith.langchain.com)
- **Project**: emailpilot-calendar
- **Metrics**: Response times, error rates, token usage

## 🚢 Deployment

### Option 1: LangGraph Cloud
```bash
langgraph cloud deploy
```

### Option 2: Google Cloud Run
```bash
gcloud run deploy emailpilot-langgraph \
  --source . \
  --port 8000 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

## 📞 Support

- **Documentation**: See `/docs` directory
- **Issues**: Create issue in GitHub repository
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangSmith Docs**: https://docs.smith.langchain.com/

## 📄 License

Proprietary - EmailPilot Platform

---

**Last Updated**: August 2025
**Version**: 1.0.0
**Status**: Production Ready