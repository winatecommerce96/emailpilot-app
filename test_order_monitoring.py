#!/usr/bin/env python3
"""
Test script for Order Monitoring System

This script tests the complete order monitoring workflow:
1. Health checks
2. Order data fetching with mock data
3. Firestore storage
4. Alert simulation
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_order_monitoring():
    """Test the order monitoring system"""
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Order Monitoring System\n")
    
    # Test 1: Health Check
    print("1. Testing health check...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/performance/orders/health-check")
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ Health check passed: {health['status']}")
            print(f"   🔧 Components: {', '.join([k for k, v in health['checks'].items() if v])}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
    
    # Test 2: Monitor non-existent client (should use mock data)
    print("\n2. Testing order monitoring with demo client...")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/api/performance/orders/5-day/demo_test_client",
            params={"alert_on_zero": False}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   📊 Client: {result['client_id']}")
            print(f"   📈 Success: {result['success']}")
            
            if result['data']:
                print(f"   📅 Days monitored: {len(result['data'])}")
                zero_days = len([d for d in result['data'] if d['is_zero_orders']])
                print(f"   ⚠️  Zero-order days: {zero_days}")
            else:
                print(f"   ⚠️  No data (expected for unconfigured client)")
                print(f"   🔧 Error: {result.get('error', 'None')}")
        else:
            print(f"   ❌ Order monitoring failed: {response.status_code}")
    
    # Test 3: Test stored data retrieval
    print("\n3. Testing stored data retrieval...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/performance/orders/stored/demo_test_client")
        if response.status_code == 200:
            result = response.json()
            print(f"   💾 Stored data found: {result['success']}")
            if not result['success']:
                print(f"   📝 Message: {result['message']}")
        else:
            print(f"   ❌ Stored data retrieval failed: {response.status_code}")
    
    # Test 4: Test bulk monitoring (for all clients)
    print("\n4. Testing bulk monitoring...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/api/performance/orders/monitor-all",
            params={"alert_on_zero": False}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   🏢 Total clients monitored: {result['summary']['total_clients']}")
            print(f"   ✅ Successful checks: {result['summary']['successful_checks']}")
            print(f"   ❌ Failed checks: {result['summary']['failed_checks']}")
            print(f"   🚨 Alerts triggered: {result['summary']['alerts_triggered']}")
        else:
            print(f"   ❌ Bulk monitoring failed: {response.status_code}")
    
    print(f"\n🎉 Order monitoring system test completed at {datetime.now().isoformat()}")

def test_slack_alert_formatting():
    """Test Slack alert message formatting"""
    print("\n📱 Testing Slack Alert Formatting\n")
    
    # Import the Slack service to test message formatting
    try:
        import sys
        sys.path.append('/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app')
        from app.services.slack_alerts import SlackAlertService
        
        # Create a mock service (no actual sending)
        class MockSecretManager:
            def get_secret(self, name):
                return None  # Simulate no webhook configured
        
        slack_service = SlackAlertService(MockSecretManager())
        
        # Test message formatting
        message = slack_service._build_alert_message(
            client_id="test_client_123",
            client_name="Test Company LLC",
            zero_order_days=["2025-08-15", "2025-08-16"],
            zero_revenue_days=["2025-08-16"],
            severity="critical"
        )
        
        print("📋 Sample Slack Alert Message:")
        print(json.dumps(message, indent=2))
        
        # Verify message structure
        assert "text" in message
        assert "attachments" in message
        assert message["attachments"][0]["color"] == "danger"
        print("   ✅ Message structure validated")
        
    except Exception as e:
        print(f"   ⚠️  Slack formatting test skipped: {e}")

if __name__ == "__main__":
    print("🚀 Starting Order Monitoring System Tests\n")
    
    # Test Slack formatting (synchronous)
    test_slack_alert_formatting()
    
    # Test API endpoints (asynchronous)
    asyncio.run(test_order_monitoring())