# Manual Integration Guide for MCP Testing UI

## Quick Fix - Run in Browser Console

Since the package deployed but the UI isn't showing, you can manually activate it by running this in your browser console while on the MCP Management page:

### Step 1: Open Browser Console
1. Go to https://emailpilot.ai/admin
2. Navigate to MCP Management section
3. Open browser console (F12 or right-click → Inspect → Console)

### Step 2: Run Integration Script

Copy and paste this entire code block into the console:

```javascript
// Quick integration to add testing button
(function() {
    // Find the header
    const headers = document.querySelectorAll('h2');
    let mcpHeader = null;
    headers.forEach(h => {
        if (h.textContent.includes('MCP')) mcpHeader = h;
    });
    
    if (!mcpHeader) {
        alert('MCP Management section not found');
        return;
    }
    
    // Find Add New Client button
    const buttons = mcpHeader.parentElement.querySelectorAll('button');
    let addButton = null;
    buttons.forEach(b => {
        if (b.textContent.includes('Add New Client')) addButton = b;
    });
    
    if (!addButton) {
        alert('Add New Client button not found');
        return;
    }
    
    // Create testing button
    const testBtn = document.createElement('button');
    testBtn.className = addButton.className.replace('blue', 'purple');
    testBtn.innerHTML = '🧪 Production Testing';
    testBtn.style.marginRight = '12px';
    
    // Add click handler
    testBtn.onclick = function() {
        // Load testing interface
        if (window.MCPTestingInterface) {
            showTestInterface();
        } else {
            const script = document.createElement('script');
            script.src = '/components/MCPTestingInterface.js';
            script.onload = () => {
                showTestInterface();
            };
            script.onerror = () => {
                alert('MCPTestingInterface.js not found. Please ensure it was deployed to /components/');
            };
            document.head.appendChild(script);
        }
    };
    
    function showTestInterface() {
        const content = document.querySelector('.p-6');
        const original = content.innerHTML;
        
        content.innerHTML = `
            <div>
                <button onclick="location.reload()" class="text-blue-600 mb-4">← Back to MCP Management</button>
                <div id="testRoot"></div>
            </div>
        `;
        
        if (window.MCPTestingInterface) {
            ReactDOM.render(React.createElement(MCPTestingInterface), document.getElementById('testRoot'));
        } else {
            content.innerHTML = original;
            alert('Testing interface component not loaded');
        }
    }
    
    // Insert button
    addButton.parentElement.insertBefore(testBtn, addButton);
    
    // Add quick test button too
    const quickBtn = document.createElement('button');
    quickBtn.className = addButton.className.replace('blue', 'green');
    quickBtn.innerHTML = '⚡ Quick Test';
    quickBtn.style.marginRight = '12px';
    quickBtn.onclick = async function() {
        const token = localStorage.getItem('token');
        try {
            const r1 = await fetch('/api/mcp/models', {headers: {'Authorization': `Bearer ${token}`}});
            const r2 = await fetch('/api/mcp/clients', {headers: {'Authorization': `Bearer ${token}`}});
            alert(`Quick Test Results:\n\nModels API: ${r1.ok ? '✅' : '❌'}\nClients API: ${r2.ok ? '✅' : '❌'}\n\nStatus: ${r1.ok && r2.ok ? 'Operational ✅' : 'Issues Detected ⚠️'}`);
        } catch(e) {
            alert('Quick test failed: ' + e.message);
        }
    };
    
    addButton.parentElement.insertBefore(quickBtn, testBtn);
    
    console.log('✅ Testing buttons added successfully!');
    alert('✅ MCP Testing buttons have been added!\n\nLook for:\n• ⚡ Quick Test\n• 🧪 Production Testing');
})();
```

## Alternative: Load Full Integration Script

If you want the complete integration with all features:

```javascript
// Load the full integration script
const script = document.createElement('script');
script.src = '/components/integrate_testing_ui.js';
script.onload = () => console.log('Integration script loaded');
script.onerror = () => {
    // If file not found, load from staged location
    script.src = '/app/staged_packages/mcp_testing_[TIMESTAMP]/integrate_testing_ui.js';
    document.head.appendChild(script);
};
document.head.appendChild(script);
```

## Permanent Fix - Update the Component

To make the testing UI permanent, you need to update the MCP Management component file on the server:

### Option 1: Update via SSH/Terminal

```bash
# 1. Find the MCPManagement component
find /app -name "MCPManagement.js" 2>/dev/null

# 2. Check staged files
ls -la /app/staged_packages/mcp_testing_*/

# 3. Copy the enhanced version
cp /app/staged_packages/mcp_testing_*/MCPManagementWithTesting.js /app/frontend/public/components/

# 4. Update the reference in the admin loader
# Edit the file that loads MCPManagement and change it to load MCPManagementWithTesting
```

### Option 2: Direct File Edit

Add this code to the existing MCPManagement.js file, right after the component loads:

```javascript
// At the top of the return statement in MCPManagement component
return (
    <div className="p-6">
        <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">MCP Client Management</h2>
            <div className="flex space-x-3">
                {/* ADD THESE NEW BUTTONS */}
                <button
                    onClick={() => {
                        if (window.MCPTestingInterface) {
                            // Show testing interface
                            setShowTestingInterface(true);
                        } else {
                            alert('Loading testing interface...');
                            const s = document.createElement('script');
                            s.src = '/components/MCPTestingInterface.js';
                            s.onload = () => setShowTestingInterface(true);
                            document.head.appendChild(s);
                        }
                    }}
                    className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
                >
                    🧪 Production Testing
                </button>
                {/* EXISTING ADD BUTTON */}
                <button onClick={() => setShowAddModal(true)} ...>
                    Add New Client
                </button>
            </div>
        </div>
        {/* Rest of component */}
    </div>
);
```

## Verification Steps

After adding the buttons, verify they work:

1. **Quick Test Button (⚡)**
   - Click it
   - Should show popup with API status

2. **Production Testing Button (🧪)**
   - Click it
   - Should load full testing interface
   - If error, check console for file path issues

3. **Check Console**
   ```javascript
   // Run in console to verify components loaded
   console.log('Testing Interface:', !!window.MCPTestingInterface);
   console.log('MCP Management:', !!window.MCPManagement);
   ```

## Troubleshooting

### If buttons don't appear:
- Clear browser cache
- Reload the page
- Re-run the integration script

### If testing interface won't load:
- Check if MCPTestingInterface.js exists:
  ```javascript
  fetch('/components/MCPTestingInterface.js').then(r => console.log('File exists:', r.ok));
  ```
- Try loading from staged location
- Check browser console for errors

### If API tests fail:
- Verify you're logged in (check token):
  ```javascript
  console.log('Token exists:', !!localStorage.getItem('token'));
  ```
- Check network tab for API responses

## Success Indicators

You'll know it's working when:
1. ✅ Two new buttons appear: "⚡ Quick Test" and "🧪 Production Testing"
2. ✅ Quick Test shows API status popup
3. ✅ Production Testing loads full interface
4. ✅ No errors in browser console

## Need Help?

If the manual integration doesn't work:
1. Check where files were staged: `/app/staged_packages/`
2. Verify components directory: `/app/frontend/public/components/`
3. Look for integration instructions in staged directory
4. Check deployment logs for any errors