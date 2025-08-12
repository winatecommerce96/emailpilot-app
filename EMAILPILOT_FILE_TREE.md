# EmailPilot Application - Complete File Tree and Dependencies

## Project Structure Overview

```
emailpilot-app/
├── Backend (FastAPI/Python)
│   ├── main_firestore.py (PRIMARY ENTRY POINT - Firebase/Firestore integration)
│   ├── main.py (Alternative entry point)
│   ├── main_with_db.py (Database-focused entry)
│   └── app/
│       ├── api/ (30+ API route modules)
│       ├── models/ (SQLAlchemy ORM models)
│       ├── schemas/ (Pydantic validation schemas)
│       ├── services/ (Business logic services)
│       ├── core/ (Configuration and database setup)
│       └── deps/ (Dependencies - Firestore)
│
├── Frontend (React/JavaScript)
│   └── frontend/
│       └── public/
│           ├── app.js (Main React application)
│           ├── index.html (Main entry point)
│           ├── components/ (25+ React components)
│           └── dist/ (Compiled JavaScript bundles)
│
├── Calendar Implementation
│   ├── calendar-implementation-complete/ (Main calendar module)
│   ├── calendar-project/ (Standalone calendar project)
│   ├── calendar-react-feature/ (React-based calendar)
│   └── Multiple backup/version directories
│
├── MCP Integration (Model Context Protocol)
│   └── email-sms-mcp-server/
│       ├── server.py (MCP server implementation)
│       ├── agents_config.json (Agent configurations)
│       └── Docker deployment files
│
├── Database Files
│   ├── emailpilot.db (SQLite database)
│   └── Firestore integration (real-time sync)
│
├── Configuration & Deployment
│   ├── requirements.txt (Python dependencies)
│   ├── package.json (Node dependencies)
│   ├── Makefile (Build automation)
│   ├── Dockerfile (Container configuration)
│   └── Multiple deployment scripts
│
└── Documentation & Tests
    ├── CLAUDE.md (AI team configuration)
    ├── Multiple test files (test_*.py)
    └── Various documentation files (*.md)
```

## Complete File Listing

### Root Level Files
```
emailpilot-app/
├── main_firestore.py              # Primary FastAPI application with Firebase
├── main.py                        # Alternative FastAPI entry point
├── main_with_db.py               # Database-focused FastAPI entry
├── firebase_calendar_integration.py
├── firebase_goals_calendar_integration.py
├── emailpilot.db                 # SQLite database file
├── requirements.txt              # Python dependencies
├── package.json                  # Node.js dependencies
├── package-lock.json
├── Makefile                      # Build automation
├── Dockerfile                    # Container configuration
├── .env                         # Environment variables (not in git)
├── .gitignore
├── CLAUDE.md                    # AI team configuration
├── README.md                    # Project documentation
```

### Backend Structure (app/)
```
app/
├── __init__.py
├── main.py                      # App module entry
│
├── api/                         # API Route Modules (30+ endpoints)
│   ├── __init__.py
│   ├── admin.py                # Admin dashboard endpoints
│   ├── admin_agents.py         # Admin agent management
│   ├── admin_clients.py        # Client administration
│   ├── admin_firestore.py      # Firestore admin operations
│   ├── auth.py                 # Authentication endpoints
│   ├── calendar.py             # Calendar operations
│   ├── clients.py              # Client management
│   ├── dashboard.py            # Dashboard data endpoints
│   ├── email_sms_agents.py    # Email/SMS agent endpoints
│   ├── firebase_calendar.py   # Firebase calendar integration
│   ├── goals.py                # Goals management
│   ├── mcp.py                  # MCP integration
│   ├── mcp_firestore.py       # MCP Firestore sync
│   ├── mcp_klaviyo.py         # Klaviyo MCP integration
│   ├── mcp_local.py           # Local MCP operations
│   ├── performance.py         # Performance monitoring
│   ├── reports.py             # Report generation
│   └── slack.py               # Slack integration
│
├── models/                     # SQLAlchemy ORM Models
│   ├── __init__.py
│   ├── calendar.py            # Calendar event models
│   ├── client.py              # Client data models
│   ├── goal.py                # Goals and objectives
│   ├── mcp_client.py          # MCP client models
│   └── report.py              # Report models
│
├── schemas/                    # Pydantic Validation Schemas
│   ├── admin.py               # Admin data schemas
│   ├── auth.py                # Authentication schemas
│   ├── calendar.py            # Calendar event schemas
│   ├── client.py              # Client data schemas
│   ├── goal.py                # Goal schemas
│   ├── mcp_client.py          # MCP client schemas
│   ├── performance.py         # Performance schemas
│   └── report.py              # Report schemas
│
├── services/                   # Business Logic Services
│   ├── calendar_service.py    # Calendar operations
│   ├── env_manager.py         # Environment management
│   ├── firestore_client.py    # Firestore operations
│   ├── gemini_service.py      # Gemini AI integration
│   ├── goal_generator.py      # Goal generation logic
│   ├── goal_manager.py        # Goal management
│   ├── google_service.py      # Google API integration
│   ├── klaviyo_direct.py      # Direct Klaviyo API
│   ├── mcp_firestore_sync.py  # MCP-Firestore sync
│   ├── mcp_service.py         # MCP operations
│   ├── performance_monitor.py # Performance tracking
│   ├── report_generator.py    # Report generation
│   └── secret_manager.py      # GCP Secret Manager
│
├── core/                       # Core Configuration
│   ├── auth.py                # Authentication logic
│   ├── config.py              # Application config
│   └── database.py            # Database setup
│
└── deps/                       # Dependencies
    └── firestore.py           # Firestore dependencies
```

### Frontend Structure
```
frontend/
└── public/
    ├── app.js                  # Main React application
    ├── index.html              # Main HTML entry
    ├── admin-agents.html       # Admin agents page
    │
    ├── components/             # React Components (25+)
    │   ├── AdminClientManagement.js
    │   ├── Calendar.js
    │   ├── CalendarChat.js
    │   ├── CalendarView.js
    │   ├── CalendarViewEnhanced.js
    │   ├── CalendarViewFirebase.js
    │   ├── CalendarViewLocal.js
    │   ├── CalendarViewSimple.js
    │   ├── DevLogin.js
    │   ├── EmailPilotCalendarTab.js
    │   ├── EventModal.js
    │   ├── FirebaseCalendarCore.js
    │   ├── FirebaseCalendarService.js
    │   ├── GeminiChatService.js
    │   ├── GoalGeneratorPanel.js
    │   ├── GoalsAwareCalendarDashboard.js
    │   ├── GoalsCompanyDashboard.js
    │   ├── GoalsDashboard.js
    │   ├── GoalsDataStatus.js
    │   ├── GoalsEnhancedDashboard.js
    │   ├── MCPFirestoreSync.js
    │   ├── MCPKlaviyoManagement.js
    │   ├── MCPManagement.js
    │   ├── MCPManagementLocal.js
    │   └── UnifiedClientForm.js
    │
    └── dist/                   # Compiled JavaScript
        ├── app.js              # Compiled main app
        └── [Component bundles]
```

### Calendar Implementation
```
calendar-implementation-complete/
├── backend/
│   ├── api/                    # Calendar API modules
│   ├── models/                 # Calendar models
│   ├── schemas/                # Calendar schemas
│   └── services/               # Calendar services
│
├── frontend/
│   ├── components/             # Calendar React components
│   └── html/                   # Calendar HTML templates
│
├── integrations/               # Integration scripts
├── scripts/                    # Deployment scripts
├── test-files/                 # Calendar tests
└── documentation/              # Calendar docs
```

### MCP Server
```
email-sms-mcp-server/
├── server.py                   # Main MCP server
├── enhanced_server.py          # Enhanced version
├── server_http.py              # HTTP server variant
├── agents_config.json          # Agent configurations
├── agent_instructions.py       # Agent instructions
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container config
├── cloudbuild.yaml            # GCP Cloud Build
└── deploy_to_cloud.sh         # Deployment script
```

### Scripts and Utilities
```
scripts/
├── build_frontend.sh           # Frontend build script
├── component_registrar.py      # Component registration
├── health_checker.py           # Health check utility
├── rollback_manager.sh         # Rollback management
└── service_manager.sh          # Service management

Test Files:
├── test_admin_endpoints.py
├── test_admin_agents.py
├── test_calendar_local.py
├── test_endpoints.py
├── test_firestore_api.py
├── test_klaviyo_connection.py
├── test_mcp_models.py
├── test_multi_agent_local.py
├── test_openai_key.py
├── test_routes.py
├── test_server.py
└── test_urls.py
```

### Deployment Scripts
```
├── deploy_mcp_to_cloud_run.sh
├── start_calendar_dev.sh
├── fix_calendar_tab.sh
├── populate_mcp_models.py
├── check_active_models.py
├── debug_routes.py
└── extract_routes.py
```

## Key Dependencies

### Python Dependencies (requirements.txt)
- FastAPI (Web framework)
- SQLAlchemy (ORM)
- Pydantic (Data validation)
- Firebase Admin SDK
- Google Cloud libraries
- Klaviyo API client
- OpenAI/Gemini AI SDKs
- Uvicorn (ASGI server)

### JavaScript Dependencies (package.json)
- React (loaded via CDN)
- TailwindCSS (loaded via CDN)
- Firebase JavaScript SDK
- esbuild (bundler)

## Database Schema

### SQLite Tables (emailpilot.db)
- clients (Client information)
- calendar_events (Campaign calendar)
- goals (Client goals)
- reports (Generated reports)
- mcp_models (MCP configurations)
- users (Authentication)

### Firestore Collections
- clients (Real-time client data)
- calendar (Real-time calendar events)
- goals (Real-time goals)
- mcp_agents (Agent configurations)

## API Endpoints Structure

### Main API Groups
- `/api/auth/*` - Authentication
- `/api/admin/*` - Admin operations
- `/api/calendar/*` - Calendar management
- `/api/clients/*` - Client operations
- `/api/goals/*` - Goals management
- `/api/reports/*` - Report generation
- `/api/mcp/*` - MCP operations
- `/api/performance/*` - Performance metrics

## Environment Variables Required
- GOOGLE_APPLICATION_CREDENTIALS
- FIREBASE_CONFIG
- KLAVIYO_API_KEY
- OPENAI_API_KEY
- GEMINI_API_KEY
- DATABASE_URL
- SECRET_KEY
- SLACK_WEBHOOK_URL

## Build and Deployment

### Local Development
```bash
# Backend
uvicorn main_firestore:app --reload --port 8000

# Frontend build
npm run build

# Or use Makefile
make dev
```

### Production Deployment
- Docker containerization
- Google Cloud Run deployment
- Firebase hosting for static assets
- Cloud SQL for production database

## Integration Points

### External Services
1. **Klaviyo API** - Campaign automation
2. **Google APIs** - Calendar, Docs, Sheets
3. **Firebase/Firestore** - Real-time sync
4. **OpenAI/Gemini** - AI content generation
5. **Slack** - Notifications
6. **Google Cloud Platform** - Infrastructure

### Internal Integration
1. Calendar ↔ Client Management
2. Goals ↔ Campaign Planning
3. MCP Agents ↔ Automation Tasks
4. Reports ↔ Performance Metrics
5. Admin Dashboard ↔ All Systems

This structure represents a mature, production-ready application with proper separation of concerns, comprehensive testing, and scalable architecture.