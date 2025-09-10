# Smart MCP Gateway Documentation

## Universal MCP Registry with AI-Enhanced HTTP Wrapper

### Overview

The Smart MCP Gateway is a revolutionary system that allows any MCP (Model Context Protocol) tool to be registered, managed, and accessed through an intelligent AI wrapper. This system automatically generates smart wrappers for any API or service, enabling natural language interactions with multiple retry strategies and self-learning capabilities.

### Key Features

1. **Universal Registration**: Register any MCP tool without code changes
2. **AI Wrapper Generation**: Automatic creation of intelligent wrappers for any service
3. **Smart Query Processing**: Natural language interface with multiple strategy fallbacks
4. **LLM Optimization**: Task-based LLM selection for optimal performance/cost
5. **Self-Learning**: System learns from successful patterns and improves over time
6. **LangChain Integration**: Automatic agent generation for each registered MCP

## Architecture

```
┌──────────────────┐
│   User Query     │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│    Universal MCP Registry        │
│  ┌─────────────────────────────┐ │
│  │  AI Wrapper Generator       │ │
│  │  - Query Analysis           │ │
│  │  - Tool Discovery           │ │
│  │  - Multi-Strategy Execution │ │
│  └─────────────────────────────┘ │
│  ┌─────────────────────────────┐ │
│  │  LLM Selector               │ │
│  │  - Task-based Selection     │ │
│  │  - Cost/Speed/Quality       │ │
│  └─────────────────────────────┘ │
│  ┌─────────────────────────────┐ │
│  │  MCP Agent Factory          │ │
│  │  - LangChain Agents         │ │
│  │  - Custom System Prompts    │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│   Firebase Tool Registry         │
│   - Tool Definitions             │
│   - Success Patterns             │
│   - Performance Metrics          │
└──────────────────────────────────┘
```

## Components

### 1. Universal MCP Registry (`app/services/mcp_registry/registry.py`)

Central registry for all MCP tools with automatic AI enhancement:

```python
registry = UniversalMCPRegistry(db)

# Register a new MCP
result = await registry.register_new_mcp({
    'name': 'Stripe Analytics',
    'base_url': 'https://api.stripe.com/v1',
    'service_type': 'financial',
    'auth_type': 'api_key',
    'example_queries': [
        'List all transactions',
        'Show revenue for last month'
    ]
})
```

### 2. AI Wrapper Generator (`app/services/mcp_registry/wrapper_generator.py`)

Automatically generates intelligent wrappers:

```python
class MCPWrapper:
    async def process_query(self, query: str, context: Dict):
        # 1. Analyze query intent with AI
        # 2. Find matching tools
        # 3. Execute with retry logic
        # 4. Learn from success/failure
```

### 3. LLM Selector (`app/services/llm_selector.py`)

Intelligent model selection based on task requirements:

```python
selector = LLMSelector()

# Select model for specific task
model = selector.select_for_task(
    task_type="query_analysis",
    optimization=OptimizationMode.BALANCED
)
```

Available models and their optimization profiles:
- **GPT-4 Turbo**: High quality code generation
- **Claude-3 Opus**: Best for complex reasoning
- **Claude-3 Haiku**: Fastest for simple queries
- **Gemini-1.5 Pro**: Long context analysis
- **GPT-4o-mini**: Balanced cost/performance

### 4. MCP Agent Factory (`app/services/mcp_registry/agent_factory.py`)

Creates LangChain agents for any MCP:

```python
factory = MCPAgentFactory(llm_selector)
agent = await factory.create_agent(mcp_config)
```

## API Endpoints

### Registration

```bash
POST /api/mcp/register
{
    "name": "Salesforce CRM",
    "base_url": "https://api.salesforce.com",
    "service_type": "crm",
    "auth_type": "oauth2",
    "description": "Salesforce customer management",
    "example_queries": [
        "List all contacts",
        "Show opportunities closing this month"
    ]
}
```

### Query Processing

```bash
POST /api/mcp/{mcp_id}/query
{
    "query": "Show me all active campaigns",
    "optimization": "balanced",
    "context": {
        "client_id": "client_123",
        "learning_enabled": true
    }
}
```

### List Registered MCPs

```bash
GET /api/mcp/list?status=active
```

### Get MCP Details

```bash
GET /api/mcp/{mcp_id}
```

### Update Agent Prompts

```bash
PUT /api/mcp/{mcp_id}/prompts
{
    "system_prompt": "You are a financial analyst...",
    "examples": ["Calculate ROI", "Analyze trends"]
}
```

### LLM Recommendations

```bash
GET /api/mcp/llm/recommend?task=query_analysis&optimization=speed
```

## UI Management

Access the Universal MCP Registry through the MCP Tools Dashboard:

1. Navigate to `/static/mcp_tools.html`
2. Click on "Universal MCP Registry" tab
3. Register new MCPs with the form
4. Test queries with AI processing
5. Monitor performance metrics

### Features in UI:

- **Registration Form**: Add new MCP tools
- **AI Configuration**: Set optimization mode and learning
- **Test Interface**: Execute queries with natural language
- **MCP Management**: View, test, and deactivate MCPs
- **LLM Recommendations**: See optimal model selection

## Use Cases

### 1. Adding Stripe Integration

```javascript
// Register Stripe MCP
const config = {
    name: "Stripe Payments",
    base_url: "https://api.stripe.com/v1",
    service_type: "financial",
    auth_type: "bearer",
    example_queries: [
        "Show revenue for October 2024",
        "List failed payments",
        "Get customer subscription status"
    ]
}

// System automatically:
// 1. Creates AI wrapper with retry logic
// 2. Generates LangChain agent
// 3. Enables natural language queries
```

### 2. Calendar Workflow Integration

The Calendar workflow can now use any registered MCP:

```python
# Calendar queries MCP for data
result = await mcp_wrapper.process_query(
    "Get campaign metrics for planning next month",
    context={"client_id": selected_client}
)

# System automatically:
# 1. Tries multiple endpoints
// 2. Falls back to alternative strategies
// 3. Learns successful patterns
```

### 3. Multi-MCP Orchestration

```python
# Query multiple MCPs in parallel
klaviyo_data = await klaviyo_wrapper.process_query("Get email metrics")
stripe_data = await stripe_wrapper.process_query("Get payment data")
analytics_data = await ga_wrapper.process_query("Get traffic data")

# Combine for comprehensive analysis
```

## Self-Learning Capabilities

The system learns and improves through:

1. **Pattern Recognition**: Successful query patterns are stored
2. **Tool Discovery**: New endpoints are discovered through usage
3. **Performance Metrics**: Track success rates and optimize
4. **Intent Mapping**: Learn query intent to tool mappings

### Learning Storage in Firebase

```
mcp_registry/
├── {mcp_id}/
│   ├── config/
│   ├── tool_registry/
│   ├── success_patterns/
│   └── metrics/

mcp_tools/
├── {mcp_id}_{tool_id}/
│   ├── intents/
│   ├── patterns_learned/
│   └── success_rate
```

## Configuration

### Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Firebase Configuration
FIREBASE_PROJECT_ID=emailpilot
FIRESTORE_EMULATOR_HOST=localhost:8080  # For local dev

# MCP Settings
MCP_LEARNING_ENABLED=true
MCP_DEFAULT_OPTIMIZATION=balanced
```

### Service Type Mappings

The system uses service types to generate appropriate prompts:

- `marketing`: Email, campaigns, customer engagement
- `financial`: Payments, billing, transactions
- `ecommerce`: Products, orders, inventory
- `analytics`: Metrics, reporting, insights
- `crm`: Customers, contacts, opportunities
- `communication`: Messaging, notifications

## Testing

### Test MCP Registration

```python
# Register a test MCP
test_mcp = {
    "name": "Test Analytics",
    "base_url": "http://localhost:9999",
    "service_type": "analytics",
    "example_queries": ["Get test metrics"]
}

response = await client.post("/api/mcp/register", json=test_mcp)
mcp_id = response.json()["mcp_id"]

# Test query processing
query_result = await client.post(
    f"/api/mcp/{mcp_id}/query",
    json={"query": "Show all data"}
)
```

### Test Workflow Integration

```bash
# Test with calendar workflow
curl -X POST http://localhost:8000/api/calendar/test-workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "calendar_workflow",
    "client_id": "milagro-mushrooms",
    "test_mcp": true
  }'
```

## Monitoring and Debugging

### View MCP Metrics

```python
# Get MCP performance metrics
metrics = await registry.get_mcp(mcp_id)
print(f"Total Queries: {metrics['metrics']['total_queries']}")
print(f"Success Rate: {metrics['metrics']['success_rate']}")
print(f"Avg Response Time: {metrics['metrics']['avg_response_time']}")
```

### Debug Query Processing

```bash
POST /api/mcp/{mcp_id}/test
{
    "query": "problematic query",
    "use_cache": false
}

# Returns detailed debug information:
# - Intent analysis
# - Tools tried
# - Errors encountered
# - Successful strategies
```

## Future Enhancements

1. **Auto-Discovery**: Automatic endpoint discovery from OpenAPI specs
2. **Multi-Agent Collaboration**: MCPs working together on complex tasks
3. **Visual Workflow Builder**: Drag-drop MCP orchestration
4. **Performance Optimization**: Predictive caching and prefetching
5. **Security Enhancements**: OAuth2 flow automation, key rotation

## Security Considerations

1. **API Keys**: Stored in Google Secret Manager
2. **Authentication**: Per-MCP auth configuration
3. **Rate Limiting**: Automatic rate limit handling with backoff
4. **Audit Logging**: All queries logged with user context
5. **Data Privacy**: PII detection and masking

## Troubleshooting

### Common Issues

1. **MCP Registration Fails**
   - Check base URL is valid
   - Ensure service type is supported
   - Verify auth credentials

2. **Query Processing Errors**
   - Check MCP is active
   - Verify API key is valid
   - Review debug output for specific errors

3. **LLM Selection Issues**
   - Ensure LLM API keys are configured
   - Check optimization mode is valid
   - Review model availability

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("mcp_registry").setLevel(logging.DEBUG)
```

## Support

For issues or questions:
1. Check the MCP Tools Dashboard for status
2. Review logs in `/logs/mcp_registry.log`
3. Use test interface to debug queries
4. Contact support with MCP ID and query details

---

**Version**: 1.0.0  
**Last Updated**: 2025-08-28  
**Status**: Production Ready

The Smart MCP Gateway revolutionizes how we integrate with external services, making any API accessible through natural language with automatic optimization and learning capabilities.