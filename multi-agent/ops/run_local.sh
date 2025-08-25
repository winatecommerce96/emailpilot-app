#!/bin/bash
set -e

# Multi-Agent Orchestration Local Runner
# Bootstrap script for local development

echo "🚀 Starting Multi-Agent Orchestration Service"

# Check if we're in the right directory
if [[ ! -f "requirements.txt" ]]; then
    echo "❌ Error: Must be run from multi-agent directory"
    echo "   Expected: /path/to/emailpilot-app/multi-agent"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -o '3\.[0-9]\+')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 11 ]]; then
    echo "❌ Error: Python 3.11+ required, found $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check for .env file
if [[ ! -f ".env" ]]; then
    echo "⚙️  Creating default .env file..."
    cat > .env << EOF
# Multi-Agent Orchestration Configuration
ENVIRONMENT=development
GOOGLE_CLOUD_PROJECT=emailpilot-dev

# Model Configuration
PRIMARY_PROVIDER=openai
PRIMARY_MODEL=gpt-4-turbo-preview
SECONDARY_PROVIDER=anthropic
SECONDARY_MODEL=claude-3-sonnet-20240229
MARKETING_PROVIDER=gemini
MARKETING_MODEL=gemini-2.0-flash

# Service Endpoints
EMAILPILOT_BASE_URL=http://localhost:8000
KLAVIYO_MCP_URL=http://localhost:9090

# Development Settings
AUTO_APPROVE_IN_DEV=true
MAX_REVISION_LOOPS=3
ENABLE_TRACING=true
LOG_LEVEL=INFO

# API Server
HOST=0.0.0.0
PORT=8100
EOF
    echo "📝 Created .env file with defaults"
    echo "   Edit .env to configure API keys and endpoints"
fi

# Load environment variables
echo "🔑 Loading environment variables..."
export $(grep -v '^#' .env | xargs)

# Create artifacts directory
mkdir -p .artifacts/{demo,test}
echo "📁 Created artifacts directory"

# Validate configuration
echo "🔍 Validating configuration..."
python -m apps.orchestrator_service.main validate

# Show available commands
echo ""
echo "🎯 Multi-Agent Orchestration Ready!"
echo ""
echo "Available commands:"
echo "  Demo Run:        python -m apps.orchestrator_service.main demo --month 2024-11 --brand acme --auto-approve"
echo "  API Server:      python -m apps.orchestrator_service.main serve"
echo "  Run Tests:       pytest tests/ -v"
echo "  Interactive:     python -m apps.orchestrator_service.main approve"
echo ""
echo "API will be available at: http://localhost:8100"
echo "Health check:            curl http://localhost:8100/health"
echo ""

# Option to run demo immediately
read -p "Run demo now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Running demo..."
    python -m apps.orchestrator_service.main demo --month 2024-11 --brand acme --auto-approve
fi

echo "✅ Setup complete!"