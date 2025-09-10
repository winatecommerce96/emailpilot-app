#!/usr/bin/env python3
"""Test the NL API to find the error"""
import asyncio
import sys
sys.path.insert(0, '/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app')

from fastapi.testclient import TestClient
from main_firestore import app

client = TestClient(app)

def test_nl_api():
    """Test the natural language API"""
    response = client.post("/api/mcp/nl/query", json={
        "query": "Show me all campaigns",
        "client_id": "christopher-bean-coffee"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code != 200:
        # Try to get more details
        print("\n--- Full Error Details ---")
        print(response.text)

if __name__ == "__main__":
    test_nl_api()