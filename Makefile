# EmailPilot Development Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install dev test build deploy clean health

# Default target - show help
help:
	@echo "EmailPilot Development Commands:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make dev        - Start development server with hot reload"
	@echo "  make test       - Run test suite"
	@echo "  make health     - Check service health"
	@echo "  make build      - Build production assets"
	@echo "  make deploy     - Deploy to Google Cloud Run"
	@echo "  make clean      - Clean temporary files and caches"
	@echo "  make firestore  - Start Firestore emulator (requires gcloud)"
	@echo "  make logs       - Show server logs"

# Install dependencies
install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Start development server
dev:
	@echo "🚀 Starting development server on http://localhost:8000"
	uvicorn main_firestore:app --reload --port 8000

# Alternative dev server using main.py (if available)
dev-simple:
	@echo "🚀 Starting simple server on http://localhost:8000"
	uvicorn main:app --reload --port 8000

# Run tests
test:
	pytest tests/ -v

# Check health endpoint
health:
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Server not running"

# Build production assets (placeholder for future webpack/vite integration)
build:
	@echo "📦 Building production assets..."
	@echo "Note: Currently using CDN React. Consider bundling for production."
	# Future: npx esbuild frontend/public/components/*.js --bundle --minify --outdir=frontend/dist/

# Deploy to Google Cloud Run
deploy:
	@echo "🚀 Deploying to Google Cloud Run..."
	gcloud run deploy emailpilot \
		--source . \
		--region us-central1 \
		--allow-unauthenticated \
		--set-env-vars-from-file .env.yaml

# Start Firestore emulator (optional, for local testing)
firestore:
	@echo "🔥 Starting Firestore emulator..."
	gcloud emulators firestore start --host-port=localhost:8081

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
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

# Quick calendar test
test-calendar:
	@echo "🗓️ Testing calendar endpoints..."
	@curl -s http://localhost:8000/api/calendar/health | python -m json.tool
	@curl -s http://localhost:8000/api/clients/ | head -c 200
	@echo "\n✅ Calendar test complete"