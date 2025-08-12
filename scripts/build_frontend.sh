#!/bin/bash

# Frontend Build Script - EmailPilot Dashboard
# Compiles JSX components to plain JavaScript for production
set -e

echo "🚀 Building EmailPilot Frontend..."

# Check if we're in the right directory
if [[ ! -f "frontend/public/index.html" ]]; then
    echo "❌ Error: Must run from project root directory"
    echo "   Looking for frontend/public/index.html"
    exit 1
fi

# Create dist directory if it doesn't exist
mkdir -p frontend/public/dist

# Check for required tools
if ! command -v npx &> /dev/null; then
    echo "❌ Error: npm/npx not found. Please install Node.js"
    exit 1
fi

# Install esbuild locally if not available
if ! npx esbuild --version &> /dev/null; then
    echo "📦 Installing esbuild..."
    npm init -y &> /dev/null || true
    npm install --save-dev esbuild
fi

echo "🔧 Compiling JSX components..."

# Define components that need JSX compilation
JSX_COMPONENTS=(
    "AdminAgentsPanel.js"
    "Calendar.js"
    "EventModal.js" 
    "CalendarChat.js"
    "CalendarView.js"
    "GoalsAwareCalendarDashboard.js"
    "GoalsEnhancedDashboard.js"
    "GoalsCompanyDashboard.js"
    "GoalsDataStatus.js"
    "GoalGeneratorPanel.js"
    "GoalsDashboard.js"
    "CalendarViewLocal.js"
)

# Compile main app.js with JSX
echo "  📄 Compiling app.js..."
npx esbuild frontend/public/app.js \
    --bundle \
    --format=iife \
    --global-name=EmailPilotApp \
    --loader:.js=jsx \
    --jsx=transform \
    --jsx-factory=React.createElement \
    --jsx-fragment=React.Fragment \
    --target=es2017 \
    --define:process.env.NODE_ENV='"production"' \
    --outfile=frontend/public/dist/app.js \
    --minify

# Compile each JSX component individually
for component in "${JSX_COMPONENTS[@]}"; do
    if [[ -f "frontend/public/components/$component" ]]; then
        echo "  📄 Compiling $component..."
        
        # Extract component name without .js extension
        component_name=$(basename "$component" .js)
        
        npx esbuild "frontend/public/components/$component" \
            --format=iife \
            --global-name="$component_name" \
            --loader:.js=jsx \
            --jsx=transform \
            --jsx-factory=React.createElement \
            --jsx-fragment=React.Fragment \
            --target=es2017 \
            --define:process.env.NODE_ENV='"production"' \
            --outfile="frontend/public/dist/$component" \
            --minify
    else
        echo "  ⚠️  Component $component not found, skipping..."
    fi
done

# Copy non-JSX components directly to dist
echo "📋 Copying non-JSX components..."
NON_JSX_COMPONENTS=(
    "FirebaseCalendarService.js"
    "GeminiChatService.js"
    "CalendarViewSimple.js"
    "AdminClientManagement.js"
    "DevLogin.js"
    "MCPKlaviyoManagement.js"
    "MCPManagementLocal.js"
    "UnifiedClientForm.js"
)

for component in "${NON_JSX_COMPONENTS[@]}"; do
    if [[ -f "frontend/public/components/$component" ]]; then
        echo "  📄 Copying $component..."
        cp "frontend/public/components/$component" "frontend/public/dist/$component"
    else
        echo "  ⚠️  Component $component not found, skipping..."
    fi
done

# Create a component loader to ensure proper loading order
echo "🔗 Creating component loader..."
cat > frontend/public/dist/component-loader.js << 'EOF'
// Component Loader - Ensures proper loading order and global availability
(function() {
    'use strict';
    
    console.log('EmailPilot: Component loader initialized');
    
    // Track loaded components
    window.EmailPilot = window.EmailPilot || {};
    window.EmailPilot.loadedComponents = {};
    window.EmailPilot.services = {};
    
    // Component loading tracker
    function markComponentLoaded(name) {
        window.EmailPilot.loadedComponents[name] = true;
        console.log('EmailPilot: Component loaded -', name);
        
        // Dispatch custom event for components that depend on others
        window.dispatchEvent(new CustomEvent('emailpilot-component-loaded', {
            detail: { componentName: name }
        }));
    }
    
    // Service initialization helper
    function initializeServices() {
        if (window.FirebaseCalendarService && !window.EmailPilot.services.firebase) {
            console.log('EmailPilot: Initializing Firebase service...');
            window.EmailPilot.services.firebase = new window.FirebaseCalendarService();
        }
        
        if (window.GeminiChatService && window.EmailPilot.services.firebase && !window.EmailPilot.services.gemini) {
            console.log('EmailPilot: Initializing Gemini service...');
            window.EmailPilot.services.gemini = new window.GeminiChatService(window.EmailPilot.services.firebase);
        }
    }
    
    // Auto-initialize services when components are loaded
    window.addEventListener('emailpilot-component-loaded', function(e) {
        initializeServices();
    });
    
    // Global error handler for component loading
    window.addEventListener('error', function(e) {
        if (e.filename && e.filename.includes('/dist/')) {
            console.error('EmailPilot: Component loading error:', e.message, e.filename);
        }
    });
    
    // Make functions available globally
    window.EmailPilot.markComponentLoaded = markComponentLoaded;
    window.EmailPilot.initializeServices = initializeServices;
    
    console.log('EmailPilot: Component loader ready');
})();
EOF

echo "✅ Frontend build complete!"
echo ""
echo "📁 Generated files:"
echo "   - frontend/public/dist/app.js (main application bundle)"
echo "   - frontend/public/dist/component-loader.js (loading utilities)"
echo "   - frontend/public/dist/*.js (individual components)"
echo ""
echo "🎯 Next steps:"
echo "   1. Update frontend/public/index.html to use compiled bundles"
echo "   2. Remove Babel runtime dependency"
echo "   3. Test the application"
echo ""
echo "💡 To run: ./scripts/build_frontend.sh"