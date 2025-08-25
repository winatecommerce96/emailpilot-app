#!/usr/bin/env python3
"""
Mock MCP Server for Calendar Automation Testing
Simulates Klaviyo MCP responses for development and testing
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import uvicorn
import json
from datetime import datetime, timedelta
import random

app = FastAPI(title="Mock Klaviyo MCP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample campaign data generator
def generate_sample_campaigns(start_date: str, end_date: str, count: int = 10) -> List[Dict[str, Any]]:
    """Generate realistic sample campaign data"""
    campaigns = []
    
    campaign_types = [
        "Cheese Club Monthly Selection",
        "RRB Flash Sale",
        "SMS Weekend Alert", 
        "Nurturing Newsletter",
        "Re-engagement Campaign",
        "Product Launch",
        "Seasonal Promotion"
    ]
    
    base_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    end_date_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    for i in range(count):
        # Random date within range
        days_diff = (end_date_dt - base_date).days
        random_days = random.randint(0, max(1, days_diff))
        campaign_date = base_date + timedelta(days=random_days)
        
        # Random performance metrics
        sends = random.randint(500, 5000)
        delivered = int(sends * random.uniform(0.95, 0.99))
        open_rate = random.uniform(0.15, 0.35)
        click_rate = random.uniform(0.02, 0.08)
        orders = int(sends * random.uniform(0.01, 0.05))
        avg_order_value = random.uniform(25, 150)
        revenue = orders * avg_order_value
        
        campaign = {
            "id": f"camp_{i:04d}_{int(campaign_date.timestamp())}",
            "name": f"{random.choice(campaign_types)} {campaign_date.strftime('%B %d')}",
            "send_time": campaign_date.isoformat() + "Z",
            "type": "sms" if "SMS" in campaign_types[i % len(campaign_types)] else "email",
            "sent_count": sends,
            "delivered_count": delivered,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "conversions": orders,
            "revenue": revenue,
            "rpr": revenue / sends if sends > 0 else 0,
            "unsubscribe_count": random.randint(0, int(sends * 0.005)),
            "spam_count": random.randint(0, int(sends * 0.001))
        }
        
        campaigns.append(campaign)
    
    return campaigns

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mock_klaviyo_mcp",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/campaigns")
async def get_campaigns(
    klaviyo_account_id: str,
    start_date: str,
    end_date: str,
    page: int = 1,
    limit: int = 50
):
    """Get campaigns for date range with pagination"""
    
    # Simulate different account behaviors
    if klaviyo_account_id == "test_klaviyo_e2e":
        # Test account with good data
        campaigns = generate_sample_campaigns(start_date, end_date, min(limit, 15))
    elif klaviyo_account_id == "demo_account":
        # Demo account with sparse data
        campaigns = generate_sample_campaigns(start_date, end_date, min(limit, 5))
    else:
        # Unknown account, return empty
        campaigns = []
    
    # Simulate pagination
    total_campaigns = len(campaigns)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_campaigns = campaigns[start_idx:end_idx]
    
    return {
        "campaigns": page_campaigns,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_campaigns,
            "has_more": end_idx < total_campaigns
        },
        "metadata": {
            "account_id": klaviyo_account_id,
            "date_range": f"{start_date} to {end_date}",
            "generated_at": datetime.utcnow().isoformat()
        }
    }

@app.get("/metrics")
async def get_metrics(
    klaviyo_account_id: str,
    metric_ids: str = None,
    start_date: str = None,
    end_date: str = None
):
    """Get campaign metrics"""
    
    # Mock metrics response
    metrics = {
        "account_id": klaviyo_account_id,
        "metrics": [
            {
                "metric_id": "revenue",
                "value": random.uniform(5000, 25000),
                "period": f"{start_date} to {end_date}"
            },
            {
                "metric_id": "orders",
                "value": random.randint(50, 500),
                "period": f"{start_date} to {end_date}"
            },
            {
                "metric_id": "avg_order_value",
                "value": random.uniform(75, 125),
                "period": f"{start_date} to {end_date}"
            }
        ],
        "generated_at": datetime.utcnow().isoformat()
    }
    
    return metrics

@app.post("/simulate-delay")
async def simulate_processing_delay():
    """Simulate a processing delay (returns 202)"""
    import asyncio
    await asyncio.sleep(1)
    return {"status": "processing", "estimated_completion": "30 seconds"}

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Mock Klaviyo MCP Server",
        "version": "1.0.0",
        "description": "Mock server for testing EmailPilot calendar automation",
        "endpoints": {
            "health": "/health",
            "campaigns": "/campaigns",
            "metrics": "/metrics"
        },
        "test_accounts": {
            "test_klaviyo_e2e": "Full test data",
            "demo_account": "Limited demo data"
        }
    }

if __name__ == "__main__":
    print("🔧 Starting Mock Klaviyo MCP Server on port 8090")
    print("📊 This server simulates Klaviyo API responses for calendar automation testing")
    print("🔗 Test it at: http://localhost:8090/campaigns?klaviyo_account_id=test_klaviyo_e2e&start_date=2024-01-01&end_date=2024-01-31")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8090,
        log_level="info"
    )