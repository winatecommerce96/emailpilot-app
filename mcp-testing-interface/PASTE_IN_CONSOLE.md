# Paste This in Browser Console

## Step 1: Navigate to MCP Management
Go to https://emailpilot.ai/admin and click on MCP Management

## Step 2: Open Browser Console
Press F12 or right-click → Inspect → Console

## Step 3: Copy and Paste This Entire Block

```javascript
// Find Add New Client button
var addBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Add New Client'));
if (addBtn) {
    // Create Quick Test button
    var testBtn = document.createElement('button');
    testBtn.style.cssText = 'background:#9333ea;color:white;padding:8px 16px;border-radius:6px;margin-right:12px';
    testBtn.textContent = '🧪 Test MCP';
    testBtn.onclick = function() {
        alert('Testing MCP...');
        fetch('/api/mcp/models', {headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')}})
            .then(r => alert(r.ok ? '✅ MCP is working!' : '❌ MCP test failed'))
            .catch(e => alert('Error: ' + e.message));
    };
    addBtn.parentNode.insertBefore(testBtn, addBtn);
    alert('✅ Test button added! Look for the purple "🧪 Test MCP" button');
} else {
    alert('Could not find Add New Client button. Are you on the MCP Management page?');
}
```

## Alternative: Super Simple Test

If the above doesn't work, just paste this to test the API directly:

```javascript
fetch('/api/mcp/models', {
    headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')}
}).then(r => r.json()).then(data => {
    console.log('MCP Models:', data);
    alert('✅ MCP API is working!\n\nFound ' + data.length + ' models');
}).catch(e => {
    console.error('MCP Test Error:', e);
    alert('❌ MCP test failed: ' + e.message);
});
```

## Even Simpler: Just Check if MCP Works

Paste this one line:

```javascript
fetch('/api/mcp/models', {headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')}}).then(r => alert(r.ok ? '✅ MCP is working!' : '❌ MCP not working. Status: ' + r.status));
```

## Manual Button Creation

If you want to manually create a test button:

1. Right-click on the "Add New Client" button
2. Select "Inspect Element"
3. Right-click on the button element in DevTools
4. Select "Edit as HTML"
5. Add this before the button:

```html
<button onclick="fetch('/api/mcp/models',{headers:{'Authorization':'Bearer '+localStorage.getItem('token')}}).then(r=>alert(r.ok?'✅ MCP Working!':'❌ Failed'))" style="background:#9333ea;color:white;padding:8px 16px;border-radius:6px;margin-right:12px">🧪 Test MCP</button>
```

## Troubleshooting

If you get errors:
1. Make sure you're logged in (check for token):
   ```javascript
   console.log('Token exists:', !!localStorage.getItem('token'));
   ```

2. Check if you're on the right page:
   ```javascript
   console.log('Current URL:', window.location.pathname);
   ```

3. Manually test the API:
   ```javascript
   // This will show the full response in console
   fetch('/api/mcp/models', {
       headers: {'Authorization': 'Bearer ' + localStorage.getItem('token')}
   }).then(r => r.text()).then(console.log);
   ```