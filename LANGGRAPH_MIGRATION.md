# LangGraph Migration Guide

## Overview

As of August 22, 2025, EmailPilot has migrated from MCP (Model Context Protocol) based agents to LangGraph visual workflows for email campaign planning and orchestration.

## What Changed

### Old Architecture (MCP-Based)
- **Location**: `email-sms-mcp-server/` (now deprecated)
- **Agents**: 7 separate MCP agents (copy_smith, layout_lab, etc.)
- **Interface**: Text-based tool execution
- **Debugging**: Limited visibility into execution flow

### New Architecture (LangGraph)
- **Location**: `emailpilot_graph/`
- **Graph**: Unified campaign planning workflow
- **Interface**: Visual Studio editor with drag-and-drop
- **Debugging**: Full LangSmith tracing and step-through debugging

## Migration Status

| Component | Old System | New System | Status |
|-----------|------------|------------|--------|
| Email Campaign Planning | MCP Email/SMS Agents | LangGraph Campaign Graph | ✅ Migrated |
| Visual Editing | None | LangGraph Studio | ✅ Active |
| Tracing | Basic logging | LangSmith Integration | ✅ Active |
| Tool Execution | MCP protocol | LangChain tools | ✅ Migrated |

## What Stays the Same

### Preserved Systems
1. **LangChain Multi-Agent System**: Still used for RAG, revenue analysis, and other non-campaign tasks
2. **Klaviyo API Integration**: Data services remain unchanged at `services/klaviyo_api/`
3. **Admin Dashboard**: All existing functionality preserved
4. **Firestore Integration**: Database layer unchanged

### MCP Services (Still Active for Data)
While email/SMS agents are deprecated, MCP is still used for deterministic data operations:
- **Klaviyo Revenue API** (Port 9090): Revenue data retrieval
- **Performance API** (Port 9091): Weekly/monthly job execution

These are now called by LangGraph tools rather than MCP agents.

## How to Use the New System

### Starting LangGraph
```bash
cd emailpilot_graph
langgraph dev --port 2024
```

### Accessing the Studio
- Auto-opens in browser when server starts
- Manual access: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

### Testing Campaign Planning
1. Open Studio in browser
2. Select "agent" graph
3. Send message: "Help me plan campaigns for [brand] next month"
4. Watch visual execution flow

## For Developers

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

### Connecting to Existing Services
LangGraph tools can call existing MCP services:
```python
@tool
def get_klaviyo_revenue(client_slug: str) -> str:
    """Fetch revenue from Klaviyo API service"""
    response = httpx.get(f"http://localhost:9090/clients/by-slug/{client_slug}/revenue/last7")
    return response.json()
```

## Deprecation Notice

The following are deprecated and should not be used for new development:
- ❌ `email-sms-mcp-server/` directory
- ❌ MCP Email/SMS agents (copy_smith, layout_lab, etc.)
- ❌ `/api/admin/mcp/agents` endpoints for email/SMS

These remain for backwards compatibility only and will be removed in a future release.

## Support

- **LangGraph Issues**: See `emailpilot_graph/README.md`
- **Migration Questions**: Contact the development team
- **Documentation**: Full docs in `LANGGRAPH_INTEGRATION.md`