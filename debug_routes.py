#!/usr/bin/env python3
"""Debug script to understand route issues"""
import sys
import os

# Suppress logs
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import logging
logging.getLogger().setLevel(logging.ERROR)

from main_firestore import app
import json

# Get all routes
routes = []
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        routes.append({
            "path": route.path,
            "methods": list(route.methods) if route.methods else []
        })

# Sort by path
routes.sort(key=lambda x: x['path'])

# Print routes in JSON format
print(json.dumps(routes, indent=2))

# Summary
api_routes = [r for r in routes if r['path'].startswith('/api/')]
print(f"\n\nTotal routes: {len(routes)}", file=sys.stderr)
print(f"API routes: {len(api_routes)}", file=sys.stderr)

# Check specific routes
test_routes = [
    '/api/mcp/health',
    '/api/calendar/health',
    '/api/agents/campaigns/health',
    '/api/mcp/models'
]

print("\n\nChecking specific routes:", file=sys.stderr)
for test_path in test_routes:
    exists = any(r['path'] == test_path for r in routes)
    print(f"  {test_path}: {'✓ EXISTS' if exists else '✗ NOT FOUND'}", file=sys.stderr)