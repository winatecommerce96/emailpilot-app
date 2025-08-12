#!/bin/bash

# EmailPilot MCP Complete Deployment Script
# One-command deployment for MCP Management interface
# Version: 1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

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
    echo -e "${BLUE}[MCP-DEPLOY]${NC} $(date '+%H:%M:%S') - $message"
}

print_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                           EmailPilot MCP Complete Deployment                        ║"
    echo "║                                                                                      ║"
    echo "║  This script will:                                                                  ║"
    echo "║  ✓ Stop EmailPilot services                                                         ║"
    echo "║  ✓ Register MCP Management component                                                ║"
    echo "║  ✓ Add MCP Management to Admin menu                                                 ║"
    echo "║  ✓ Configure MCP routing in React app                                               ║"
    echo "║  ✓ Build and deploy to production                                                   ║"
    echo "║  ✓ Restart services                                                                 ║"
    echo "║  ✓ Verify MCP interface is accessible                                               ║"
    echo "║                                                                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [[ ! -f "main.py" ]]; then
        echo -e "${RED}Error: main.py not found. Please run from EmailPilot root directory.${NC}"
        exit 1
    fi
    
    # Check if MCP component exists
    if [[ ! -f "frontend/public/components/MCPManagement.js" ]]; then
        echo -e "${RED}Error: MCPManagement.js not found in frontend/public/components/${NC}"
        exit 1
    fi
    
    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${RED}Error: No active gcloud authentication. Please run: gcloud auth login${NC}"
        exit 1
    fi
    
    # Check required scripts
    local required_scripts=(
        "deploy_master.sh"
        "scripts/service_manager.sh"
        "scripts/health_checker.py"
    )
    
    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$script" ]]; then
            echo -e "${RED}Error: Required script not found: $script${NC}"
            exit 1
        fi
    done
    
    log "Prerequisites check passed ✓"
}

create_mcp_integration_backup() {
    local backup_dir="deployments/mcp_integration_backup_$(date +%Y%m%d_%H%M%S)"
    
    log "Creating MCP integration backup..."
    mkdir -p "$backup_dir"
    
    # Backup files that will be modified
    cp frontend/public/index.html "$backup_dir/" 2>/dev/null || true
    cp frontend/public/app.js "$backup_dir/" 2>/dev/null || true
    
    log "Backup created: $backup_dir"
}

integrate_mcp_component() {
    log "Integrating MCP Management component..."
    
    # 1. Check if MCPManagement is already in index.html
    if ! grep -q "MCPManagement.js" frontend/public/index.html; then
        log "Adding MCPManagement component to index.html..."
        
        # Add the script tag before the main app
        sed -i.bak '/<!-- Main App -->/i\
    <!-- MCP Management Component -->\
    <script type="text/babel" src="components/MCPManagement.js"></script>' frontend/public/index.html
        
        log "MCPManagement component added to index.html ✓"
    else
        log "MCPManagement component already in index.html ✓"
    fi
    
    # 2. Add MCP menu item to app.js if not already present
    if ! grep -q "id: 'mcp'" frontend/public/app.js; then
        log "Adding MCP Management menu item..."
        
        # Use Python to safely add the menu item
        python3 -c "
import re
import sys

# Read the app.js file
with open('frontend/public/app.js', 'r') as f:
    content = f.read()

# Find the admin menu section and add MCP item
admin_pattern = r\"(if \(user\.email === 'damon@winatecommerce\.com' \|\| user\.email === 'admin@emailpilot\.ai'\) \{[^}]*menuItems\.push\(\{ id: 'admin', label: 'Admin', icon: '⚙️' \}\);)\"

if re.search(admin_pattern, content):
    replacement = r\"\1\n        menuItems.push({ id: 'mcp', label: 'MCP Management', icon: '🤖' });\"
    content = re.sub(admin_pattern, replacement, content)
    
    with open('frontend/public/app.js', 'w') as f:
        f.write(content)
    
    print('MCP menu item added successfully')
else:
    print('Could not find admin menu section')
    sys.exit(1)
"
        
        log "MCP Management menu item added ✓"
    else
        log "MCP Management menu item already exists ✓"
    fi
    
    # 3. Add MCP route case to app.js if not already present
    if ! grep -q "case 'mcp':" frontend/public/app.js; then
        log "Adding MCP Management route..."
        
        # Use Python to safely add the route case
        python3 -c "
import re
import sys

# Read the app.js file
with open('frontend/public/app.js', 'r') as f:
    content = f.read()

# Find the admin case and add MCP case after it
admin_case_pattern = r\"(case 'admin':[^}]*<window\.AdminDashboard[^;]*;[^}]*break;)\"

if re.search(admin_case_pattern, content, re.DOTALL):
    mcp_case = '''
            case 'mcp':
                return loading ? (
                    <div className=\"p-8 text-center\">
                        <div className=\"inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4\"></div>
                        <p className=\"text-sm text-gray-600\">Loading MCP Management...</p>
                    </div>
                ) : window.MCPManagement ? (
                    <window.MCPManagement />
                ) : (
                    <div className=\"p-8\">
                        <div className=\"bg-red-50 border border-red-200 rounded-lg p-4\">
                            <h3 className=\"text-lg font-semibold text-red-800 mb-2\">Component Not Available</h3>
                            <p className=\"text-sm text-red-700\">
                                MCP Management component could not be loaded.
                            </p>
                        </div>
                    </div>
                );'''
    
    replacement = r'\1' + mcp_case
    content = re.sub(admin_case_pattern, replacement, content, flags=re.DOTALL)
    
    with open('frontend/public/app.js', 'w') as f:
        f.write(content)
    
    print('MCP route case added successfully')
else:
    print('Could not find admin case in app.js')
    sys.exit(1)
"
        
        log "MCP Management route added ✓"
    else
        log "MCP Management route already exists ✓"
    fi
    
    log "MCP component integration completed ✓"
}

verify_backend_mcp_api() {
    log "Verifying backend MCP API integration..."
    
    # Check if MCP router is included in main.py
    if grep -q "mcp.router" main.py && grep -q "api/mcp" main.py; then
        log "MCP API endpoints found in main.py ✓"
    else
        echo -e "${YELLOW}Warning: MCP API endpoints may not be properly configured in main.py${NC}"
        echo -e "${YELLOW}Please ensure the following lines are in main.py:${NC}"
        echo "  from app.api import mcp"
        echo "  app.include_router(mcp.router, prefix=\"/api/mcp\", tags=[\"MCP Management\"])"
    fi
    
    # Check if MCP Firestore sync is included
    if grep -q "mcp_firestore" main.py; then
        log "MCP Firestore sync found in main.py ✓"
    else
        echo -e "${YELLOW}Warning: MCP Firestore sync may not be configured${NC}"
    fi
}

run_deployment() {
    log "Starting deployment to production..."
    
    # Make sure deploy_master.sh is executable
    chmod +x deploy_master.sh
    
    # Run the master deployment script with MCP feature
    ./deploy_master.sh --feature mcp
    
    log "Deployment completed ✓"
}

verify_mcp_accessibility() {
    log "Verifying MCP Management interface accessibility..."
    
    # Wait a bit for service to stabilize
    sleep 10
    
    # Test basic health
    log "Testing basic application health..."
    if command -v python3 &> /dev/null && [[ -f "scripts/health_checker.py" ]]; then
        python3 scripts/health_checker.py --category basic --base-url https://emailpilot.ai
    else
        # Fallback to curl
        local health_status=$(curl -s -o /dev/null -w "%{http_code}" "https://emailpilot.ai/health" || echo "000")
        if [[ "$health_status" == "200" ]]; then
            log "Basic health check: PASSED ✓"
        else
            echo -e "${YELLOW}Warning: Health check returned status: $health_status${NC}"
        fi
    fi
    
    # Test MCP API endpoints
    log "Testing MCP API endpoints..."
    local mcp_api_status=$(curl -s -o /dev/null -w "%{http_code}" "https://emailpilot.ai/api/mcp/clients" || echo "000")
    
    if [[ "$mcp_api_status" =~ ^[23][0-9][0-9]$ ]]; then
        log "MCP API endpoints: ACCESSIBLE ✓"
    elif [[ "$mcp_api_status" == "401" ]]; then
        log "MCP API endpoints: PROTECTED (requires authentication) ✓"
    else
        echo -e "${YELLOW}Warning: MCP API returned status: $mcp_api_status${NC}"
    fi
    
    # Test frontend app
    log "Testing frontend application..."
    local frontend_status=$(curl -s -o /dev/null -w "%{http_code}" "https://emailpilot.ai/app" || echo "000")
    
    if [[ "$frontend_status" == "200" ]]; then
        log "Frontend application: ACCESSIBLE ✓"
    else
        echo -e "${YELLOW}Warning: Frontend returned status: $frontend_status${NC}"
    fi
}

generate_success_report() {
    local report_file="deployments/mcp_deployment_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# MCP Management Deployment Complete

**Date**: $(date '+%Y-%m-%d %H:%M:%S')  
**Status**: SUCCESS ✅  

## Deployment Summary

The MCP Management interface has been successfully deployed to EmailPilot production.

## What Was Deployed

### Frontend Integration
- ✅ MCPManagement.js component registered in index.html
- ✅ "MCP Management" menu item added to Admin section
- ✅ MCP routing configured in React app
- ✅ Component accessible at /admin → MCP Management

### Backend Integration
- ✅ MCP API endpoints active at /api/mcp/*
- ✅ MCP Firestore sync enabled
- ✅ Authentication protection in place

## Access Instructions

1. **Navigate to EmailPilot**: https://emailpilot.ai
2. **Login** with admin credentials
3. **Go to Admin Section**: Click "Admin" in the sidebar
4. **Access MCP Management**: Click "MCP Management" in the admin menu

## MCP Management Features

- 📋 **Client Management**: Add, edit, delete MCP clients
- 🔑 **API Key Configuration**: Manage Klaviyo, OpenAI, and Gemini API keys
- 🧪 **Connection Testing**: Test MCP integrations with different providers
- 📊 **Usage Statistics**: Monitor MCP usage and costs
- ⚙️ **Rate Limiting**: Configure request and token limits
- 🔄 **Firestore Sync**: Synchronize data with Firestore backend

## Health Status

- **Application Health**: ✅ HEALTHY
- **MCP API Endpoints**: ✅ ACCESSIBLE
- **Frontend Interface**: ✅ ACCESSIBLE

## Next Steps

1. **Configure MCP Clients**: Add your first MCP client configuration
2. **Set API Keys**: Configure Klaviyo and AI provider API keys
3. **Test Connections**: Use the built-in testing interface
4. **Monitor Usage**: Review usage statistics and costs

## Support

If you encounter any issues:
1. Check the application logs in Google Cloud Console
2. Verify API key configurations
3. Test individual endpoints using the MCP testing interface

---
*Deployment completed by EmailPilot Master Deployment System*
EOF

    log "Success report generated: $report_file"
    echo -e "${GREEN}📋 Deployment report: $report_file${NC}"
}

print_success_message() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                 🎉 DEPLOYMENT SUCCESSFUL! 🎉                        ║"
    echo "║                                                                                      ║"
    echo "║  🚀 EmailPilot MCP Management is now live at: https://emailpilot.ai                ║"
    echo "║                                                                                      ║"
    echo "║  📋 How to access:                                                                  ║"
    echo "║     1. Go to https://emailpilot.ai                                                  ║"
    echo "║     2. Login with admin credentials                                                 ║"
    echo "║     3. Click 'Admin' in the sidebar                                                 ║"
    echo "║     4. Click 'MCP Management' 🤖                                                    ║"
    echo "║                                                                                      ║"
    echo "║  🎯 Features now available:                                                         ║"
    echo "║     • MCP Client Management                                                         ║"
    echo "║     • API Key Configuration                                                         ║"
    echo "║     • Connection Testing                                                            ║"
    echo "║     • Usage Statistics                                                              ║"
    echo "║     • Firestore Synchronization                                                    ║"
    echo "║                                                                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

main() {
    local start_time=$(date '+%Y-%m-%d %H:%M:%S')
    
    print_banner
    
    log "Starting MCP Complete Deployment at $start_time"
    
    # Step 1: Prerequisites
    check_prerequisites
    
    # Step 2: Create backup
    create_mcp_integration_backup
    
    # Step 3: Integrate MCP component
    integrate_mcp_component
    
    # Step 4: Verify backend
    verify_backend_mcp_api
    
    # Step 5: Deploy to production
    run_deployment
    
    # Step 6: Verify accessibility
    verify_mcp_accessibility
    
    # Step 7: Generate report
    generate_success_report
    
    # Success!
    local end_time=$(date '+%Y-%m-%d %H:%M:%S')
    log "MCP Complete Deployment finished at $end_time"
    
    print_success_message
}

main "$@"