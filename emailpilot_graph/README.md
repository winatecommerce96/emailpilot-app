# LangGraph Studio - EmailPilot Campaign Planning

## Overview

This is the LangGraph-powered campaign planning system for EmailPilot. It provides a visual workflow editor and intelligent agent system for email campaign planning, replacing the previous MCP-based email/SMS agents with a unified LangGraph implementation.

## Current Status ✅

- **LangGraph Server**: Running successfully on port 2024
- **Studio UI**: Accessible via LangSmith Studio (browser-based)
- **Graph**: EmailPilot Campaign Planning graph loaded and operational
- **LangSmith Integration**: Full tracing enabled to project "emailpilot-calendar"

## Architecture

### What This Replaces
- ❌ MCP Email/SMS Agents (deprecated)
- ❌ Standalone agent implementations
- ✅ Now using unified LangGraph workflow system

### Technology Stack
- **LangGraph**: Workflow orchestration and state management
- **LangChain**: LLM integration and tool execution
- **LangSmith**: Tracing, monitoring, and debugging
- **OpenAI GPT-4**: Primary language model
- **Python 3.12**: Runtime environment

## Quick Start

### 1. Prerequisites

```bash
# Ensure you're in the emailpilot_graph directory
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/emailpilot_graph

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Start the Server

```bash
# Start LangGraph development server
langgraph dev --port 2024
```

### 3. Access the Studio

The server will automatically open the Studio in your browser. If not, access it at:

- **Studio UI**: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
- **API Server**: `http://127.0.0.1:2024`
- **API Docs**: `http://127.0.0.1:2024/docs`

## Available Tools

The EmailPilot graph includes three specialized tools:

### 1. `analyze_klaviyo_metrics`
Analyzes Klaviyo metrics for a specific brand and month.
- **Input**: brand name, month (YYYY-MM format)
- **Output**: Metrics analysis including open rates, click rates, revenue, and recommendations

### 2. `generate_campaign_calendar`
Generates a campaign calendar for the specified month.
- **Input**: brand name, month, campaign count
- **Output**: JSON calendar with campaign dates, types, subjects, and segments

### 3. `optimize_send_times`
Suggests optimal send times based on brand and timezone.
- **Input**: brand name, timezone
- **Output**: Best days/times for sending, recommendations

## Using the Studio

### Testing Your Graph

1. **Open Studio** - Should auto-open when server starts
2. **Select "agent" graph** - Your EmailPilot campaign planning workflow
3. **Start a conversation**:
   ```
   "Help me plan email campaigns for Buca di Beppo next month"
   ```
4. **Watch the execution** - See tools being called and state changes in real-time

### Example Prompts

- "Analyze the email metrics for [brand] for this month"
- "Generate a campaign calendar for [brand] for February 2025"
- "What are the best times to send emails for [brand]?"
- "Help me optimize my email campaign strategy"

## API Usage

### Direct API Calls

```bash
# List available assistants
curl -X POST http://127.0.0.1:2024/assistants/search \
  -H "Content-Type: application/json" \
  -d '{}'

# Get assistant details
curl http://127.0.0.1:2024/assistants/agent

# Create a new thread and run
curl -X POST http://127.0.0.1:2024/threads \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"role": "user", "content": "Plan campaigns for next month"}]
    }
  }'
```

### Python Integration

```python
import httpx

# Create client
client = httpx.Client(base_url="http://127.0.0.1:2024")

# Start a conversation
response = client.post("/threads", json={
    "assistant_id": "agent",
    "input": {
        "messages": [{"role": "user", "content": "Analyze metrics for Buca di Beppo"}],
        "brand": "Buca di Beppo",
        "month": "2025-02"
    }
})

thread_id = response.json()["thread_id"]
print(f"Thread created: {thread_id}")
```

## Development

### File Structure

```
emailpilot_graph/
├── README.md           # This file
├── agent.py           # Main graph implementation
├── langgraph.json     # LangGraph configuration
├── requirements.txt   # Python dependencies
└── .env              # Environment variables (contains API keys)
```

### Modifying the Graph

1. **Edit `agent.py`** - Make changes to tools, state, or workflow
2. **Hot Reload** - Changes auto-reload (watch the server logs)
3. **Test in Studio** - Verify changes work as expected

### Adding New Tools

```python
# In agent.py, add a new tool:
@tool
def your_new_tool(param1: str, param2: int) -> str:
    """Description of what your tool does."""
    # Tool implementation
    return "Tool result"

# Add to tools list:
tools = [analyze_klaviyo_metrics, generate_campaign_calendar, 
         optimize_send_times, your_new_tool]
```

## Environment Variables

Required environment variables (already configured in `.env`):

```bash
# OpenAI API Key (required for GPT-4)
OPENAI_API_KEY=sk-proj-...

# LangSmith API Key (for tracing)
LANGSMITH_API_KEY=lsv2_pt_...

# LangSmith Project Name
LANGSMITH_PROJECT=emailpilot-calendar

# Enable tracing
LANGCHAIN_TRACING_V2=true

# Optional: Klaviyo API Key (for production)
KLAVIYO_API_KEY=

# Google Cloud Project
GOOGLE_CLOUD_PROJECT=emailpilot-438321
```

## Monitoring & Debugging

### LangSmith Tracing

All runs are automatically traced to LangSmith. View traces at:
- [https://smith.langchain.com](https://smith.langchain.com)
- Project: `emailpilot-calendar`

### Server Logs

Monitor the terminal where you started `langgraph dev` for:
- Tool executions
- State changes
- API requests
- Hot reload notifications

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill existing process on port 2024
   lsof -i :2024 | grep LISTEN | awk '{print $2}' | xargs kill -9
   ```

2. **OpenAI API Key Issues**
   - Verify key in `.env` file
   - Check key has sufficient credits
   - Ensure key has GPT-4 access

3. **Studio Won't Open**
   - Check browser popup blockers
   - Manually open: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

## Integration with EmailPilot

### Current Integration Points

1. **Frontend Access**: Link to Studio from EmailPilot admin dashboard
2. **API Integration**: Call LangGraph API from FastAPI backend
3. **Shared Context**: Pass brand, month, and user context to graph

### Future Integration Plans

1. **Direct Embedding**: Embed Studio UI in EmailPilot dashboard
2. **Firestore Integration**: Connect tools to live Firestore data
3. **Klaviyo Live Data**: Replace mock data with actual Klaviyo API calls
4. **Multi-Agent Orchestration**: Coordinate multiple specialized graphs

## Production Deployment

### Option 1: LangGraph Cloud (Recommended)

```bash
# Deploy to LangGraph Cloud
langgraph cloud deploy
```

### Option 2: Self-Hosted

```bash
# Build Docker image
docker build -t emailpilot-langgraph .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e LANGSMITH_API_KEY=$LANGSMITH_API_KEY \
  emailpilot-langgraph
```

### Option 3: Google Cloud Run

```bash
# Build and deploy to Cloud Run
gcloud run deploy emailpilot-langgraph \
  --source . \
  --port 8000 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

## Support & Documentation

- **LangGraph Docs**: [https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)
- **LangSmith Docs**: [https://docs.smith.langchain.com/](https://docs.smith.langchain.com/)
- **LangChain Docs**: [https://python.langchain.com/](https://python.langchain.com/)
- **EmailPilot Issues**: Create issue in main EmailPilot repository

## License

Part of the EmailPilot platform. All rights reserved.