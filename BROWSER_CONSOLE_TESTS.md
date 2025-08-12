# Browser Console Tests for EmailPilot Dashboard

## Quick Console Checks

Open Developer Console (F12) and paste these commands to verify fixes:

### 1. Check Service Availability
```javascript
// Should return objects, not undefined
console.log('FirebaseCalendarService:', typeof window.FirebaseCalendarService);
console.log('GeminiChatService:', typeof window.GeminiChatService);
console.log('EmailPilot services:', window.EmailPilot?.services);
```

**Expected Output:**
```
FirebaseCalendarService: function
GeminiChatService: function  
EmailPilot services: {firebase: FirebaseCalendarService, gemini: GeminiChatService}
```

### 2. Check Component Loading
```javascript
// Check if components loaded successfully
console.log('Calendar:', typeof window.Calendar);
console.log('CalendarView:', typeof window.CalendarView);
console.log('Loaded components:', window.EmailPilot?.loadedComponents);
```

**Expected Output:**
```
Calendar: function
CalendarView: function
Loaded components: {Calendar: true, CalendarView: true, ...}
```

### 3. Test API Endpoints
```javascript
// Test key endpoints
fetch('/api/auth/session')
  .then(r => r.json())
  .then(d => console.log('Session API:', d))
  .catch(e => console.error('Session error:', e));

fetch('/api/admin/environment')
  .then(r => r.json()) 
  .then(d => console.log('Environment API:', d))
  .catch(e => console.error('Environment error:', e));

fetch('/api/performance/mtd/demo_client_1')
  .then(r => r.json())
  .then(d => console.log('Performance API:', d))
  .catch(e => console.error('Performance error:', e));
```

**Expected Output:**
```
Session API: {authenticated: true, user: {...}, demo_mode: true}
Environment API: {demoMode: true, environment: "development", ...}
Performance API: {client_id: "demo_client_1", mtd: {...}, ...}
```

### 4. Check for Common Errors
```javascript
// Look for error patterns in console history
const errors = [];
console.history = console.history || [];

// Check for Babel warnings
if (document.body.innerHTML.includes('@babel/standalone')) {
    errors.push('❌ Still using Babel runtime');
} else {
    console.log('✅ No Babel runtime detected');
}

// Check for 404s in network tab
performance.getEntriesByType('resource').forEach(entry => {
    if (entry.name.includes('.js') && entry.responseEnd === 0) {
        errors.push(`❌ Failed to load: ${entry.name}`);
    }
});

if (errors.length === 0) {
    console.log('✅ No critical errors detected');
} else {
    console.error('❌ Issues found:', errors);
}
```

### 5. Test Service Initialization
```javascript
// Test Firebase service
if (window.EmailPilot?.services?.firebase) {
    console.log('✅ Firebase service initialized');
    if (typeof window.EmailPilot.services.firebase.initialize === 'function') {
        console.log('✅ Firebase initialize() method available');
    }
} else {
    console.error('❌ Firebase service not available');
}

// Test Gemini service  
if (window.EmailPilot?.services?.gemini) {
    console.log('✅ Gemini service initialized');
} else {
    console.log('⚠️ Gemini service not initialized (may be normal)');
}
```

## Network Tab Checks

1. **Open Network Tab** in Developer Tools
2. **Reload the page**
3. **Filter by JS** files
4. **Look for:**
   - ✅ All `/dist/*.js` files return **200 OK**
   - ✅ Content-Type is **application/javascript**
   - ❌ No **404 Not Found** for JavaScript files
   - ❌ No HTML responses for JS requests

## Console Error Patterns

### ✅ Good - No Errors:
```
EmailPilot: Component loader initialized
EmailPilot: Component loaded - FirebaseCalendarService  
EmailPilot: Initializing Firebase service...
EmailPilot: Component loaded - Calendar
React components rendered successfully
```

### ❌ Bad - Errors to Fix:
```
Unexpected token '<' (HTML returned instead of JS)
404 (Not Found) for /components/Calendar.js
TypeError: Cannot read property 'initialize' of undefined  
Warning: You are using the in-browser Babel transformer
SyntaxError: Unexpected token in JSON
```

## Quick Fix Verification

After updating index.html to use dist files, run this one-liner:

```javascript
// Complete health check
Promise.all([
    fetch('/api/auth/session').then(r => r.json()),
    fetch('/api/admin/environment').then(r => r.json()),
    fetch('/dist/app.js').then(r => r.text().then(t => ({size: t.length, type: r.headers.get('content-type')}))),
]).then(results => {
    console.log('✅ Session API:', results[0].authenticated \!== undefined);
    console.log('✅ Environment API:', results[1].demoMode \!== undefined); 
    console.log('✅ App bundle:', results[2].size > 50000 && results[2].type.includes('javascript'));
    console.log('✅ Services:', window.EmailPilot?.services ? 'Available' : 'Missing');
    console.log('🎉 Dashboard fixes verified\!');
}).catch(e => console.error('❌ Issues detected:', e));
```

## Expected Final State

When everything is working correctly:

1. **No Babel warnings** in console
2. **All JavaScript files load** from `/dist/` URLs  
3. **Services initialize** without errors
4. **API calls return** proper JSON responses
5. **No 404 errors** for component files
6. **React components render** without issues

Run the tests above after each change to verify the fixes are working correctly.
EOF < /dev/null