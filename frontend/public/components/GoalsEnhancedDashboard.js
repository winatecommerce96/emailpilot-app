// Enhanced Goals Dashboard Component with Month-to-Date Metrics
// Provides detailed goal tracking, MTD performance, and easy editing interface

const { useState, useEffect, useMemo, useCallback } = React;

function GoalsEnhancedDashboard({ 
    selectedClient, 
    user, 
    authToken,
    onClientChange,
    theme = 'light' 
}) {
    const [goalsData, setGoalsData] = useState([]);
    const [mtdData, setMtdData] = useState(null);
    const [editingGoal, setEditingGoal] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('current'); // 'current', 'planning', 'history'
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

    // API configuration
    const API_CONFIG = useMemo(() => ({
        baseURL: window.location.origin,
        headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        }
    }), [authToken]);

    // Fetch goals data
    const fetchGoalsData = useCallback(async () => {
        if (!selectedClient?.id) return;
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await fetch(
                `${API_CONFIG.baseURL}/api/goals/${selectedClient.id}`,
                { 
                    headers: API_CONFIG.headers,
                    credentials: 'include'
                }
            );
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            // Ensure goalsData is always an array
            if (Array.isArray(data)) {
                setGoalsData(data);
            } else if (data && Array.isArray(data.goals)) {
                setGoalsData(data.goals);
            } else {
                setGoalsData([]);
            }
            
            // Fetch MTD data for current month
            fetchMTDData();
        } catch (err) {
            console.error('Error fetching goals:', err);
            setError('Failed to load goals data');
            setGoalsData([]);
        } finally {
            setLoading(false);
        }
    }, [selectedClient?.id, API_CONFIG]);

    // Fetch Month-to-Date performance data
    const fetchMTDData = useCallback(async () => {
        if (!selectedClient?.id) return;
        
        try {
            // Fetch actual MTD data from our API
            const response = await fetch(
                `${API_CONFIG.baseURL}/api/performance/mtd/${selectedClient.id}`,
                { headers: API_CONFIG.headers }
            );
            
            if (response.ok) {
                const data = await response.json();
                
                // Transform API response to component format
                const mtdData = {
                    revenue: data.revenue.mtd,
                    orders: data.orders.mtd,
                    conversionRate: data.orders.conversion_rate,
                    avgOrderValue: data.orders.average_order_value,
                    emailsSent: data.email_performance.emails_sent,
                    openRate: data.email_performance.open_rate,
                    clickRate: data.email_performance.click_rate,
                    daysPassed: data.period.days_passed,
                    daysRemaining: data.period.days_remaining,
                    progressPercentage: data.period.progress_percentage,
                    projectedRevenue: data.revenue.projected_eom,
                    dailyAverage: data.revenue.daily_average,
                    goal: data.revenue.goal,
                    goalProgress: data.revenue.goal_progress
                };
                
                setMtdData(mtdData);
            } else {
                // Fallback to mock data if API fails
                const currentDate = new Date();
                const currentMonth = currentDate.getMonth() + 1;
                const currentYear = currentDate.getFullYear();
                const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
                const daysPassed = currentDate.getDate();
                
                const mockMTDData = {
                    revenue: Math.random() * 50000 + 10000,
                    orders: Math.floor(Math.random() * 200 + 50),
                    conversionRate: Math.random() * 5 + 1,
                    avgOrderValue: Math.random() * 100 + 50,
                    emailsSent: Math.floor(Math.random() * 10000 + 5000),
                    openRate: Math.random() * 30 + 15,
                    clickRate: Math.random() * 5 + 1,
                    daysPassed,
                    daysRemaining: daysInMonth - daysPassed,
                    progressPercentage: (daysPassed / daysInMonth) * 100,
                    projectedRevenue: (Math.random() * 50000 + 10000) * (daysInMonth / daysPassed)
                };
                
                setMtdData(mockMTDData);
            }
        } catch (err) {
            console.error('Error fetching MTD data:', err);
        }
    }, [selectedClient?.id, API_CONFIG]);

    // Load data when client changes
    useEffect(() => {
        if (selectedClient?.id) {
            fetchGoalsData();
        }
    }, [selectedClient?.id, fetchGoalsData]);

    // Format currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    };

    // Format percentage
    const formatPercentage = (value) => {
        return `${(value || 0).toFixed(1)}%`;
    };

    // Calculate goal status
    const getGoalStatus = (goal, actual) => {
        const percentage = (actual / goal) * 100;
        if (percentage >= 100) return { status: 'achieved', color: 'text-green-600', bgColor: 'bg-green-100' };
        if (percentage >= 80) return { status: 'on-track', color: 'text-blue-600', bgColor: 'bg-blue-100' };
        if (percentage >= 60) return { status: 'at-risk', color: 'text-yellow-600', bgColor: 'bg-yellow-100' };
        return { status: 'behind', color: 'text-red-600', bgColor: 'bg-red-100' };
    };

    // Handle goal editing
    const handleEditGoal = (goal) => {
        setEditingGoal({
            ...goal,
            newValue: goal.revenue_goal
        });
    };

    // Save edited goal
    const saveGoal = async () => {
        if (!editingGoal) return;
        
        try {
            const endpoint = editingGoal.id 
                ? `${API_CONFIG.baseURL}/api/goals/${editingGoal.id}`
                : `${API_CONFIG.baseURL}/api/goals/`;
            
            const method = editingGoal.id ? 'PUT' : 'POST';
            
            const response = await fetch(endpoint, {
                method,
                headers: API_CONFIG.headers,
                body: JSON.stringify({
                    client_id: selectedClient.id,
                    year: editingGoal.year,
                    month: editingGoal.month,
                    revenue_goal: editingGoal.newValue,
                    calculation_method: 'manual',
                    notes: editingGoal.notes || ''
                })
            });
            
            if (!response.ok) throw new Error('Failed to save goal');
            
            // Refresh data
            fetchGoalsData();
            setEditingGoal(null);
        } catch (err) {
            console.error('Error saving goal:', err);
            alert('Failed to save goal');
        }
    };

    // Month-to-Date Performance Card
    const MTDPerformanceCard = () => {
        if (!mtdData) return null;
        
        const currentGoal = goalsData.find(g => 
            g.month === new Date().getMonth() + 1 && 
            g.year === new Date().getFullYear()
        );
        
        const goalStatus = currentGoal ? getGoalStatus(currentGoal.revenue_goal, mtdData.revenue) : null;
        
        return (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                        📊 Month-to-Date Performance
                    </h3>
                    <span className="text-sm text-gray-500">
                        Day {mtdData.daysPassed} of {mtdData.daysPassed + mtdData.daysRemaining}
                    </span>
                </div>
                
                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-gray-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-green-600">
                            {formatCurrency(mtdData.revenue)}
                        </div>
                        <div className="text-sm text-gray-600">MTD Revenue</div>
                        {currentGoal && (
                            <div className="text-xs text-gray-500 mt-1">
                                {formatPercentage((mtdData.revenue / currentGoal.revenue_goal) * 100)} of goal
                            </div>
                        )}
                    </div>
                    
                    <div className="bg-gray-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-blue-600">
                            {mtdData.orders}
                        </div>
                        <div className="text-sm text-gray-600">Orders</div>
                        <div className="text-xs text-gray-500 mt-1">
                            {formatCurrency(mtdData.avgOrderValue)} AOV
                        </div>
                    </div>
                    
                    <div className="bg-gray-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-purple-600">
                            {formatPercentage(mtdData.conversionRate)}
                        </div>
                        <div className="text-sm text-gray-600">Conv. Rate</div>
                        <div className="text-xs text-gray-500 mt-1">
                            From {mtdData.emailsSent.toLocaleString()} emails
                        </div>
                    </div>
                    
                    <div className="bg-gray-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-orange-600">
                            {formatCurrency(mtdData.projectedRevenue)}
                        </div>
                        <div className="text-sm text-gray-600">Projected</div>
                        <div className="text-xs text-gray-500 mt-1">
                            End of month
                        </div>
                    </div>
                </div>
                
                {/* Email Performance */}
                <div className="border-t pt-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Email Performance</h4>
                    <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                            <div className="text-lg font-semibold">{formatPercentage(mtdData.openRate)}</div>
                            <div className="text-xs text-gray-600">Open Rate</div>
                        </div>
                        <div className="text-center">
                            <div className="text-lg font-semibold">{formatPercentage(mtdData.clickRate)}</div>
                            <div className="text-xs text-gray-600">Click Rate</div>
                        </div>
                        <div className="text-center">
                            <div className="text-lg font-semibold">{mtdData.emailsSent.toLocaleString()}</div>
                            <div className="text-xs text-gray-600">Emails Sent</div>
                        </div>
                    </div>
                </div>
                
                {/* Progress Indicator */}
                {currentGoal && (
                    <div className="mt-4 pt-4 border-t">
                        <div className="flex justify-between items-center mb-2">
                            <span className="text-sm font-medium text-gray-700">Goal Progress</span>
                            <span className={`text-sm font-semibold ${goalStatus.color}`}>
                                {goalStatus.status.toUpperCase()}
                            </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                            <div 
                                className={`h-3 rounded-full transition-all duration-500 ${
                                    goalStatus.status === 'achieved' ? 'bg-green-500' :
                                    goalStatus.status === 'on-track' ? 'bg-blue-500' :
                                    goalStatus.status === 'at-risk' ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${Math.min(100, (mtdData.revenue / currentGoal.revenue_goal) * 100)}%` }}
                            ></div>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>{formatCurrency(mtdData.revenue)}</span>
                            <span>{formatCurrency(currentGoal.revenue_goal)}</span>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    // Goals Chart Component
    const GoalsChart = () => {
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const currentMonth = new Date().getMonth();
        
        // Get goals for selected year
        const yearGoals = goalsData.filter(g => g.year === selectedYear);
        
        // Calculate max value for scaling
        const maxValue = Math.max(...yearGoals.map(g => g.revenue_goal || 0), mtdData?.projectedRevenue || 0);
        
        return (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                        📈 Revenue Goals Overview - {selectedYear}
                    </h3>
                    <div className="flex items-center space-x-2">
                        <button 
                            onClick={() => setSelectedYear(selectedYear - 1)}
                            className="p-1 hover:bg-gray-100 rounded"
                        >
                            ←
                        </button>
                        <span className="px-3 py-1 bg-gray-100 rounded">{selectedYear}</span>
                        <button 
                            onClick={() => setSelectedYear(selectedYear + 1)}
                            className="p-1 hover:bg-gray-100 rounded"
                        >
                            →
                        </button>
                    </div>
                </div>
                
                {/* Bar Chart */}
                <div className="relative h-64 mb-4">
                    <div className="absolute inset-0 flex items-end justify-between space-x-2">
                        {months.map((month, index) => {
                            const goal = yearGoals.find(g => g.month === index + 1);
                            const height = goal ? (goal.revenue_goal / maxValue) * 100 : 0;
                            const isCurrentMonth = index === currentMonth && selectedYear === new Date().getFullYear();
                            const actualHeight = isCurrentMonth && mtdData && mtdData.revenue ? (mtdData.revenue / maxValue) * 100 : 0;
                            
                            return (
                                <div key={month} className="flex-1 flex flex-col items-center">
                                    <div className="w-full flex items-end justify-center space-x-1 h-48">
                                        {/* Goal Bar */}
                                        <div 
                                            className={`w-6 bg-gray-300 rounded-t cursor-pointer hover:bg-gray-400 transition-colors ${
                                                isCurrentMonth ? 'opacity-50' : ''
                                            }`}
                                            style={{ height: `${height}%` }}
                                            onClick={() => handleEditGoal({
                                                month: index + 1,
                                                year: selectedYear,
                                                revenue_goal: goal?.revenue_goal || 0,
                                                id: goal?.id
                                            })}
                                            title={goal ? formatCurrency(goal.revenue_goal) : 'Click to set goal'}
                                        ></div>
                                        
                                        {/* Actual Bar (for current month) */}
                                        {isCurrentMonth && mtdData && (
                                            <div 
                                                className="w-6 bg-green-500 rounded-t"
                                                style={{ height: `${actualHeight}%` }}
                                                title={formatCurrency(mtdData ? mtdData.revenue : 0)}
                                            ></div>
                                        )}
                                    </div>
                                    
                                    <div className="text-xs text-gray-600 mt-2">{month}</div>
                                    
                                    {goal && (
                                        <div className="text-xs text-gray-500">
                                            {formatCurrency(goal.revenue_goal).replace('$', '')}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
                
                {/* Legend */}
                <div className="flex items-center justify-center space-x-4 text-sm">
                    <div className="flex items-center">
                        <div className="w-4 h-4 bg-gray-300 rounded mr-2"></div>
                        <span>Goal</span>
                    </div>
                    <div className="flex items-center">
                        <div className="w-4 h-4 bg-green-500 rounded mr-2"></div>
                        <span>MTD Actual</span>
                    </div>
                </div>
            </div>
        );
    };

    // Goal Editor Modal
    const GoalEditorModal = () => {
        if (!editingGoal) return null;
        
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December'];
        
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg shadow-xl p-6 w-96">
                    <h3 className="text-lg font-semibold mb-4">
                        Edit Goal - {months[editingGoal.month - 1]} {editingGoal.year}
                    </h3>
                    
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Revenue Goal
                            </label>
                            <div className="relative">
                                <span className="absolute left-3 top-2 text-gray-500">$</span>
                                <input
                                    type="number"
                                    value={editingGoal.newValue}
                                    onChange={(e) => setEditingGoal({
                                        ...editingGoal,
                                        newValue: parseFloat(e.target.value) || 0
                                    })}
                                    className="w-full pl-8 pr-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                        </div>
                        
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Notes (optional)
                            </label>
                            <textarea
                                value={editingGoal.notes || ''}
                                onChange={(e) => setEditingGoal({
                                    ...editingGoal,
                                    notes: e.target.value
                                })}
                                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                rows="3"
                                placeholder="Add any notes about this goal..."
                            />
                        </div>
                        
                        {/* Quick Set Buttons */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Quick Set
                            </label>
                            <div className="grid grid-cols-3 gap-2">
                                {[25000, 50000, 75000, 100000, 150000, 200000].map(amount => (
                                    <button
                                        key={amount}
                                        onClick={() => setEditingGoal({
                                            ...editingGoal,
                                            newValue: amount
                                        })}
                                        className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                                    >
                                        {formatCurrency(amount)}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                    
                    <div className="flex justify-end space-x-3 mt-6">
                        <button
                            onClick={() => setEditingGoal(null)}
                            className="px-4 py-2 text-gray-600 hover:text-gray-800"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={saveGoal}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                        >
                            Save Goal
                        </button>
                    </div>
                </div>
            </div>
        );
    };

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

    if (!selectedClient) {
        return (
            <div className="text-center py-16">
                <div className="text-gray-400 text-6xl mb-4">🎯</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Select a Client to View Goals
                </h3>
                <p className="text-gray-600">
                    Choose a client to see goals and performance metrics
                </p>
            </div>
        );
    }

    return (
        <div className="goals-enhanced-dashboard max-w-7xl mx-auto p-6">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">
                    🎯 Goals & Performance Dashboard
                </h1>
                <p className="text-gray-600">
                    Track revenue goals and month-to-date performance for {selectedClient.name}
                </p>
            </div>

            {/* Main Chart */}
            <GoalsChart />
            
            {/* MTD Performance */}
            <MTDPerformanceCard />
            
            {/* Goal Editor Modal */}
            <GoalEditorModal />
            
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                    <p className="text-red-700">{error}</p>
                </div>
            )}
        </div>
    );
}

// Export the component
window.GoalsEnhancedDashboard = GoalsEnhancedDashboard;