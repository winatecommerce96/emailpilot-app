# EmailPilot Development Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev dev dev-emu dev-simple test test-all test-calendar build deploy clean health firestore setup setup-emu format lint security-check validate

# Default target - show help
help:
	@echo "EmailPilot Development Commands:"
	@echo ""
	@echo "🎯 Workflow Management (NEW):"
	@echo "  make workflow-hub    - Open Workflow Management Hub in browser"
	@echo "  make workflow-new    - Create new workflow with wizard"
	@echo "  make workflow-test   - Test workflows with real data"
	@echo "  make agent-list      - List all available AI agents"
	@echo "  make calendar-plan   - Plan next month's email calendar"
	@echo "  make tools-available - Show all Enhanced MCP tools"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make setup      - Install dependencies and start dev server"
	@echo "  make setup-emu  - Install dependencies and start with emulator"
	@echo "  make dev        - Start development server with hot reload"
	@echo "  make dev-emu    - Start development server with Firestore emulator"
	@echo ""
	@echo "📦 Dependencies:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make install-dev - Install development dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test       - Run test suite"
	@echo "  make test-all   - Run comprehensive test suite"
	@echo "  make test-calendar - Test calendar endpoints"
	@echo ""
	@echo "🏗️  Building & Deployment:"
	@echo "  make build      - Build production assets"
	@echo "  make deploy     - Deploy to Google Cloud Run"
	@echo ""
	@echo "🔧 Development Tools:"
	@echo "  make validate   - Validate development environment"
	@echo "  make firestore  - Start Firestore emulator"
	@echo "  make health     - Check service health"
	@echo "  make format     - Format Python code with black"
	@echo "  make lint       - Lint Python code with flake8"
	@echo "  make security-check - Check for security vulnerabilities"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean      - Clean temporary files and build artifacts"
	@echo "  make logs       - Show server logs"
	@echo "  make logs-clean - Find and clean large log files (opts: SIZE=1G MODE=list|truncate|delete)"
	@echo "  make bigfiles   - List large non-log files (>200M)"
	@echo "  make quick-check-revenue - Start Revenue API on :9090 and test CORS"
	@echo "  make quick-check-simple  - Start simplified backend and probe endpoints"
	@echo "  make status-revenue      - Probe Revenue API and show CORS headers (no start)"
	@echo "  make cron-clean-logs     - Non-interactive log truncation for cron (opts: SIZE=1G)"
	@echo "  make test-smoke          - Run minimal smoke tests (no GCP deps)"
	@echo "  make docker-build-app    - Build Docker image for Cloud Run"
	@echo "  make docker-run-app      - Run Docker image locally (port 8080)"
	@echo "  make deploy-cloudrun     - Deploy to Cloud Run (set PROJECT_ID, REGION)"
	@echo "  make status-all          - Probe key endpoints (health, admin, auth, optional revenue)"

# Install dependencies
install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Start development server
dev:
	@echo "🚀 Starting development server on http://localhost:8000"
	uvicorn main_firestore:app --reload --port 8000 --host localhost

# Start development server with Firestore emulator
# Uses local Firestore emulator instead of production Firebase
dev-emu:
	@echo "🚀 Starting development server with Firestore emulator on http://localhost:8000"
	@echo "📡 Using Firestore emulator at 127.0.0.1:8080"
	@echo "🔧 Project: emailpilot-dev"
	@echo ""
	@echo "💡 Make sure Firestore emulator is running: make firestore"
	@echo ""
	FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 \
	GOOGLE_CLOUD_PROJECT=emailpilot-dev \
	FIREBASE_PROJECT_ID=emailpilot-dev \
	uvicorn main_firestore:app --reload --port 8000 --host localhost

# Alternative dev server using main.py (if available)
dev-simple:
	@echo "🚀 Starting simple server on http://localhost:8000"
	uvicorn main:app --reload --port 8000 --host localhost

# Run tests
test:
	@echo "🧪 Running test suite..."
	@if [ -d "tests/" ]; then \
		pytest tests/ -v; \
	elif [ -f "test_*.py" ]; then \
		echo "Running individual test files..."; \
		python -m pytest test_*.py -v; \
	else \
		echo "No tests directory found. Running available test files..."; \
		python -m pytest . -k "test_" -v || echo "No test files found"; \
	fi

# Check health endpoint
health:
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Server not running"

# Build production assets
build:
	@echo "📦 Building production assets..."
	@chmod +x scripts/build_frontend.sh
	./scripts/build_frontend.sh

# Deploy to Google Cloud Run
deploy:
	@echo "🚀 Deploying to Google Cloud Run..."
	@chmod +x deploy.sh
	./deploy.sh

# Start Firestore emulator (optional, for local testing)
firestore:
	@echo "🔥 Starting Firestore emulator..."
	@echo "📡 Emulator will run on 127.0.0.1:8080"
	@echo "🔧 Project: emailpilot-dev"
	gcloud emulators firestore start --host-port=127.0.0.1:8080 --project=emailpilot-dev

# Clean temporary files and build artifacts
clean:
	@echo "🧹 Cleaning temporary files and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	find . -type f -name "*.log" -delete 2>/dev/null || true
	rm -rf frontend/public/dist/ 2>/dev/null || true
	rm -rf node_modules/ 2>/dev/null || true
	rm -rf .pytest_cache/ 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	rm -rf *.egg-info/ 2>/dev/null || true
	@echo "✅ Cleaned"

# Show server logs
logs:
	@echo "📋 Showing server logs (last 50 lines)..."
	@tail -n 50 -f *.log 2>/dev/null || echo "No log files found. Server logs to console."

# Find and optionally clean large logs
# Usage: make logs-clean SIZE=1G MODE=truncate YES=yes
logs-clean:
	@chmod +x scripts/cleanup_large_files.sh
	@SIZE=$${SIZE:-500M}; MODE=$${MODE:-list}; YES_FLAG=$$( [ "$${YES:-no}" = "yes" ] && echo "--yes" ); \
	 echo "🔎 Cleaning logs (threshold: $$SIZE, mode: $$MODE)"; \
	 ./scripts/cleanup_large_files.sh -t $$SIZE $$( [ "$$MODE" = "delete" ] && echo --delete ) $$( [ "$$MODE" = "truncate" ] && echo --truncate ) $$YES_FLAG

# List large non-log files (>200M)
bigfiles:
	@echo "🔎 Large non-log files (>200M):"
	@find . -type f -size +200M ! -name "*.log" ! -name "*.out" ! -path "./logs/*" -print 2>/dev/null | sed -n '1,200p' || true

# Start Klaviyo API (formerly Revenue API) and test CORS preflight; then stop
quick-check-revenue:
	@echo "🚀 Starting Klaviyo API on http://127.0.0.1:9090 (background)"
	@mkdir -p logs
	@LOG_DIR=logs GOOGLE_CLOUD_PROJECT=$${GOOGLE_CLOUD_PROJECT:-emailpilot-438321} nohup uvicorn services.klaviyo_api.main:app --host 127.0.0.1 --port 9090 > logs/klaviyo_api_uvicorn.out 2>&1 & echo $$! > .revenue_api.pid
	@sleep 1
	@echo "🏥 /healthz:" && curl -sS http://127.0.0.1:9090/healthz || true
	@echo "-- CORS Preflight (Origin http://localhost:3000) --"
	@curl -sSI -X OPTIONS http://127.0.0.1:9090/clients/test/revenue/last7 -H 'Origin: http://localhost:3000' -H 'Access-Control-Request-Method: GET' -H 'Access-Control-Request-Headers: content-type' | sed -n '1,40p'
	@echo "🛑 Stopping Klaviyo API"; kill $$(cat .revenue_api.pid) 2>/dev/null || true; rm -f .revenue_api.pid

# Start simplified backend (no GCP deps) and probe a few endpoints; then stop
quick-check-simple:
	@echo "🚀 Starting simplified backend on http://127.0.0.1:8088 (background)"
	@mkdir -p logs
	@nohup uvicorn test_agent_sanity_app:app --host 127.0.0.1 --port 8088 > logs/simple_uvicorn.out 2>&1 & echo $$! > .simple_backend.pid
	@sleep 1
	@echo "🏥 /health:" && curl -sS http://127.0.0.1:8088/health || true
	@echo "📄 / (index.html):" && curl -sSI http://127.0.0.1:8088/ | head -n 1 || true
	@echo "🛑 Stopping simplified backend"; kill $$(cat .simple_backend.pid) 2>/dev/null || true; rm -f .simple_backend.pid

# Probe Klaviyo API status and report CORS headers (does not start the server)
status-revenue:
	@BASE=$${KLAVIYO_API_BASE:-$${REVENUE_API_BASE:-http://127.0.0.1:9090}}; ORIGIN=$${ORIGIN:-http://localhost:3000}; \
	echo "🔎 Klaviyo API status ($$BASE)"; \
	echo "- GET /healthz:"; curl -sS "$$BASE/healthz" || true; echo; \
	echo "- CORS preflight headers (OPTIONS /clients/test/revenue/last7 Origin $$ORIGIN):"; \
	curl -sSI -X OPTIONS "$$BASE/clients/test/revenue/last7" -H "Origin: $$ORIGIN" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: content-type" | awk 'BEGIN{IGNORECASE=1} /^HTTP|^Access-Control-Allow-Origin|^Access-Control-Allow-Methods|^Access-Control-Allow-Headers/ {print}'

# Cron-friendly log cleanup (truncate files over SIZE)
cron-clean-logs:
	@SIZE=$${SIZE:-1G}; echo "🧹 Cron log cleanup: truncating logs > $$SIZE"; \
	chmod +x scripts/cleanup_large_files.sh; ./scripts/cleanup_large_files.sh -t $$SIZE --truncate --yes || true

# Kill process on port 8000 (useful when port is stuck)
kill-port:
	@echo "🔫 Killing process on port 8000..."
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No process found on port 8000"

# Full restart - kill port and start dev
restart: kill-port dev

# Check all services status
status:
	@echo "📊 Service Status:"
	@echo -n "FastAPI Server: "
	@curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Not running"
	@echo -n "Calendar API: "
	@curl -s http://localhost:8000/api/calendar/health > /dev/null 2>&1 && echo "✅ Available" || echo "❌ Not available"
	@echo -n "Auth API: "
	@curl -s http://localhost:8000/api/auth/session > /dev/null 2>&1 && echo "✅ Available" || echo "❌ Not available"

# ========== WORKFLOW MANAGEMENT COMMANDS ==========
# Open Workflow Hub in browser
workflow-hub:
	@echo "🎯 Opening Workflow Management Hub..."
	@python -m webbrowser "http://localhost:8000/static/workflow_hub.html" || open "http://localhost:8000/static/workflow_hub.html" || xdg-open "http://localhost:8000/static/workflow_hub.html"
	@echo "✅ Hub opened in browser"

# Create new workflow with wizard
workflow-new:
	@echo "🪄 Opening Workflow Creation Wizard..."
	@python -m webbrowser "http://localhost:8000/static/workflow_wizard.html" || open "http://localhost:8000/static/workflow_wizard.html" || xdg-open "http://localhost:8000/static/workflow_wizard.html"
	@echo "✅ Wizard opened in browser"

# Test workflows
workflow-test:
	@echo "🧪 Testing Enhanced MCP and Workflows..."
	@python verify_enhanced_mcp.py || echo "⚠️  Please ensure services are running: make dev"

# List all agents
agent-list:
	@echo "🤖 Available AI Agents with Enhanced MCP:"
	@echo ""
	@echo "High Priority:"
	@echo "  • monthly_goals_generator_v3 - Revenue goal planning"
	@echo "  • calendar_planner - Campaign scheduling"
	@echo "  • ab_test_coordinator - A/B test management"
	@echo ""
	@echo "Medium Priority:"
	@echo "  • revenue_analyst - Financial analysis"
	@echo "  • campaign_strategist - Strategy planning"
	@echo "  • audience_architect - Segmentation"
	@echo "  • compliance_checker - Regulatory compliance"
	@echo "  • engagement_optimizer - Engagement optimization"
	@echo "  • performance_analyst - Performance metrics"
	@echo ""
	@echo "All agents have Enhanced MCP tools for real Klaviyo data access"

# Plan calendar
calendar-plan:
	@echo "📅 Opening Calendar Planner..."
	@python -m webbrowser "http://localhost:8000/static/calendar_planner.html" || open "http://localhost:8000/static/calendar_planner.html" || xdg-open "http://localhost:8000/static/calendar_planner.html"
	@echo "✅ Calendar planner opened"

# Show available tools
tools-available:
	@echo "🔧 Enhanced MCP Tools (26 Available):"
	@echo ""
	@echo "📧 Campaign Tools:"
	@echo "  • campaigns.list - List all campaigns"
	@echo "  • campaigns.get - Get specific campaign"
	@echo "  • campaign_messages.list - List campaign messages"
	@echo ""
	@echo "📊 Metrics Tools:"
	@echo "  • metrics.list - List all metrics"
	@echo "  • metrics.aggregate - Aggregate metrics data"
	@echo "  • metrics.timeline - Timeline metrics"
	@echo "  • reporting.revenue - Revenue reports"
	@echo ""
	@echo "👥 Audience Tools:"
	@echo "  • segments.list - List segments"
	@echo "  • segments.get - Get segment details"
	@echo "  • profiles.get - Get profile data"
	@echo ""
	@echo "🎯 Event Tools:"
	@echo "  • events.list - List events"
	@echo "  • flows.list - List flows"
	@echo "  • templates.list - List templates"
	@echo ""
	@echo "Use 'rogue-creamery' client for testing (has API keys configured)"

# Extended status with HTTP codes and snippets
status-all:
	@BASE=$${BASE:-http://localhost:8000}; REV=$${REV:-http://127.0.0.1:9090}; ORIGIN=$${ORIGIN:-http://localhost:3000}; \
	echo "📊 Status (BASE=$$BASE)"; \
	echo "- /health:"; curl -sSI "$$BASE/health" | head -n1 || true; \
	echo "- /api/admin/system/status:"; curl -sS "$$BASE/api/admin/system/status" | sed -e 's/{.*/{...}/' -e 's/"status":"[^"]*"/"status":"..."/' | head -c 200; echo; \
	echo "- /api/auth/google/status:"; curl -sS "$$BASE/api/auth/google/status" | head -c 200; echo; \
	echo "- /api/auth/me (unauth):"; curl -sSI "$$BASE/api/auth/me" | head -n1; \
	echo "- Revenue /healthz (optional at $$REV):"; curl -sSI "$$REV/healthz" | head -n1 || true; \
	echo "- Revenue CORS preflight:"; curl -sSI -X OPTIONS "$$REV/clients/test/revenue/last7" -H "Origin: $$ORIGIN" -H "Access-Control-Request-Method: GET" | awk 'BEGIN{IGNORECASE=1} /^HTTP|^Access-Control-Allow/ {print}' || true

# Development setup - install and run
setup: install dev

# Development setup with emulator - install and run with Firestore emulator
setup-emu: install dev-emu

# Quick calendar test
test-calendar:
	@echo "🗓️ Testing calendar endpoints..."
	@curl -s http://localhost:8000/api/calendar/health | python -m json.tool
	@curl -s http://localhost:8000/api/clients/ | head -c 200
	@echo "\n✅ Calendar test complete"

# Run all available tests
test-all:
	@echo "🧪 Running comprehensive test suite..."
	@chmod +x run_all_tests.sh
	./run_all_tests.sh

# Minimal smoke tests that don't require GCP
test-smoke:
	@echo "🧪 Running smoke tests..."
	pytest -q tests || true

# Docker targets for Cloud Run deployment
docker-build-app:
	@echo "🐳 Building Docker image emailpilot-app:latest"
	docker build -t emailpilot-app:latest .

docker-run-app:
	@echo "🐳 Running Docker image on http://localhost:8080"
	docker run --rm -p 8080:8080 -e PORT=8080 emailpilot-app:latest

deploy-cloudrun:
	@echo "🚀 Deploying to Cloud Run (PROJECT_ID=$${PROJECT_ID:-unset}, REGION=$${REGION:-us-central1})"
	@chmod +x scripts/deploy_cloud_run.sh
	PROJECT_ID=$${PROJECT_ID:-$${GOOGLE_CLOUD_PROJECT}} REGION=$${REGION:-us-central1} SERVICE_NAME=$${SERVICE_NAME:-emailpilot-app} \
	./scripts/deploy_cloud_run.sh $${NO_BUILD:+--no-build}

# Preflight deploy: run smoke tests, status checks, and prompt before deploy
preflight-deploy:
	@echo "🧪 Running smoke tests..."; \
	pytest -q tests || { echo "❌ Smoke tests failed"; exit 1; }; \
	BASE=$${BASE:-http://localhost:8000}; echo "📊 Running status-all (BASE=$$BASE)"; \
	$(MAKE) -s status-all || true; \
	read -p "Proceed with deploy to Cloud Run? (y/N) " ans; \
	[ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || { echo "Aborted."; exit 1; }; \
	$(MAKE) deploy-cloudrun

# Install development dependencies (includes pytest if needed)
install-dev: install
	@echo "📦 Installing development dependencies..."
	pip install pytest pytest-cov pytest-asyncio httpx || echo "Some dev dependencies may already be installed"

# Format code (if black is available)
format:
	@echo "🎨 Formatting Python code..."
	@if command -v black >/dev/null 2>&1; then \
		black . --exclude="/(node_modules|dist|__pycache__|\.git)/" || echo "Formatting completed with warnings"; \
	else \
		echo "Black not installed. Install with: pip install black"; \
	fi

# Lint code (if flake8 is available)
lint:
	@echo "🔍 Linting Python code..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 . --exclude=node_modules,dist,__pycache__,.git --max-line-length=88 || echo "Linting completed with warnings"; \
	else \
		echo "Flake8 not installed. Install with: pip install flake8"; \
	fi

# Check dependencies for security issues
security-check:
	@echo "🔒 Checking for security vulnerabilities..."
	@if command -v safety >/dev/null 2>&1; then \
		safety check; \
	else \
		echo "Safety not installed. Install with: pip install safety"; \
	fi

# Validate development environment
validate:
	@echo "🔍 Validating development environment..."
	@chmod +x scripts/validate_dev_env.sh
	./scripts/validate_dev_env.sh
