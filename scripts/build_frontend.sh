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
    "app.js"
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
    "MCPManagement.js"
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
        
        # Compile without global-name to avoid variable shadowing
        # The source files already have window.ComponentName assignments
        npx esbuild "frontend/public/components/$component" \
            --format=iife \
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
    "AdminOAuthConfig.js"
    "DevLogin.js"
    "MCPKlaviyoManagement.js"
    "MCPManagementLocal.js"
    "UnifiedClientForm.js"
)

# Copy utilities from utils folder
echo "📋 Copying utility files..."
UTILITY_FILES=(
    "auth.js"
)

for utility in "${UTILITY_FILES[@]}"; do
    if [[ -f "frontend/public/utils/$utility" ]]; then
        echo "  📄 Copying utils/$utility..."
        cp "frontend/public/utils/$utility" "frontend/public/dist/$utility"
    else
        echo "  ⚠️  Utility $utility not found, skipping..."
    fi
done

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
// Component loader with event-based ready signal
(function() {
    const requiredComponents = ['CalendarView', 'Calendar', 'EventModal', 'CalendarViewSimple'];
    
    function checkComponents() {
        const missing = [];
        const available = [];
        
        requiredComponents.forEach(name => {
            if (typeof window[name] === 'function') {
                available.push(name);
            } else {
                missing.push(name);
            }
        });
        
        console.log('Component check:', {
            required: requiredComponents,
            available: available,
            missing: missing
        });
        
        return missing.length === 0;
    }
    
    function notifyReady() {
        console.log('All components ready!');
        window.dispatchEvent(new CustomEvent('components:ready', {
            detail: { components: requiredComponents }
        }));
    }
    
    // Check immediately
    if (checkComponents()) {
        notifyReady();
    } else {
        // Poll for components
        let attempts = 0;
        const maxAttempts = 30; // 3 seconds at 100ms intervals
        
        const interval = setInterval(() => {
            attempts++;
            if (checkComponents()) {
                clearInterval(interval);
                notifyReady();
            } else if (attempts >= maxAttempts) {
                clearInterval(interval);
                console.warn('Component loading timeout - some components may be missing');
                window.dispatchEvent(new CustomEvent('components:timeout', {
                    detail: { 
                        missing: requiredComponents.filter(n => typeof window[n] !== 'function')
                    }
                }));
            }
        }, 100);
    }
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