// Goals-Aware Calendar SPA Component
// Enhanced calendar component designed specifically for EmailPilot's SPA architecture
// Integrates seamlessly with existing sidebar navigation and component loading system

const { useState, useEffect, useMemo, useCallback } = React;

// Make component available globally for SPA loading
window.GoalsAwareCalendarSPA = function GoalsAwareCalendarSPA() {
    // State management
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [selectedClient, setSelectedClient] = useState(null);
    const [clients, setClients] = useState([]);
    const [dashboardData, setDashboardData] = useState(null);
    const [activeView, setActiveView] = useState('calendar'); // 'calendar', 'goals', 'analytics'
    
    // API configuration
    const API_BASE_URL = window.API_BASE_URL || window.location.origin;
    
    // Initialize component
    useEffect(() => {
        loadClients();
    }, []);
    
    // Load clients for selection
    const loadClients = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/api/clients/`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setClients(data);
                
                // Auto-select first client if available
                if (data.length > 0) {
                    setSelectedClient(data[0]);
                }
            }
        } catch (error) {
            console.error('Error loading clients:', error);
            setError('Failed to load clients');
        } finally {
            setLoading(false);
        }
    };
    
    // Load goals dashboard data
    const loadDashboardData = useCallback(async (clientId) => {
        if (!clientId) return;
        
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/api/goals-calendar/dashboard/${clientId}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setDashboardData(data);
            } else {
                // Goals data may not exist - this is ok
                setDashboardData({ has_goal: false });
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            setDashboardData({ has_goal: false });
        } finally {
            setLoading(false);
        }
    }, [API_BASE_URL]);
    
    // Load dashboard data when client changes
    useEffect(() => {
        if (selectedClient?.id) {
            loadDashboardData(selectedClient.id);
        }
    }, [selectedClient, loadDashboardData]);
    
    // Format currency values
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    };
    
    // Get progress color
    const getProgressColor = (percentage, isOnTrack) => {
        if (isOnTrack) return 'bg-green-500';
        if (percentage >= 70) return 'bg-yellow-500';
        if (percentage >= 40) return 'bg-orange-500';
        return 'bg-red-500';
    };
    
    // Client selector component
    const ClientSelector = () => (
        <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Client
            </label>
            <select
                value={selectedClient?.id || ''}
                onChange={(e) => {
                    const client = clients.find(c => c.id.toString() === e.target.value);
                    setSelectedClient(client);
                }}
                className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
                <option value="">Select a client...</option>
                {clients.map(client => (
                    <option key={client.id} value={client.id}>
                        {client.name}
                    </option>
                ))}
            </select>
        </div>
    );
    
    // Goals progress widget
    const GoalsProgressWidget = () => {
        if (!dashboardData?.has_goal) return null;
        
        const { goal, progress } = dashboardData;
        
        return (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                        <span className="text-2xl mr-2">🎯</span>
                        Revenue Goal Progress
                    </h3>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        progress?.is_on_track 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                    }`}>
                        {progress?.is_on_track ? 'On Track' : 'Needs Attention'}
                    </span>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="text-center">
                        <div className="text-lg md:text-2xl font-bold text-blue-600">
                            {formatCurrency(goal?.revenue_goal)}
                        </div>
                        <div className="text-sm text-gray-500">Goal</div>
                    </div>
                    <div className="text-center">
                        <div className="text-lg md:text-2xl font-bold text-green-600">
                            {formatCurrency(progress?.current_revenue)}
                        </div>
                        <div className="text-sm text-gray-500">Current</div>
                    </div>
                    <div className="text-center">
                        <div className="text-lg md:text-2xl font-bold text-orange-600">
                            {formatCurrency(progress?.remaining_revenue)}
                        </div>
                        <div className="text-sm text-gray-500">Remaining</div>
                    </div>
                    <div className="text-center">
                        <div className="text-lg md:text-2xl font-bold text-purple-600">
                            {progress?.days_remaining || 0}
                        </div>
                        <div className="text-sm text-gray-500">Days Left</div>
                    </div>
                </div>
                
                <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
                    <div 
                        className={`h-4 rounded-full transition-all duration-300 ${
                            getProgressColor(progress?.progress_percentage, progress?.is_on_track)
                        }`}
                        style={{ width: `${Math.min(progress?.progress_percentage || 0, 100)}%` }}
                    />
                </div>
                <div className="text-center text-sm text-gray-600">
                    {Math.round(progress?.progress_percentage || 0)}% Complete
                </div>
            </div>
        );
    };
    
    // AI Recommendations widget
    const AIRecommendations = () => {
        if (!dashboardData?.recommendations?.length) return null;
        
        return (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <span className="text-2xl mr-2">🤖</span>
                    AI Campaign Recommendations
                </h3>
                
                <div className="space-y-4">
                    {dashboardData.recommendations.slice(0, 3).map((rec, index) => (
                        <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                            <div className="font-medium text-gray-900">{rec.title}</div>
                            <div className="text-sm text-gray-600 mt-1">{rec.description}</div>
                            {rec.priority && (
                                <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium mt-2 ${
                                    rec.priority === 'high' ? 'bg-red-100 text-red-800' :
                                    rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-green-100 text-green-800'
                                }`}>
                                    {rec.priority.charAt(0).toUpperCase() + rec.priority.slice(1)} Priority
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        );
    };
    
    // Calendar view switcher
    const ViewSwitcher = () => (
        <div className="flex bg-gray-100 rounded-lg p-1 mb-6">
            {[
                { id: 'calendar', label: 'Calendar', icon: '📅' },
                { id: 'goals', label: 'Goals', icon: '🎯' },
                { id: 'analytics', label: 'Analytics', icon: '📊' }
            ].map(view => (
                <button
                    key={view.id}
                    onClick={() => setActiveView(view.id)}
                    className={`flex items-center px-4 py-2 rounded-md font-medium text-sm transition-colors ${
                        activeView === view.id
                            ? 'bg-white text-indigo-600 shadow'
                            : 'text-gray-600 hover:text-gray-900'
                    }`}
                >
                    <span className="mr-2">{view.icon}</span>
                    {view.label}
                </button>
            ))}
        </div>
    );
    
    // Calendar component wrapper
    const CalendarComponent = () => {
        // Try to use existing calendar components with fallback
        if (window.CalendarView) {
            return React.createElement(window.CalendarView);
        } else if (window.CalendarViewSimple) {
            return React.createElement(window.CalendarViewSimple);
        } else {
            return (
                <div className="bg-white rounded-lg shadow-md p-8 text-center">
                    <div className="text-6xl mb-4">📅</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Calendar Loading</h3>
                    <p className="text-gray-600 mb-4">
                        Calendar components are initializing. This may take a moment.
                    </p>
                    <button 
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                    >
                        Refresh Page
                    </button>
                </div>
            );
        }
    };
    
    // No client selected state
    if (!selectedClient) {
        return (
            <div className="bg-white rounded-lg shadow-md p-8">
                <div className="text-center">
                    <div className="text-6xl mb-4">📅</div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">Calendar with Goals</h2>
                    <p className="text-gray-600 mb-6">
                        Select a client to view their calendar and revenue goals.
                    </p>
                    <ClientSelector />
                    
                    {loading && (
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    )}
                    
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
                            <p className="text-red-800">{error}</p>
                            <button 
                                onClick={loadClients}
                                className="mt-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                            >
                                Try Again
                            </button>
                        </div>
                    )}
                </div>
            </div>
        );
    }
    
    // Main calendar view with goals integration
    return (
        <div className="space-y-6">
            {/* Client selector */}
            <ClientSelector />
            
            {/* Goals progress (if available) */}
            <GoalsProgressWidget />
            
            {/* AI Recommendations (if available) */}
            <AIRecommendations />
            
            {/* View switcher */}
            <ViewSwitcher />
            
            {/* Active view content */}
            <div className="min-h-96">
                {loading && (
                    <div className="flex items-center justify-center py-12">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mr-3"></div>
                        <span className="text-gray-600">Loading...</span>
                    </div>
                )}
                
                {!loading && (
                    <>
                        {activeView === 'calendar' && <CalendarComponent />}
                        
                        {activeView === 'goals' && (
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Goals Management</h3>
                                {dashboardData?.has_goal ? (
                                    <div className="space-y-4">
                                        <p className="text-gray-600">
                                            Manage and track revenue goals for {selectedClient.name}.
                                        </p>
                                        <GoalsProgressWidget />
                                    </div>
                                ) : (
                                    <div className="text-center py-8">
                                        <div className="text-4xl mb-4">🎯</div>
                                        <h4 className="text-lg font-medium text-gray-900 mb-2">
                                            No Goals Set
                                        </h4>
                                        <p className="text-gray-600 mb-4">
                                            Set revenue goals to track progress and get AI recommendations.
                                        </p>
                                        <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                                            Set Goals
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                        
                        {activeView === 'analytics' && (
                            <div className="bg-white rounded-lg shadow-md p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Analytics & Performance</h3>
                                <div className="text-center py-8">
                                    <div className="text-4xl mb-4">📊</div>
                                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                                        Analytics Dashboard
                                    </h4>
                                    <p className="text-gray-600">
                                        Advanced analytics and performance metrics coming soon.
                                    </p>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.GoalsAwareCalendarSPA;
}

console.log('✅ GoalsAwareCalendarSPA component loaded for EmailPilot SPA');