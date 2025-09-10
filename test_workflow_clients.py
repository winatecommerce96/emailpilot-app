#!/usr/bin/env python3
"""
Test that workflow pages are loading clients dynamically
"""

import httpx
import asyncio
from bs4 import BeautifulSoup

async def test_workflow_pages():
    """Test that workflow HTML pages no longer have hardcoded test clients"""
    
    test_clients = [
        "Rogue Creamery",
        "Christopher Bean Coffee",
        "Colorado Hemp Honey",
        "Milagro Mushrooms",
        "Rocky Mountain Spice",
        "The Frozen Garden",
        "Wyoming Wildflower Honey"
    ]
    
    pages_to_test = [
        "/static/workflow_manager.html",
        "/static/workflow_builder.html",
        "/static/workflow_builder_ai.html",
        "/static/workflow_library.html",
        "/static/workflow_wizard.html"
    ]
    
    results = {}
    
    async with httpx.AsyncClient() as client:
        for page in pages_to_test:
            try:
                response = await client.get(f"http://localhost:8000{page}")
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Check for hardcoded test clients in option/label tags
                    hardcoded_found = []
                    for test_client in test_clients:
                        # Look for the client name in option tags (for selects)
                        if f'<option value=' in html_content and test_client in html_content:
                            # Check if it's in a hardcoded option tag
                            lines = html_content.split('\n')
                            for line in lines:
                                if '<option value=' in line and test_client in line:
                                    hardcoded_found.append(test_client)
                                    break
                    
                    # Check for "Loading clients..." placeholder
                    has_loading_placeholder = "Loading clients..." in html_content
                    
                    results[page] = {
                        "status": "success",
                        "hardcoded_clients": hardcoded_found,
                        "has_loading_placeholder": has_loading_placeholder,
                        "dynamic": len(hardcoded_found) == 0 and has_loading_placeholder
                    }
                else:
                    results[page] = {
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    }
            except Exception as e:
                results[page] = {
                    "status": "error",
                    "error": str(e)
                }
    
    # Print results
    print("\n🔍 Workflow Pages Client Loading Test")
    print("=" * 60)
    
    all_dynamic = True
    for page, result in results.items():
        page_name = page.split('/')[-1]
        if result["status"] == "success":
            if result["dynamic"]:
                print(f"✅ {page_name}: Dynamic loading (no hardcoded clients)")
            else:
                print(f"⚠️  {page_name}: Found hardcoded clients: {result['hardcoded_clients']}")
                all_dynamic = False
        else:
            print(f"❌ {page_name}: {result['error']}")
            all_dynamic = False
    
    # Test the API (need a new client since the previous one is inside the context manager)
    print("\n📊 Client API Test:")
    async with httpx.AsyncClient() as api_client:
        try:
            api_response = await api_client.get("http://localhost:8000/api/admin/clients")
            if api_response.status_code == 200:
                data = api_response.json()
                print(f"✅ API returns {data.get('total_clients', 0)} clients")
                print(f"   Active: {data.get('active_clients', 0)}, With Keys: {data.get('clients_with_keys', 0)}")
            
                # Show first 3 clients
                clients = data.get('clients', [])[:3]
                if clients:
                    print("   Sample clients from API:")
                    for c in clients:
                        print(f"     - {c['name']} (id: {c['id']})")
            else:
                print(f"❌ API returned status {api_response.status_code}")
        except Exception as e:
            print(f"❌ API error: {e}")
    
    print("\n" + "=" * 60)
    if all_dynamic:
        print("🎉 SUCCESS: All workflow pages use dynamic client loading!")
        print("   Test clients have been removed from the system.")
    else:
        print("⚠️  Some pages may still have hardcoded clients.")
        print("   Check browser console for any JavaScript errors.")
    
    return all_dynamic

if __name__ == "__main__":
    success = asyncio.run(test_workflow_pages())
    exit(0 if success else 1)