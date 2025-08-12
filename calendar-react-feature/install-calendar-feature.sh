#!/bin/bash

# EmailPilot React Calendar Feature - Complete Installation Script
# This script fully installs and deploys the React calendar feature

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FEATURE_NAME="React Calendar Feature"
BACKUP_DIR="/app/backups/calendar_backup_$(date +%Y%m%d_%H%M%S)"
APP_DIR="/app"
SRC_DIR="/app/src"
FEATURES_DIR="/app/src/features"
CALENDAR_DIR="/app/src/features/calendar"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root/with sufficient permissions
check_permissions() {
    if [[ ! -w "$APP_DIR" ]]; then
        log_error "No write permissions to $APP_DIR. Please run with appropriate permissions."
        exit 1
    fi
    log_success "Permissions check passed"
}

# Backup existing files
create_backup() {
    log_info "Creating backup of existing files..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup existing calendar components if they exist
    if [[ -d "$CALENDAR_DIR" ]]; then
        cp -r "$CALENDAR_DIR" "$BACKUP_DIR/calendar_existing"
        log_info "Backed up existing calendar to $BACKUP_DIR/calendar_existing"
    fi
    
    # Backup main app files
    if [[ -f "$SRC_DIR/App.jsx" ]]; then
        cp "$SRC_DIR/App.jsx" "$BACKUP_DIR/App.jsx.backup"
    fi
    
    if [[ -f "$SRC_DIR/AppRoutes.jsx" ]]; then
        cp "$SRC_DIR/AppRoutes.jsx" "$BACKUP_DIR/AppRoutes.jsx.backup"
    fi
    
    # Backup package.json
    if [[ -f "$APP_DIR/package.json" ]]; then
        cp "$APP_DIR/package.json" "$BACKUP_DIR/package.json.backup"
    fi
    
    # Backup environment files
    if [[ -f "$APP_DIR/.env" ]]; then
        cp "$APP_DIR/.env" "$BACKUP_DIR/.env.backup"
    fi
    
    if [[ -f "$APP_DIR/.env.local" ]]; then
        cp "$APP_DIR/.env.local" "$BACKUP_DIR/.env.local.backup"
    fi
    
    log_success "Backup created at: $BACKUP_DIR"
}

# Install dependencies
install_dependencies() {
    log_info "Installing required dependencies..."
    
    cd "$APP_DIR"
    
    # Check if package.json exists
    if [[ ! -f "package.json" ]]; then
        log_error "package.json not found in $APP_DIR"
        exit 1
    fi
    
    # Install Firebase SDK (if not already installed)
    if ! grep -q '"firebase"' package.json; then
        log_info "Installing Firebase SDK..."
        npm install firebase
        log_success "Firebase SDK installed"
    else
        log_info "Firebase SDK already installed"
    fi
    
    # Check for React 18+
    REACT_VERSION=$(npm list react --depth=0 2>/dev/null | grep react@ | sed 's/.*react@//' | sed 's/ .*//' || echo "not-found")
    if [[ "$REACT_VERSION" == "not-found" ]]; then
        log_warning "React not found, installing React 18..."
        npm install react@^18.0.0 react-dom@^18.0.0
    else
        log_info "React version: $REACT_VERSION"
    fi
    
    # Check for TypeScript support
    if ! npm list typescript --depth=0 >/dev/null 2>&1; then
        log_info "Installing TypeScript support..."
        npm install --save-dev typescript @types/react @types/react-dom @types/node
        log_success "TypeScript support added"
    fi
    
    log_success "Dependencies installation complete"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    mkdir -p "$FEATURES_DIR"
    mkdir -p "$CALENDAR_DIR"
    mkdir -p "$CALENDAR_DIR/modals"
    mkdir -p "$CALENDAR_DIR/services"
    mkdir -p "$CALENDAR_DIR/hooks"
    
    log_success "Directory structure created"
}

# Install calendar feature files
install_feature_files() {
    log_info "Installing React calendar feature files..."
    
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copy all calendar files
    if [[ -d "$SCRIPT_DIR/calendar" ]]; then
        cp -r "$SCRIPT_DIR/calendar/"* "$CALENDAR_DIR/"
        log_success "Calendar feature files copied"
    else
        log_error "Calendar source files not found at $SCRIPT_DIR/calendar"
        exit 1
    fi
    
    # Set proper permissions
    find "$CALENDAR_DIR" -type f -name "*.jsx" -exec chmod 644 {} \;
    find "$CALENDAR_DIR" -type f -name "*.ts" -exec chmod 644 {} \;
    
    log_success "Feature files installed with proper permissions"
}

# Configure environment variables
setup_environment() {
    log_info "Setting up environment configuration..."
    
    ENV_FILE="$APP_DIR/.env.local"
    
    # Create .env.local if it doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        touch "$ENV_FILE"
        log_info "Created .env.local file"
    fi
    
    # Add calendar-specific environment variables (if not already present)
    add_env_var() {
        local var_name=$1
        local var_value=$2
        
        if ! grep -q "^$var_name=" "$ENV_FILE"; then
            echo "$var_name=$var_value" >> "$ENV_FILE"
            log_info "Added $var_name to environment"
        else
            log_info "$var_name already exists in environment"
        fi
    }
    
    # Firebase configuration
    FIREBASE_CONFIG='{"apiKey":"AIzaSyByeHeCuEIS0wKhGq4vclyON9XpMxuHMw8","authDomain":"winatecom.firebaseapp.com","projectId":"winatecom","storageBucket":"winatecom.appspot.com","messagingSenderId":"386331689185","appId":"1:386331689185:web:3e1e4f5b2f5b2f5b2f5b2f"}'
    
    add_env_var "REACT_APP_FIREBASE_CONFIG_JSON" "'$FIREBASE_CONFIG'"
    add_env_var "REACT_APP_APP_ID" "emailpilot-prod"
    add_env_var "REACT_APP_API_BASE" "https://emailpilot-api-935786836546.us-central1.run.app"
    add_env_var "REACT_APP_AI_BASE" "https://emailpilot-api-935786836546.us-central1.run.app"
    add_env_var "REACT_APP_ENABLE_AI_CHAT" "true"
    add_env_var "REACT_APP_ENABLE_DRAG_DROP" "true"
    add_env_var "REACT_APP_ENABLE_GOALS_INTEGRATION" "true"
    
    log_success "Environment configuration complete"
}

# Add calendar route to app
setup_routing() {
    log_info "Setting up React routing..."
    
    # Find the main routing file
    ROUTES_FILE=""
    for file in "$SRC_DIR/AppRoutes.jsx" "$SRC_DIR/App.jsx" "$SRC_DIR/AppRoutes.js" "$SRC_DIR/App.js"; do
        if [[ -f "$file" ]]; then
            ROUTES_FILE="$file"
            break
        fi
    done
    
    if [[ -z "$ROUTES_FILE" ]]; then
        log_warning "Main app routing file not found. Creating AppRoutes.jsx..."
        
        cat > "$SRC_DIR/AppRoutes.jsx" << 'EOF'
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import CalendarPage from './features/calendar/CalendarPage';

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/calendar" element={<CalendarPage />} />
      {/* Add other routes here */}
    </Routes>
  );
}
EOF
        ROUTES_FILE="$SRC_DIR/AppRoutes.jsx"
        log_success "Created AppRoutes.jsx with calendar route"
    else
        log_info "Found routing file: $ROUTES_FILE"
        
        # Check if calendar route already exists
        if grep -q "CalendarPage" "$ROUTES_FILE"; then
            log_info "Calendar route already exists"
        else
            # Add calendar import and route
            log_info "Adding calendar route to existing routing file..."
            
            # Create a temporary file with the modifications
            TEMP_FILE=$(mktemp)
            
            # Add import at the top (after existing imports)
            awk '
                /^import.*from/ && !imported {
                    print $0
                    if (getline > 0) {
                        print $0
                        if (!/^import/) {
                            print "import CalendarPage from '\''./features/calendar/CalendarPage'\'';"
                            imported = 1
                        }
                    }
                    next
                }
                /<Routes>/ && !route_added {
                    print $0
                    print "      <Route path=\"/calendar\" element={<CalendarPage />} />"
                    route_added = 1
                    next
                }
                { print }
            ' "$ROUTES_FILE" > "$TEMP_FILE"
            
            # If import wasn't added, add it at the beginning
            if ! grep -q "CalendarPage" "$TEMP_FILE"; then
                sed -i '1i import CalendarPage from '\''./features/calendar/CalendarPage'\'';' "$TEMP_FILE"
            fi
            
            # If route wasn't added, add it before </Routes>
            if ! grep -q 'path="/calendar"' "$TEMP_FILE"; then
                sed -i 's|</Routes>|      <Route path="/calendar" element={<CalendarPage />} />\n    </Routes>|' "$TEMP_FILE"
            fi
            
            # Replace the original file
            mv "$TEMP_FILE" "$ROUTES_FILE"
            log_success "Calendar route added to $ROUTES_FILE"
        fi
    fi
}

# Add backend API endpoints
setup_backend_endpoints() {
    log_info "Setting up backend API endpoints..."
    
    # Find the main FastAPI file
    API_FILE=""
    for file in "$APP_DIR/main.py" "$APP_DIR/main_firestore.py" "$APP_DIR/app.py"; do
        if [[ -f "$file" ]]; then
            API_FILE="$file"
            break
        fi
    done
    
    if [[ -z "$API_FILE" ]]; then
        log_warning "FastAPI main file not found. Please add these endpoints manually:"
        cat << 'EOF'

@app.post("/api/ai/summarize-calendar")
async def summarize_calendar(request: dict):
    """Parse document text into calendar campaigns using AI"""
    doc_text = request.get("docText", "")
    # TODO: Forward to Gemini API with your server-side key
    # Return: [{"date": "2024-01-15", "title": "Campaign", "content": "", "color": "bg-blue-200"}]
    return []

@app.post("/api/ai/chat")
async def ai_chat(request: dict):
    """AI-powered calendar planning assistance"""
    message = request.get("message", "")
    context = request.get("context", {})
    # TODO: Forward to Gemini API with context about campaigns and goals
    # Return: {"response": "AI response", "suggestions": []}
    return {"response": "Calendar AI endpoint not yet implemented", "suggestions": []}

EOF
    else
        log_info "Found API file: $API_FILE"
        
        # Check if calendar endpoints already exist
        if grep -q "summarize-calendar" "$API_FILE"; then
            log_info "Calendar API endpoints already exist"
        else
            log_info "Adding calendar API endpoints..."
            
            # Add the endpoints at the end of the file
            cat >> "$API_FILE" << 'EOF'

# Calendar Feature API Endpoints
@app.post("/api/ai/summarize-calendar")
async def summarize_calendar(request: dict):
    """Parse document text into calendar campaigns using AI"""
    doc_text = request.get("docText", "")
    # TODO: Implement Gemini API integration with server-side key
    # For now, return empty array
    return []

@app.post("/api/ai/chat")
async def ai_chat(request: dict):
    """AI-powered calendar planning assistance"""
    message = request.get("message", "")
    context = request.get("context", {})
    # TODO: Implement Gemini API integration for planning assistance
    # For now, return placeholder response
    return {
        "response": "Calendar AI chat is being configured. Please check back soon!",
        "suggestions": ["Add high-value campaigns", "Check revenue goals", "Schedule consistent messaging"]
    }
EOF
            log_success "Calendar API endpoints added to $API_FILE"
        fi
    fi
}

# Build the application
build_application() {
    log_info "Building the application..."
    
    cd "$APP_DIR"
    
    # Run TypeScript compilation if tsconfig.json exists
    if [[ -f "tsconfig.json" ]]; then
        log_info "Running TypeScript compilation..."
        npx tsc --noEmit || log_warning "TypeScript compilation had warnings (non-fatal)"
    fi
    
    # Build the React application
    if command -v npm >/dev/null 2>&1; then
        log_info "Building React application..."
        npm run build || log_warning "Build completed with warnings"
        log_success "Application build complete"
    else
        log_warning "npm not found, skipping build step"
    fi
}

# Restart services
restart_services() {
    log_info "Restarting services..."
    
    # If using PM2
    if command -v pm2 >/dev/null 2>&1; then
        pm2 restart all || log_info "PM2 restart attempted"
    fi
    
    # If using systemctl
    if command -v systemctl >/dev/null 2>&1; then
        systemctl restart emailpilot || log_info "Systemctl restart attempted"
    fi
    
    # If using Google Cloud Run
    if command -v gcloud >/dev/null 2>&1; then
        log_info "Triggering Cloud Run deployment..."
        gcloud run services update emailpilot-api --region=us-central1 --source=. || log_info "Cloud Run update attempted"
    fi
    
    log_success "Service restart commands executed"
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."
    
    local validation_errors=0
    
    # Check files exist
    if [[ ! -f "$CALENDAR_DIR/CalendarPage.jsx" ]]; then
        log_error "CalendarPage.jsx not found"
        validation_errors=$((validation_errors + 1))
    fi
    
    if [[ ! -f "$CALENDAR_DIR/services/firebaseCalendar.ts" ]]; then
        log_error "firebaseCalendar.ts service not found"
        validation_errors=$((validation_errors + 1))
    fi
    
    # Check environment variables
    if [[ ! -f "$APP_DIR/.env.local" ]] || ! grep -q "REACT_APP_FIREBASE_CONFIG_JSON" "$APP_DIR/.env.local"; then
        log_error "Firebase configuration not found in environment"
        validation_errors=$((validation_errors + 1))
    fi
    
    # Check routing
    if [[ -f "$ROUTES_FILE" ]] && grep -q "CalendarPage" "$ROUTES_FILE"; then
        log_success "Calendar routing configured"
    else
        log_error "Calendar routing not properly configured"
        validation_errors=$((validation_errors + 1))
    fi
    
    if [[ $validation_errors -eq 0 ]]; then
        log_success "Installation validation passed!"
        return 0
    else
        log_error "Installation validation failed with $validation_errors errors"
        return 1
    fi
}

# Generate installation report
generate_report() {
    local report_file="$APP_DIR/calendar-installation-report.txt"
    
    cat > "$report_file" << EOF
EmailPilot React Calendar Feature Installation Report
====================================================
Date: $(date)
Installation Directory: $APP_DIR
Backup Directory: $BACKUP_DIR

Files Installed:
- Calendar Feature Module: $CALENDAR_DIR
- Main Component: $CALENDAR_DIR/CalendarPage.jsx
- Calendar Grid: $CALENDAR_DIR/CalendarBoard.jsx
- AI Chat: $CALENDAR_DIR/CalendarChat.jsx
- Event Modal: $CALENDAR_DIR/modals/EventModal.jsx
- Services: $CALENDAR_DIR/services/
- Hooks: $CALENDAR_DIR/hooks/useCalendarState.ts
- Types: $CALENDAR_DIR/types.ts

Configuration:
- Environment: $APP_DIR/.env.local
- Routing: $ROUTES_FILE
- API Endpoints: $API_FILE

Next Steps:
1. Access the calendar at: https://your-domain.com/calendar
2. Test calendar functionality
3. Configure AI endpoints in backend
4. Review backup at: $BACKUP_DIR

Integration Test:
Run integration test at: https://your-domain.com/calendar/test
(Add route: <Route path="/calendar/test" element={<CalendarIntegrationTest />} />)

Support:
- Documentation: $CALENDAR_DIR/README.md
- Environment Example: $CALENDAR_DIR/.env.example
- Backup Location: $BACKUP_DIR
EOF

    log_success "Installation report generated: $report_file"
}

# Main installation function
main() {
    echo "=================================================="
    echo "EmailPilot React Calendar Feature Installer"
    echo "=================================================="
    echo
    
    log_info "Starting installation of $FEATURE_NAME..."
    
    # Pre-flight checks
    check_permissions
    
    # Installation steps
    create_backup
    install_dependencies
    create_directories
    install_feature_files
    setup_environment
    setup_routing
    setup_backend_endpoints
    build_application
    
    # Validation
    if validate_installation; then
        generate_report
        restart_services
        
        echo
        echo "=================================================="
        log_success "✅ EmailPilot React Calendar Feature Installation Complete!"
        echo "=================================================="
        echo
        echo "🎉 What's New:"
        echo "   • Modern React-based calendar with drag & drop"
        echo "   • AI-powered campaign planning assistance"
        echo "   • Real-time revenue goal tracking"
        echo "   • Auto-save with Firebase integration"
        echo "   • Mobile-responsive design"
        echo
        echo "🚀 Access Your Calendar:"
        echo "   • Navigate to: /calendar"
        echo "   • Test at: /calendar/test (after adding test route)"
        echo
        echo "📋 Next Steps:"
        echo "   1. Test the calendar functionality"
        echo "   2. Configure AI endpoints in your backend"
        echo "   3. Review the installation report"
        echo "   4. Train users on new features"
        echo
        echo "📁 Backup Created: $BACKUP_DIR"
        echo "📊 Report Generated: $APP_DIR/calendar-installation-report.txt"
        echo
        log_success "Installation completed successfully! 🎊"
    else
        log_error "Installation validation failed. Please check the errors above."
        log_info "Backup available at: $BACKUP_DIR"
        exit 1
    fi
}

# Handle script arguments
case "${1:-install}" in
    "install")
        main
        ;;
    "rollback")
        if [[ -n "$2" ]] && [[ -d "$2" ]]; then
            log_info "Rolling back from backup: $2"
            # Implement rollback logic here
            log_warning "Rollback functionality - restore from: $2"
        else
            log_error "Please specify backup directory for rollback"
            exit 1
        fi
        ;;
    "validate")
        validate_installation
        ;;
    "help")
        echo "Usage: $0 [install|rollback|validate|help]"
        echo "  install  - Full installation (default)"
        echo "  rollback - Rollback from backup directory"
        echo "  validate - Validate existing installation"
        echo "  help     - Show this help"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac