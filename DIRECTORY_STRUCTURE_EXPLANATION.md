# Directory Structure Explanation

## ✅ Correct Structure: `multi-agent/` (with hyphen)

The **`multi-agent/`** directory (with hyphen) is the correct and only directory for multi-agent systems in EmailPilot.

### Purpose of `multi-agent/` Directory

This is the main directory containing all agent-based systems:

```
emailpilot-app/
└── multi-agent/                    # Main multi-agent systems directory
    ├── apps/                       # Applications
    │   └── orchestrator_service/   # LangGraph-based orchestration
    │       ├── main.py            # CLI and API entry point
    │       ├── graph.py           # Campaign workflow graph
    │       ├── nodes/             # Individual agent nodes
    │       ├── schemas.py         # Data models
    │       └── config.py          # Configuration
    │
    ├── langchain_lab/             # NEW: Sandboxed LangChain evaluation
    │   ├── rag/                   # RAG implementation
    │   ├── agents/                # Agent implementation
    │   ├── config.py              # LangChain configuration
    │   └── cli.py                 # LangChain CLI
    │
    ├── prompts/                    # Shared prompt templates
    ├── ops/                        # Operational scripts
    └── tests/                      # Test suites
```

### Why `multi-agent` with Hyphen?

- **Convention**: Follows directory naming conventions (kebab-case)
- **Clarity**: Clearly indicates multi-agent systems
- **Organization**: Groups all agent-related code together

### Python Import Considerations

Since Python doesn't allow hyphens in module names, when importing from `multi-agent/`:

```python
# Method 1: Add to Python path
import sys
sys.path.append('/path/to/emailpilot-app/multi-agent')
import langchain_lab  # Now you can import directly

# Method 2: Use absolute imports from project root
# When running from emailpilot-app directory:
python -m multi-agent.langchain_lab.cli  # Won't work due to hyphen
```

For CLI usage, we handle this internally:
```bash
# CLI commands work directly
cd multi-agent
python langchain_lab/cli.py rag.ingest

# Or from project root
cd emailpilot-app
python multi-agent/langchain_lab/cli.py rag.ask -q "question"
```

## ❌ Removed: `multi_agent/` (with underscore)

The `multi_agent/` directory was mistakenly created for Python import compatibility but has been removed because:

1. **Duplication**: Created confusion with two similarly named directories
2. **Unnecessary**: The import issue can be handled with proper path management
3. **Not Standard**: The existing `multi-agent/` is the established convention

## Directory Purposes Summary

| Directory | Purpose | Status |
|-----------|---------|--------|
| `multi-agent/` | All multi-agent systems (orchestrator, langchain_lab, etc.) | ✅ Active |
| `multi_agent/` | Was created for imports, now removed | ❌ Deleted |

## Import Best Practices

When working with the `multi-agent/` directory:

1. **For Scripts**: Add to sys.path when needed
   ```python
   import sys
   sys.path.insert(0, '/path/to/multi-agent')
   ```

2. **For CLI**: Run directly as scripts
   ```bash
   python multi-agent/langchain_lab/cli.py [command]
   ```

3. **For Integration**: Use try/except for optional features
   ```python
   try:
       # Attempt import with path management
       sys.path.insert(0, 'multi-agent')
       from langchain_lab import something
   except ImportError:
       # Graceful degradation
       pass
   ```

## Conclusion

The single `multi-agent/` directory (with hyphen) is the correct structure. It contains:
- The existing orchestrator service
- The new LangChain Lab module
- All other agent-related code

No duplicate directories should exist.