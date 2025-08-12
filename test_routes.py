#!/usr/bin/env python3
"""Test script to verify route registration"""
from main_firestore import app

print("Registered routes:")
print("=" * 50)

routes = []
for route in app.routes:
    if hasattr(route, 'path'):
        routes.append(route.path)

# Sort and display routes
for route in sorted(routes):
    print(route)

print("\n" + "=" * 50)
print(f"Total routes: {len(routes)}")