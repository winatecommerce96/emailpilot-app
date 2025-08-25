# LangGraph Calendar Workflow

## Overview
This is a LangGraph-based workflow for calendar planning operations in EmailPilot. It integrates with LangSmith for observability and MCP for tool execution.

## Project Structure
```
emailpilot-app/
├── graph/
│   ├── state.py          # State definitions with reducers
│   └── graph.py          # Main graph with SQLite checkpointing
├── agents/
│   └── calendar/
│       ├── planner.py    # Task planning node
│       ├── router.py     # Conditional routing node
│       └── worker.py     # Task execution node
├── tools/
│   └── calendar_tools.py # Calendar-specific tools
├── mcp_tools/
│   └── calendar_mcp.py   # MCP integration layer
├── var/
│   └── app.db           # SQLite checkpoint database
├── main.py              # Entry point
├── requirements.langgraph.txt
└── README_LANGGRAPH.md  # This file
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.langgraph.txt
```

### 2. Set Environment Variables
```bash
export LANGSMITH_API_KEY="your-api-key"
export LANGSMITH_PROJECT="emailpilot-calendar"
export LANGCHAIN_TRACING_V2="true"
```

### 3. Run Development Server
```bash
# Using the script
./scripts/run_langgraph_dev.sh

# Or directly
langgraph dev --port 2024
```

### 4. Access LangGraph Studio
Open browser to: http://localhost:2024

## Workflow Architecture

### State Management
The workflow uses `CalendarState` with the following fields:
- `messages`: User/system messages (with reducer)
- `tasks`: Queue of tasks to process
- `current_task`: Task being executed
- `artifacts`: Results from completed tasks
- `brand`: Target brand for calendar
- `month`: Target month for planning
- `run_context`: Execution metadata
- `error`: Error tracking
- `completed`: Completion flag

### Graph Flow
```
START → planner → router → worker ↔ tools
                    ↓
                   END
```

1. **Planner**: Converts user input into actionable tasks
2. **Router**: Manages task queue and conditional routing
3. **Worker**: Executes individual tasks
4. **Tools**: Calendar-specific operations (metrics, calendar generation, etc.)

### Tools Available
- `analyze_metrics`: Analyze campaign performance metrics
- `generate_calendar`: Create campaign calendar
- `read_calendar_events`: Retrieve existing events
- `mock_create_event`: Simulate event creation (safe mode)
- `optimize_send_time`: Recommend optimal send times

## MCP Integration
The workflow integrates with MCP servers for extended capabilities:
- Calendar operations via `calendar_mcp.py`
- Tool execution with safety boundaries
- Async/sync bridge for compatibility

## Testing

### Run Smoke Test
```bash
python tests/test_graph_smoke.py
```

### Run Main Workflow
```bash
python main.py --brand "TestBrand" --month "March 2025"
```

### Custom Instructions
```bash
python main.py --brand "MyBrand" --month "April 2025" --instructions "Create a holiday campaign calendar"
```

## LangSmith Integration
All workflow executions are traced in LangSmith:
1. View traces at: https://smith.langchain.com
2. Project: `emailpilot-calendar`
3. Look for traces with:
   - Run type: "chain"
   - Tags: ["calendar", "workflow", "langgraph"]

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're in the correct directory
   - Check that all dependencies are installed
   - Verify Python path includes project root

2. **LangSmith Not Tracing**
   - Verify LANGSMITH_API_KEY is set
   - Check LANGCHAIN_TRACING_V2="true"
   - Ensure network connectivity to LangSmith

3. **Studio Not Loading**
   - Check port 2024 is available
   - Verify langgraph package is installed
   - Check browser console for errors

4. **SQLite Errors**
   - Ensure var/ directory exists
   - Check write permissions
   - Delete var/app.db to reset state

## Development Tips

### Adding New Tools
1. Add tool function to `tools/calendar_tools.py`
2. Use `@tool` decorator
3. Include in `get_calendar_tools()` return list
4. Test with mock data first

### Modifying Workflow
1. Update state in `graph/state.py`
2. Modify graph edges in `graph/graph.py`
3. Update node logic in `agents/calendar/*.py`
4. Test with `test_graph_smoke.py`

### Debugging
- Enable debug logging: `LANGGRAPH_DEBUG=true`
- Check SQLite state: `sqlite3 var/app.db`
- View LangSmith traces for execution details
- Use breakpoints in node functions

## Integration with EmailPilot

### API Endpoints
The workflow can be exposed via FastAPI:
```python
from main import run_calendar_workflow

@app.post("/api/calendar/workflow")
async def run_workflow(brand: str, month: str):
    result = run_calendar_workflow(brand, month)
    return result
```

### Frontend Integration
```javascript
// Call from React components
const response = await fetch('/api/calendar/workflow', {
    method: 'POST',
    body: JSON.stringify({ brand, month })
});
```

## Next Steps
1. Add more specialized tools
2. Implement persistent storage beyond SQLite
3. Add webhook notifications for long-running workflows
4. Integrate with existing EmailPilot auth system
5. Add rate limiting and quotas