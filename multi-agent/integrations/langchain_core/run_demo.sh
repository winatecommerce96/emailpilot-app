#!/bin/bash
# Demo script showing LangChain Core integration with Secret Manager

echo "=========================================="
echo "LangChain Core Demo with Secret Manager"
echo "=========================================="
echo

# Export environment variables
export GOOGLE_CLOUD_PROJECT=emailpilot-438321
export USE_SECRET_MANAGER=true
export LC_PROVIDER=gemini
export LC_MODEL=gemini-1.5-flash
export EMBEDDINGS_PROVIDER=local

echo "Configuration:"
echo "  - Provider: $LC_PROVIDER"
echo "  - Model: $LC_MODEL"
echo "  - Embeddings: $EMBEDDINGS_PROVIDER"
echo "  - Secret Manager: Enabled"
echo

echo "1. Testing RAG System"
echo "===================="
python -m "multi-agent.integrations.langchain_core.cli" rag.ask \
    -q "What does the orchestrator do?" \
    --show-sources

echo
echo "2. Testing Agent System"
echo "======================="
python -m "multi-agent.integrations.langchain_core.cli" agent.run \
    -t "What are the main features of EmailPilot?"

echo
echo "3. Testing with Different Provider"
echo "==================================="
LC_PROVIDER=anthropic LC_MODEL=claude-3-haiku-20240307 \
python -m "multi-agent.integrations.langchain_core.cli" rag.ask \
    -q "How does the calendar integration work?"

echo
echo "Demo complete!"