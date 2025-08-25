#!/usr/bin/env python3
"""
Direct test of the Klaviyo OAuth router
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import sys
import os

# Add the app directory to path
sys.path.insert(0, '/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app')
os.chdir('/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app')

# Create a test app
app = FastAPI()

# Try to import and mount the router
try:
    from app.api.integrations.klaviyo_oauth import router as klaviyo_oauth_router
    app.include_router(klaviyo_oauth_router, prefix="/api/integrations/klaviyo")
    print("✓ Router imported and mounted successfully")
except ImportError as e:
    print(f"✗ Failed to import router: {e}")
    klaviyo_oauth_router = None

# Create test client
client = TestClient(app)

# Test the endpoints
print("\nTesting endpoints:")
print("-" * 50)

endpoints = [
    "/api/integrations/klaviyo/test",
    "/api/integrations/klaviyo/oauth/start-simple"
]

for endpoint in endpoints:
    response = client.get(endpoint, follow_redirects=False)
    print(f"{endpoint}: {response.status_code}")
    if response.status_code == 200:
        print(f"  Response: {response.json()}")
    elif response.status_code in [302, 307]:
        print(f"  Redirect to: {response.headers.get('location', 'N/A')}")

# List all routes
print("\nAll registered routes:")
print("-" * 50)
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"  {route.methods} {route.path}")