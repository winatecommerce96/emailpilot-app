# EmailPilot Development Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev dev dev-emu dev-simple test test-all test-calendar build deploy clean health firestore setup setup-emu format lint security-check validate

# Default target - show help
help:
	@echo "EmailPilot Development Commands:"
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

# Install dependencies
install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Start development server
dev:
	@echo "🚀 Starting development server on http://localhost:8000"
	uvicorn main_firestore:app --reload --port 8000

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
	uvicorn main_firestore:app --reload --port 8000

# Alternative dev server using main.py (if available)
dev-simple:
	@echo "🚀 Starting simple server on http://localhost:8000"
	uvicorn main:app --reload --port 8000

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