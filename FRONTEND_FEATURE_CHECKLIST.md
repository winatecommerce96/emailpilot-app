# Frontend Feature Addition Checklist

**CRITICAL**: Follow ALL steps to ensure new features appear in production.

## ✅ 10-Step Checklist for Adding New Features

### 1. Create Component File
- [ ] Create component in `frontend/public/components/YourComponent.js`
- [ ] Export component: `window.YourComponent = YourComponent;`
- [ ] Use React without JSX or wrap in build process

### 2. Add to Build Script
- [ ] Open `scripts/build_frontend.sh`
- [ ] Add component name to `JSX_COMPONENTS` array (line 46-71)
- [ ] Verify exact filename matches

### 3. Update App Router
- [ ] Open `frontend/public/app.js`
- [ ] Add route/tab case: `activeTab === 'your-feature'`
- [ ] Add loading logic for lazy-loaded components
- [ ] Add navigation button/link to access feature

### 4. Build Frontend
```bash
npm run build
# Verify output shows your component being compiled
```

### 5. Update Cache Busting
```bash
# Update version in index.html
TIMESTAMP=$(date +%s)
sed -i '' "s|app.js?v=[0-9]*|app.js?v=${TIMESTAMP}|g" frontend/public/index.html
```

### 6. Clear Service Workers (if any)
```javascript
// Run in browser console
navigator.serviceWorker.getRegistrations().then(r => r.forEach(reg => reg.unregister()))
```

### 7. Test Locally
- [ ] Start server: `uvicorn main_firestore:app --port 8000 --host localhost --reload`
- [ ] Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
- [ ] Open DevTools Network tab
- [ ] Verify new version loads (check query parameter)
- [ ] Test feature functionality

### 8. Check for Errors
```javascript
// Browser console - should be empty
console.clear();
// Navigate to your feature
// Check for any red errors
```

### 9. Verify Component Registration
```javascript
// Browser console
console.log(window.YourComponent); // Should not be undefined
```

### 10. Production Deployment
- [ ] Commit all changes including `dist/` files
- [ ] Deploy with cache invalidation
- [ ] Test in incognito/private window
- [ ] Verify feature appears without cache clear

## Common Issues & Solutions

### Feature Not Appearing
1. **Check build output**: Component must be in `frontend/public/dist/`
2. **Check app.js compilation**: Must include your route/tab logic
3. **Check browser cache**: Use Network tab, disable cache
4. **Check console errors**: Component may be failing silently

### Component Not Loading
1. **Verify path**: Script src must match actual file location
2. **Check lazy loading**: Ensure script.onload triggers correctly
3. **Check window assignment**: Component must be on `window` object

### Cache Issues
1. **Add timestamp**: `?v=${Date.now()}` to script URLs
2. **Use hard refresh**: Bypass cache completely
3. **Clear storage**: DevTools > Application > Clear Storage

### Build Not Working
1. **Check JSX syntax**: Use proper React.createElement if not using build
2. **Check dependencies**: All imports must resolve
3. **Check build script**: Component must be in JSX_COMPONENTS array

## Testing Commands

```bash
# Full rebuild and test
npm run build && \
pkill -f uvicorn || true && \
uvicorn main_firestore:app --port 8000 --host localhost --reload

# Check if component built
ls -la frontend/public/dist/YourComponent.js

# Check if in app bundle
grep -c "YourComponent" frontend/public/dist/app.js

# Force cache clear
curl -X POST http://localhost:8000/admin/clear-cache
```

## Verification Script

```javascript
// Run in browser console to verify setup
(function() {
    const checks = {
        'React loaded': typeof React !== 'undefined',
        'ReactDOM loaded': typeof ReactDOM !== 'undefined',
        'App loaded': typeof window.App !== 'undefined',
        'Component loaded': typeof window.YourComponent !== 'undefined',
        'No console errors': !document.querySelector('.console-error-level')
    };
    
    console.table(checks);
    
    const failed = Object.entries(checks)
        .filter(([k, v]) => !v)
        .map(([k]) => k);
    
    if (failed.length) {
        console.error('❌ Failed checks:', failed);
    } else {
        console.log('✅ All checks passed!');
    }
})();
```

## Definition of Done

- [ ] Feature renders in development build
- [ ] Feature renders in production build  
- [ ] No console errors
- [ ] Works after cache clear
- [ ] Works in incognito window
- [ ] Component appears in build manifest
- [ ] Route/navigation works
- [ ] Lazy loading works (if applicable)
- [ ] Mobile responsive (if applicable)
- [ ] Documented in README