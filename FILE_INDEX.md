# EmailPilot Application - Complete File Index

## 1. Core Application Code

### Main Application Files
- [`main_firestore.py`](main_firestore.py) - Primary FastAPI application with Firestore integration
- [`main.py`](main.py) - Alternative simple FastAPI application
- [`app/__init__.py`](app/__init__.py) - App package initialization
- [`app/main.py`](app/main.py) - App module main file

### API Endpoints (`app/api/`)
- [`app/api/__init__.py`](app/api/__init__.py)
- [`app/api/admin.py`](app/api/admin.py) - Admin endpoints
- [`app/api/admin_agents.py`](app/api/admin_agents.py) - Admin agent management
- [`app/api/admin_clients.py`](app/api/admin_clients.py) - Client administration
- [`app/api/admin_firestore.py`](app/api/admin_firestore.py) - Firestore admin config
- [`app/api/auth.py`](app/api/auth.py) - Authentication endpoints
- [`app/api/calendar.py`](app/api/calendar.py) - Calendar API
- [`app/api/clients.py`](app/api/clients.py) - Client management
- [`app/api/dashboard.py`](app/api/dashboard.py) - Dashboard endpoints
- [`app/api/email_sms_agents.py`](app/api/email_sms_agents.py) - Email/SMS agent system
- [`app/api/firebase_calendar.py`](app/api/firebase_calendar.py) - Firebase calendar integration
- [`app/api/goals.py`](app/api/goals.py) - Goals management (Firestore-based)
- [`app/api/goals_aware_calendar.py`](app/api/goals_aware_calendar.py) - Goals-integrated calendar
- [`app/api/mcp.py`](app/api/mcp.py) - MCP management
- [`app/api/mcp_firestore.py`](app/api/mcp_firestore.py) - MCP Firestore integration
- [`app/api/mcp_klaviyo.py`](app/api/mcp_klaviyo.py) - MCP Klaviyo integration
- [`app/api/mcp_local.py`](app/api/mcp_local.py) - Local MCP management
- [`app/api/performance.py`](app/api/performance.py) - Performance metrics API
- [`app/api/reports.py`](app/api/reports.py) - Reports API
- [`app/api/slack.py`](app/api/slack.py) - Slack integration

### Core Configuration (`app/core/`)
- [`app/core/auth.py`](app/core/auth.py) - Authentication core
- [`app/core/config.py`](app/core/config.py) - Application configuration
- [`app/core/database.py`](app/core/database.py) - Database configuration

### Dependencies (`app/deps/`)
- [`app/deps/firestore.py`](app/deps/firestore.py) - Firestore dependency injection

### Data Models (`app/models/`)
- [`app/models/__init__.py`](app/models/__init__.py)
- [`app/models/calendar.py`](app/models/calendar.py) - Calendar models
- [`app/models/client.py`](app/models/client.py) - Client models
- [`app/models/goal.py`](app/models/goal.py) - Goal models
- [`app/models/mcp_client.py`](app/models/mcp_client.py) - MCP client models
- [`app/models/report.py`](app/models/report.py) - Report models

### Schemas (`app/schemas/`)
- [`app/schemas/admin.py`](app/schemas/admin.py) - Admin schemas
- [`app/schemas/auth.py`](app/schemas/auth.py) - Auth schemas
- [`app/schemas/calendar.py`](app/schemas/calendar.py) - Calendar schemas
- [`app/schemas/client.py`](app/schemas/client.py) - Client schemas
- [`app/schemas/goal.py`](app/schemas/goal.py) - Goal schemas
- [`app/schemas/mcp_client.py`](app/schemas/mcp_client.py) - MCP client schemas
- [`app/schemas/performance.py`](app/schemas/performance.py) - Performance schemas
- [`app/schemas/report.py`](app/schemas/report.py) - Report schemas

### Services (`app/services/`)
- [`app/services/calendar_service.py`](app/services/calendar_service.py) - Calendar business logic
- [`app/services/env_manager.py`](app/services/env_manager.py) - Environment management
- [`app/services/firestore_client.py`](app/services/firestore_client.py) - Firestore client wrapper
- [`app/services/gemini_service.py`](app/services/gemini_service.py) - Gemini AI service
- [`app/services/goal_generator.py`](app/services/goal_generator.py) - Goal generation service
- [`app/services/goal_manager.py`](app/services/goal_manager.py) - Goal management service
- [`app/services/goals_aware_gemini_service.py`](app/services/goals_aware_gemini_service.py) - Goals-aware AI
- [`app/services/google_service.py`](app/services/google_service.py) - Google APIs service
- [`app/services/klaviyo_client.py`](app/services/klaviyo_client.py) - Klaviyo API client
- [`app/services/klaviyo_direct.py`](app/services/klaviyo_direct.py) - Direct Klaviyo integration
- [`app/services/mcp_firestore_sync.py`](app/services/mcp_firestore_sync.py) - MCP-Firestore sync
- [`app/services/mcp_service.py`](app/services/mcp_service.py) - MCP service layer
- [`app/services/performance_monitor.py`](app/services/performance_monitor.py) - Performance monitoring
- [`app/services/report_generator.py`](app/services/report_generator.py) - Report generation
- [`app/services/secret_manager.py`](app/services/secret_manager.py) - Secret management

## 2. Project Configuration & Environment

### Requirements Files
- [`requirements.txt`](requirements.txt) - Main Python dependencies
- [`requirements_firestore.txt`](requirements_firestore.txt) - Firestore-specific dependencies
- [`requirements_simple.txt`](requirements_simple.txt) - Minimal dependencies
- [`test_requirements.txt`](test_requirements.txt) - Testing dependencies

### Docker & Build Configuration
- [`Dockerfile`](Dockerfile) - Main Docker configuration
- [`Dockerfile.simple`](Dockerfile.simple) - Simple Docker configuration
- [`docker-compose.yml`](docker-compose.yml) - Docker Compose configuration (if exists)
- [`cloudbuild.yaml`](cloudbuild.yaml) - Google Cloud Build configuration

### Environment Configuration
- [`.env.example`](.env.example) - Example environment variables (if exists)
- [`.gitignore`](.gitignore) - Git ignore configuration

### Firestore Configuration
- [`firestore.indexes.json`](firestore.indexes.json) - Firestore index definitions

## 3. Deployment & Local Run Scripts

### Deployment Scripts
- [`deploy.sh`](deploy.sh) - Main deployment script
- [`deploy_master.sh`](deploy_master.sh) - Master deployment script
- [`deploy_with_secrets.sh`](deploy_with_secrets.sh) - Deployment with secrets
- [`deploy_to_cloud.sh`](deploy_to_cloud.sh) - Cloud deployment (if exists)

### Local Development Scripts
- [`startup.sh`](startup.sh) - Application startup script
- [`start_calendar_dev.sh`](start_calendar_dev.sh) - Calendar development startup
- [`restart.sh`](restart.sh) - Server restart script
- [`verify_and_start.sh`](verify_and_start.sh) - Verification and startup script
- [`archive_old_calendars.sh`](archive_old_calendars.sh) - Archive old implementations

### Utility Scripts
- [`scripts/build_frontend.sh`](scripts/build_frontend.sh) - Frontend build script
- [`scripts/component_registrar.py`](scripts/component_registrar.py) - Component registration
- [`scripts/health_checker.py`](scripts/health_checker.py) - Health check utility
- [`scripts/rollback_manager.sh`](scripts/rollback_manager.sh) - Rollback management
- [`scripts/service_manager.sh`](scripts/service_manager.sh) - Service management
- [`scripts/validate_dev_env.sh`](scripts/validate_dev_env.sh) - Environment validation

## 4. Documentation

### Main Documentation
- [`README.md`](README.md) - Main project README (if exists)
- [`EMAILPILOT_SETUP.md`](EMAILPILOT_SETUP.md) - EmailPilot setup guide
- [`production_deployment_guide.md`](production_deployment_guide.md) - Production deployment
- [`CALENDAR_IMPLEMENTATION_GUIDE.md`](CALENDAR_IMPLEMENTATION_GUIDE.md) - Calendar implementation guide
- [`CLAUDE.md`](CLAUDE.md) - AI assistant instructions

### Additional Documentation
- [`CALENDAR_DEPLOYMENT_READY.md`](CALENDAR_DEPLOYMENT_READY.md)
- [`CALENDAR_LOCAL_READY.md`](CALENDAR_LOCAL_READY.md)
- [`CALENDAR_LOCAL_DEV.md`](CALENDAR_LOCAL_DEV.md)
- [`CALENDAR_TAB_FIX.md`](CALENDAR_TAB_FIX.md)
- [`SECRET_MANAGER_MIGRATION.md`](SECRET_MANAGER_MIGRATION.md)

## 5. Test Coverage

### Main Test Files
- [`test_main.py`](test_main.py) - Main application tests
- [`test_admin_endpoints.py`](test_admin_endpoints.py) - Admin endpoint tests
- [`test_admin_agents.py`](test_admin_agents.py) - Admin agent tests
- [`test_auth.py`](test_auth.py) - Authentication tests (if exists)
- [`test_calendar_route.py`](test_calendar_route.py) - Calendar route tests
- [`test_calendar_local.py`](test_calendar_local.py) - Local calendar tests
- [`test_compatibility.py`](test_compatibility.py) - Compatibility tests
- [`test_endpoints.py`](test_endpoints.py) - General endpoint tests
- [`test_firebase_calendar_local.py`](test_firebase_calendar_local.py) - Firebase calendar tests
- [`test_firestore_api.py`](test_firestore_api.py) - Firestore API tests
- [`test_klaviyo_connection.py`](test_klaviyo_connection.py) - Klaviyo connection tests
- [`test_live_api.py`](test_live_api.py) - Live API tests
- [`test_local_calendar.py`](test_local_calendar.py) - Local calendar tests
- [`test_mcp_firestore_sync.py`](test_mcp_firestore_sync.py) - MCP-Firestore sync tests
- [`test_mcp_models.py`](test_mcp_models.py) - MCP model tests
- [`test_multi_agent_local.py`](test_multi_agent_local.py) - Multi-agent tests
- [`test_openai_key.py`](test_openai_key.py) - OpenAI key tests
- [`test_package_extraction.py`](test_package_extraction.py) - Package extraction tests
- [`test_routes.py`](test_routes.py) - Route tests
- [`test_secret_manager.py`](test_secret_manager.py) - Secret manager tests
- [`test_server.py`](test_server.py) - Server tests
- [`test_urls.py`](test_urls.py) - URL tests

### Test Utilities
- [`final_test.py`](final_test.py) - Final integration tests
- [`inspect_firestore.py`](inspect_firestore.py) - Firestore inspection utility
- [`check_active_models.py`](check_active_models.py) - Model checking utility
- [`check_package_compatibility.py`](check_package_compatibility.py) - Compatibility checker
- [`debug_routes.py`](debug_routes.py) - Route debugging utility
- [`extract_routes.py`](extract_routes.py) - Route extraction utility
- [`populate_mcp_models.py`](populate_mcp_models.py) - MCP model population

## 6. Frontend Files

### Main Frontend Directory
- [`frontend/public/index.html`](frontend/public/index.html) - Main HTML entry point
- [`frontend/public/app.js`](frontend/public/app.js) - Main React application
- [`frontend/public/logo.png`](frontend/public/logo.png) - Application logo
- [`frontend/public/logo2.png`](frontend/public/logo2.png) - Alternative logo

### React Components (`frontend/public/components/`)
- [`frontend/public/components/Calendar.js`](frontend/public/components/Calendar.js)
- [`frontend/public/components/CalendarChat.js`](frontend/public/components/CalendarChat.js)
- [`frontend/public/components/CalendarView.js`](frontend/public/components/CalendarView.js)
- [`frontend/public/components/CalendarViewLocal.js`](frontend/public/components/CalendarViewLocal.js)
- [`frontend/public/components/CalendarViewSimple.js`](frontend/public/components/CalendarViewSimple.js)
- [`frontend/public/components/EventModal.js`](frontend/public/components/EventModal.js)
- [`frontend/public/components/FirebaseCalendarService.js`](frontend/public/components/FirebaseCalendarService.js)
- [`frontend/public/components/GeminiChatService.js`](frontend/public/components/GeminiChatService.js)
- [`frontend/public/components/GoalGeneratorPanel.js`](frontend/public/components/GoalGeneratorPanel.js)
- [`frontend/public/components/GoalsAwareCalendarDashboard.js`](frontend/public/components/GoalsAwareCalendarDashboard.js)
- [`frontend/public/components/GoalsCompanyDashboard.js`](frontend/public/components/GoalsCompanyDashboard.js)
- [`frontend/public/components/GoalsDashboard.js`](frontend/public/components/GoalsDashboard.js)
- [`frontend/public/components/GoalsDataStatus.js`](frontend/public/components/GoalsDataStatus.js)
- [`frontend/public/components/GoalsEnhancedDashboard.js`](frontend/public/components/GoalsEnhancedDashboard.js)
- [`frontend/public/components/AdminClientManagement.js`](frontend/public/components/AdminClientManagement.js)
- [`frontend/public/components/DevLogin.js`](frontend/public/components/DevLogin.js)
- [`frontend/public/components/MCPKlaviyoManagement.js`](frontend/public/components/MCPKlaviyoManagement.js)
- [`frontend/public/components/MCPManagementLocal.js`](frontend/public/components/MCPManagementLocal.js)

### Compiled Frontend (`frontend/public/dist/`)
- All compiled JavaScript files from components

## 7. Additional Configuration Files

### Makefile
- [`Makefile`](Makefile) - Development commands and shortcuts

### Package Management
- [`package.json`](package.json) - Node.js dependencies (if exists)
- [`package-lock.json`](package-lock.json) - Locked Node.js dependencies (if exists)

### Database Files
- [`emailpilot.db`](emailpilot.db) - SQLite database (if using SQLite)
- [`sample_client_document.json`](sample_client_document.json) - Sample Firestore document structure

---

## Quick Access Commands

### Start Development Server
```bash
make dev
# or
./verify_and_start.sh
# or
uvicorn main_firestore:app --reload --port 8000
```

### Run Tests
```bash
make test
# or
pytest test_*.py -v
```

### Deploy to Production
```bash
./deploy.sh
# or
make deploy
```

### Check Health
```bash
make health
# or
curl http://localhost:8000/health
```

---

*Last updated: December 2024*
*All paths are relative to `/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/`*