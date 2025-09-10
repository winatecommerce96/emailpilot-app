# Calendar Master Restore Instructions

## Quick Restore (Emergency Rollback)

If you need to quickly restore calendar_master functionality, run these commands:

```bash
# 1. Backup current version (optional)
cp frontend/public/calendar_master.html frontend/public/calendar_master.html.backup-$(date +%Y%m%d-%H%M%S)

# 2. Restore the working version
cp calendar_master_backup_2025-09-08/calendar_master.html frontend/public/

# 3. Ensure API files are in place (if needed)
cp calendar_master_backup_2025-09-08/api/calendar_chat.py app/api/
cp calendar_master_backup_2025-09-08/services/ai_models_service.py app/services/
```

## Full Restore Process

### Step 1: Verify Server Dependencies
```bash
# Check if these packages are installed
pip show openai anthropic google-generativeai

# If not installed:
pip install openai>=1.0 anthropic>=0.8 google-generativeai>=0.3
```

### Step 2: Restore Files
```bash
# Frontend
cp calendar_master_backup_2025-09-08/calendar_master.html frontend/public/

# API files
cp calendar_master_backup_2025-09-08/api/calendar*.py app/api/
cp calendar_master_backup_2025-09-08/api/admin.py app/api/
cp calendar_master_backup_2025-09-08/api/goals.py app/api/

# Services
cp calendar_master_backup_2025-09-08/services/*.py app/services/
```

### Step 3: Verify Server Configuration
Ensure `main_firestore.py` includes these router imports:

```python
from app.api.calendar_chat import router as calendar_chat_router
from app.api.admin import router as admin_router
from app.api.goals import router as goals_router
from app.api.calendar import router as calendar_router

# And includes them in the app:
app.include_router(calendar_chat_router)
app.include_router(admin_router)
app.include_router(goals_router)
app.include_router(calendar_router)
```

### Step 4: Test Key Functionality

1. **Server Health Check**:
```bash
curl http://localhost:8000/health
```

2. **Client Loading**:
```bash
curl http://localhost:8000/api/admin/clients | python3 -m json.tool
```

3. **LLM Chat Test**:
```bash
curl -X POST http://localhost:8000/api/calendar/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a campaign called Test Campaign on the 15th",
    "context": {"current_month": "October 2025"},
    "provider": "gemini"
  }' | python3 -m json.tool
```

### Step 5: Verify Frontend Functionality

1. Open `http://localhost:8000/static/calendar_master.html`
2. Select a client from dropdown
3. Test chat: "Add a campaign called Test Event on the 20th"
4. Switch to List View and verify icons work (copy, edit, delete)
5. Create a campaign manually and test drag & drop

## Troubleshooting

### If LLM Chat Doesn't Work:
- Check Google Secret Manager has keys: `emailpilot-claude`, `openai-api-key`, `gemini-api-key`
- Verify server logs for authentication errors
- Test with `provider: "regex"` as fallback

### If List View Icons Don't Work:
- Clear browser cache
- Check console for JavaScript errors
- Verify Font Awesome CSS is loading

### If Calendar Doesn't Load:
- Check `/api/admin/clients` returns data
- Verify Firestore connection
- Check client has `is_active: true` and `has_klaviyo_key: true`

## File Manifest

### Critical Files for Core Functionality:
- `calendar_master.html` - Main interface ⭐
- `calendar_chat.py` - LLM integration ⭐
- `ai_models_service.py` - AI service ⭐
- `admin.py` - Client management
- `calendar.py` - Event CRUD

### Enhanced Features:
- `calendar_grader.py` - Performance grading
- `calendar_workflow_api.py` - AI workflows
- `goals.py` - Goals integration

### Supporting Services:
- `client_key_resolver.py` - API key management
- `secrets.py` - Secret management

## Rollback Strategy

If restore causes issues:

```bash
# Quick rollback to backup
cp frontend/public/calendar_master.html.backup-* frontend/public/calendar_master.html

# Or restore from git
git checkout HEAD -- frontend/public/calendar_master.html
git checkout HEAD -- app/api/calendar_chat.py
```

## Testing Checklist

- [ ] Server starts without errors
- [ ] Calendar loads with client selection
- [ ] Chat responds to "Create test campaign"
- [ ] List view icons (copy/edit/delete) work
- [ ] Calendar grading functions
- [ ] Events save to Firestore
- [ ] Drag & drop between dates works
- [ ] Multiple LLM providers selectable

---

**Last Updated**: September 8, 2025
**Backup Version**: Enhanced Calendar Master with LLM Integration