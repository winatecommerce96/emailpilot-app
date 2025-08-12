#!/bin/bash

# EmailPilot Rollback Manager
# Comprehensive rollback system for Cloud Run deployments
# Version: 1.0.0

set -euo pipefail

PROJECT_ID="emailpilot-438321"
SERVICE_NAME="emailpilot-api"
REGION="us-central1"
DEPLOYMENT_DIR="/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")  echo -e "${BLUE}[INFO]${NC} $timestamp - $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $timestamp - $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $timestamp - $message" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $timestamp - $message" ;;
    esac
}

# Get available revisions
get_revisions() {
    log "INFO" "Fetching available revisions..."
    
    gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --format="table(
            metadata.name:label=REVISION,
            status.conditions[0].lastTransitionTime:label=DEPLOYED,
            spec.template.spec.containers[0].image:label=IMAGE,
            status.allocatedTraffic:label=TRAFFIC
        )" \
        --sort-by="~metadata.creationTimestamp"
}

# Get current revision
get_current_revision() {
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.traffic[0].revisionName)"
}

# Rollback to specific revision
rollback_to_revision() {
    local target_revision="$1"
    local traffic_percentage="${2:-100}"
    
    log "INFO" "Rolling back to revision: $target_revision"
    log "INFO" "Traffic percentage: $traffic_percentage%"
    
    # Validate revision exists
    if ! gcloud run revisions describe "$target_revision" \
         --region="$REGION" >/dev/null 2>&1; then
        log "ERROR" "Revision $target_revision not found"
        return 1
    fi
    
    # Perform rollback
    gcloud run services update-traffic "$SERVICE_NAME" \
        --region="$REGION" \
        --to-revisions="$target_revision=$traffic_percentage"
    
    log "SUCCESS" "Rollback completed"
    
    # Wait for rollback to be ready
    log "INFO" "Waiting for service to be ready..."
    gcloud run services wait "$SERVICE_NAME" --region="$REGION"
    
    log "SUCCESS" "Service is ready"
}

# Rollback to previous revision
rollback_to_previous() {
    log "INFO" "Rolling back to previous revision..."
    
    # Get the second most recent revision (first is current)
    local previous_revision=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(metadata.name)" \
        --sort-by="~metadata.creationTimestamp" \
        --limit=2 | tail -n1)
    
    if [[ -z "$previous_revision" ]]; then
        log "ERROR" "No previous revision found"
        return 1
    fi
    
    log "INFO" "Previous revision: $previous_revision"
    rollback_to_revision "$previous_revision"
}

# Canary rollback (gradual traffic shifting)
canary_rollback() {
    local target_revision="$1"
    local steps="${2:-5}"
    local delay="${3:-30}"
    
    log "INFO" "Starting canary rollback to: $target_revision"
    log "INFO" "Steps: $steps, Delay: ${delay}s between steps"
    
    local current_revision=$(get_current_revision)
    local step_size=$((100 / steps))
    
    for ((i=1; i<=steps; i++)); do
        local target_traffic=$((step_size * i))
        local current_traffic=$((100 - target_traffic))
        
        log "INFO" "Step $i/$steps: Shifting ${target_traffic}% traffic to $target_revision"
        
        if [[ $target_traffic -eq 100 ]]; then
            # Final step - all traffic to target
            gcloud run services update-traffic "$SERVICE_NAME" \
                --region="$REGION" \
                --to-revisions="$target_revision=100"
        else
            # Gradual shift
            gcloud run services update-traffic "$SERVICE_NAME" \
                --region="$REGION" \
                --to-revisions="$target_revision=$target_traffic,$current_revision=$current_traffic"
        fi
        
        # Wait between steps (except for the last one)
        if [[ $i -lt $steps ]]; then
            log "INFO" "Waiting ${delay}s before next step..."
            sleep "$delay"
            
            # Optional: Check health here
            if command -v python3 &> /dev/null && [[ -f "scripts/health_checker.py" ]]; then
                log "INFO" "Running health check..."
                python3 scripts/health_checker.py --category basic --base-url https://emailpilot.ai
            fi
        fi
    done
    
    log "SUCCESS" "Canary rollback completed"
}

# Emergency rollback (immediate previous version)
emergency_rollback() {
    log "WARN" "EMERGENCY ROLLBACK INITIATED"
    
    # Get previous revision quickly
    local previous_revision=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(metadata.name)" \
        --sort-by="~metadata.creationTimestamp" \
        --limit=2 | tail -n1)
    
    if [[ -z "$previous_revision" ]]; then
        log "ERROR" "No previous revision found for emergency rollback"
        return 1
    fi
    
    log "WARN" "Rolling back to: $previous_revision"
    
    # Immediate rollback - no gradual traffic shifting
    gcloud run services update-traffic "$SERVICE_NAME" \
        --region="$REGION" \
        --to-revisions="$previous_revision=100"
    
    log "SUCCESS" "Emergency rollback completed"
    
    # Quick health check
    sleep 10
    local service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    local health_status=$(curl -s -o /dev/null -w "%{http_code}" "$service_url/health" || echo "000")
    
    if [[ "$health_status" == "200" ]]; then
        log "SUCCESS" "Emergency rollback health check: PASSED"
    else
        log "ERROR" "Emergency rollback health check: FAILED ($health_status)"
    fi
}

# Create rollback backup
create_rollback_backup() {
    local backup_name="rollback_backup_$(date +%Y%m%d_%H%M%S)"
    local backup_dir="$DEPLOYMENT_DIR/deployments/backups/$backup_name"
    
    log "INFO" "Creating rollback backup: $backup_name"
    
    mkdir -p "$backup_dir"
    
    # Save current revision info
    gcloud run revisions describe "$(get_current_revision)" \
        --region="$REGION" \
        --format="export" > "$backup_dir/current_revision.yaml"
    
    # Save traffic allocation
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.traffic)" > "$backup_dir/traffic_allocation.txt"
    
    # Save service configuration
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="export" > "$backup_dir/service_config.yaml"
    
    echo "$backup_name" > "$backup_dir/../latest_backup.txt"
    
    log "SUCCESS" "Rollback backup created: $backup_dir"
    echo "$backup_name"
}

# Restore from backup
restore_from_backup() {
    local backup_name="$1"
    local backup_dir="$DEPLOYMENT_DIR/deployments/backups/$backup_name"
    
    if [[ ! -d "$backup_dir" ]]; then
        log "ERROR" "Backup not found: $backup_dir"
        return 1
    fi
    
    log "INFO" "Restoring from backup: $backup_name"
    
    # This is complex and risky - would need to restore entire service config
    log "WARN" "Backup restoration is complex and may cause issues"
    log "INFO" "Consider using revision rollback instead"
    
    # For now, just show what would be restored
    if [[ -f "$backup_dir/current_revision.yaml" ]]; then
        log "INFO" "Backup contains revision configuration"
    fi
    
    if [[ -f "$backup_dir/traffic_allocation.txt" ]]; then
        log "INFO" "Backup contains traffic allocation: $(cat "$backup_dir/traffic_allocation.txt")"
    fi
}

# Validate rollback target
validate_rollback_target() {
    local target_revision="$1"
    
    log "INFO" "Validating rollback target: $target_revision"
    
    # Check if revision exists
    if ! gcloud run revisions describe "$target_revision" \
         --region="$REGION" >/dev/null 2>&1; then
        log "ERROR" "Target revision does not exist: $target_revision"
        return 1
    fi
    
    # Check revision status
    local revision_status=$(gcloud run revisions describe "$target_revision" \
        --region="$REGION" \
        --format="value(status.conditions[0].status)")
    
    if [[ "$revision_status" != "True" ]]; then
        log "WARN" "Target revision status is not ready: $revision_status"
        log "WARN" "Rollback may fail or cause issues"
    fi
    
    # Get revision info
    local revision_image=$(gcloud run revisions describe "$target_revision" \
        --region="$REGION" \
        --format="value(spec.template.spec.containers[0].image)")
    
    local revision_time=$(gcloud run revisions describe "$target_revision" \
        --region="$REGION" \
        --format="value(metadata.creationTimestamp)")
    
    log "INFO" "Target revision details:"
    log "INFO" "  Image: $revision_image"
    log "INFO" "  Created: $revision_time"
    log "INFO" "  Status: $revision_status"
    
    return 0
}

# Interactive rollback selection
interactive_rollback() {
    log "INFO" "Interactive rollback mode"
    
    echo "Available revisions:"
    get_revisions
    
    echo ""
    read -p "Enter revision name to rollback to: " target_revision
    
    if [[ -z "$target_revision" ]]; then
        log "ERROR" "No revision specified"
        return 1
    fi
    
    validate_rollback_target "$target_revision"
    
    echo ""
    echo "Rollback options:"
    echo "1. Immediate rollback (100% traffic)"
    echo "2. Canary rollback (gradual traffic shift)"
    echo "3. Cancel"
    
    read -p "Select option (1-3): " option
    
    case "$option" in
        1)
            rollback_to_revision "$target_revision"
            ;;
        2)
            read -p "Number of steps (default: 5): " steps
            read -p "Delay between steps in seconds (default: 30): " delay
            canary_rollback "$target_revision" "${steps:-5}" "${delay:-30}"
            ;;
        3)
            log "INFO" "Rollback cancelled"
            return 0
            ;;
        *)
            log "ERROR" "Invalid option"
            return 1
            ;;
    esac
}

show_help() {
    echo "EmailPilot Rollback Manager"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list                       List available revisions"
    echo "  current                    Show current revision"
    echo "  rollback <revision>        Rollback to specific revision"
    echo "  previous                   Rollback to previous revision"
    echo "  canary <revision> [steps] [delay]  Canary rollback"
    echo "  emergency                  Emergency rollback (immediate)"
    echo "  interactive                Interactive rollback selection"
    echo "  backup                     Create rollback backup"
    echo "  restore <backup_name>      Restore from backup"
    echo "  validate <revision>        Validate rollback target"
    echo ""
    echo "Examples:"
    echo "  $0 list                                    # List revisions"
    echo "  $0 rollback emailpilot-api-00042-xyz      # Rollback to specific revision"
    echo "  $0 previous                               # Rollback to previous revision"
    echo "  $0 canary emailpilot-api-00042-xyz 10 60 # Canary rollback with 10 steps, 60s delay"
    echo "  $0 emergency                              # Emergency rollback"
}

main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        "list")
            get_revisions
            ;;
        "current")
            current=$(get_current_revision)
            echo "Current revision: $current"
            ;;
        "rollback")
            if [[ $# -eq 0 ]]; then
                log "ERROR" "Revision name required"
                exit 1
            fi
            rollback_to_revision "$1"
            ;;
        "previous")
            rollback_to_previous
            ;;
        "canary")
            if [[ $# -eq 0 ]]; then
                log "ERROR" "Revision name required for canary rollback"
                exit 1
            fi
            canary_rollback "$1" "${2:-5}" "${3:-30}"
            ;;
        "emergency")
            emergency_rollback
            ;;
        "interactive")
            interactive_rollback
            ;;
        "backup")
            create_rollback_backup
            ;;
        "restore")
            if [[ $# -eq 0 ]]; then
                log "ERROR" "Backup name required"
                exit 1
            fi
            restore_from_backup "$1"
            ;;
        "validate")
            if [[ $# -eq 0 ]]; then
                log "ERROR" "Revision name required"
                exit 1
            fi
            validate_rollback_target "$1"
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log "ERROR" "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"