#!/usr/bin/env python3
"""
Test script to verify the copywriting module integration
Tests that campaign brief + client context + model selection work together
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_copywriting_flow():
    """Test the complete flow with brief, client, and model"""
    base_url = "http://localhost:8002"
    
    print("=" * 60)
    print("COPYWRITING MODULE INTEGRATION TEST")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health check
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Test 2: Fetch models
        print("\n2. Testing model fetching...")
        try:
            response = await client.get(f"{base_url}/api/models")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"✅ Found {len(models)} models")
                if models:
                    print(f"   Available models: {', '.join([m['name'] for m in models[:3]])}")
                    selected_model = models[0]["id"]
                else:
                    selected_model = "claude-3-haiku"
                    print("   Using fallback model")
            else:
                print(f"❌ Model fetch failed: {response.status_code}")
                selected_model = "claude-3-haiku"
        except Exception as e:
            print(f"❌ Model fetch error: {e}")
            selected_model = "claude-3-haiku"
        
        # Test 3: Fetch agents
        print("\n3. Testing agent fetching...")
        selected_agents = []
        try:
            response = await client.get(f"{base_url}/api/agents")
            if response.status_code == 200:
                data = response.json()
                agents = data.get("agents", [])
                print(f"✅ Found {len(agents)} agents")
                if agents:
                    # Select first 2 agents
                    selected_agents = [a["id"] for a in agents[:2]]
                    print(f"   Selected agents: {selected_agents}")
            else:
                print(f"⚠️  Agent fetch returned: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Agent fetch error: {e}")
        
        # Test 4: Fetch clients
        print("\n4. Testing client fetching...")
        client_id = "test-client"
        client_name = "Test Client"
        try:
            response = await client.get(f"{base_url}/api/clients")
            if response.status_code == 200:
                data = response.json()
                clients = data.get("clients", [])
                if clients:
                    client_id = clients[0]["id"]
                    client_name = clients[0]["name"]
                    print(f"✅ Using client: {client_name}")
                else:
                    print("⚠️  No clients found, using test client")
            else:
                print(f"⚠️  Client fetch returned: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Client fetch error: {e}")
        
        # Test 5: Generate copy with full context
        print("\n5. Testing copy generation with full context...")
        print(f"   Model: {selected_model}")
        print(f"   Client: {client_name}")
        print(f"   Agents: {len(selected_agents)} selected")
        
        campaign_brief = """
        Create an email campaign for our Summer Sale event.
        - 30% off all products
        - Free shipping on orders over $50
        - Limited time: July 15-20
        - Target audience: Existing customers and newsletter subscribers
        - Goal: Drive sales and clear summer inventory
        - Tone: Exciting but not overly pushy
        - Include urgency without being aggressive
        """
        
        payload = {
            "brief_content": campaign_brief,
            "client_id": client_id,
            "client_name": client_name,
            "campaign_type": "email",
            "selected_agents": selected_agents,
            "selected_model": selected_model
        }
        
        print("\n   Sending request...")
        print(f"   Brief preview: {campaign_brief[:100]}...")
        
        try:
            response = await client.post(
                f"{base_url}/api/generate-copy",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Copy generation successful!")
                print(f"   Client: {data.get('client_name', 'Unknown')}")
                print(f"   Variants generated: {len(data.get('variants', []))}")
                
                # Check if variants include the brief content
                if data.get("variants"):
                    variant = data["variants"][0]
                    
                    # Check if content reflects the brief
                    brief_keywords = ["summer", "sale", "30%", "shipping"]
                    content_check = any(
                        keyword.lower() in str(variant).lower() 
                        for keyword in brief_keywords
                    )
                    
                    if content_check:
                        print(f"   ✅ Content reflects campaign brief")
                    else:
                        print(f"   ⚠️  Content may not reflect brief fully")
                    
                    # Check for full body content
                    if variant.get("full_email_body") and len(variant["full_email_body"]) > 100:
                        print(f"   ✅ Full email body generated ({len(variant['full_email_body'])} chars)")
                    else:
                        print(f"   ⚠️  Full email body missing or too short")
                    
                    # Display sample output
                    print(f"\n   Sample Output (Variant 1 - {variant['framework']}):")
                    print(f"   Subject: {variant.get('subject_line_a', 'N/A')}")
                    print(f"   Preview: {variant.get('preview_text', 'N/A')[:50]}...")
                    print(f"   Hero: {variant.get('hero_h1', 'N/A')}")
                    
            else:
                print(f"❌ Copy generation failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Copy generation error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    print("Starting copywriting module integration test...")
    print("Make sure the module is running on http://localhost:8002")
    print()
    
    asyncio.run(test_copywriting_flow())