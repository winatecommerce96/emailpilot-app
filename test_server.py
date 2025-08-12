#!/usr/bin/env python3
"""Minimal test server to verify routing"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Import the app
from main_firestore import app

# Test a specific endpoint
@app.get("/test/routing")
async def test_routing():
    return {"message": "Test routing works!", "routes_count": len(app.routes)}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Starting test server...")
    print("="*50)
    
    # Print some key routes for verification
    print("\nKey routes registered:")
    for route in app.routes:
        if hasattr(route, 'path') and '/api/' in route.path:
            print(f"  {route.path}")
            if len([r for r in app.routes if hasattr(r, 'path') and '/api/' in r.path]) > 20:
                print("  ... (truncated)")
                break
    
    print("\n" + "="*50)
    print(f"Total routes: {len(app.routes)}")
    print("="*50 + "\n")
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8080)