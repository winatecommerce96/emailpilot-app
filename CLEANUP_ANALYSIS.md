# EmailPilot Calendar App - Non-Calendar Code Cleanup Analysis

## Summary
The calendar application uses only a subset of the features in emailpilot-app. This document identifies files that can be safely removed without affecting calendar functionality.

## Calendar Dependencies (KEEP)

### Core Calendar API Files
- `app/api/calendar.py` - Main calendar operations
- `app/api/calendar_chat.py` - AI chat interface
- `app/api/calendar_enhanced.py` - Enhanced calendar features
- `app/api/calendar_grader.py` - Campaign grading
- `app/api/calendar_holidays.py` - Holiday management
- `app/api/calendar_langsmith.py` - LangSmith tracing
- `app/api/calendar_orchestrator_v2.py` - Multi-agent orchestration
- `app/api/calendar_planning_ai.py` - AI planning
- `app/api/calendar_planning_templates.py` - Campaign templates
- `app/api/calendar_planning.py` - Planning features
- `app/api/calendar_workflow_agents.py` - Workflow agents
- `app/api/calendar_workflow_api.py` - Workflow API
- `app/api/firebase_calendar.py` - Firebase integration

### Supporting API Files
- `app/api/goals.py` - Monthly goals (used by calendar)
- `app/api/clients_public.py` - Client data for calendar
- `app/api/admin_clients.py` - Client management
- `app/api/auth.py` - Authentication
- `app/api/auth_v2.py` - Auth v2
- `app/api/clerk_auth.py` - Clerk integration
- `app/api/comprehensive_query.py` - Query handler
- `app/api/natural_query.py` - Natural language queries

### AI/MCP Integration (used by calendar AI features)
- `app/api/mcp_gateway.py` - MCP routing
- `app/api/mcp_natural_language.py` - NL interface
- `app/api/mcp_klaviyo.py` - Klaviyo MCP
- `app/api/mcp_registry.py` - MCP registry
- `app/api/mcp_management.py` - MCP management
- `app/api/agent_creator.py` - Agent creation
- `app/api/agent_config.py` - Agent configuration

### Frontend Files
- `frontend/public/calendar_master.html` - Main calendar interface
- `frontend/public/calendar_master.css` - Calendar styles
- `frontend/public/calendar_master.js` - Calendar JavaScript

---

## Non-Calendar Code (CAN BE REMOVED)

### 1. Asana Integration (3 files)
**Purpose**: Project management integration - NOT used by calendar

API Files:
- `app/api/admin_asana.py`
- `app/api/asana.py`
- `app/api/asana_oauth.py`

### 2. Reports & Analytics (4 files)
**Purpose**: Business intelligence dashboards - NOT used by calendar

API Files:
- `app/api/reports.py`
- `app/api/reports_mcp.py`
- `app/api/reports_mcp_v2.py`
- `app/api/dashboard.py`
- `app/api/performance.py`

### 3. Slack Integration (1 file)
**Purpose**: Slack notifications - NOT used by calendar

API Files:
- `app/api/slack.py`

### 4. Workflow Builder (5 files)
**Purpose**: LangChain workflow visual editor - NOT used by calendar operation

API Files:
- `app/api/workflow.py`
- `app/api/workflow_fixed.py`
- `app/api/workflow_generation.py`
- `app/api/workflow_templates.py`
- `app/api/hub.py`

Frontend Files:
- `frontend/public/workflow_builder.html`
- `frontend/public/workflow_builder_ai.html`
- `frontend/public/workflow_editor.html`
- `frontend/public/workflow_hub.html`
- `frontend/public/workflow_library.html`
- `frontend/public/workflow_manager.html`
- `frontend/public/workflow_wizard.html`

### 5. General Admin Panels (7 files)
**Purpose**: System administration - NOT needed for calendar operation

API Files:
- `app/api/admin.py` (package upload, general admin)
- `app/api/admin_agents.py`
- `app/api/admin_firestore.py`
- `app/api/admin_notifications.py`
- `app/api/admin_secret_manager.py`
- `app/api/admin_services.py`
- `app/api/admin_users.py`

Frontend Files:
- `frontend/public/admin_agents.html`
- `frontend/public/admin_dashboard.html`

### 6. Klaviyo Discovery & Feedback (2 files)
**Purpose**: Klaviyo API exploration tools - NOT used by calendar

API Files:
- `app/api/klaviyo_discovery.py`
- `app/api/klaviyo_feedback.py`

### 7. Legacy/Deprecated Files (5 files)
**Purpose**: Old implementations or duplicates

API Files:
- `app/api/goals_old.py` - Replaced by goals.py
- `app/api/goals2.py` - Empty duplicate
- `app/api/agents.py` - Replaced by agents_unified.py
- `app/api/ai_orchestrator.py` - Replaced by LangChain
- `app/api/email_sms_agents.py.deprecated`

### 8. Test & Development Files (10+ files)
**Purpose**: Testing interfaces - NOT needed for production calendar

Frontend Files:
- `frontend/public/test*.html` (all test files)
- `frontend/public/clerk-auth-test.html`
- `frontend/public/klaviyo_*_test.html`
- `frontend/public/mcp_chat.html` (test interface)
- `frontend/public/CHECK_FIRESTORE_PERMISSIONS.html`

### 9. Advanced Admin Tools (5 files)
**Purpose**: Developer tools - NOT needed for calendar operation

Frontend Files:
- `frontend/public/agent_creator_enhanced.html`
- `frontend/public/agent_editor.html`
- `frontend/public/backfill_manager.html`
- `frontend/public/langchain_dashboard.html`
- `frontend/public/langchain_debug.html`
- `frontend/public/langchain_debug_editor.html`
- `frontend/public/llm_selector_demo.html`
- `frontend/public/mcp_tools.html`

---

## Cleanup Plan

### Phase 1: Remove Non-Essential API Files (Conservative)
Remove only files that are clearly NOT used by calendar:
- Asana integration (3 files)
- Reports/Analytics (5 files)
- Slack integration (1 file)
- Workflow builders (5 files)
- Legacy/deprecated (5 files)
- Klaviyo discovery (2 files)

**Total: ~21 API files**

### Phase 2: Remove Non-Calendar Frontend Files
Remove HTML files not related to calendar:
- Workflow UIs (~7 files)
- Admin panels (~2 files)
- Test files (~10 files)
- Advanced admin tools (~8 files)

**Total: ~27 HTML files**

### Phase 3: Clean Up Dependencies (After Testing)
Once calendar is confirmed working, remove unused:
- Python packages from requirements.txt
- Services not used by calendar
- Middleware not needed

---

## Risk Assessment

### LOW RISK (Safe to Remove)
- Asana integration
- Reports/Analytics
- Slack integration
- Legacy/deprecated files
- Test HTML files

### MEDIUM RISK (Test After Removal)
- Workflow builder files
- Admin panel files
- Advanced admin tools

### HIGH RISK (Keep for Now)
- Any MCP/AI/LangChain files (calendar uses AI)
- Auth files (calendar requires auth)
- Client management (calendar needs clients)
- Goals API (calendar displays goals)

---

## Execution Steps

1. **Backup complete** ✅ (Already done: emailpilot-app-ARCHIVE.tar.gz)
2. **Create removal script** to move files to archive directory
3. **Test calendar after each phase**
4. **Update main_firestore.py** to remove router imports
5. **Clean up requirements.txt** after all removals
6. **Update CLAUDE.md** to reflect simplified structure

---

## Expected Results

- **Reduced API files**: From 88 to ~67 files (~24% reduction)
- **Reduced frontend files**: Significant reduction in HTML files
- **Cleaner codebase**: Easier to navigate and maintain
- **Faster startup**: Fewer imports and routers to load
- **Calendar functionality**: UNCHANGED
