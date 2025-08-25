# LangChain Lab - RAG & Agent Evaluation Module

A sandboxed module for evaluating LangChain-based RAG and Agent flows as potential enhancements to the EmailPilot orchestration system.

## Overview

LangChain Lab provides experimental capabilities that can be evaluated alongside the existing EmailPilot system. It includes:

1. **RAG Demo**: Document ingestion, vector search, and grounded Q&A with citations
2. **Agent Demo**: Task-oriented agents with tool calling and structured output
3. **Policy Enforcement**: Safety guardrails and resource limits
4. **Evaluation Framework**: Automated assessment of RAG faithfulness and agent performance

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create or update `.env` file with LangChain Lab settings:

```bash
# LLM Configuration
LC_PROVIDER=openai                # openai, anthropic, gemini
LC_MODEL=gpt-4o-mini             # Model name
OPENAI_API_KEY=your_key_here

# Embeddings Configuration  
EMBEDDINGS_PROVIDER=openai        # openai, vertex, sentence-transformers
EMBEDDINGS_MODEL=text-embedding-3-small

# Vector Store
VECTORSTORE=faiss                 # faiss, chroma

# External Services
READONLY_KLAVIYO_BASE_URL=http://localhost:9090
FIRESTORE_PROJECT=emailpilot-438321

# Observability (optional)
ENABLE_TRACING=false
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_langsmith_key
```

### 3. Build RAG Index

```bash
python -m multi-agent.langchain_lab.cli rag.ingest --rebuild
```

### 4. Test RAG

```bash
python -m multi-agent.langchain_lab.cli rag.ask -q "What does EmailPilot orchestrator do?"
```

### 5. Test Agent

```bash
python -m multi-agent.langchain_lab.cli agent.run -t "Fetch top 3 insights from Klaviyo stub and Firestore RO and draft a plan"
```

## Configuration Reference

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LC_PROVIDER` | `openai` | LLM provider (openai/anthropic/gemini) |
| `LC_MODEL` | `gpt-4o-mini` | Model name |
| `EMBEDDINGS_PROVIDER` | `openai` | Embeddings provider |
| `EMBEDDINGS_MODEL` | `text-embedding-3-small` | Embeddings model |
| `VECTORSTORE` | `faiss` | Vector store backend |

### Agent Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MAX_ITERATIONS` | `10` | Max agent iterations |
| `AGENT_TIMEOUT_SECONDS` | `30` | Agent execution timeout |
| `TOOL_CALL_BUDGET` | `15` | Max tool calls per run |

### RAG Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_CHUNK_SIZE` | `1000` | Text chunk size |
| `RAG_CHUNK_OVERLAP` | `200` | Chunk overlap |
| `RAG_K_DOCUMENTS` | `5` | Documents to retrieve |

## CLI Reference

### RAG Commands

#### Document Ingestion
```bash
python -m multi-agent.langchain_lab.cli rag.ingest [options]

Options:
  --rebuild         Rebuild index from scratch
  --source PATH     Additional source directories
```

#### Question Answering
```bash
python -m multi-agent.langchain_lab.cli rag.ask [options]

Options:
  -q, --question TEXT    Question to ask (required)
  -k, --k-documents INT  Number of documents to retrieve (default: 5)
  --max-tokens INT       Maximum response tokens (default: 600)
  --evaluate            Run evaluation on response
```

### Agent Commands

#### Task Execution
```bash
python -m multi-agent.langchain_lab.cli agent.run [options]

Options:
  -t, --task TEXT      Task description (required)
  --timeout INT        Timeout in seconds (default: 30)
  --max-tools INT      Maximum tool calls (default: 15)
```

### Utility Commands

#### Dependency Check
```bash
python -m multi-agent.langchain_lab.cli check
```

## Available Tools

### Agent Tools

1. **klaviyo_api**: Query Klaviyo API stub for campaign and metric data
2. **firestore_read**: Read data from Firestore collections (read-only)
3. **calendar_read**: Read calendar events and campaign schedules
4. **web_fetch**: Fetch content from allowed web URLs (Klaviyo docs, etc.)

### Tool Safety

All tools implement safety measures:
- **Read-only operations**: No database writes or mutations
- **Domain allowlists**: Web fetch limited to trusted domains
- **Collection allowlists**: Firestore access limited to safe collections
- **Rate limiting**: Minimum delays between tool calls
- **PII redaction**: Automatic scrubbing of sensitive data

## Orchestrator Integration

The LangChain Lab can be called from the orchestrator service:

```bash
# From orchestrator_service directory
python -m apps.orchestrator_service.main lc-rag -q "How does calendar planning work?"
python -m apps.orchestrator_service.main lc-agent -t "Draft next steps based on last week's performance"
```

This integration is optional and won't impact existing flows if LangChain Lab is unavailable.

## Directory Structure

```
multi-agent/langchain_lab/
├── __init__.py              # Module exports
├── config.py                # Configuration management
├── deps.py                  # Dependency factories
├── cli.py                   # Command-line interface
├── rag/                     # RAG implementation
│   ├── __init__.py
│   ├── ingest.py           # Document ingestion
│   ├── chain.py            # Q&A chains
│   └── evaluators.py       # Response evaluation
├── agents/                  # Agent implementation
│   ├── __init__.py
│   ├── tools.py            # Tool definitions
│   ├── agent.py            # Agent execution
│   └── policies.py         # Safety policies
├── data/                    # Data storage
│   ├── seed_docs/          # Sample documents
│   └── calendar_sample.json # Sample calendar data
├── tests/                   # Test suite
│   ├── test_rag_chain.py
│   └── test_agent_tools.py
├── artifacts/               # Output artifacts
└── README.md               # This file
```

## Artifacts and Output

All CLI commands save their output to `artifacts/` with timestamps:

- `rag_ingest_YYYYMMDD_HHMMSS.json` - Ingestion statistics
- `rag_ask_YYYYMMDD_HHMMSS.json` - Q&A responses with evaluation
- `agent_run_YYYYMMDD_HHMMSS.json` - Agent execution results

## Development

### Adding New Tools

1. Define tool function in `agents/tools.py`
2. Create Pydantic input schema
3. Add to `get_agent_tools()` function
4. Update allowlists and safety policies as needed

### Adding New Evaluators

1. Create evaluator class in `rag/evaluators.py`
2. Implement scoring methods with LLM judges
3. Add to evaluation pipeline in CLI

### Custom Configurations

Extend configuration classes in `config.py` for new features:

```python
class CustomConfig(LangChainConfig):
    custom_setting: str = Field(default="value", description="Custom setting")
```

## Safety and Compliance

### Data Protection
- All operations are read-only on external systems
- PII is automatically redacted from outputs
- No persistent storage of sensitive data

### Resource Limits
- Tool call budgets prevent runaway execution
- Timeouts ensure bounded execution time
- Rate limiting prevents API abuse

### Content Safety
- Output filtering for inappropriate content
- Citation requirements for factual claims
- Source attribution for all generated content

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Check dependencies
python -m multi-agent.langchain_lab.cli check

# Reinstall if needed
pip install -r requirements.txt
```

#### API Key Issues
```bash
# Verify keys are set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Test with minimal config
LC_PROVIDER=openai LC_MODEL=gpt-3.5-turbo python -m multi-agent.langchain_lab.cli check
```

#### Vector Store Issues
```bash
# Rebuild index
python -m multi-agent.langchain_lab.cli rag.ingest --rebuild

# Check FAISS installation
python -c "import faiss; print('FAISS OK')"
```

#### Firestore Connection
```bash
# Test with explicit project
FIRESTORE_PROJECT=your-project python -m multi-agent.langchain_lab.cli agent.run -t "Test Firestore access"
```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python -m multi-agent.langchain_lab.cli [command]
```

## Roadmap and Future Enhancements

### Planned Features
1. **Advanced RAG**: Multi-modal document support, hybrid search
2. **Agent Workflows**: Multi-agent collaboration, delegation patterns
3. **Evaluation Suite**: Comprehensive benchmarks, A/B testing
4. **Integration Hooks**: Deeper EmailPilot integration, webhook support

### Evaluation Criteria

The module will be promoted to core if it demonstrates:
1. **Performance**: >20% improvement in relevant metrics
2. **Reliability**: <1% failure rate in production scenarios  
3. **Adoption**: Regular use by 3+ team members
4. **Maintenance**: Stable API with backwards compatibility

### Rollback Path

The module can be safely removed by:
1. Removing orchestrator integration calls
2. Deleting `multi-agent/langchain_lab/` directory
3. Removing LangChain dependencies from `requirements.txt`
4. No core application changes required

## Architecture Decision Record

### Context
EmailPilot needs to evaluate LangChain for potential RAG and agent capabilities while maintaining system stability.

### Decision
Implement LangChain features as a sandboxed module with optional integration points.

### Rationale
- **Safety**: Zero impact on core functionality
- **Evaluation**: Real-world testing with production data
- **Flexibility**: Easy to expand or remove based on results
- **Learning**: Team experience with LangChain patterns

### Consequences
- **Positive**: Risk-free evaluation, potential capability enhancement
- **Negative**: Additional dependency management, code maintenance
- **Mitigation**: Strict boundaries, optional integration, clear rollback path

---

For questions or issues, consult the development team or create an issue in the project repository.