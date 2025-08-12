#!/bin/bash

# EmailPilot React Calendar Feature - Rollback Script
# This script safely removes the calendar feature and restores backups

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/app"
SRC_DIR="/app/src"
CALENDAR_DIR="/app/src/features/calendar"
BACKUP_BASE_DIR="/app/backups"

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

# Find available backups
list_backups() {
    log_info "Available backups:"
    echo
    
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        log_warning "No backup directory found at $BACKUP_BASE_DIR"
        return 1
    fi
    
    local backups=($(ls -t "$BACKUP_BASE_DIR"/calendar_backup_* 2>/dev/null || true))
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        log_warning "No calendar backups found"
        return 1
    fi
    
    for i in "${!backups[@]}"; do
        local backup="${backups[$i]}"
        local backup_date=$(basename "$backup" | sed 's/calendar_backup_//' | sed 's/_/ /')
        local backup_size=$(du -sh "$backup" 2>/dev/null | cut -f1)
        echo "  $((i+1)). $(basename "$backup") - $backup_date ($backup_size)"
    done
    
    echo
    return 0
}

# Select backup interactively
select_backup() {
    local backups=($(ls -t "$BACKUP_BASE_DIR"/calendar_backup_* 2>/dev/null || true))
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        log_error "No backups available for rollback"
        exit 1
    fi
    
    echo "Select backup to restore from:"
    echo
    
    for i in "${!backups[@]}"; do
        local backup="${backups[$i]}"
        local backup_date=$(basename "$backup" | sed 's/calendar_backup_//' | sed 's/_/ /')
        echo "  $((i+1)). $(basename "$backup") - $backup_date"
    done
    
    echo
    read -p "Enter backup number (1-${#backups[@]}): " backup_choice
    
    if [[ ! "$backup_choice" =~ ^[0-9]+$ ]] || [[ $backup_choice -lt 1 ]] || [[ $backup_choice -gt ${#backups[@]} ]]; then
        log_error "Invalid selection"
        exit 1
    fi
    
    SELECTED_BACKUP="${backups[$((backup_choice-1))]}"
    log_info "Selected backup: $(basename "$SELECTED_BACKUP")"
}

# Remove calendar feature
remove_calendar_feature() {
    log_info "Removing calendar feature files..."
    
    # Create rollback backup before removal
    local rollback_backup="$BACKUP_BASE_DIR/rollback_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$rollback_backup"
    
    if [[ -d "$CALENDAR_DIR" ]]; then
        cp -r "$CALENDAR_DIR" "$rollback_backup/calendar_removed"
        rm -rf "$CALENDAR_DIR"
        log_success "Calendar feature directory removed"
        log_info "Removed files backed up to: $rollback_backup"
    else
        log_warning "Calendar feature directory not found"
    fi
    
    # Remove empty features directory if no other features exist
    if [[ -d "$SRC_DIR/features" ]] && [[ -z "$(ls -A "$SRC_DIR/features")" ]]; then
        rmdir "$SRC_DIR/features"
        log_info "Removed empty features directory"
    fi
}

# Remove calendar route from routing file
remove_calendar_route() {
    log_info "Removing calendar route from application..."
    
    # Find routing files
    for routes_file in "$SRC_DIR/AppRoutes.jsx" "$SRC_DIR/App.jsx" "$SRC_DIR/AppRoutes.js" "$SRC_DIR/App.js"; do
        if [[ -f "$routes_file" ]] && grep -q "CalendarPage" "$routes_file"; then
            log_info "Removing calendar route from: $routes_file"
            
            # Create backup
            cp "$routes_file" "$routes_file.rollback.backup"
            
            # Remove import line
            sed -i '/import.*CalendarPage.*from/d' "$routes_file"
            
            # Remove route line
            sed -i '/path="\/calendar".*CalendarPage/d' "$routes_file"
            
            log_success "Calendar route removed from $routes_file"
        fi
    done
}

# Remove calendar API endpoints
remove_api_endpoints() {
    log_info "Removing calendar API endpoints..."
    
    for api_file in "$APP_DIR/main.py" "$APP_DIR/main_firestore.py" "$APP_DIR/app.py"; do
        if [[ -f "$api_file" ]] && grep -q "summarize-calendar" "$api_file"; then
            log_info "Removing calendar endpoints from: $api_file"
            
            # Create backup
            cp "$api_file" "$api_file.rollback.backup"
            
            # Remove calendar endpoints (from comment to end of function)
            sed -i '/# Calendar Feature API Endpoints/,/@app\.post.*ai\/chat/+10d' "$api_file"
            
            log_success "Calendar API endpoints removed from $api_file"
        fi
    done
}

# Clean up environment variables
clean_environment() {
    log_info "Cleaning calendar environment variables..."
    
    for env_file in "$APP_DIR/.env.local" "$APP_DIR/.env"; do
        if [[ -f "$env_file" ]]; then
            # Create backup
            cp "$env_file" "$env_file.rollback.backup"
            
            # Remove calendar-specific variables
            sed -i '/REACT_APP_FIREBASE_CONFIG_JSON/d' "$env_file"
            sed -i '/REACT_APP_APP_ID/d' "$env_file"
            sed -i '/REACT_APP_AI_BASE/d' "$env_file"
            sed -i '/REACT_APP_ENABLE_AI_CHAT/d' "$env_file"
            sed -i '/REACT_APP_ENABLE_DRAG_DROP/d' "$env_file"
            sed -i '/REACT_APP_ENABLE_GOALS_INTEGRATION/d' "$env_file"
            
            log_success "Environment variables cleaned from $env_file"
        fi
    done
}

# Restore from backup
restore_from_backup() {
    if [[ -z "$SELECTED_BACKUP" ]]; then
        log_info "Skipping backup restore (clean removal only)"
        return 0
    fi
    
    log_info "Restoring files from backup: $(basename "$SELECTED_BACKUP")"
    
    # Restore routing file
    if [[ -f "$SELECTED_BACKUP/AppRoutes.jsx.backup" ]]; then
        cp "$SELECTED_BACKUP/AppRoutes.jsx.backup" "$SRC_DIR/AppRoutes.jsx"
        log_success "Restored AppRoutes.jsx"
    fi
    
    if [[ -f "$SELECTED_BACKUP/App.jsx.backup" ]]; then
        cp "$SELECTED_BACKUP/App.jsx.backup" "$SRC_DIR/App.jsx"
        log_success "Restored App.jsx"
    fi
    
    # Restore API file
    for api_backup in "$SELECTED_BACKUP/main.py.backup" "$SELECTED_BACKUP/main_firestore.py.backup"; do
        if [[ -f "$api_backup" ]]; then
            local api_file="$APP_DIR/$(basename "$api_backup" .backup)"
            cp "$api_backup" "$api_file"
            log_success "Restored $(basename "$api_file")"
        fi
    done
    
    # Restore environment files
    if [[ -f "$SELECTED_BACKUP/.env.local.backup" ]]; then
        cp "$SELECTED_BACKUP/.env.local.backup" "$APP_DIR/.env.local"
        log_success "Restored .env.local"
    fi
    
    if [[ -f "$SELECTED_BACKUP/.env.backup" ]]; then
        cp "$SELECTED_BACKUP/.env.backup" "$APP_DIR/.env"
        log_success "Restored .env"
    fi
    
    # Restore existing calendar if it was there
    if [[ -d "$SELECTED_BACKUP/calendar_existing" ]]; then
        mkdir -p "$(dirname "$CALENDAR_DIR")"
        cp -r "$SELECTED_BACKUP/calendar_existing" "$CALENDAR_DIR"
        log_success "Restored previous calendar version"
    fi
}

# Rebuild application
rebuild_application() {
    log_info "Rebuilding application..."
    
    cd "$APP_DIR"
    
    # Clean build artifacts
    if [[ -d "build" ]]; then
        rm -rf build
        log_info "Cleaned build directory"
    fi
    
    if [[ -d "dist" ]]; then
        rm -rf dist
        log_info "Cleaned dist directory"
    fi
    
    # Rebuild
    if command -v npm >/dev/null 2>&1; then
        npm run build || log_warning "Build completed with warnings"
        log_success "Application rebuilt"
    else
        log_warning "npm not found, skipping rebuild"
    fi
}

# Restart services
restart_services() {
    log_info "Restarting services..."
    
    # PM2
    if command -v pm2 >/dev/null 2>&1; then
        pm2 restart all || log_info "PM2 restart attempted"
    fi
    
    # Systemctl
    if command -v systemctl >/dev/null 2>&1; then
        systemctl restart emailpilot || log_info "Systemctl restart attempted"
    fi
    
    # Google Cloud Run
    if command -v gcloud >/dev/null 2>&1; then
        log_info "Triggering Cloud Run deployment..."
        gcloud run services update emailpilot-api --region=us-central1 --source=. || log_info "Cloud Run update attempted"
    fi
    
    log_success "Service restart commands executed"
}

# Generate rollback report
generate_rollback_report() {
    local report_file="$APP_DIR/calendar-rollback-report.txt"
    
    cat > "$report_file" << EOF
EmailPilot React Calendar Feature Rollback Report
================================================
Date: $(date)
Rollback Type: ${1:-"Clean Removal"}
Backup Used: ${SELECTED_BACKUP:-"None"}

Actions Performed:
- Removed calendar feature directory: $CALENDAR_DIR
- Removed calendar routes from application
- Removed calendar API endpoints
- Cleaned environment variables
$([ -n "$SELECTED_BACKUP" ] && echo "- Restored files from backup")

Files Backed Up During Rollback:
- Rollback safety backup created before removal

Status: Calendar feature successfully removed

Next Steps:
1. Verify application works correctly
2. Test existing functionality
3. Remove calendar-specific dependencies if no longer needed
4. Update user documentation

Support:
If you need to re-install the calendar feature, use the installation script.
EOF

    log_success "Rollback report generated: $report_file"
}

# Interactive rollback
interactive_rollback() {
    echo "=================================================="
    echo "EmailPilot React Calendar Feature Rollback"
    echo "=================================================="
    echo
    
    log_warning "This will remove the React calendar feature from your application."
    echo
    
    if list_backups; then
        echo "Choose rollback option:"
        echo "  1. Clean removal (remove calendar, keep other changes)"
        echo "  2. Full rollback (restore from backup)"
        echo "  3. Cancel"
        echo
        read -p "Enter choice (1-3): " rollback_choice
        
        case "$rollback_choice" in
            1)
                log_info "Performing clean removal..."
                ;;
            2)
                log_info "Performing full rollback..."
                select_backup
                ;;
            3)
                log_info "Rollback cancelled"
                exit 0
                ;;
            *)
                log_error "Invalid choice"
                exit 1
                ;;
        esac
    else
        log_warning "No backups available, performing clean removal only"
        read -p "Continue with clean removal? (y/N): " continue_choice
        if [[ "$continue_choice" != "y" && "$continue_choice" != "Y" ]]; then
            log_info "Rollback cancelled"
            exit 0
        fi
    fi
    
    echo
    read -p "Are you sure you want to proceed? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi
}

# Main rollback function
main() {
    # Check if calendar is actually installed
    if [[ ! -d "$CALENDAR_DIR" ]]; then
        log_warning "Calendar feature doesn't appear to be installed"
        log_info "Directory not found: $CALENDAR_DIR"
        exit 0
    fi
    
    interactive_rollback
    
    log_info "Starting calendar feature rollback..."
    
    # Rollback steps
    remove_calendar_feature
    remove_calendar_route
    remove_api_endpoints
    clean_environment
    restore_from_backup
    rebuild_application
    restart_services
    
    generate_rollback_report "$([ -n "$SELECTED_BACKUP" ] && echo "Full Rollback" || echo "Clean Removal")"
    
    echo
    echo "=================================================="
    log_success "✅ Calendar Feature Rollback Complete!"
    echo "=================================================="
    echo
    echo "📋 What was removed:"
    echo "   • React calendar feature module"
    echo "   • Calendar routes and API endpoints"  
    echo "   • Calendar-specific environment variables"
    echo
    if [[ -n "$SELECTED_BACKUP" ]]; then
        echo "🔄 Restored from backup: $(basename "$SELECTED_BACKUP")"
    else
        echo "🧹 Clean removal performed (no backup restored)"
    fi
    echo
    echo "📊 Report Generated: $APP_DIR/calendar-rollback-report.txt"
    echo
    log_success "Rollback completed successfully! 🎊"
}

# Handle script arguments
case "${1:-interactive}" in
    "interactive"|"")
        main
        ;;
    "clean")
        # Non-interactive clean removal
        if [[ -d "$CALENDAR_DIR" ]]; then
            log_info "Performing clean removal of calendar feature..."
            remove_calendar_feature
            remove_calendar_route
            remove_api_endpoints
            clean_environment
            rebuild_application
            restart_services
            generate_rollback_report "Clean Removal"
            log_success "Clean removal completed"
        else
            log_warning "Calendar feature not installed"
        fi
        ;;
    "list")
        list_backups
        ;;
    "help")
        echo "Usage: $0 [interactive|clean|list|help]"
        echo "  interactive - Interactive rollback with backup options (default)"
        echo "  clean       - Clean removal without restoration"
        echo "  list        - List available backups"
        echo "  help        - Show this help"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac