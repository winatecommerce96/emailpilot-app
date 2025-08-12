#!/usr/bin/env python3
"""Extract and organize all routes from the EmailPilot application"""
import os
import sys

# Suppress logging
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import logging
logging.getLogger().setLevel(logging.ERROR)

from main_firestore import app
from collections import defaultdict

# Get all routes
routes_by_module = defaultdict(list)

for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        path = route.path
        methods = list(route.methods) if route.methods else []
        
        # Skip OpenAPI internal routes
        if path in ['/openapi.json', '/docs', '/redoc', '/docs/oauth2-redirect']:
            continue
            
        # Categorize by module
        if path.startswith('/api/agents/admin'):
            module = 'Admin Agent Management'
        elif path.startswith('/api/agents/campaigns'):
            module = 'Email/SMS Campaign Agents'
        elif path.startswith('/api/mcp/klaviyo'):
            module = 'MCP Klaviyo Management'
        elif path.startswith('/api/mcp'):
            module = 'MCP Management'
        elif path.startswith('/api/admin/clients'):
            module = 'Admin Client Management'
        elif path.startswith('/api/admin'):
            module = 'Admin System'
        elif path.startswith('/api/auth'):
            module = 'Authentication'
        elif path.startswith('/api/calendar'):
            module = 'Calendar'
        elif path.startswith('/api/goals'):
            module = 'Goals Management'
        elif path.startswith('/api/performance'):
            module = 'Performance Metrics'
        elif path.startswith('/api/reports'):
            module = 'Reports'
        elif path.startswith('/api/dashboard'):
            module = 'Dashboard'
        elif path.startswith('/api/clients'):
            module = 'Clients (Legacy)'
        elif path.startswith('/api/'):
            module = 'Other API'
        elif path == '/':
            module = 'Root'
        else:
            module = 'Static/Other'
            
        # Format methods
        method_str = ', '.join(sorted(methods))
        routes_by_module[module].append((path, method_str))

# Print organized routes
print("=" * 80)
print("EMAILPILOT API ROUTES - ORGANIZED BY MODULE")
print("=" * 80)
print(f"Base URL: http://127.0.0.1:8000")
print("=" * 80)
print()

# Sort modules for consistent output
module_order = [
    'Root',
    'Authentication',
    'Admin System',
    'Admin Agent Management',
    'Admin Client Management',
    'Email/SMS Campaign Agents',
    'Calendar',
    'Clients (Legacy)',
    'Dashboard',
    'Goals Management',
    'MCP Management',
    'MCP Klaviyo Management',
    'Performance Metrics',
    'Reports',
    'Other API',
    'Static/Other'
]

for module in module_order:
    if module in routes_by_module:
        routes = sorted(routes_by_module[module])
        print(f"\n## {module}")
        print("-" * 60)
        for path, methods in routes:
            # Format the output nicely
            if methods:
                print(f"  {methods:7} → {path}")
            else:
                print(f"         → {path}")

# Print summary
print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
total_routes = sum(len(routes) for routes in routes_by_module.values())
print(f"Total Routes: {total_routes}")
print(f"Modules: {len(routes_by_module)}")
print()
print("Key Naming Conventions:")
print("  • /api/agents/admin/*     - Admin agent management")
print("  • /api/agents/campaigns/* - Email/SMS campaign agents")
print("  • /api/mcp/*              - Model Configuration Platform")
print("  • /api/mcp/klaviyo/*      - Klaviyo-specific MCP")
print("  • /api/admin/*            - Admin system endpoints")
print("  • /api/calendar/*         - Calendar functionality")
print("  • /api/goals/*            - Goals management")
print("  • /api/performance/*      - Performance metrics")
print("  • /api/reports/*          - Report generation")
print("  • /api/dashboard/*        - Dashboard views")
print("=" * 80)