#!/bin/bash

# Test saving OPENAI_API_KEY via admin API
# This script demonstrates how to save the OpenAI API key

echo "Testing OPENAI_API_KEY save functionality..."
echo "=========================================="

# You would replace this with your actual API key
TEST_KEY="sk-test-key-example"

# Make the API call to save the key
curl -X POST "http://127.0.0.1:8000/api/admin/environment" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "OPENAI_API_KEY",
    "value": "'"$TEST_KEY"'"
  }' | python -m json.tool

echo ""
echo "If you see a success message above, the key has been saved!"
echo "The key will be stored in Google Secret Manager as: emailpilot-openai-api-key"
echo ""
echo "To use a real key:"
echo "1. Replace TEST_KEY with your actual OpenAI API key"
echo "2. Run this script again"
echo "3. Or use the Admin Dashboard UI to set it"