#!/bin/bash

export PYTHONPATH=.
export LITELLM_MASTER_KEY="$(openssl rand -hex 16)"
export ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY_HERE"

# Start the application
echo "Starting EmailPilot API..."
uvicorn main_firestore:app --host 0.0.0.0 --port 8000