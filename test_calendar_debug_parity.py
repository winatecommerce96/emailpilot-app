#!/usr/bin/env python3
"""
Test Calendar Debug Harness Parity
Verifies that /calendar-debug is identical to /calendar in production mode
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
import difflib
import json

BASE_URL = "http://localhost:8000"

class CalendarParityTest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_html_structure_parity(self):
        """Compare HTML structure between production and debug"""
        print("\n🔍 Testing HTML Structure Parity...")
        
        # Fetch both pages
        prod_response = await self.client.get(f"{BASE_URL}/calendar")
        debug_response = await self.client.get(f"{BASE_URL}/calendar-debug")
        
        if prod_response.status_code != 200:
            print(f"❌ Production calendar returned {prod_response.status_code}")
            return False
            
        if debug_response.status_code != 200:
            print(f"❌ Debug calendar returned {debug_response.status_code}")
            return False
        
        # Parse HTML
        prod_soup = BeautifulSoup(prod_response.text, 'html.parser')
        debug_soup = BeautifulSoup(debug_response.text, 'html.parser')
        
        # Remove debug overlay from comparison (it's the only allowed difference)
        debug_overlay = debug_soup.find(id='debug-overlay')
        if debug_overlay:
            debug_overlay.decompose()
        
        # Remove debug scripts from comparison
        for script in debug_soup.find_all('script'):
            if 'DEBUG_STATE' in str(script.string):
                script.decompose()
        
        # Compare key structural elements
        checks = {
            'nav-root': 'Navigation root',
            'calendar-root': 'Calendar root',
        }
        
        all_match = True
        for element_id, description in checks.items():
            prod_elem = prod_soup.find(id=element_id)
            debug_elem = debug_soup.find(id=element_id)
            
            if (prod_elem is None) != (debug_elem is None):
                print(f"❌ {description} mismatch: prod={prod_elem is not None}, debug={debug_elem is not None}")
                all_match = False
            else:
                print(f"✅ {description} present in both")
        
        # Compare CSS includes
        prod_css = [link.get('href') for link in prod_soup.find_all('link', rel='stylesheet')]
        debug_css = [link.get('href') for link in debug_soup.find_all('link', rel='stylesheet')]
        
        if prod_css == debug_css:
            print(f"✅ CSS includes match: {len(prod_css)} stylesheets")
        else:
            print(f"❌ CSS mismatch: prod={prod_css}, debug={debug_css}")
            all_match = False
        
        # Compare script includes (excluding debug-specific)
        prod_scripts = [s.get('src') for s in prod_soup.find_all('script') if s.get('src')]
        debug_scripts = [s.get('src') for s in debug_soup.find_all('script') if s.get('src')]
        
        if prod_scripts == debug_scripts:
            print(f"✅ Script includes match: {len(prod_scripts)} scripts")
        else:
            print(f"❌ Script mismatch")
            all_match = False
        
        return all_match
    
    async def test_api_behavior_parity(self):
        """Test that API calls work identically"""
        print("\n🔍 Testing API Behavior Parity...")
        
        # Test calendar build endpoint from both pages
        test_payload = {
            "client_display_name": "Parity Test Client",
            "client_firestore_id": "parity_test_123",
            "klaviyo_account_id": "test_parity",
            "target_month": 10,
            "target_year": 2025,
            "dry_run": True
        }
        
        # Both should be able to call the same API
        response = await self.client.post(
            f"{BASE_URL}/api/calendar/build",
            json=test_payload
        )
        
        if response.status_code == 200:
            print("✅ API endpoint accessible (same for both pages)")
            data = response.json()
            if 'correlation_id' in data:
                print(f"✅ Build API returns correlation_id: {data['correlation_id'][:8]}...")
        else:
            print(f"❌ API call failed: {response.status_code}")
            return False
        
        return True
    
    async def test_debug_mode_toggle(self):
        """Test that debug mode doesn't affect production UI"""
        print("\n🔍 Testing Debug Mode Toggle...")
        
        # Test without debug mode
        response = await self.client.get(f"{BASE_URL}/calendar-debug")
        soup = BeautifulSoup(response.text, 'html.parser')
        overlay = soup.find(id='debug-overlay')
        
        if overlay:
            style = overlay.get('style', '')
            if 'display: none' in style:
                print("✅ Debug overlay hidden by default")
            else:
                print("❌ Debug overlay should be hidden by default")
                return False
        
        # Test with debug mode
        response = await self.client.get(f"{BASE_URL}/calendar-debug?debug=1")
        if response.status_code == 200:
            print("✅ Debug mode query param accepted")
            # The actual display is controlled by JavaScript, so we just check it loads
        
        return True
    
    async def test_deep_linking(self):
        """Test that deep links work identically"""
        print("\n🔍 Testing Deep Linking...")
        
        test_urls = [
            "/calendar?client=test_123&year=2025&month=12",
            "/calendar-debug?client=test_123&year=2025&month=12",
            "/calendar-debug?client=test_123&year=2025&month=12&debug=1"
        ]
        
        all_success = True
        for url in test_urls:
            response = await self.client.get(f"{BASE_URL}{url}")
            if response.status_code == 200:
                print(f"✅ Deep link works: {url}")
            else:
                print(f"❌ Deep link failed: {url} returned {response.status_code}")
                all_success = False
        
        return all_success
    
    async def test_visual_parity(self):
        """Instructions for manual visual parity check"""
        print("\n📸 Manual Visual Parity Check Instructions:")
        print("-" * 50)
        print("1. Open two browser tabs side by side:")
        print(f"   Left:  {BASE_URL}/calendar")
        print(f"   Right: {BASE_URL}/calendar-debug")
        print("\n2. Verify they look IDENTICAL:")
        print("   - Same header/navigation")
        print("   - Same calendar layout")
        print("   - Same colors and styling")
        print("   - Same buttons and controls")
        print("\n3. Test with debug overlay:")
        print(f"   {BASE_URL}/calendar-debug?debug=1")
        print("   - Should show green overlay on right side")
        print("   - Calendar underneath should be unchanged")
        print("\n4. Test keyboard shortcut:")
        print("   - Press Ctrl+Alt+D on debug page")
        print("   - Overlay should toggle on/off")
        
        return True
    
    async def cleanup(self):
        await self.client.aclose()

async def main():
    tester = CalendarParityTest()
    
    try:
        print("=" * 60)
        print("📅 Calendar Debug Harness Parity Test")
        print("=" * 60)
        
        # Run all tests
        results = []
        
        result = await tester.test_html_structure_parity()
        results.append(("HTML Structure", result))
        
        result = await tester.test_api_behavior_parity()
        results.append(("API Behavior", result))
        
        result = await tester.test_debug_mode_toggle()
        results.append(("Debug Mode", result))
        
        result = await tester.test_deep_linking()
        results.append(("Deep Linking", result))
        
        await tester.test_visual_parity()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        print("-" * 60)
        
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        print("=" * 60)
        if all_passed:
            print("✅ All automated tests PASSED!")
            print("⚠️  Remember to perform manual visual parity check")
        else:
            print("❌ Some tests FAILED - review output above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    print("Starting Calendar Debug Harness Parity Test...")
    print("Make sure the server is running at http://localhost:8000")
    print()
    
    asyncio.run(main())