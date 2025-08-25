#!/usr/bin/env python3
"""
Test script for inline prompt editing functionality
"""

import asyncio
import httpx
import json

async def test_prompt_editing():
    """Test the prompt editing API endpoints"""
    
    base_url = "http://localhost:8002"
    agent_id = "email_marketing_expert"
    
    print("Testing Inline Prompt Editing Functionality")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # 1. Test fetching default prompt
        print(f"\n1. Fetching default prompt for {agent_id}...")
        response = await client.get(f"{base_url}/api/agents/{agent_id}/prompt")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Default prompt retrieved:")
            print(f"   {data['prompt'][:100]}...")
        else:
            print(f"❌ Failed to fetch prompt: {response.status_code}")
            return
        
        # 2. Test saving custom prompt
        print(f"\n2. Saving custom prompt for {agent_id}...")
        custom_prompt = """You are an expert email marketing specialist with deep knowledge of:
- Psychological triggers and persuasion techniques
- A/B testing and data-driven optimization
- Brand voice consistency

Your task: {user_input}

Focus on creating compelling subject lines and CTAs that drive conversions."""
        
        response = await client.put(
            f"{base_url}/api/agents/{agent_id}/prompt",
            json={"prompt": custom_prompt}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Custom prompt saved: {data['message']}")
        else:
            print(f"❌ Failed to save prompt: {response.status_code}")
            return
        
        # 3. Test fetching updated prompt
        print(f"\n3. Verifying custom prompt was saved...")
        response = await client.get(f"{base_url}/api/agents/{agent_id}/prompt")
        if response.status_code == 200:
            data = response.json()
            if custom_prompt in data['prompt']:
                print(f"✅ Custom prompt verified!")
            else:
                print(f"⚠️  Prompt changed but doesn't match exactly")
                print(f"   Retrieved: {data['prompt'][:100]}...")
        else:
            print(f"❌ Failed to verify prompt: {response.status_code}")
        
        # 4. Test generating copy with custom prompt
        print(f"\n4. Testing copy generation with custom prompt...")
        generation_request = {
            "brief_content": "Create an email for our summer sale with 50% off all products",
            "client_id": "test_client",
            "client_name": "Test Company",
            "campaign_type": "email",
            "selected_agents": [agent_id],
            "selected_model": "gpt-3.5-turbo",
            "custom_prompts": {
                agent_id: custom_prompt
            }
        }
        
        response = await client.post(
            f"{base_url}/api/generate-copy",
            json=generation_request
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Copy generated with custom prompt!")
            if data.get("variants"):
                variant = data["variants"][0]
                print(f"   Subject: {variant.get('subject', 'N/A')[:50]}...")
                print(f"   Preview: {variant.get('preview_text', 'N/A')[:50]}...")
        else:
            print(f"❌ Failed to generate copy: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text[:200]}")
    
    print("\n" + "=" * 50)
    print("Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_prompt_editing())