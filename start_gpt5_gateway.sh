#!/bin/bash
# start_gpt5_gateway.sh
# This script starts LiteLLM with a fixed port so the URL is always predictable.

# Exit on error
set -e

# Set fixed port
PORT=4000

echo "🚀 Starting LiteLLM GPT-5 Gateway on http://localhost:$PORT ..."
litellm --config config/gpt5/litellm.yaml --port $PORT
