#!/usr/bin/env python3
"""
Initialize Calendar Planning Template in AI Models System

This script adds the calendar planning master template to the prompt templates
available in the EmailPilot AI Models management system.

Usage:
    python scripts/initialize_calendar_template.py
"""

import httpx
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def initialize_template():
    """Initialize the calendar planning template via API"""
    
    # Configuration
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # If you have authentication, add token here
    # token = os.getenv("ACCESS_TOKEN", "")
    # headers = {"Authorization": f"Bearer {token}"}
    headers = {}
    
    print("🚀 Initializing Calendar Planning Template...")
    print(f"   API Base: {base_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            # Initialize the main calendar template
            print("\n1. Creating master calendar planning template...")
            response = await client.post(
                f"{base_url}/api/calendar/templates/initialize-calendar-template",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("existing"):
                    print("   ✅ Template already exists")
                else:
                    print("   ✅ Template created successfully")
                print(f"   Template ID: {result.get('prompt_id')}")
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text}")
                return False
            
            # Create quick prompts
            print("\n2. Creating quick calendar prompts...")
            response = await client.post(
                f"{base_url}/api/calendar/templates/calendar-template/quick-prompts",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Created {result.get('message')}")
            else:
                print(f"   ⚠️  Quick prompts may already exist or failed: {response.status_code}")
            
            # List all calendar templates
            print("\n3. Verifying calendar templates...")
            response = await client.get(
                f"{base_url}/api/calendar/templates/calendar-templates/list",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Found {result.get('count')} calendar templates:")
                for template in result.get("templates", []):
                    print(f"      - {template.get('name')} (v{template.get('version')})")
            else:
                print(f"   ⚠️  Could not list templates: {response.status_code}")
            
            print("\n✨ Calendar planning templates initialized successfully!")
            print("\nYou can now:")
            print("1. View templates at: /admin/ai-models → Prompt Templates")
            print("2. Use the calendar planning AI at: /calendar → AI Planning")
            print("3. Render prompts via API: POST /api/calendar/templates/render-calendar-prompt")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

async def test_render():
    """Test rendering the template with sample data"""
    
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    headers = {}
    
    print("\n\n📝 Testing template rendering...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test render with sample client
            response = await client.post(
                f"{base_url}/api/calendar/templates/render-calendar-prompt",
                headers=headers,
                params={
                    "client_id": "test_client",
                    "target_month": "September",
                    "target_year": 2025
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Template rendered successfully")
                print(f"   Period: {result.get('period')}")
                print(f"   Variables used: {len(result.get('variables_used', {}))}")
                
                # Show first 500 chars of rendered prompt
                prompt = result.get("rendered_prompt", "")
                if prompt:
                    print(f"\n   Preview (first 500 chars):")
                    print("   " + "-" * 50)
                    print(prompt[:500] + "...")
            elif response.status_code == 404:
                print("   ⚠️  Test client not found (expected for new installations)")
            else:
                print(f"   ❌ Render failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Test error: {e}")

async def main():
    """Main execution"""
    success = await initialize_template()
    
    if success:
        # Optionally test rendering
        await test_render()
    
    return success

if __name__ == "__main__":
    print("=" * 60)
    print("Calendar Planning Template Initialization")
    print("=" * 60)
    
    success = asyncio.run(main())
    
    sys.exit(0 if success else 1)