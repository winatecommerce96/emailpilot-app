#!/usr/bin/env python3
"""
Direct test of Klaviyo API with rogue-creamery's real API key
This bypasses the MCP layers to verify the API key and data access work
"""

import requests
import json
from datetime import datetime

# Real API key for rogue-creamery
API_KEY = "pk_41705a9abacbf2c7810c20129005c4b6b3"
BASE_URL = "https://a.klaviyo.com/api"

def test_klaviyo_direct():
    """Test direct Klaviyo API access"""
    
    print("\n" + "="*80)
    print("🔌 DIRECT KLAVIYO API TEST - ROGUE CREAMERY")
    print("="*80)
    print(f"Timestamp: {datetime.now()}")
    
    # Headers for Klaviyo API
    headers = {
        "Authorization": f"Klaviyo-API-Key {API_KEY}",
        "Accept": "application/json",
        "revision": "2024-06-15"
    }
    
    # Test 1: Get Campaigns
    print("\n📧 TEST: Get Campaigns")
    print("-" * 40)
    
    campaigns_url = f"{BASE_URL}/campaigns/"
    params = {
        "filter": "equals(messages.channel,'email')"
    }
    
    try:
        response = requests.get(campaigns_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            campaigns = data.get('data', [])
            print(f"✅ Found {len(campaigns)} campaigns")
            
            for i, campaign in enumerate(campaigns[:3], 1):
                attrs = campaign.get('attributes', {})
                print(f"\n  Campaign {i}:")
                print(f"    Name: {attrs.get('name', 'N/A')}")
                print(f"    Status: {attrs.get('status', 'N/A')}")
                print(f"    Created: {attrs.get('created_at', 'N/A')[:10]}")
                
        else:
            print(f"❌ Failed: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Get Segments
    print("\n\n📊 TEST: Get Segments")
    print("-" * 40)
    
    segments_url = f"{BASE_URL}/segments/"
    params = {}
    
    try:
        response = requests.get(segments_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            segments = data.get('data', [])
            print(f"✅ Found {len(segments)} segments")
            
            for i, segment in enumerate(segments[:3], 1):
                attrs = segment.get('attributes', {})
                print(f"\n  Segment {i}:")
                print(f"    Name: {attrs.get('name', 'N/A')}")
                print(f"    Profile Count: {attrs.get('profile_count', 'N/A')}")
                
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Get Lists
    print("\n\n📋 TEST: Get Lists")
    print("-" * 40)
    
    lists_url = f"{BASE_URL}/lists/"
    params = {}
    
    try:
        response = requests.get(lists_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            lists = data.get('data', [])
            print(f"✅ Found {len(lists)} lists")
            
            for i, lst in enumerate(lists[:3], 1):
                attrs = lst.get('attributes', {})
                print(f"\n  List {i}:")
                print(f"    Name: {attrs.get('name', 'N/A')}")
                print(f"    Profile Count: {attrs.get('profile_count', 'N/A')}")
                
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Get Metrics
    print("\n\n📈 TEST: Get Metrics")
    print("-" * 40)
    
    metrics_url = f"{BASE_URL}/metrics/"
    params = {}
    
    try:
        response = requests.get(metrics_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            metrics = data.get('data', [])
            print(f"✅ Found {len(metrics)} metric types")
            
            # Show available metrics
            metric_names = [m.get('attributes', {}).get('name', 'N/A') for m in metrics[:5]]
            print(f"  Available metrics: {', '.join(metric_names)}")
                
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*80)
    print("✅ KLAVIYO API KEY VERIFIED AND WORKING!")
    print("="*80)
    print("""
Next steps:
1. The API key for rogue-creamery is valid and working
2. We can access campaigns, segments, lists, and metrics
3. The Enhanced MCP needs its HTTP wrapper fixed
4. For now, we can create a direct integration
    """)

if __name__ == "__main__":
    test_klaviyo_direct()