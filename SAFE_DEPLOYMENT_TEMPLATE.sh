#!/bin/bash
# Safe Deployment Script Template for EmailPilot Packages
# This template ensures packages don't break EmailPilot with dependency conflicts

echo "🚀 Deploying [PACKAGE_NAME] to EmailPilot.ai"
echo "==========================================="

# IMPORTANT: Check if we're being deployed by EmailPilot
if [ "$EMAILPILOT_DEPLOYMENT" = "true" ]; then
    echo "✅ Detected EmailPilot deployment environment"
    SAFE_MODE=true
else
    echo "⚠️  Running outside EmailPilot deployment"
    SAFE_MODE=false
fi

# Function to safely deploy without installing dependencies
safe_deploy() {
    echo "🛡️  Running in SAFE MODE - no dependency installation"
    
    # Find EmailPilot root directory
    EMAILPILOT_ROOT=""
    if [ -f "../main_firestore.py" ]; then
        EMAILPILOT_ROOT=".."
    elif [ -f "../../main_firestore.py" ]; then
        EMAILPILOT_ROOT="../.."
    elif [ -f "../../../main_firestore.py" ]; then
        EMAILPILOT_ROOT="../../.."
    fi
    
    if [ -z "$EMAILPILOT_ROOT" ]; then
        echo "❌ Cannot determine EmailPilot root directory"
        echo "   Please ensure this package is extracted within EmailPilot"
        exit 1
    fi
    
    echo "📍 EmailPilot root: $EMAILPILOT_ROOT"
    
    # Step 1: Copy frontend components (if any)
    if [ -d "frontend" ]; then
        echo "📦 Copying frontend components..."
        # Add your frontend file copying logic here
        # Example:
        # mkdir -p "$EMAILPILOT_ROOT/frontend/public/components/[package_name]"
        # cp -r frontend/* "$EMAILPILOT_ROOT/frontend/public/components/[package_name]/"
    fi
    
    # Step 2: Copy backend components (if any)
    if [ -d "api" ] || [ -d "services" ]; then
        echo "📦 Preparing backend components for integration..."
        # Create a directory for manual integration
        INTEGRATION_DIR="$EMAILPILOT_ROOT/integrations/[package_name]_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$INTEGRATION_DIR"
        
        # Copy files for manual review
        [ -d "api" ] && cp -r api "$INTEGRATION_DIR/"
        [ -d "services" ] && cp -r services "$INTEGRATION_DIR/"
        [ -d "models" ] && cp -r models "$INTEGRATION_DIR/"
        [ -d "schemas" ] && cp -r schemas "$INTEGRATION_DIR/"
        
        echo "✅ Backend files copied to: $INTEGRATION_DIR"
        echo "   Please manually integrate these into main_firestore.py"
    fi
    
    # Step 3: Copy configuration files (if any)
    if [ -f "config.json" ] || [ -f ".env.example" ]; then
        echo "📦 Copying configuration templates..."
        # Add configuration copying logic here
    fi
    
    # Step 4: Create integration documentation
    cat > "$EMAILPILOT_ROOT/INTEGRATION_[PACKAGE_NAME].md" << EOF
# [PACKAGE_NAME] Integration Guide

## Installation Date
$(date)

## Components Installed
- Frontend: [List frontend components]
- Backend: [List backend components]
- Configuration: [List config files]

## Manual Integration Required
1. Review files in integrations/[package_name]_*/
2. Add necessary API endpoints to main_firestore.py
3. Update frontend to include new components
4. Test functionality before deploying

## Important Notes
- Dependencies were NOT installed to prevent conflicts
- Use EmailPilot's existing packages
- Test thoroughly in development first

EOF
    
    echo "✅ Integration guide created"
}

# Main deployment logic
if [ "$SAFE_MODE" = true ] || [ "$EMAILPILOT_DEPLOYMENT" = "true" ]; then
    # Always use safe deployment when called by EmailPilot
    safe_deploy
else
    # Manual execution - give options
    echo ""
    echo "🤔 How would you like to deploy?"
    echo "1. Safe mode (recommended) - no dependency installation"
    echo "2. Full installation - may cause conflicts"
    echo "3. Exit"
    
    read -p "Choice (1-3): " choice
    
    case $choice in
        1)
            safe_deploy
            ;;
        2)
            echo "⚠️  WARNING: Full installation may break EmailPilot!"
            read -p "Are you sure? (y/N): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                # Original unsafe deployment
                pip install -r requirements.txt
                # Add your original deployment logic here
            else
                echo "👍 Good choice! Using safe mode instead."
                safe_deploy
            fi
            ;;
        *)
            echo "👋 Exiting..."
            exit 0
            ;;
    esac
fi

echo ""
echo "🎉 Deployment complete!"
echo "=================================="
echo ""
echo "📋 Next steps:"
echo "1. Review the integration guide"
echo "2. Manually integrate components as needed"
echo "3. Test in development environment"
echo "4. Deploy using standard EmailPilot deployment"