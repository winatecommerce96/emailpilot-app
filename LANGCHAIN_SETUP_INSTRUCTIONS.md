# LangChain Complete Setup Instructions

## ✅ Configuration Completed

### 1. **API Keys Configuration**
The API keys are already configured in Google Secret Manager:
- **OpenAI**: `openai-api-key`
- **Anthropic**: `emailpilot-claude`
- **Google/Gemini**: `emailpilot-gemini-api-key`

The LangChain secrets.py file has been updated to use these correct secret names.

### 2. **Firestore Configuration**
Firestore is configured for run storage and persistence:
- **Project ID**: `emailpilot-438321` (set in config.py)
- **Collections Used**:
  - `agent_runs` - Stores run history and state
  - `agent_checkpoints` - Stores LangGraph checkpoints
  - `agent_results` - Stores run results

### 3. **MCP Server Auto-Start**
Created scripts to automatically manage MCP servers:
- **Start Script**: `./start_mcp_servers.sh`
- **Stop Script**: `./stop_mcp_servers.sh`

### 4. **RAG Setup**
Created RAG initialization script:
- **Setup Script**: `python setup_rag.py`
- **Query Script**: `python query_rag.py "Your question"`

## 📋 Quick Start Guide

### Step 1: Install Dependencies
```bash
# Install LangChain dependencies
pip install langchain langchain-community langchain-openai \
            langchain-anthropic langchain-google-genai \
            faiss-cpu sentence-transformers tiktoken \
            langgraph mcp

# Or use requirements.txt
pip install -r requirements.txt
```

### Step 2: Start MCP Servers
```bash
# Start all MCP servers automatically
./start_mcp_servers.sh

# This starts:
# - Klaviyo Revenue API on port 9090
# - Performance API on port 9091
# - Multi-Agent System (stdio mode, on-demand)
```

### Step 3: Initialize RAG System
```bash
# Run the RAG setup script
python setup_rag.py

# This will:
# - Create vector store directory
# - Ingest initial documents
# - Test the vector store
```

### Step 4: Start Main Application
```bash
# Start EmailPilot with LangChain
uvicorn main_firestore:app --reload --port 8000 --host localhost
```

### Step 5: Access Admin Interface
Open your browser and navigate to:
- **Main App**: http://localhost:8000
- **Admin Dashboard**: http://localhost:8000/admin-dashboard.html
- **LangChain Models**: http://localhost:8000/admin/langchain/models.html
- **LangChain Agents**: http://localhost:8000/admin/langchain/agents.html

## 🧪 Testing LangChain Features

### Test RAG Queries
```bash
# Query the knowledge base
python query_rag.py "What is EmailPilot?"
python query_rag.py "How does the AI orchestration work?"
```

### Test Agent Execution
```bash
# Via API
curl -X POST http://localhost:8000/api/admin/langchain/agents/default/runs \
  -H "Content-Type: application/json" \
  -d '{"context": {"task": "Analyze last week revenue"}, "overrides": {}}'
```

### Test MCP Integration
```bash
# Check MCP server health
curl http://127.0.0.1:9090/healthz  # Klaviyo Revenue API
curl http://127.0.0.1:9091/healthz  # Performance API
```

### Test Model Providers
```bash
# List available models
curl http://localhost:8000/api/admin/langchain/models/available?provider=openai
curl http://localhost:8000/api/admin/langchain/models/available?provider=anthropic
curl http://localhost:8000/api/admin/langchain/models/available?provider=gemini
```

## 🎯 Available LangChain Agents

1. **RAG Agent** (`rag`)
   - Purpose: Question answering with document retrieval
   - Variables: `question`, `k` (number of docs)
   - Usage: Knowledge base queries

2. **Default Agent** (`default`)
   - Purpose: General-purpose task execution
   - Variables: `task`
   - Usage: Generic automation tasks

3. **Revenue Analyst** (`revenue_analyst`)
   - Purpose: Analyzes Klaviyo revenue data
   - Variables: `brand`, `month`, `comparison_period`
   - Usage: Revenue insights and reporting

4. **Campaign Planner** (`campaign_planner`)
   - Purpose: Creates email campaign plans
   - Variables: `brand`, `num_emails`, `objective`
   - Usage: Campaign strategy development

## 🚨 Troubleshooting

### If MCP servers don't start:
```bash
# Check if ports are already in use
lsof -i :9090
lsof -i :9091

# Kill existing processes
./stop_mcp_servers.sh

# Restart servers
./start_mcp_servers.sh
```

### If RAG setup fails:
```bash
# Check dependencies
pip install faiss-cpu sentence-transformers

# Verify API keys are accessible
gcloud secrets versions access latest --secret=openai-api-key

# Check Firestore access
gcloud auth application-default login
```

### If agent execution fails:
```bash
# Check logs
tail -f logs/emailpilot_app.log
tail -f logs/agent_orchestrator.log

# Verify Firestore permissions
gcloud projects add-iam-policy-binding emailpilot-438321 \
  --member="user:YOUR_EMAIL" \
  --role="roles/datastore.user"
```

## 📊 Monitoring

### Check System Status
```bash
# LangChain health
curl http://localhost:8000/api/admin/langchain/agents

# MCP server status
curl http://127.0.0.1:9090/healthz
curl http://127.0.0.1:9091/healthz

# RAG test
python query_rag.py "test query"
```

### View Logs
```bash
# Application logs
tail -f logs/emailpilot_app.log

# MCP server logs
tail -f logs/klaviyo_revenue_mcp.log
tail -f logs/performance_mcp.log

# Agent execution logs
tail -f logs/agent_orchestrator.log
```

## ✅ Setup Complete!

Your LangChain integration is now fully configured with:
- ✅ API keys from Secret Manager
- ✅ Firestore for persistence
- ✅ Auto-start scripts for MCP servers
- ✅ RAG system with vector store
- ✅ Admin interface for management
- ✅ 4 pre-configured agents ready to use

To start everything:
```bash
# 1. Start MCP servers
./start_mcp_servers.sh

# 2. Start main app
uvicorn main_firestore:app --reload --port 8000 --host localhost

# 3. Access admin at http://localhost:8000/admin-dashboard.html
```

---

*Last Updated: 2024-12-20*
*LangChain Version: 0.3.0+*
*Status: Fully Operational*