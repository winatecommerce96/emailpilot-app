# ARCHIVED: AI Orchestrator Documentation

**⚠️ DEPRECATED**: This system has been replaced by LangChain integration as of 2025-08-20.

## Overview
The AI Orchestrator was the previous centralized interface for all AI API calls in EmailPilot. It has been replaced by the LangChain multi-agent system which provides better tool integration via MCP (Model Context Protocol) and more robust agent orchestration capabilities.

## Migration Status
- **Disabled in**: `main_firestore.py` (router commented out)
- **Replaced by**: LangChain integration in `multi-agent/` directory
- **Migration date**: 2025-08-20

## Why Replaced
1. **Limited tool integration** - AI Orchestrator couldn't easily integrate with external tools
2. **No MCP support** - Couldn't leverage Model Context Protocol for deterministic operations
3. **Complex fallback logic** - LangChain provides better provider management
4. **Lack of RAG** - No built-in retrieval augmented generation capabilities

## New System Benefits
- ✅ MCP integration for Klaviyo data retrieval
- ✅ Multi-agent orchestration with specialized roles
- ✅ RAG capabilities for document-based Q&A
- ✅ Better error handling and fallbacks
- ✅ Production-tested with real client data

## Migration Guide
If you need to migrate code from the old AI Orchestrator to LangChain:

### Old Way (AI Orchestrator)
```python
from app.api.ai_orchestrator import router as ai_orchestrator_router

# API call
response = await ai_orchestrator.complete(
    messages=[{"role": "user", "content": "Hello"}],
    provider="auto",
    model_tier="standard"
)
```

### New Way (LangChain)
```python
from multi_agent.integrations.langchain_core.deps import get_llm
from multi_agent.integrations.langchain_core.config import get_config

config = get_config()
llm = get_llm(config)

# Direct LLM call
response = llm.invoke("Hello")

# Or with MCP tools for data
from services.klaviyo_revenue_api import get_revenue_data
data = get_revenue_data("rogue-creamery", "last_7_days")
analysis = llm.invoke(f"Analyze this data: {data}")
```

## Archived Files
The following files are part of the deprecated AI Orchestrator system:
- `app/api/ai_orchestrator.py` (disabled)
- `app/core/ai_orchestrator.py` (deprecated)
- `docs/AI_ORCHESTRATOR_MIGRATION_GUIDE.md` (obsolete)

## Support
For questions about the new LangChain system, see:
- [LANGCHAIN_INTEGRATION_SUMMARY.md](../LANGCHAIN_INTEGRATION_SUMMARY.md)
- [ROGUE_CREAMERY_SUCCESS.md](../ROGUE_CREAMERY_SUCCESS.md)

---
*This documentation is archived for historical reference only. Do not use the AI Orchestrator system for new development.*