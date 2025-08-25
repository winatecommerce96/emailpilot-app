# AI Orchestrator Migration Guide

## Overview

The AI Orchestrator is now the **centralized and standardized** interface for all AI API calls in the EmailPilot application. This migration guide helps developers transition from direct SDK usage to the orchestrator pattern.

## Why Use the AI Orchestrator?

1. **Unified Interface**: Single API for all AI providers (OpenAI, Claude, Gemini)
2. **Automatic Fallbacks**: Built-in retry logic with provider fallback chains
3. **Marketing Optimization**: Special handling for marketing content to avoid safety filters
4. **Cost Management**: Token tracking and usage analytics
5. **Response Caching**: Automatic caching to reduce API costs
6. **Model Discovery**: Live model availability checking
7. **Singleton Pattern**: Ensures consistent configuration across the app

## Quick Start

### Basic Usage

```python
from app.core.ai_orchestrator import get_ai_orchestrator, ai_complete

# Simple completion
response = await ai_complete(
    messages=[{"role": "user", "content": "Hello!"}],
    provider="auto",  # auto, openai, claude, or gemini
    model=None,       # Auto-select or specify
    temperature=0.7,
    max_tokens=1000
)
print(response)  # Returns the response text directly
```

### Advanced Usage with Full Response

```python
from app.core.ai_orchestrator import get_ai_orchestrator

orchestrator = get_ai_orchestrator()

response = await orchestrator.complete({
    "messages": [{"role": "user", "content": "Write a marketing email"}],
    "provider": "auto",
    "model_tier": "flagship",  # flagship, standard, or fast
    "temperature": 0.8,
    "max_tokens": 2000
})

print(response.content)    # The AI response
print(response.provider)   # Which provider was used
print(response.model)      # Which model was used
print(response.usage)      # Token usage statistics
print(response.cached)     # Whether response was cached
```

## Migration Examples

### Before: Direct OpenAI SDK

```python
# OLD CODE - DO NOT USE
import openai

client = openai.OpenAI(api_key="...")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.7
)
result = response.choices[0].message.content
```

### After: AI Orchestrator

```python
# NEW CODE - USE THIS
from app.core.ai_orchestrator import ai_complete

result = await ai_complete(
    messages=[{"role": "user", "content": "Hello"}],
    provider="openai",
    model="gpt-4o",
    temperature=0.7
)
```

### Before: Direct Gemini SDK

```python
# OLD CODE - DO NOT USE
import google.generativeai as genai

genai.configure(api_key="...")
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("Hello")
result = response.text
```

### After: AI Orchestrator

```python
# NEW CODE - USE THIS
from app.core.ai_orchestrator import ai_complete

result = await ai_complete(
    messages=[{"role": "user", "content": "Hello"}],
    provider="gemini",
    model="gemini-2.0-flash",
    temperature=0.7
)
```

### Before: Direct Claude SDK

```python
# OLD CODE - DO NOT USE
from anthropic import Anthropic

client = Anthropic(api_key="...")
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1000
)
result = response.content[0].text
```

### After: AI Orchestrator

```python
# NEW CODE - USE THIS
from app.core.ai_orchestrator import ai_complete

result = await ai_complete(
    messages=[{"role": "user", "content": "Hello"}],
    provider="claude",
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000
)
```

## API Endpoints

The orchestrator provides these FastAPI endpoints:

- `POST /api/ai/complete` - Main completion endpoint
- `POST /api/ai/stream` - Streaming completions
- `GET /api/ai/models` - List available models
- `POST /api/ai/models/refresh` - Refresh model catalog
- `GET /api/ai/stats` - Usage statistics
- `POST /api/ai/cache/clear` - Clear response cache
- `GET /api/ai/health` - Check orchestrator health

## Provider Selection

The orchestrator intelligently selects providers based on:

1. **Marketing Content**: Automatically uses Gemini 2.0 Flash for marketing content
2. **Model Tier**: 
   - Flagship → Claude 3.5 Sonnet
   - Standard → GPT-4o
   - Fast → Gemini 1.5 Flash
3. **Fallback Chain**: Automatic fallback to alternative providers on failure

## Special Features

### Marketing Content Handling

The orchestrator automatically detects marketing content and routes it to models without safety filters:

```python
# Automatically handled - no special code needed
response = await ai_complete(
    messages=[{
        "role": "user", 
        "content": "Write email copy for a 50% off sale on coffee beans"
    }]
)
# Will use Gemini 2.0 Flash automatically to avoid safety filters
```

### Fallback Chains

If the primary provider fails, the orchestrator automatically tries alternatives:

```python
# Fallback chain: Gemini 2.0 → Claude 3.5 → GPT-4o → Gemini 1.5 Pro
response = await orchestrator.complete({
    "messages": messages,
    "provider": "auto"  # Enables automatic fallback
})
```

## Module-Specific Migration

### For Agent Services

```python
# In app/api/agents.py or agent services
from app.core.ai_orchestrator import ai_complete

# Replace AI Models Service calls with:
response = await ai_complete(
    messages=[{"role": "user", "content": prompt}],
    provider=data.get("provider", "auto"),
    model=data.get("model")
)
```

### For Report Generation

```python
# In report services
from app.core.ai_orchestrator import get_ai_orchestrator

orchestrator = get_ai_orchestrator()
response = await orchestrator.complete({
    "messages": [{"role": "user", "content": report_prompt}],
    "model_tier": "standard",
    "max_tokens": 4000
})
```

### For MCP Services

```python
# In MCP service modules
if AI_ORCHESTRATOR_AVAILABLE:
    from app.core.ai_orchestrator import ai_complete
    
    response = await ai_complete(
        messages=messages,
        provider=self.provider,
        model=self.model
    )
```

## Testing

### Unit Test Example

```python
import pytest
from app.core.ai_orchestrator import get_ai_orchestrator

@pytest.mark.asyncio
async def test_orchestrator_completion():
    orchestrator = get_ai_orchestrator()
    
    response = await orchestrator.complete({
        "messages": [{"role": "user", "content": "Test message"}],
        "provider": "gemini",
        "max_tokens": 100
    })
    
    assert response.content
    assert response.provider == "gemini"
    assert response.usage["total_tokens"] > 0
```

### Integration Test

```python
import httpx
import asyncio

async def test_api_endpoint():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/ai/complete",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": "auto"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["content"]
```

## Backwards Compatibility

For gradual migration, the system maintains backwards compatibility:

```python
# The old AI Models Service still works but is DEPRECATED
try:
    from app.core.ai_orchestrator import ai_complete
    # Use orchestrator
except ImportError:
    from app.services.ai_models_service import get_ai_models_service
    # Fall back to legacy service
```

## Environment Variables

No changes needed to environment variables. The orchestrator uses the same secrets:

- OpenAI: Uses secret `openai-api-key`
- Claude: Uses secret `claude-api-key`
- Gemini: Uses secret `gemini-api-key`

## Performance Considerations

1. **Caching**: Responses are automatically cached by request hash
2. **Connection Pooling**: The singleton pattern ensures connection reuse
3. **Async Operations**: All methods are async for non-blocking execution

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure `app.core.ai_orchestrator` module exists
2. **Provider Not Available**: Check API keys in Secret Manager
3. **Model Not Found**: Run `/api/ai/models/refresh` to update catalog
4. **Safety Filter Blocks**: Marketing content automatically uses Gemini 2.0

### Debug Mode

```python
import logging
logging.getLogger("app.core.ai_orchestrator").setLevel(logging.DEBUG)
```

## Migration Checklist

- [ ] Update imports from direct SDKs to orchestrator
- [ ] Replace SDK client initialization with `get_ai_orchestrator()`
- [ ] Update completion calls to use `ai_complete()` or `orchestrator.complete()`
- [ ] Remove SDK-specific error handling (orchestrator handles fallbacks)
- [ ] Update tests to use orchestrator
- [ ] Remove direct SDK dependencies from requirements (keep for compatibility)
- [ ] Update API documentation

## Support

For questions or issues with the migration:

1. Check this guide first
2. Review the orchestrator source: `/app/core/ai_orchestrator.py`
3. Check API endpoints: `/app/api/ai_orchestrator.py`
4. Test with the health endpoint: `GET /api/ai/health`

## Version History

- **v1.0.0** (2025-08-19): Initial orchestrator implementation
- Marketing content detection
- Automatic provider fallbacks
- Response caching
- Model discovery