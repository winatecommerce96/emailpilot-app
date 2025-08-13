#!/usr/bin/env python3
"""
Test script for the new Campaign Planning API endpoint
"""

import requests
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
CALENDAR_API_URL = f"{BASE_URL}/api/calendar"

def test_endpoint_availability():
    """Test if the calendar API is available"""
    try:
        response = requests.get(f"{CALENDAR_API_URL}/health", timeout=10)
        if response.status_code == 200:
            logger.info("✅ Calendar API health check passed")
            return True
        else:
            logger.error(f"❌ Calendar API health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Cannot reach calendar API: {e}")
        return False

def test_campaign_planning():
    """Test the new campaign planning endpoint"""
    
    # Test data
    test_campaign = {
        "client_id": "test-client-001",
        "campaign_type": "Limited Time Offer",
        "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "promotion_details": "Summer Flash Sale - 30% off all products. Features best-selling items with urgency messaging."
    }
    
    try:
        logger.info("🚀 Testing campaign planning endpoint...")
        logger.info(f"Request data: {json.dumps(test_campaign, indent=2)}")
        
        response = requests.post(
            f"{CALENDAR_API_URL}/plan-campaign",
            json=test_campaign,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ Campaign planning succeeded!")
            logger.info(f"Campaign Plan: {result['campaign_plan']}")
            logger.info(f"Total Events Created: {result['total_events']}")
            logger.info(f"Touchpoint Breakdown: {result['touchpoints']}")
            
            # Log created events
            for i, event in enumerate(result['events_created'], 1):
                logger.info(f"Event {i}: {event['title']} on {event['date']} ({event['event_type']})")
            
            return True
        else:
            logger.error(f"❌ Campaign planning failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing campaign planning: {e}")
        return False

def test_get_events():
    """Test fetching the created events"""
    try:
        logger.info("📅 Testing event retrieval...")
        
        response = requests.get(
            f"{CALENDAR_API_URL}/events",
            params={"client_id": "test-client-001"},
            timeout=10
        )
        
        if response.status_code == 200:
            events = response.json()
            logger.info(f"✅ Found {len(events)} events for test client")
            
            # Show AI-generated events
            ai_events = [e for e in events if e.get('generated_by_ai')]
            logger.info(f"🤖 AI-generated events: {len(ai_events)}")
            
            return True
        else:
            logger.error(f"❌ Failed to fetch events: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing event retrieval: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Starting Campaign Planning API Tests")
    logger.info("=" * 50)
    
    # Test 1: API availability
    if not test_endpoint_availability():
        logger.error("❌ API not available. Make sure the server is running:")
        logger.error("   uvicorn main_firestore:app --port 8000")
        return False
    
    # Test 2: Campaign planning
    if not test_campaign_planning():
        logger.error("❌ Campaign planning test failed")
        return False
    
    # Test 3: Event retrieval
    if not test_get_events():
        logger.error("❌ Event retrieval test failed")
        return False
    
    logger.info("=" * 50)
    logger.info("🎉 All tests passed! Campaign Planning API is working correctly.")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)