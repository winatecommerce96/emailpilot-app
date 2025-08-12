# MCP Management System - Troubleshooting Guide

## Critical Lessons Learned (Expensive Mistakes to Avoid)

### ❌ MISTAKE 1: Using Relative Paths Instead of Cloud Function URLs
**Problem**: Frontend code used `/api/mcp/*` paths which only work in development due to Create React App proxy.
```javascript
// ❌ WRONG - Only works in development
fetch('/api/mcp/models')

// ✅ CORRECT - Works in production
fetch('https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models')
```
**Fix**: Always use full Cloud Function URLs in production code.

### ❌ MISTAKE 2: Attempting Container Modification
**Problem**: Tried to modify running Docker containers, which lose changes on restart.
**Fix**: Use frontend injection instead of container modification.

### ❌ MISTAKE 3: Ignoring CORS Configuration
**Problem**: Missing `mode: 'cors'` in fetch requests caused opaque responses.
```javascript
// ❌ WRONG - May fail with CORS issues  
fetch(url)

// ✅ CORRECT - Proper CORS handling
fetch(url, { mode: 'cors' })
```

### ❌ MISTAKE 4: React Version Incompatibility
**Problem**: Using React 18 methods on React 17 applications.
```javascript
// ❌ WRONG - Only works in React 18+
ReactDOM.createRoot(element).render(component)

// ✅ CORRECT - Version-aware mounting
if (ReactDOM.createRoot) {
    ReactDOM.createRoot(element).render(component);
} else {
    ReactDOM.render(component, element);
}
```

## Common Issues and Solutions

### Issue 1: MCP Button Doesn't Appear
**Symptoms**: No button visible after injection
**Causes**:
- React not loaded on the page
- Script injection failed
- JavaScript errors preventing execution

**Solutions**:
1. Check browser console for errors
2. Verify you're on https://emailpilot.ai
3. Wait for page to fully load before injecting
4. Try the test-endpoints.html file first

**Debug Commands**:
```javascript
// Check if React is available
console.log('React:', typeof React !== 'undefined');
console.log('ReactDOM:', typeof ReactDOM !== 'undefined');

// Check if MCP was injected
console.log('MCP Components:', window.MCPManagement);
console.log('MCP Endpoints:', window.MCP_ENDPOINTS);
```

### Issue 2: Modal Opens But No Data Loads
**Symptoms**: Button appears, modal opens, but shows "Loading..." forever
**Causes**:
- Cloud Functions not responding
- CORS issues
- Network connectivity problems

**Solutions**:
1. Test endpoints with test-endpoints.html
2. Check browser network tab for failed requests
3. Verify Cloud Function URLs are accessible

**Debug Commands**:
```javascript
// Test individual endpoints
Object.entries(window.MCP_ENDPOINTS).forEach(async ([name, url]) => {
    try {
        const response = await fetch(url, { mode: 'cors' });
        console.log(`${name}:`, response.status, await response.json());
    } catch (error) {
        console.error(`${name} failed:`, error);
    }
});
```

### Issue 3: Console Errors About CORS
**Symptoms**: "CORS policy: No 'Access-Control-Allow-Origin' header"
**Causes**:
- Missing `mode: 'cors'` in fetch requests
- Cloud Functions CORS not configured

**Solutions**:
1. Always use `mode: 'cors'` in fetch calls
2. Verify Cloud Functions have CORS enabled
3. Check if requests are being blocked by browser

### Issue 4: Performance Issues or Slow Loading
**Symptoms**: Browser becomes slow after injection
**Causes**:
- Memory leaks in React components
- Too many re-renders
- Large response data

**Solutions**:
1. Use rollback.sh to remove MCP
2. Clear browser cache
3. Refresh page
4. Use incognito mode for testing

**Debug Commands**:
```javascript
// Check component state
console.log('MCP Root:', document.getElementById('mcp-root'));
console.log('Active Components:', document.querySelectorAll('[id*="mcp"]'));
```

### Issue 5: Button Appears Multiple Times
**Symptoms**: Multiple "🤖 MCP Management" buttons visible
**Causes**:
- Script injected multiple times
- Previous injection not cleaned up

**Solutions**:
1. Use rollback.sh to clean up
2. Refresh page
3. Only inject once per page load

## Network Troubleshooting

### Cloud Function Endpoint Testing
Use these curl commands to test endpoints directly:

```bash
# Test Models endpoint
curl -X GET "https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models" \
  -H "Accept: application/json"

# Test Clients endpoint  
curl -X GET "https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients" \
  -H "Accept: application/json"

# Test Health endpoint
curl -X GET "https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health" \
  -H "Accept: application/json"
```

### Browser Network Analysis
1. Open Developer Tools (F12)
2. Go to Network tab
3. Trigger MCP data load
4. Look for failed requests (red entries)
5. Check response details for error messages

## Emergency Recovery

### Quick Removal
```javascript
// Paste in browser console to immediately remove MCP
document.getElementById('mcp-root')?.remove();
delete window.MCPManagement;
delete window.MCP_ENDPOINTS;
```

### Complete Reset
1. Run `./rollback.sh` script
2. Choose option 1 for browser console rollback  
3. Refresh page
4. Clear browser cache if needed

### Nuclear Option
If all else fails:
1. Close all browser tabs
2. Clear all browser data for emailpilot.ai
3. Restart browser
4. Navigate fresh to https://emailpilot.ai

## Verification Steps

After deployment, verify these work:
1. ✅ Button appears in top-right corner
2. ✅ Modal opens when button clicked
3. ✅ Health status shows "Healthy"
4. ✅ Models load with data
5. ✅ No console errors
6. ✅ Refresh data button works

## Debug Information Collection

If you need to report an issue, collect this info:

```javascript
// Run in browser console to collect debug info
console.group('🐛 MCP Debug Information');
console.log('URL:', window.location.href);
console.log('User Agent:', navigator.userAgent);
console.log('React:', typeof React, React?.version);
console.log('ReactDOM:', typeof ReactDOM);
console.log('MCP Endpoints:', window.MCP_ENDPOINTS);
console.log('MCP Component:', typeof window.MCPManagement);
console.log('DOM Elements:', document.querySelectorAll('[id*="mcp"]').length);
console.log('Console Errors:', 'Check console above for any errors');
console.groupEnd();
```

## Best Practices for Deployment

1. **Always test locally first**: Use test-endpoints.html
2. **Verify React availability**: Check console before injection
3. **Use proper URLs**: Never use relative paths for Cloud Functions
4. **Handle errors gracefully**: Include try/catch blocks
5. **Clean up properly**: Use rollback script when needed
6. **Document changes**: Keep track of what was modified

## Contact and Support

- Check existing logs in deployment directory
- Use rollback.sh for emergency removal
- Test endpoints with test-endpoints.html
- Review browser console for specific errors
- Clear browser cache as last resort