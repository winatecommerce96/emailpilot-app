#!/bin/bash

# EmailPilot Service Manager
# Handles starting, stopping, scaling Cloud Run services
# Version: 1.0.0

set -euo pipefail

PROJECT_ID="emailpilot-438321"
SERVICE_NAME="emailpilot-api"
REGION="us-central1"

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

# Get service status
get_status() {
    log "INFO" "Checking service status..."
    
    local status=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.conditions[0].type,status.conditions[0].status)" 2>/dev/null || echo "NotFound,Unknown")
    
    local url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "N/A")
    
    local traffic=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.traffic[0].percent)" 2>/dev/null || echo "0")
    
    local min_instances=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(spec.template.metadata.annotations['run.googleapis.com/execution-environment'])" 2>/dev/null || echo "N/A")
    
    echo "Service Status Report"
    echo "====================="
    echo "Service: $SERVICE_NAME"
    echo "Region: $REGION"
    echo "Status: $status"
    echo "URL: $url"
    echo "Traffic: ${traffic}%"
    echo "Min Instances: $min_instances"
    
    # Test service health
    if [[ "$url" != "N/A" ]]; then
        log "INFO" "Testing service health..."
        local health_code=$(curl -s -o /dev/null -w "%{http_code}" "$url/health" 2>/dev/null || echo "000")
        if [[ "$health_code" == "200" ]]; then
            log "SUCCESS" "Service is healthy"
        else
            log "WARN" "Service health check returned: $health_code"
        fi
    fi
}

# Stop service
stop_service() {
    log "INFO" "Stopping Cloud Run service..."
    
    gcloud run services update "$SERVICE_NAME" \
        --region="$REGION" \
        --min-instances=0 \
        --max-instances=0 \
        --no-cpu-throttling
    
    log "SUCCESS" "Service stopped (scaled to 0 instances)"
}

# Start service
start_service() {
    local min_instances="${1:-0}"
    local max_instances="${2:-10}"
    
    log "INFO" "Starting Cloud Run service..."
    log "INFO" "Min instances: $min_instances, Max instances: $max_instances"
    
    gcloud run services update "$SERVICE_NAME" \
        --region="$REGION" \
        --min-instances="$min_instances" \
        --max-instances="$max_instances"
    
    # Wait for service to be ready
    log "INFO" "Waiting for service to be ready..."
    gcloud run services wait "$SERVICE_NAME" --region="$REGION"
    
    log "SUCCESS" "Service started and ready"
}

# Scale service
scale_service() {
    local min_instances="$1"
    local max_instances="$2"
    
    log "INFO" "Scaling service to min: $min_instances, max: $max_instances"
    
    gcloud run services update "$SERVICE_NAME" \
        --region="$REGION" \
        --min-instances="$min_instances" \
        --max-instances="$max_instances"
    
    log "SUCCESS" "Service scaled successfully"
}

# Restart service
restart_service() {
    log "INFO" "Restarting service..."
    stop_service
    sleep 5
    start_service
    log "SUCCESS" "Service restarted"
}

# Get logs
get_logs() {
    local lines="${1:-100}"
    
    log "INFO" "Fetching last $lines log entries..."
    
    gcloud logs read "projects/$PROJECT_ID/logs/run.googleapis.com%2Frequests" \
        --filter="resource.labels.service_name=$SERVICE_NAME" \
        --limit="$lines" \
        --format="table(timestamp,severity,textPayload)"
}

# Monitor service
monitor_service() {
    log "INFO" "Monitoring service (press Ctrl+C to stop)..."
    
    while true; do
        clear
        get_status
        echo ""
        echo "Last 10 log entries:"
        echo "==================="
        get_logs 10
        sleep 30
    done
}

show_help() {
    echo "EmailPilot Service Manager"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  status                     Show service status"
    echo "  stop                       Stop service (scale to 0)"
    echo "  start [min] [max]         Start service with scaling"
    echo "  restart                   Restart service"
    echo "  scale <min> <max>         Scale service"
    echo "  logs [lines]              Show service logs"
    echo "  monitor                   Monitor service in real-time"
    echo ""
    echo "Examples:"
    echo "  $0 status                 # Show current status"
    echo "  $0 stop                   # Stop service"
    echo "  $0 start 1 5             # Start with 1-5 instances"
    echo "  $0 scale 0 10            # Scale to 0-10 instances"
    echo "  $0 logs 50               # Show last 50 log entries"
}

# Main function
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        "status")
            get_status
            ;;
        "stop")
            stop_service
            ;;
        "start")
            start_service "${1:-0}" "${2:-10}"
            ;;
        "restart")
            restart_service
            ;;
        "scale")
            if [[ $# -lt 2 ]]; then
                log "ERROR" "Scale command requires min and max instances"
                echo "Usage: $0 scale <min> <max>"
                exit 1
            fi
            scale_service "$1" "$2"
            ;;
        "logs")
            get_logs "${1:-100}"
            ;;
        "monitor")
            monitor_service
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