// Goals-Aware Calendar Dashboard Component
// Enhanced calendar interface that displays goal progress and strategic recommendations

const { useState, useEffect, useMemo } = React;

function GoalsAwareCalendarDashboard({ 
    selectedClient, 
    user, 
    authToken,
    onClientChange,
    theme = 'light' 
}) {
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeView, setActiveView] = useState('overview'); // 'overview', 'calendar', 'analytics', 'recommendations'
    const [error, setError] = useState(null);

    // API configuration for EmailPilot.ai
    const API_CONFIG = useMemo(() => ({
        baseURL: window.location.origin,
        headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        }
    }), [authToken]);

    // Fetch dashboard data when client changes
    useEffect(() => {
        if (selectedClient?.id) {
            fetchDashboardData();
        }
    }, [selectedClient?.id]);

    const fetchDashboardData = async () => {
        if (!selectedClient?.id || !authToken) return;
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await fetch(
                `${API_CONFIG.baseURL}/api/goals-calendar/dashboard/${selectedClient.id}`,
                { headers: API_CONFIG.headers }
            );
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            setDashboardData(data);
        } catch (err) {
            console.error('Error fetching dashboard data:', err);
            setError('Failed to load goals dashboard');
        } finally {
            setLoading(false);
        }
    };

    // Format currency values
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    };

    // Get progress color based on status
    const getProgressColor = (percentage, isOnTrack) => {
        if (isOnTrack) return 'bg-green-500';
        if (percentage >= 70) return 'bg-yellow-500';
        if (percentage >= 40) return 'bg-orange-500';
        return 'bg-red-500';
    };

    // Render goal progress widget
    const GoalProgressWidget = () => {
        if (!dashboardData?.has_goal) return null;
        
        const { goal, progress } = dashboardData;
        
        return (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                        🎯 Revenue Goal Progress
                    </h3>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        progress.is_on_track 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                    }`}>
                        {progress.is_on_track ? 'On Track' : 'Needs Attention'}
                    </span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                    <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">
                            {formatCurrency(goal.revenue_goal)}
                        </div>
                        <div className="text-sm text-gray-600">Monthly Goal</div>
                    </div>
                    
                    <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">
                            {formatCurrency(progress.estimated_revenue)}
                        </div>
                        <div className="text-sm text-gray-600">Progress</div>
                    </div>
                    
                    <div className="text-center">
                        <div className="text-2xl font-bold text-orange-600">
                            {formatCurrency(progress.remaining_amount)}
                        </div>
                        <div className="text-sm text-gray-600">Remaining</div>
                    </div>
                    
                    <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600">
                            {progress.days_remaining}
                        </div>
                        <div className="text-sm text-gray-600">Days Left</div>
                    </div>
                </div>
                
                {/* Progress Bar */}
                <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>{progress.progress_percentage.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                            className={`h-3 rounded-full transition-all duration-500 ${
                                getProgressColor(progress.progress_percentage, progress.is_on_track)
                            }`}
                            style={{ width: `${Math.min(100, progress.progress_percentage)}%` }}
                        ></div>
                    </div>
                </div>
                
                {/* Campaign Count */}
                <div className="text-center text-sm text-gray-600">
                    📅 {progress.campaign_count} campaigns scheduled • 
                    💡 {dashboardData.recommendations?.length || 0} strategic recommendations available
                </div>
            </div>
        );
    };

    // Render recommendations widget
    const RecommendationsWidget = () => {
        if (!dashboardData?.recommendations?.length) return null;
        
        return (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    💡 Strategic Recommendations
                </h3>
                
                <div className="space-y-3">
                    {dashboardData.recommendations.slice(0, 3).map((rec, index) => (
                        <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                            <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-gray-900">
                                    {rec.title}
                                </span>
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                    rec.priority === 'high' ? 'bg-red-100 text-red-800' :
                                    rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-green-100 text-green-800'
                                }`}>
                                    {rec.priority} priority
                                </span>
                            </div>
                            <p className="text-sm text-gray-600">{rec.description}</p>
                            {rec.estimated_impact && (
                                <div className="text-xs text-green-600 mt-1">
                                    💰 Estimated impact: {formatCurrency(rec.estimated_impact)}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
                
                <button 
                    onClick={() => setActiveView('recommendations')}
                    className="mt-4 w-full text-center text-blue-600 text-sm font-medium hover:text-blue-800"
                >
                    View All Recommendations →
                </button>
            </div>
        );
    };

    // Render view tabs
    const ViewTabs = () => (
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-6">
            {[
                { id: 'overview', label: '📊 Overview', icon: '📊' },
                { id: 'calendar', label: '📅 Calendar', icon: '📅' },
                { id: 'analytics', label: '📈 Analytics', icon: '📈' },
                { id: 'recommendations', label: '💡 Strategy', icon: '🎯' }
            ].map(tab => (
                <button
                    key={tab.id}
                    onClick={() => setActiveView(tab.id)}
                    className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        activeView === tab.id 
                            ? 'bg-white text-blue-600 shadow-sm' 
                            : 'text-gray-600 hover:text-gray-900'
                    }`}
                >
                    {tab.label}
                </button>
            ))}
        </div>
    );

    // Main render
    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="animate-spin h-8 w-8 border-b-2 border-blue-600 rounded-full mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading goals dashboard...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <div className="text-red-600 text-lg mb-2">⚠️ Error</div>
                <p className="text-red-700 mb-4">{error}</p>
                <button 
                    onClick={() => { setError(null); fetchDashboardData(); }}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
                >
                    Try Again
                </button>
            </div>
        );
    }

    if (!selectedClient) {
        return (
            <div className="text-center py-16">
                <div className="text-gray-400 text-6xl mb-4">🎯</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Select a Client to View Goals Dashboard
                </h3>
                <p className="text-gray-600">
                    Choose a client to see goal progress and strategic recommendations
                </p>
            </div>
        );
    }

    if (!dashboardData?.has_goal) {
        return (
            <div className="text-center py-16">
                <div className="text-gray-400 text-6xl mb-4">🎯</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No Revenue Goals Found
                </h3>
                <p className="text-gray-600 mb-4">
                    Set revenue goals to enable strategic campaign planning and AI recommendations.
                </p>
                <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
                    Set Goals
                </button>
            </div>
        );
    }

    return (
        <div className="goals-aware-calendar-dashboard max-w-7xl mx-auto p-6">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            🎯 Strategic Campaign Calendar
                        </h1>
                        <p className="text-gray-600 mt-1">
                            Goal-driven email campaign planning for {selectedClient.name}
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-gray-500">Welcome, {user?.name}</p>
                        <p className="text-xs text-gray-400">
                            Goals-aware • AI-powered • Revenue-focused
                        </p>
                    </div>
                </div>
                
                {/* View Tabs */}
                <ViewTabs />
            </div>

            {/* Main Content */}
            <div className="dashboard-content">
                {/* Overview View */}
                {activeView === 'overview' && (
                    <div className="space-y-6">
                        <GoalProgressWidget />
                        <RecommendationsWidget />
                        
                        {/* Quick Actions */}
                        <div className="bg-white rounded-lg shadow-md p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                ⚡ Quick Actions
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <button 
                                    onClick={() => setActiveView('calendar')}
                                    className="p-4 border rounded-lg hover:bg-blue-50 transition-colors"
                                >
                                    <div className="text-blue-600 text-2xl mb-2">📅</div>
                                    <div className="font-medium">View Calendar</div>
                                    <div className="text-sm text-gray-600">Manage campaigns</div>
                                </button>
                                
                                <button 
                                    onClick={() => setActiveView('recommendations')}
                                    className="p-4 border rounded-lg hover:bg-green-50 transition-colors"
                                >
                                    <div className="text-green-600 text-2xl mb-2">🎯</div>
                                    <div className="font-medium">Get Strategy</div>
                                    <div className="text-sm text-gray-600">AI recommendations</div>
                                </button>
                                
                                <button 
                                    onClick={() => setActiveView('analytics')}
                                    className="p-4 border rounded-lg hover:bg-purple-50 transition-colors"
                                >
                                    <div className="text-purple-600 text-2xl mb-2">📈</div>
                                    <div className="font-medium">View Analytics</div>
                                    <div className="text-sm text-gray-600">Performance trends</div>
                                </button>
                            </div>
                        </div>
                    </div>
                )}
                
                {/* Calendar View */}
                {activeView === 'calendar' && (
                    <div className="bg-white rounded-lg border shadow-sm">
                        <GoalsAwareCalendarView 
                            clientId={selectedClient.id}
                            clientName={selectedClient.name}
                            apiConfig={API_CONFIG}
                            goalsData={dashboardData}
                            theme={theme}
                        />
                    </div>
                )}
                
                {/* Analytics View */}
                {activeView === 'analytics' && (
                    <div className="bg-white rounded-lg border shadow-sm p-6">
                        <GoalsAnalyticsView 
                            clientId={selectedClient.id}
                            apiConfig={API_CONFIG}
                            goalsData={dashboardData}
                        />
                    </div>
                )}
                
                {/* Recommendations View */}
                {activeView === 'recommendations' && (
                    <div className="bg-white rounded-lg border shadow-sm p-6">
                        <GoalsRecommendationsView 
                            clientId={selectedClient.id}
                            apiConfig={API_CONFIG}
                            goalsData={dashboardData}
                            onRefresh={fetchDashboardData}
                        />
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="mt-12 pt-6 border-t border-gray-200 text-center">
                <p className="text-xs text-gray-500">
                    🎯 Revenue Goal Tracking • 🤖 AI Strategic Planning • 📊 Performance Analytics • 🔥 Powered by Firebase
                </p>
            </div>
        </div>
    );
}

// Placeholder components for different views (to be implemented)
function GoalsAwareCalendarView({ clientId, clientName, apiConfig, goalsData, theme }) {
    return (
        <div className="p-6">
            <div className="mb-4 p-4 bg-blue-50 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">🎯 Goal-Aware Calendar Planning</h4>
                <p className="text-blue-700 text-sm">
                    This enhanced calendar considers your {goalsData?.goal ? `$${goalsData.goal.revenue_goal?.toLocaleString()} revenue goal` : 'revenue goals'} 
                    {' '}when suggesting campaign types and scheduling recommendations.
                </p>
            </div>
            {/* Calendar component would be integrated here */}
            <div className="text-center py-8 text-gray-500">
                Enhanced Calendar View - Integration with existing calendar components
            </div>
        </div>
    );
}

function GoalsAnalyticsView({ clientId, apiConfig, goalsData }) {
    return (
        <div>
            <h3 className="text-lg font-semibold mb-4">📈 Goal Achievement Analytics</h3>
            <div className="text-center py-8 text-gray-500">
                Analytics view showing goal trends, achievement rates, and performance forecasts
            </div>
        </div>
    );
}

function GoalsRecommendationsView({ clientId, apiConfig, goalsData, onRefresh }) {
    return (
        <div>
            <h3 className="text-lg font-semibold mb-4">🎯 Strategic Recommendations</h3>
            <div className="text-center py-8 text-gray-500">
                AI-powered strategic recommendations for achieving revenue goals
            </div>
        </div>
    );
}

// Export the component
window.GoalsAwareCalendarDashboard = GoalsAwareCalendarDashboard;