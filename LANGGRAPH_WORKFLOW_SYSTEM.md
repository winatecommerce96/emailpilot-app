# LangGraph Workflow System for EmailPilot

## Overview

A complete minimal-viable LangGraph workflow system that allows you to design, edit, and run multi-step workflows for EmailPilot using a declarative schema as the source of truth.

## Features

✅ **Schema-Driven Design**: JSON schema defines entire workflow structure
✅ **Visual Editor**: React Flow-based drag-and-drop workflow designer
✅ **Agent Discovery**: Automatic discovery of existing LangChain agents and tools
✅ **Code Generation**: Compiles schema to executable LangGraph runtime
✅ **CLI Runner**: Execute workflows from command line with streaming support
✅ **Human Gates**: Built-in support for human review checkpoints
✅ **API Integration**: RESTful API for all workflow operations
✅ **Test Suite**: Comprehensive testing framework

## Quick Start

### 1. Access the Visual Editor
Navigate to: http://localhost:8000/static/workflow_editor.html

### 2. Design Your Workflow
- Drag agents and tools from the sidebar
- Connect nodes to create execution flow
- Add conditions for branching logic
- Include human review gates where needed

### 3. Compile and Run
```bash
# Compile workflow from schema
python workflow/tools/codegen.py

# Run workflow with CLI
python workflow/run_graph.py workflow.json --inputs '{"brand": "test", "month": "2024-12"}'

# Run with streaming output
python workflow/run_graph.py --stream --inputs input.json

# Interactive mode with checkpoints
python workflow/run_graph.py --interactive
```

## Architecture

```
workflow/
├── workflow.json           # Main workflow schema
├── tools/
│   ├── codegen.py         # Schema → LangGraph compiler
│   └── inspect_agents.py  # Agent/tool discovery
├── runtime/
│   ├── graph_compiled.py  # Generated runtime code
│   └── nodes_stubs.py     # Stub implementations
├── schemas/               # Saved workflow schemas
├── nodes/                 # Custom node implementations
├── run_graph.py          # CLI runner
└── test_workflow.py      # Test suite
```

## API Endpoints

### Workflow Management
- `GET /api/workflow/agents` - Discover available agents and tools
- `GET /api/workflow/schemas` - List saved schemas
- `GET /api/workflow/schemas/{id}` - Get specific schema
- `POST /api/workflow/schemas` - Save new schema
- `POST /api/workflow/schemas/{id}/compile` - Compile schema to code
- `POST /api/workflow/schemas/{id}/run` - Execute workflow
- `POST /api/workflow/schemas/{id}/validate` - Validate schema
- `GET /api/workflow/export/{id}/mermaid` - Export as Mermaid diagram

## Schema Format

```json
{
  "name": "emailpilot_calendar",
  "state": {
    "brand": "str",
    "month": "str",
    "inputs": "dict",
    "candidates": "list",
    "calendar": "dict",
    "valid": "bool",
    "approvals": "dict"
  },
  "nodes": [
    {
      "id": "ingest",
      "type": "python_fn",
      "impl": "nodes.ingest:run"
    },
    {
      "id": "generate",
      "type": "agent",
      "impl": "agents.calendar_planner",
      "params": {
        "tool_allowlist": ["tools.brand_knowledge", "tools.menu_lookup"]
      }
    },
    {
      "id": "review",
      "type": "human_gate",
      "impl": "nodes.human_review:run"
    }
  ],
  "edges": [
    {"from": "ingest", "to": "generate"},
    {"from": "generate", "to": "review"}
  ],
  "checkpointer": {
    "type": "sqlite",
    "dsn": "sqlite:///emailpilot.db"
  }
}
```

## Node Types

### 1. Agent Node
Executes a LangChain agent with tools
```json
{
  "id": "planner",
  "type": "agent",
  "impl": "agents.calendar_planner",
  "params": {
    "tool_allowlist": ["klaviyo_campaigns", "firestore_ro"],
    "max_tool_calls": 20,
    "timeout_seconds": 120
  }
}
```

### 2. Python Function Node
Runs custom Python code
```json
{
  "id": "transform",
  "type": "python_fn",
  "impl": "nodes.transform:run"
}
```

### 3. Human Gate Node
Requires human approval
```json
{
  "id": "approval",
  "type": "human_gate",
  "impl": "nodes.human_review:run"
}
```

### 4. Tool Node
Executes a specific tool
```json
{
  "id": "fetch_data",
  "type": "tool",
  "impl": "tools.klaviyo_fetch"
}
```

## Conditional Edges

Add branching logic with conditions:
```json
{
  "from": "validate",
  "to": "success",
  "condition": "state.get('valid', False)"
}
```

## CLI Usage

### Basic Execution
```bash
python workflow/run_graph.py workflow.json \
  --inputs '{"client": "milagro", "month": "2024-12"}'
```

### Stream Events
```bash
python workflow/run_graph.py --stream \
  --inputs input.json \
  --thread-id session_123
```

### Interactive Mode
```bash
python workflow/run_graph.py --interactive
> run {"client": "test"}
> continue
> state
> quit
```

### Resume from Checkpoint
```bash
python workflow/run_graph.py \
  --thread-id session_123 \
  --checkpoint-id checkpoint_456
```

## Testing

Run the test suite:
```bash
python workflow/test_workflow.py
```

Tests include:
- Schema validation
- Code generation
- Agent discovery
- Conditional edges
- Human gates
- End-to-end execution

## Creating Custom Nodes

### 1. Create Node Implementation
```python
# workflow/nodes/my_node.py
def run(state):
    """Custom node logic"""
    state["processed"] = True
    return state
```

### 2. Reference in Schema
```json
{
  "id": "my_node",
  "type": "python_fn",
  "impl": "nodes.my_node:run"
}
```

## Agent Discovery

Scan codebase for available agents:
```bash
python workflow/tools/inspect_agents.py

# Export as workflow nodes
python workflow/tools/inspect_agents.py --format workflow
```

## Visual Editor Features

- **Drag & Drop**: Add nodes from sidebar
- **Connect Nodes**: Draw edges between nodes
- **Properties Panel**: Configure node parameters
- **Live Validation**: Real-time schema validation
- **Export/Import**: Save and load workflows
- **Compile & Run**: Execute directly from UI
- **Minimap**: Navigate large workflows
- **Zoom Controls**: Pan and zoom canvas

## Integration with EmailPilot

The workflow system integrates seamlessly with EmailPilot's existing infrastructure:

1. **LangChain Agents**: All registered agents are discoverable
2. **Klaviyo Tools**: Access to Klaviyo API tools
3. **Firestore**: Read/write to Firestore collections
4. **MCP Tools**: Compatible with MCP protocol tools
5. **Authentication**: Uses EmailPilot auth system

## Deployment

### Production Setup
1. Configure checkpointer for Redis (instead of SQLite)
2. Set up persistent storage for schemas
3. Configure proper authentication
4. Enable WebSocket for real-time updates

### Environment Variables
```bash
# Workflow configuration
WORKFLOW_SCHEMAS_DIR=/path/to/schemas
WORKFLOW_CHECKPOINTER_DSN=redis://localhost:6379
WORKFLOW_MAX_EXECUTION_TIME=300
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all node implementations exist
2. **Validation Failures**: Check schema structure and required fields
3. **Execution Timeouts**: Increase timeout in node params
4. **Missing Agents**: Run agent discovery to update catalog

### Debug Mode
```bash
# Verbose output
python workflow/run_graph.py --verbose

# Test compilation only
python workflow/tools/codegen.py
```

## Future Enhancements

- [ ] WebSocket support for real-time execution updates
- [ ] Version control for schemas
- [ ] Workflow templates library
- [ ] Performance monitoring dashboard
- [ ] Distributed execution support
- [ ] Advanced retry policies
- [ ] Workflow composition (sub-workflows)
- [ ] A/B testing for workflow variants

## Summary

The LangGraph Workflow System provides a complete solution for designing, managing, and executing complex multi-step workflows in EmailPilot. With its visual editor, declarative schema approach, and seamless integration with existing LangChain agents, it enables rapid development and deployment of sophisticated automation workflows.