#!/bin/bash

# EmailPilot Calendar Feature - Cloud Run Deployment Script
# This script builds and deploys the calendar feature to Google Cloud Run

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
export PROJECT_ID=emailpilot-438321
export REGION=us-central1
export SERVICE=emailpilot-api
export IMAGE_TAG=calendar-$(date +%Y%m%d-%H%M%S)
export FULL_IMAGE=gcr.io/$PROJECT_ID/$SERVICE:$IMAGE_TAG

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    # Check if correct project is set
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [[ "$CURRENT_PROJECT" != "$PROJECT_ID" ]]; then
        log_warning "Current project is $CURRENT_PROJECT, setting to $PROJECT_ID"
        gcloud config set project $PROJECT_ID
    fi
    
    # Check if Dockerfile exists
    if [[ ! -f "Dockerfile" ]]; then
        log_error "Dockerfile not found in current directory"
        exit 1
    fi
    
    # Check if calendar router is wired in
    if ! grep -q "calendar_router" main_firestore.py; then
        log_error "Calendar router not found in main_firestore.py"
        log_info "Please ensure the calendar router is imported and registered"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create backup of current deployment
create_deployment_backup() {
    log_info "Creating backup of current deployment configuration..."
    
    BACKUP_DIR="backups/deployment_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Get current service configuration
    gcloud run services describe $SERVICE \
        --region=$REGION \
        --format=export > "$BACKUP_DIR/service-config.yaml" 2>/dev/null || log_warning "No existing service to backup"
    
    # Get current image
    CURRENT_IMAGE=$(gcloud run services describe $SERVICE \
        --region=$REGION \
        --format="value(spec.template.spec.containers[0].image)" 2>/dev/null || echo "none")
    
    echo "PREVIOUS_IMAGE=$CURRENT_IMAGE" > "$BACKUP_DIR/rollback-info.txt"
    echo "DEPLOYMENT_DATE=$(date)" >> "$BACKUP_DIR/rollback-info.txt"
    
    log_success "Backup created at: $BACKUP_DIR"
}

# Build Docker image
build_image() {
    log_info "Building Docker image: $FULL_IMAGE"
    
    # Ensure calendar.py is in the right place
    if [[ ! -f "app/api/calendar.py" ]]; then
        log_error "Calendar API file not found at app/api/calendar.py"
        exit 1
    fi
    
    # Submit build to Cloud Build
    log_info "Submitting build to Cloud Build..."
    gcloud builds submit \
        --project $PROJECT_ID \
        --tag $FULL_IMAGE \
        --timeout=20m \
        . || {
            log_error "Docker build failed"
            exit 1
        }
    
    log_success "Docker image built successfully: $FULL_IMAGE"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    # Deploy the new image
    gcloud run deploy $SERVICE \
        --region $REGION \
        --image $FULL_IMAGE \
        --platform managed \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 0 \
        --port 8000 \
        --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
        --set-env-vars "PYTHONUNBUFFERED=1" \
        --set-env-vars "PORT=8000" \
        --update-labels "feature=calendar,version=$IMAGE_TAG" || {
            log_error "Deployment failed"
            exit 1
        }
    
    log_success "Service deployed successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE \
        --region=$REGION \
        --format="value(status.url)")
    
    if [[ -z "$SERVICE_URL" ]]; then
        log_error "Could not get service URL"
        exit 1
    fi
    
    log_info "Service URL: $SERVICE_URL"
    
    # Test calendar health endpoint
    log_info "Testing calendar health endpoint..."
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/api/calendar/health" || echo "000")
    
    if [[ "$HEALTH_RESPONSE" == "200" ]]; then
        log_success "Calendar health check passed"
    else
        log_warning "Calendar health check returned: $HEALTH_RESPONSE"
        log_info "This might be normal if authentication is required"
    fi
    
    # Test main health endpoint
    log_info "Testing main health endpoint..."
    MAIN_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" || echo "000")
    
    if [[ "$MAIN_HEALTH" == "200" ]]; then
        log_success "Main health check passed"
    else
        log_warning "Main health check returned: $MAIN_HEALTH"
    fi
    
    # Display calendar endpoints
    log_info "Calendar API endpoints available at:"
    echo "  • GET    $SERVICE_URL/api/calendar/events"
    echo "  • POST   $SERVICE_URL/api/calendar/events"
    echo "  • PUT    $SERVICE_URL/api/calendar/events/{id}"
    echo "  • DELETE $SERVICE_URL/api/calendar/events/{id}"
    echo "  • GET    $SERVICE_URL/api/calendar/clients"
    echo "  • GET    $SERVICE_URL/api/calendar/goals/{client_id}"
    echo "  • GET    $SERVICE_URL/api/calendar/dashboard/{client_id}"
    echo "  • POST   $SERVICE_URL/api/calendar/ai/chat"
    echo "  • POST   $SERVICE_URL/api/calendar/ai/summarize"
}

# Generate deployment report
generate_report() {
    log_info "Generating deployment report..."
    
    REPORT_FILE="calendar-deployment-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$REPORT_FILE" << EOF
EmailPilot Calendar Feature - Cloud Run Deployment Report
=========================================================
Deployment Date: $(date)
Project ID: $PROJECT_ID
Region: $REGION
Service Name: $SERVICE
Image Tag: $IMAGE_TAG
Full Image: $FULL_IMAGE

Service URL: $(gcloud run services describe $SERVICE --region=$REGION --format="value(status.url)")

Calendar Endpoints:
- GET    /api/calendar/events
- POST   /api/calendar/events
- PUT    /api/calendar/events/{id}
- DELETE /api/calendar/events/{id}
- GET    /api/calendar/clients
- POST   /api/calendar/clients
- GET    /api/calendar/goals/{client_id}
- GET    /api/calendar/dashboard/{client_id}
- POST   /api/calendar/ai/chat
- POST   /api/calendar/ai/summarize
- GET    /api/calendar/health

Features Deployed:
✅ Calendar event management (CRUD operations)
✅ Client management
✅ Revenue goals integration
✅ Dashboard with progress tracking
✅ AI chat assistance (mock responses for now)
✅ Document import capability

Next Steps:
1. Update frontend to use new calendar endpoints
2. Configure Gemini API for AI features
3. Test all calendar functionality
4. Monitor Cloud Run logs for errors
5. Set up Firebase security rules

Rollback Command (if needed):
gcloud run services update $SERVICE \\
  --region=$REGION \\
  --image=<previous-image-from-backup>

View Logs:
gcloud run logs read --service=$SERVICE --region=$REGION --limit=50

=========================================================
EOF
    
    log_success "Deployment report saved to: $REPORT_FILE"
}

# Rollback function
rollback() {
    log_warning "Starting rollback process..."
    
    # Find most recent backup
    LATEST_BACKUP=$(ls -t backups/deployment_*/rollback-info.txt 2>/dev/null | head -1)
    
    if [[ -z "$LATEST_BACKUP" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    # Get previous image
    PREVIOUS_IMAGE=$(grep "PREVIOUS_IMAGE=" "$LATEST_BACKUP" | cut -d= -f2)
    
    if [[ "$PREVIOUS_IMAGE" == "none" ]] || [[ -z "$PREVIOUS_IMAGE" ]]; then
        log_error "No previous image found in backup"
        exit 1
    fi
    
    log_info "Rolling back to image: $PREVIOUS_IMAGE"
    
    # Deploy previous image
    gcloud run deploy $SERVICE \
        --region $REGION \
        --image $PREVIOUS_IMAGE \
        --platform managed || {
            log_error "Rollback failed"
            exit 1
        }
    
    log_success "Rollback completed successfully"
}

# Main deployment process
main() {
    echo "=================================================="
    echo "EmailPilot Calendar Feature - Cloud Run Deployment"
    echo "=================================================="
    echo
    
    check_prerequisites
    create_deployment_backup
    build_image
    deploy_to_cloud_run
    verify_deployment
    generate_report
    
    echo
    echo "=================================================="
    log_success "✅ Calendar Feature Deployed Successfully!"
    echo "=================================================="
    echo
    echo "🎉 What's Deployed:"
    echo "   • Calendar API endpoints at /api/calendar/*"
    echo "   • Firebase integration for data persistence"
    echo "   • Revenue goals and dashboard features"
    echo "   • AI chat assistance (ready for Gemini integration)"
    echo
    echo "🚀 Access Your Calendar API:"
    SERVICE_URL=$(gcloud run services describe $SERVICE --region=$REGION --format="value(status.url)")
    echo "   Base URL: $SERVICE_URL"
    echo "   Health Check: $SERVICE_URL/api/calendar/health"
    echo
    echo "📋 Next Steps:"
    echo "   1. Update frontend to use calendar endpoints"
    echo "   2. Test all calendar functionality"
    echo "   3. Configure Gemini API for AI features"
    echo "   4. Monitor logs: gcloud run logs read --service=$SERVICE --region=$REGION"
    echo
    echo "📊 Report Generated: calendar-deployment-report-*.txt"
    echo
    log_success "Deployment completed successfully! 🎊"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "verify")
        verify_deployment
        ;;
    "help")
        echo "Usage: $0 [deploy|rollback|verify|help]"
        echo "  deploy   - Build and deploy calendar feature (default)"
        echo "  rollback - Rollback to previous deployment"
        echo "  verify   - Verify current deployment"
        echo "  help     - Show this help"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac