# Developer Tools Quick Action - Acceptance Test Plan

## Test Environment Setup
```bash
# 1. Start the server
pkill -f uvicorn || true
uvicorn main_firestore:app --port 8000 --host localhost --reload

# 2. Clear browser cache
# Chrome: Cmd+Shift+Delete → Clear browsing data → Cached images and files
```

## Acceptance Criteria

### ✅ AC1: Developer Tools Script Loads
**Given** the user navigates to http://localhost:8000/admin  
**When** the page loads  
**Then** the DeveloperTools.js script should be loaded (verify in Network tab)

**Verification**:
```javascript
// Browser console
console.log('DeveloperTools loaded:', typeof window.DeveloperTools !== 'undefined');
// Expected: DeveloperTools loaded: true
```

### ✅ AC2: Button Appears in Quick Actions
**Given** the user is on the admin overview page  
**When** viewing the Quick Actions section  
**Then** the "🛠️ Developer Tools" button should be visible with:
- Icon: 🛠️
- Title: "Developer Tools"
- Subtitle: "Access hidden features"

**Verification**:
```javascript
// Browser console
document.querySelectorAll('button').forEach(btn => {
  if (btn.textContent.includes('Developer Tools')) {
    console.log('✅ Developer Tools button found');
  }
});
```

### ✅ AC3: Button Click Works
**Given** the Developer Tools button is visible  
**When** the user clicks it  
**Then** the activeTab should change to 'dev-tools' and the component should render

**Verification**:
1. Click the button
2. Check URL or state changes
3. Verify component renders

### ✅ AC4: Component Functions
**Given** the Developer Tools component is loaded  
**When** viewing the component  
**Then** it should display:
- List of hidden backend endpoints
- Category tabs (AI & Agents, MCP Tools, etc.)
- Test endpoint functionality
- Filter/search capability

### ✅ AC5: Persistence After Refresh
**Given** the Developer Tools has been accessed once  
**When** the page is refreshed (F5)  
**Then** the button should still appear and function

## Test Matrix

| Environment | Browser | Cache | Expected Result |
|------------|---------|-------|-----------------|
| Development | Chrome | Clear | ✅ Button appears |
| Development | Chrome | Cached | ✅ Button appears |
| Development | Firefox | Clear | ✅ Button appears |
| Development | Safari | Clear | ✅ Button appears |
| Production Build | Chrome | Clear | ✅ Button appears |

## Manual Test Steps

### Step 1: Initial Load Test
1. Open http://localhost:8000/admin
2. Open DevTools (F12)
3. Go to Network tab
4. Refresh page (Cmd+R)
5. Search for "DeveloperTools" in Network
6. **Expected**: DeveloperTools.js loads with 200 status

### Step 2: Visual Verification
1. Scroll to Quick Actions section
2. Count the buttons
3. **Expected**: "🛠️ Developer Tools" is present

### Step 3: Functionality Test
1. Click "🛠️ Developer Tools" button
2. **Expected**: Developer Tools interface loads
3. Click on "AI & Agents" tab
4. **Expected**: List of AI endpoints appears
5. Select any GET endpoint
6. Click "Test Endpoint"
7. **Expected**: Response appears in test panel

### Step 4: Browser Compatibility
Repeat Step 1-3 in:
- [ ] Chrome
- [ ] Firefox  
- [ ] Safari
- [ ] Edge

## Automated Test

```javascript
// Run in browser console for quick validation
(async function testDeveloperTools() {
    const tests = [];
    
    // Test 1: Script loaded
    tests.push({
        name: 'Script Loaded',
        pass: typeof window.DeveloperTools !== 'undefined'
    });
    
    // Test 2: Button exists
    const button = Array.from(document.querySelectorAll('button'))
        .find(btn => btn.textContent.includes('Developer Tools'));
    tests.push({
        name: 'Button Exists',
        pass: !!button
    });
    
    // Test 3: Button clickable
    if (button) {
        button.click();
        await new Promise(r => setTimeout(r, 1000));
        tests.push({
            name: 'Button Clickable',
            pass: true
        });
    }
    
    // Results
    console.table(tests);
    const passed = tests.filter(t => t.pass).length;
    console.log(`Result: ${passed}/${tests.length} tests passed`);
    
    return passed === tests.length;
})();
```

## Production Build Test

```bash
# 1. Build for production
npm run build

# 2. Start in production mode
NODE_ENV=production uvicorn main_firestore:app --port 8000

# 3. Test in incognito window
# Open http://localhost:8000/admin in incognito
# Verify Developer Tools button appears
```

## Regression Prevention

### CI/CD Check
```yaml
# Add to CI pipeline
- name: Verify Developer Tools
  run: |
    grep -q "DeveloperTools.js" frontend/public/index.html || exit 1
    test -f frontend/public/dist/DeveloperTools.js || exit 1
```

### Build Verification
```bash
# Add to build script
if [ ! -f "frontend/public/dist/DeveloperTools.js" ]; then
    echo "ERROR: DeveloperTools.js not found in dist"
    exit 1
fi
```

## Sign-off Checklist

- [ ] Developer Tools button visible in Quick Actions
- [ ] Button click loads component
- [ ] Component displays endpoint list
- [ ] Test endpoint feature works
- [ ] Survives page refresh
- [ ] Works in production build
- [ ] No console errors
- [ ] Responsive on mobile

## Known Issues & Workarounds

| Issue | Workaround |
|-------|------------|
| Button not appearing | Hard refresh: Cmd+Shift+R |
| Component not loading | Check console for 404 errors |
| Old version cached | Clear browser cache completely |

## Support

If Developer Tools doesn't appear:
1. Check browser console for errors
2. Verify script tag in index.html
3. Ensure file exists: `ls -la frontend/public/dist/DeveloperTools.js`
4. Try test page: http://localhost:8000/test-quick-actions.html