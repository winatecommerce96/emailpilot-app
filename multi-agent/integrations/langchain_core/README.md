# LangChain Core Integration

✅ **Status**: Production-ready with Google Secret Manager integration

Production-quality LangChain/LangGraph integration for EmailPilot, providing RAG (Retrieval-Augmented Generation) and Agent capabilities with MCP service interoperability. API keys are securely fetched from Google Secret Manager.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r multi-agent/integrations/langchain_core/requirements.txt

# Set up environment variables (API keys from Secret Manager)
cat > .env << EOF
GOOGLE_CLOUD_PROJECT=emailpilot-438321
LC_PROVIDER=gemini
LC_MODEL=gemini-1.5-flash
EMBEDDINGS_PROVIDER=local
USE_SECRET_MANAGER=true
OPENAI_SECRET_NAME=openai-api-key
ANTHROPIC_SECRET_NAME=emailpilot-claude
GEMINI_SECRET_NAME=emailpilot-gemini-api-key
EOF
```

### Basic Usage

```bash
# Build RAG index
python -m "multi-agent.integrations.langchain_core.cli" rag.ingest --rebuild

# Ask a question
python -m "multi-agent.integrations.langchain_core.cli" rag.ask \
  -q "What does the orchestrator service do?"

# Run an agent task
python -m "multi-agent.integrations.langchain_core.cli" agent.run \
  -t "Fetch last October's campaign insights and propose improvements"
```

### Via Orchestrator CLI

```bash
# RAG query through orchestrator
python -m apps.orchestrator_service.main lc-rag \
  --q "How does calendar planning work?" \
  --k 5

# Agent task through orchestrator
python -m apps.orchestrator_service.main lc-agent \
  --task "Draft next steps based on last week's performance" \
  --brand acme \
  --month 2024-11
```

## 📋 Features

### RAG Pipeline
- **Document Ingestion**: Automatic loading from project docs
- **Vector Store**: FAISS (default) or Chroma for similarity search
- **Grounded Answers**: All responses include source citations
- **Evaluation**: Built-in faithfulness and relevance scoring

### Agent System
- **Native Tools**: Firestore (read-only), HTTP (allowlisted), caching
- **MCP Tools**: Klaviyo data, enrichment jobs, campaign insights
- **Policy Enforcement**: Tool budgets, timeouts, PII redaction
- **Structured Output**: Plans, steps, tool calls, final answers

### Integration
- **Zero Breaking Changes**: Optional feature that doesn't affect core
- **Pydantic Settings**: All configuration via environment/files
- **Graceful Degradation**: Falls back if dependencies unavailable
- **Observable**: Comprehensive logging and optional tracing

## 🔧 Configuration

### Environment Variables

Create a `.env` file with:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=emailpilot-438321

# LLM Provider (openai|anthropic|gemini)
LC_PROVIDER=gemini
LC_MODEL=gemini-1.5-flash

# Secret Manager Configuration (recommended)
USE_SECRET_MANAGER=true
OPENAI_SECRET_NAME=openai-api-key
ANTHROPIC_SECRET_NAME=emailpilot-claude
GEMINI_SECRET_NAME=emailpilot-gemini-api-key

# Embeddings (local to avoid quota issues)
EMBEDDINGS_PROVIDER=local
EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Vector Store
VECTORSTORE=faiss

# MCP Integration
MCP_BASE_URL=http://localhost:8090/api/mcp
KLAVIYO_MCP_URL=http://localhost:8090/api/klaviyo

# Firestore (optional)
GOOGLE_CLOUD_PROJECT=your-project
FIRESTORE_EMULATOR_HOST=localhost:8080  # If using emulator

# Agent Limits
AGENT_BUDGET_STEPS=15
AGENT_TIMEOUT_S=60

# Tracing (optional)
ENABLE_TRACING=false
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=emailpilot-langchain
```

### Configuration Object

All settings are managed via `config.py`:

```python
from integrations.langchain_core import get_config

config = get_config()
print(config.model_banner())  # Shows current configuration
```

## 🏗️ Architecture

### Module Structure

```
langchain_core/
├── config.py           # Pydantic settings management
├── deps.py            # Dependency factories (LLM, embeddings, etc.)
├── engine.py          # LangGraph workflow composition
├── rag/
│   ├── ingest.py      # Document loading and indexing
│   ├── chain.py       # RAG chain with citations
│   └── evaluators.py  # Answer quality evaluation
├── agents/
│   ├── tools.py       # Native and MCP-backed tools
│   ├── policies.py    # Budgets and guardrails
│   └── agent.py       # Agent executor
├── adapters/
│   ├── mcp_client.py  # Typed MCP client
│   └── orchestrator_bridge.py  # Integration functions
└── tests/
    ├── test_rag.py
    └── test_agent.py
```

### Design Principles

1. **Sandboxed**: Isolated module with no core dependencies
2. **Production-Quality**: Error handling, retries, logging
3. **Configurable**: All behavior controlled via settings
4. **Observable**: Metrics, tracing, structured logs
5. **Safe**: Read-only by default, policy enforcement

## 🛠️ Tools

### Native Tools (Fast, SDK-based)

#### `firestore_ro_get`
Read-only Firestore access for collections and documents.

```python
result = firestore_ro_get(
    collection="campaigns",
    document_id="campaign_123",
    max_fields=10
)
```

#### `http_get_json`
Fetch JSON from allowlisted domains.

```python
result = http_get_json(
    url="https://api.klaviyo.com/v3/campaigns",
    headers={"Authorization": "Bearer token"}
)
```

#### `simple_cache_get/set`
In-process caching for performance.

```python
simple_cache_set("key", {"data": "value"}, ttl_seconds=300)
cached = simple_cache_get("key")
```

### MCP Tools (Slow, via FastAPI)

#### `klaviyo_fetch`
Fetch Klaviyo data through MCP gateway.

#### `enrichment_job_status`
Check enrichment job status.

#### `campaign_insights`
Generate campaign insights via MCP.

## 📊 RAG Usage

### Document Ingestion

```python
from integrations.langchain_core.rag import ingest_documents

# Ingest with default paths
result = ingest_documents(rebuild=True)

# Ingest specific paths
result = ingest_documents(
    source_paths=["docs/", "README.md"],
    rebuild=False  # Update existing index
)

print(f"Ingested {result['stats']['total_chunks']} chunks")
```

### Query with Citations

```python
from integrations.langchain_core.rag import create_rag_chain

chain = create_rag_chain()
response = chain.ask(
    "What are the core features of EmailPilot?",
    max_tokens=500
)

print(f"Answer: {response.answer}")
print(f"Citations: {response.citations}")
print(f"Confidence: {response.confidence}")
```

### Evaluation

```python
from integrations.langchain_core.rag.evaluators import evaluate_response

scores = evaluate_response(
    question="What does the orchestrator do?",
    answer=response.answer,
    source_documents=response.source_documents
)

print(f"Faithfulness: {scores['faithfulness']}")
print(f"Relevance: {scores['relevance']}")
```

## 🤖 Agent Usage

### Basic Agent Task

```python
from integrations.langchain_core.agents import run_agent_task

result = run_agent_task(
    task="Analyze last month's email performance and suggest improvements",
    context={"brand": "acme", "month": "2024-10"},
    timeout=30,
    max_tools=10
)

print(f"Plan: {result['plan']}")
print(f"Steps: {len(result['steps'])}")
print(f"Final Answer: {result['final_answer']}")
```

### With Custom Policy

```python
from integrations.langchain_core.agents import AgentPolicy, AgentExecutor

policy = AgentPolicy(
    max_tool_calls=5,
    timeout_seconds=20,
    enable_pii_redaction=True,
    denied_tools={"write_to_firestore", "delete_anything"}
)

executor = AgentExecutor(policy=policy)
result = executor.run(
    task="Check campaign status",
    context={"brand": "test"}
)
```

### Policy Enforcement

```python
# Check policy violations
if result.policy_summary["has_critical"]:
    print("Critical policy violations detected!")
    
print(f"Tool calls used: {result.policy_summary['tool_calls']}")
print(f"Time elapsed: {result.policy_summary['elapsed_seconds']}s")
```

## 🔍 MCP Client Usage

### Direct MCP Calls

```python
from integrations.langchain_core.adapters import MCPClient

with MCPClient() as client:
    # Health check
    if client.healthcheck():
        print("MCP service is healthy")
    
    # Fetch campaigns
    response = client.klaviyo_campaigns(
        brand_id="acme",
        month="2024-11",
        limit=10
    )
    
    if response.success:
        campaigns = response.data["campaigns"]
        print(f"Found {len(campaigns)} campaigns")
```

### Batch Operations

```python
requests = [
    {"method": "GET", "endpoint": "klaviyo/campaigns"},
    {"method": "GET", "endpoint": "enrichment/jobs/123"},
    {"method": "POST", "endpoint": "campaigns/insights", "body": {...}}
]

responses = client.batch_request(requests)
for resp in responses:
    if resp.success:
        print(f"{resp.endpoint}: {resp.data}")
```

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest multi-agent/integrations/langchain_core/tests/

# Just RAG tests
pytest multi-agent/integrations/langchain_core/tests/test_rag.py

# Integration tests (requires API keys)
pytest -m integration
```

### Test Coverage

- ✅ RAG document ingestion and splitting
- ✅ RAG chain with citations
- ✅ Agent policy enforcement
- ✅ Tool execution with mocks
- ✅ MCP client with retries
- ✅ End-to-end integration tests

## 📈 Observability

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or set via environment
LOG_LEVEL=DEBUG
```

### Tracing (LangSmith)

```bash
# Enable tracing
ENABLE_TRACING=true
LANGCHAIN_API_KEY=your-key
LANGCHAIN_PROJECT=emailpilot

# View traces at https://smith.langchain.com
```

### Metrics

Every execution includes timing and count metrics:

```json
{
  "diagnostics": {
    "duration_ms": 1234,
    "model": "gpt-4o-mini",
    "provider": "openai",
    "tool_calls": 5,
    "num_sources": 3
  }
}
```

## ⚠️ Limitations & Guardrails

### Read-Only by Default
- No writes to Firestore unless explicitly allowed
- No destructive operations
- Tool allowlists for HTTP domains

### Resource Limits
- Maximum 15 tool calls per agent run
- 60-second timeout for agent tasks
- 5 calls per tool maximum
- 2MB response size limit

### PII Protection
- Automatic redaction of emails, phones, SSNs
- Configurable PII patterns
- Audit logging of redactions

## 🚦 Rollback & Safety

### Graceful Degradation

If LangChain is unavailable, the orchestrator continues working:

```python
try:
    from integrations.langchain_core.adapters import lc_rag
    result = lc_rag(question="...")
except ImportError:
    # Fall back to legacy behavior
    result = legacy_search(question="...")
```

### Feature Flags

Control feature rollout via configuration:

```python
# Disable agent features
AGENT_BUDGET_STEPS=0  # Effectively disables agents

# Use different models for A/B testing
LC_PROVIDER=anthropic
LC_MODEL=claude-3-haiku
```

## 📚 Additional Resources

### Architecture Decision Record

**Why Hybrid LangGraph + MCP?**

1. **LangGraph**: Orchestration, state management, retries
2. **Native Tools**: Hot paths needing low latency
3. **MCP Tools**: Complex, slow, or risky operations
4. **Separation**: Clean boundaries for testing and rollback

### Success Metrics

- **Latency**: RAG < 2s, Agent < 10s for typical tasks
- **Reliability**: 99%+ success rate with retries
- **Developer Experience**: Single config, clear APIs
- **Safety**: Zero production incidents from agent actions

### Future Enhancements

- [ ] Streaming responses for better UX
- [ ] Multi-turn conversations with memory
- [ ] Custom tool creation UI
- [ ] Fine-tuned models for domain tasks
- [ ] Distributed tracing integration

## 🤝 Contributing

1. Keep changes backward compatible
2. Add tests for new features
3. Update documentation
4. Follow existing patterns
5. Pin dependency versions

## 📄 License

Part of EmailPilot platform. See main repository for license details.