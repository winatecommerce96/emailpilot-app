# 🚀 EmailPilot UI Quick Reference Card

## Adding a New UI Feature in 3 Steps

### Step 1: Create Component
```javascript
// frontend/public/components/YourFeature.js
const YourFeature = () => {
  return React.createElement('div', null, 'Hello World');
};
window.YourFeature = YourFeature; // ← CRITICAL!
```

### Step 2: Add to Build
```bash
# scripts/build_frontend.sh line 46
JSX_COMPONENTS=(
    "YourFeature"  # ← Add here
    # ... others
)
```

### Step 3: Include in HTML
```html
<!-- frontend/public/index.html line ~470 -->
<script src="/static/dist/YourFeature.js"></script>
```

### Build & Run
```bash
npm run build
uvicorn main_firestore:app --port 8000 --host localhost
```

---

## Quick Actions (Easy Way)

Edit `frontend/public/components/QuickActionsFramework.js`:
```javascript
const QUICK_ACTIONS_CONFIG = [
  {
    id: 'your-feature',
    icon: '🎯',
    title: 'Your Feature',
    subtitle: 'Description',
    onClick: () => setActiveTab('your-feature'),
    enabled: true
  }
];
```

---

## Common Issues & Fixes

| Problem | Solution |
|---------|----------|
| Feature not appearing | Check script tag in index.html |
| Component undefined | Did you export to `window`? |
| Changes not showing | Run `npm run build` |
| Cache issues | Hard refresh: Cmd+Shift+R |
| Build errors | Check component syntax |

---

## Essential Commands

```bash
# Build frontend
npm run build

# Start server
uvicorn main_firestore:app --port 8000 --host localhost

# Check if component built
ls -la frontend/public/dist/YourFeature.js

# Find your component in HTML
grep "YourFeature" frontend/public/index.html

# Test in browser console
console.log(window.YourFeature);
```

---

## File Locations

| What | Where |
|------|-------|
| Create components | `frontend/public/components/` |
| Build config | `scripts/build_frontend.sh` |
| HTML includes | `frontend/public/index.html` |
| Built files | `frontend/public/dist/` |
| Main app | `frontend/public/app.js` |

---

## Need Help?

1. Check browser console for errors
2. Run: `python diagnose_frontend_gaps.py`
3. Use Developer Tools in admin Quick Actions
4. Read: [Full UI Development Guide](UI_DEVELOPMENT_GUIDE.md)

---

**Remember**: Component → Build → Include → Test