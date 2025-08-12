// Calendar SPA Loader Component
// Smart loading system for EmailPilot SPA calendar components
// Provides fallback mechanisms and enhanced loading experience

const { useState, useEffect, useRef } = React;

// Make component available globally for SPA loading
window.CalendarSPALoader = function CalendarSPALoader() {
    const [componentState, setComponentState] = useState({
        loading: true,
        component: null,
        error: null,
        retryCount: 0,
        loadingStartTime: Date.now()
    });
    
    const retryTimeoutRef = useRef(null);
    const componentCheckIntervalRef = useRef(null);
    
    // Component priority order for loading
    const componentPriority = [
        {
            name: 'GoalsAwareCalendarSPA',
            displayName: 'Goals-Aware Calendar',
            description: 'Full-featured calendar with revenue goal tracking'
        },
        {
            name: 'CalendarView', 
            displayName: 'Enhanced Calendar',
            description: 'Feature-rich calendar with event management'
        },
        {
            name: 'CalendarViewSimple',
            displayName: 'Basic Calendar',
            description: 'Simple calendar interface'
        }
    ];
    
    // Check for available components
    const checkForComponents = () => {
        for (const comp of componentPriority) {
            if (typeof window[comp.name] === 'function') {
                console.log(`📅 Calendar SPA Loader: Found ${comp.displayName}`);
                return {
                    component: window[comp.name],
                    info: comp
                };
            }
        }
        return null;
    };
    
    // Initialize component loading
    useEffect(() => {
        let checkCount = 0;
        const maxChecks = 50; // 5 seconds at 100ms intervals
        
        const startLoading = () => {
            console.log('🔄 Calendar SPA Loader: Starting component search...');
            
            componentCheckIntervalRef.current = setInterval(() => {
                checkCount++;
                const found = checkForComponents();
                
                if (found) {
                    clearInterval(componentCheckIntervalRef.current);
                    const loadingTime = Date.now() - componentState.loadingStartTime;
                    
                    console.log(`✅ Calendar SPA Loader: Loaded ${found.info.displayName} in ${loadingTime}ms`);
                    
                    setComponentState(prev => ({
                        ...prev,
                        loading: false,
                        component: found.component,
                        componentInfo: found.info,
                        error: null
                    }));
                    
                } else if (checkCount >= maxChecks) {
                    clearInterval(componentCheckIntervalRef.current);
                    console.warn('⚠️ Calendar SPA Loader: No components found after timeout');
                    
                    setComponentState(prev => ({
                        ...prev,
                        loading: false,
                        error: 'Components not found'
                    }));
                }
            }, 100);
        };
        
        // Start loading immediately
        const immediate = checkForComponents();
        if (immediate) {
            console.log(`⚡ Calendar SPA Loader: Immediately found ${immediate.info.displayName}`);
            setComponentState(prev => ({
                ...prev,
                loading: false,
                component: immediate.component,
                componentInfo: immediate.info
            }));
        } else {
            startLoading();
        }
        
        // Cleanup
        return () => {
            if (componentCheckIntervalRef.current) {
                clearInterval(componentCheckIntervalRef.current);
            }
            if (retryTimeoutRef.current) {
                clearTimeout(retryTimeoutRef.current);
            }
        };
    }, [componentState.retryCount]);
    
    // Retry loading function
    const retryLoading = () => {
        console.log('🔄 Calendar SPA Loader: Retrying component loading...');
        setComponentState(prev => ({
            loading: true,
            component: null,
            error: null,
            retryCount: prev.retryCount + 1,
            loadingStartTime: Date.now()
        }));
    };
    
    // Force refresh function
    const forceRefresh = () => {
        console.log('🔄 Calendar SPA Loader: Force refreshing page...');
        window.location.reload();
    };
    
    // Loading state with progress indicator
    if (componentState.loading) {
        const loadingTime = Date.now() - componentState.loadingStartTime;
        const progressPercentage = Math.min((loadingTime / 3000) * 100, 95); // 3 second expected load
        
        return (
            <div className="bg-white rounded-lg shadow-md p-8">
                <div className="text-center">
                    <div className="mb-6">
                        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4"></div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            Loading Calendar Components
                        </h3>
                        <p className="text-gray-600 text-sm mb-4">
                            Searching for available calendar interfaces...
                        </p>
                    </div>
                    
                    {/* Loading progress bar */}
                    <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                        <div 
                            className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${progressPercentage}%` }}
                        />
                    </div>
                    
                    <div className="text-xs text-gray-500">
                        <p>Attempt {componentState.retryCount + 1} • {loadingTime}ms elapsed</p>
                        <p className="mt-2">Looking for: {componentPriority.map(c => c.displayName).join(', ')}</p>
                    </div>
                    
                    {loadingTime > 3000 && (
                        <button 
                            onClick={retryLoading}
                            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
                        >
                            Retry Loading
                        </button>
                    )}
                </div>
            </div>
        );
    }
    
    // Error state with diagnostics
    if (componentState.error) {
        return (
            <div className="bg-white rounded-lg shadow-md p-8">
                <div className="text-center">
                    <div className="text-6xl mb-4">⚠️</div>
                    <h3 className="text-lg font-semibold text-red-900 mb-2">
                        Calendar Components Not Available
                    </h3>
                    <p className="text-gray-600 mb-6">
                        Unable to load calendar components. This might be due to:
                    </p>
                    
                    <div className="text-left bg-gray-50 rounded-lg p-4 mb-6">
                        <ul className="text-sm text-gray-700 space-y-2">
                            <li className="flex items-start">
                                <span className="text-red-500 mr-2">•</span>
                                Component files not properly loaded
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-500 mr-2">•</span>
                                JavaScript execution errors
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-500 mr-2">•</span>
                                Network connectivity issues
                            </li>
                            <li className="flex items-start">
                                <span className="text-red-500 mr-2">•</span>
                                Browser compatibility problems
                            </li>
                        </ul>
                    </div>
                    
                    {/* Component availability diagnostic */}
                    <div className="text-left bg-blue-50 rounded-lg p-4 mb-6">
                        <h4 className="font-medium text-blue-900 mb-2">Component Diagnostic:</h4>
                        <div className="text-sm space-y-1">
                            {componentPriority.map(comp => (
                                <div key={comp.name} className="flex justify-between">
                                    <span className="text-blue-700">{comp.displayName}:</span>
                                    <span className={typeof window[comp.name] === 'function' ? 'text-green-600' : 'text-red-600'}>
                                        {typeof window[comp.name] === 'function' ? '✅ Available' : '❌ Missing'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                    
                    <div className="flex gap-4 justify-center">
                        <button 
                            onClick={retryLoading}
                            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                        >
                            Try Again
                        </button>
                        <button 
                            onClick={forceRefresh}
                            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                        >
                            Refresh Page
                        </button>
                    </div>
                    
                    <div className="mt-4 text-xs text-gray-500">
                        <p>Retry attempt: {componentState.retryCount}</p>
                        <p>For support, check browser console for errors</p>
                    </div>
                </div>
            </div>
        );
    }
    
    // Success state - render the loaded component
    if (componentState.component) {
        const ComponentToRender = componentState.component;
        
        return (
            <div>
                {/* Component info header (only show for a few seconds) */}
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center">
                            <span className="text-green-600 mr-2">✅</span>
                            <span className="text-sm font-medium text-green-800">
                                Loaded: {componentState.componentInfo?.displayName}
                            </span>
                        </div>
                        <span className="text-xs text-green-600">
                            Ready
                        </span>
                    </div>
                    {componentState.componentInfo?.description && (
                        <p className="text-xs text-green-700 mt-1">
                            {componentState.componentInfo.description}
                        </p>
                    )}
                </div>
                
                {/* Render the actual calendar component */}
                <ComponentToRender />
            </div>
        );
    }
    
    // Fallback state (shouldn't reach here)
    return (
        <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <div className="text-6xl mb-4">📅</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Calendar System</h3>
            <p className="text-gray-600">Initializing calendar interface...</p>
        </div>
    );
};

// Enhanced CalendarWrapper replacement that uses the smart loader
window.EnhancedCalendarWrapper = function EnhancedCalendarWrapper() {
    return React.createElement(window.CalendarSPALoader);
};

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CalendarSPALoader: window.CalendarSPALoader,
        EnhancedCalendarWrapper: window.EnhancedCalendarWrapper
    };
}

console.log('✅ CalendarSPALoader component loaded for EmailPilot SPA');