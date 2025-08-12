// Company-Wide Goals Dashboard with Multi-Client View
// Shows all clients' MTD performance and goals in a unified dashboard

const { useState, useEffect, useMemo, useCallback } = React;

function GoalsCompanyDashboard({ user, authToken }) {
    const [clients, setClients] = useState([]);
    const [clientsData, setClientsData] = useState({});
    const [mtdData, setMtdData] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
    const [editingGoal, setEditingGoal] = useState(null);

    // API configuration
    const API_CONFIG = useMemo(() => ({
        baseURL: window.location.origin,
        headers: {
            'Content-Type': 'application/json'
        }
    }), []);

    // Fetch all clients with goals
    const fetchAllClientsData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            
            // Fetch clients list
            const clientsResponse = await fetch(
                `${API_CONFIG.baseURL}/api/goals/clients`,
                { 
                    headers: API_CONFIG.headers,
                    credentials: 'include'
                }
            );
            
            if (!clientsResponse.ok) throw new Error('Failed to fetch clients');
            const clientsList = await clientsResponse.json();
            setClients(clientsList);
            
            // Fetch goals and MTD data for each client
            const dataPromises = clientsList.map(async (client) => {
                try {
                    // Fetch goals
                    const goalsResponse = await fetch(
                        `${API_CONFIG.baseURL}/api/goals/${client.id}`,
                        { 
                            headers: API_CONFIG.headers,
                            credentials: 'include'
                        }
                    );
                    
                    // Fetch MTD performance for selected month/year
                    const mtdResponse = await fetch(
                        `${API_CONFIG.baseURL}/api/performance/mtd/${client.id}?year=${selectedYear}&month=${selectedMonth}`,
                        { 
                            headers: API_CONFIG.headers,
                            credentials: 'include'
                        }
                    );
                    
                    const goalsData = goalsResponse.ok ? await goalsResponse.json() : [];
                    const mtdPerf = mtdResponse.ok ? await mtdResponse.json() : null;
                    
                    return {
                        clientId: client.id,
                        goals: Array.isArray(goalsData) ? goalsData : goalsData.goals || [],
                        mtd: mtdPerf
                    };
                } catch (err) {
                    console.error(`Error fetching data for client ${client.id}:`, err);
                    return {
                        clientId: client.id,
                        goals: [],
                        mtd: null
                    };
                }
            });
            
            const results = await Promise.all(dataPromises);
            
            // Organize data by client ID
            const clientsDataMap = {};
            const mtdDataMap = {};
            
            results.forEach(result => {
                clientsDataMap[result.clientId] = result.goals;
                mtdDataMap[result.clientId] = result.mtd;
            });
            
            setClientsData(clientsDataMap);
            setMtdData(mtdDataMap);
            
        } catch (err) {
            console.error('Error fetching clients data:', err);
            setError('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    }, [API_CONFIG]);

    // Load data on mount and when month/year changes
    useEffect(() => {
        fetchAllClientsData();
    }, [selectedMonth, selectedYear]);

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

    // Calculate totals
    const calculateTotals = () => {
        let totalGoal = 0;
        let totalActual = 0;
        let totalProjected = 0;
        
        clients.forEach(client => {
            const goals = clientsData[client.id] || [];
            const currentMonthGoal = goals.find(g => 
                g.month === selectedMonth && g.year === selectedYear
            );
            const mtd = mtdData[client.id];
            
            if (currentMonthGoal) {
                totalGoal += currentMonthGoal.revenue_goal || 0;
            }
            
            if (mtd?.revenue) {
                totalActual += mtd.revenue.mtd || 0;
                totalProjected += mtd.revenue.projected_eom || 0;
            }
        });
        
        return { totalGoal, totalActual, totalProjected };
    };

    // Get status color
    const getStatusColor = (actual, goal) => {
        if (!goal || goal === 0) return 'text-gray-500';
        const percentage = (actual / goal) * 100;
        if (percentage >= 100) return 'text-green-600';
        if (percentage >= 80) return 'text-blue-600';
        if (percentage >= 60) return 'text-yellow-600';
        return 'text-red-600';
    };

    // Get status badge
    const getStatusBadge = (actual, goal) => {
        if (!goal || goal === 0) return { text: 'No Goal', color: 'bg-gray-100 text-gray-600' };
        const percentage = (actual / goal) * 100;
        if (percentage >= 100) return { text: 'Achieved', color: 'bg-green-100 text-green-800' };
        if (percentage >= 80) return { text: 'On Track', color: 'bg-blue-100 text-blue-800' };
        if (percentage >= 60) return { text: 'At Risk', color: 'bg-yellow-100 text-yellow-800' };
        return { text: 'Behind', color: 'bg-red-100 text-red-800' };
    };

    // Save goal
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
                credentials: 'include',
                body: JSON.stringify({
                    client_id: editingGoal.client_id,
                    year: editingGoal.year,
                    month: editingGoal.month,
                    revenue_goal: editingGoal.revenue_goal,
                    calculation_method: 'manual',
                    notes: editingGoal.notes || ''
                })
            });
            
            if (!response.ok) throw new Error('Failed to save goal');
            
            // Refresh data
            fetchAllClientsData();
            setEditingGoal(null);
        } catch (err) {
            console.error('Error saving goal:', err);
            alert('Failed to save goal');
        }
    };

    // Company Overview Chart with Line Graph
    const CompanyOverviewChart = () => {
        const { totalGoal, totalActual, totalProjected } = calculateTotals();
        const progressPercentage = totalGoal > 0 ? (totalActual / totalGoal) * 100 : 0;
        
        // Prepare data for line graph (last 6 months trend)
        const getTrendData = () => {
            const months = [];
            const goalData = [];
            const actualData = [];
            
            for (let i = 5; i >= 0; i--) {
                let trendMonth = selectedMonth - i;
                let trendYear = selectedYear;
                
                if (trendMonth <= 0) {
                    trendMonth += 12;
                    trendYear -= 1;
                }
                
                const monthName = new Date(trendYear, trendMonth - 1).toLocaleDateString('en-US', { month: 'short' });
                months.push(monthName);
                
                // Calculate totals for this month
                let monthGoal = 0;
                let monthActual = 0;
                
                clients.forEach(client => {
                    const goals = clientsData[client.id] || [];
                    const monthGoalData = goals.find(g => g.month === trendMonth && g.year === trendYear);
                    if (monthGoalData) {
                        monthGoal += monthGoalData.revenue_goal || 0;
                    }
                    
                    // Only show actual data for current or past months
                    const now = new Date();
                    const isCurrentOrPast = (trendYear < now.getFullYear()) || 
                                          (trendYear === now.getFullYear() && trendMonth <= now.getMonth() + 1);
                    
                    if (isCurrentOrPast) {
                        const mtd = mtdData[client.id];
                        if (mtd && trendMonth === selectedMonth && trendYear === selectedYear) {
                            monthActual += mtd.revenue?.mtd || 0;
                        }
                    }
                });
                
                goalData.push(monthGoal);
                actualData.push(monthActual);
            }
            
            return { months, goalData, actualData };
        };
        
        const trendData = getTrendData();
        
        return (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900">
                            Company-Wide Performance - {new Date(selectedYear, selectedMonth - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                        </h2>
                        <p className="text-sm text-gray-600 mt-1">
                            Tracking {clients.length} active clients
                        </p>
                    </div>
                    <div className="flex items-center space-x-2">
                        <button 
                            onClick={() => {
                                const newMonth = selectedMonth - 1;
                                if (newMonth < 1) {
                                    setSelectedMonth(12);
                                    setSelectedYear(selectedYear - 1);
                                } else {
                                    setSelectedMonth(newMonth);
                                }
                            }}
                            className="p-1 hover:bg-gray-100 rounded"
                        >
                            ←
                        </button>
                        <span className="px-3 py-1 bg-gray-100 rounded">
                            {new Date(selectedYear, selectedMonth - 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                        </span>
                        <button 
                            onClick={() => {
                                const newMonth = selectedMonth + 1;
                                if (newMonth > 12) {
                                    setSelectedMonth(1);
                                    setSelectedYear(selectedYear + 1);
                                } else {
                                    setSelectedMonth(newMonth);
                                }
                            }}
                            className="p-1 hover:bg-gray-100 rounded"
                        >
                            →
                        </button>
                    </div>
                </div>
                
                {/* Summary Cards */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-blue-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-blue-600">
                            {formatCurrency(totalGoal)}
                        </div>
                        <div className="text-sm text-gray-600">Total Goal</div>
                    </div>
                    
                    <div className="bg-green-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-green-600">
                            {formatCurrency(totalActual)}
                        </div>
                        <div className="text-sm text-gray-600">MTD Actual</div>
                        <div className="text-xs text-gray-500">{formatPercentage(progressPercentage)} of goal</div>
                    </div>
                    
                    <div className="bg-purple-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-purple-600">
                            {formatCurrency(totalProjected)}
                        </div>
                        <div className="text-sm text-gray-600">Projected EOM</div>
                    </div>
                    
                    <div className="bg-orange-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-orange-600">
                            {formatCurrency(totalProjected - totalGoal)}
                        </div>
                        <div className="text-sm text-gray-600">
                            {totalProjected >= totalGoal ? 'Surplus' : 'Gap'}
                        </div>
                    </div>
                </div>
                
                {/* Progress Bar */}
                <div className="mb-6">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Company Progress</span>
                        <span>{formatPercentage(progressPercentage)}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-4">
                        <div 
                            className={`h-4 rounded-full transition-all duration-500 ${
                                progressPercentage >= 100 ? 'bg-green-500' :
                                progressPercentage >= 80 ? 'bg-blue-500' :
                                progressPercentage >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${Math.min(100, progressPercentage)}%` }}
                        ></div>
                    </div>
                </div>
                
                {/* Line Graph - 6 Month Trend */}
                <div className="border-t pt-6">
                    <h3 className="text-sm font-medium text-gray-700 mb-4">6-Month Performance Trend</h3>
                    <div className="relative h-48">
                        {/* Y-axis labels */}
                        <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between text-xs text-gray-500">
                            <span>{formatCurrency(Math.max(...trendData.goalData, ...trendData.actualData))}</span>
                            <span>{formatCurrency(Math.max(...trendData.goalData, ...trendData.actualData) / 2)}</span>
                            <span>$0</span>
                        </div>
                        
                        {/* Chart area */}
                        <div className="ml-14 h-full relative">
                            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                                {/* Grid lines */}
                                <line x1="0" y1="0" x2="100" y2="0" stroke="#e5e7eb" strokeWidth="0.5" />
                                <line x1="0" y1="50" x2="100" y2="50" stroke="#e5e7eb" strokeWidth="0.5" />
                                <line x1="0" y1="100" x2="100" y2="100" stroke="#e5e7eb" strokeWidth="0.5" />
                                
                                {/* Goal line - continuous blue line */}
                                <polyline
                                    fill="none"
                                    stroke="#3b82f6"
                                    strokeWidth="2.5"
                                    points={trendData.goalData.map((value, index) => {
                                        const maxValue = Math.max(...trendData.goalData, ...trendData.actualData) || 1;
                                        const x = (index / (trendData.goalData.length - 1)) * 100;
                                        const y = 100 - (value / maxValue * 100);
                                        return `${x},${y}`;
                                    }).join(' ')}
                                />
                                
                                {/* Actual line - continuous green line */}
                                <polyline
                                    fill="none"
                                    stroke="#10b981"
                                    strokeWidth="2.5"
                                    points={trendData.actualData.map((value, index) => {
                                        const maxValue = Math.max(...trendData.goalData, ...trendData.actualData) || 1;
                                        const x = (index / (trendData.actualData.length - 1)) * 100;
                                        const y = 100 - (value / maxValue * 100);
                                        return `${x},${y}`;
                                    }).join(' ')}
                                />
                                
                                {/* Data points for goal values */}
                                {trendData.goalData.map((value, index) => {
                                    if (value > 0) {
                                        const maxValue = Math.max(...trendData.goalData, ...trendData.actualData) || 1;
                                        const x = (index / (trendData.goalData.length - 1)) * 100;
                                        const y = 100 - (value / maxValue * 100);
                                        return (
                                            <circle
                                                key={`goal-${index}`}
                                                cx={x}
                                                cy={y}
                                                r="3"
                                                fill="#3b82f6"
                                            />
                                        );
                                    }
                                    return null;
                                })}
                                
                                {/* Data points for actual values */}
                                {trendData.actualData.map((value, index) => {
                                    if (value > 0) {
                                        const maxValue = Math.max(...trendData.goalData, ...trendData.actualData) || 1;
                                        const x = (index / (trendData.actualData.length - 1)) * 100;
                                        const y = 100 - (value / maxValue * 100);
                                        return (
                                            <circle
                                                key={`actual-${index}`}
                                                cx={x}
                                                cy={y}
                                                r="3"
                                                fill="#10b981"
                                            />
                                        );
                                    }
                                    return null;
                                })}
                            </svg>
                            
                            {/* X-axis labels */}
                            <div className="flex justify-between mt-2 text-xs text-gray-500">
                                {trendData.months.map((month, index) => (
                                    <span key={index}>{month}</span>
                                ))}
                            </div>
                        </div>
                    </div>
                    
                    {/* Legend */}
                    <div className="flex items-center justify-center space-x-6 mt-4 text-sm">
                        <div className="flex items-center">
                            <div className="w-4 h-0 border-t-2 border-blue-500 mr-2"></div>
                            <span className="text-gray-600">Goal</span>
                        </div>
                        <div className="flex items-center">
                            <div className="w-4 h-0 border-t-2 border-green-500 mr-2"></div>
                            <span className="text-gray-600">Actual</span>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    // Client Performance Table
    const ClientPerformanceTable = () => {
        return (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900">
                        Client Performance Details
                    </h3>
                </div>
                
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Client
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Goal
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    MTD Actual
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Progress
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Projected EOM
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {clients.map(client => {
                                const goals = clientsData[client.id] || [];
                                const currentGoal = goals.find(g => 
                                    g.month === selectedMonth && g.year === selectedYear
                                );
                                const mtd = mtdData[client.id];
                                const actual = mtd?.revenue?.mtd || 0;
                                const goal = currentGoal?.revenue_goal || 0;
                                const progress = goal > 0 ? (actual / goal) * 100 : 0;
                                const projected = mtd?.revenue?.projected_eom || 0;
                                const status = getStatusBadge(actual, goal);
                                
                                return (
                                    <tr key={client.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">
                                                {client.name}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <div className={`text-sm ${goal > 0 ? 'text-gray-900' : 'text-gray-400'}`}>
                                                {goal > 0 ? formatCurrency(goal) : 'Not Set'}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <div className={`text-sm font-medium ${getStatusColor(actual, goal)}`}>
                                                {formatCurrency(actual)}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <div className="flex items-center justify-end">
                                                <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                                                    <div 
                                                        className={`h-2 rounded-full ${
                                                            progress >= 100 ? 'bg-green-500' :
                                                            progress >= 80 ? 'bg-blue-500' :
                                                            progress >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                                        }`}
                                                        style={{ width: `${Math.min(100, progress)}%` }}
                                                    ></div>
                                                </div>
                                                <span className="text-sm text-gray-600">
                                                    {formatPercentage(progress)}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center">
                                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${status.color}`}>
                                                {status.text}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <div className="text-sm text-gray-900">
                                                {formatCurrency(projected)}
                                            </div>
                                            {projected > goal && goal > 0 && (
                                                <div className="text-xs text-green-600">
                                                    +{formatCurrency(projected - goal)}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-center">
                                            <button
                                                onClick={() => setEditingGoal({
                                                    client_id: client.id,
                                                    client_name: client.name,
                                                    year: selectedYear,
                                                    month: selectedMonth,
                                                    revenue_goal: goal || 0,
                                                    id: currentGoal?.id
                                                })}
                                                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                            >
                                                {goal > 0 ? 'Edit' : 'Set'} Goal
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    // Goal Editor Modal
    const GoalEditorModal = () => {
        if (!editingGoal) return null;
        
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg shadow-xl p-6 w-96">
                    <h3 className="text-lg font-semibold mb-4">
                        {editingGoal.id ? 'Edit' : 'Set'} Goal - {editingGoal.client_name}
                    </h3>
                    <p className="text-sm text-gray-600 mb-4">
                        {new Date(editingGoal.year, editingGoal.month - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                    </p>
                    
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Revenue Goal
                            </label>
                            <div className="relative">
                                <span className="absolute left-3 top-2 text-gray-500">$</span>
                                <input
                                    type="number"
                                    value={editingGoal.revenue_goal}
                                    onChange={(e) => setEditingGoal({
                                        ...editingGoal,
                                        revenue_goal: parseFloat(e.target.value) || 0
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
                                            revenue_goal: amount
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

    // Loading state
    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="animate-spin h-8 w-8 border-b-2 border-blue-600 rounded-full mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading company dashboard...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <div className="text-red-600 text-lg mb-2">⚠️ Error</div>
                <p className="text-red-700 mb-4">{error}</p>
                <button 
                    onClick={fetchAllClientsData}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
                >
                    Try Again
                </button>
            </div>
        );
    }

    // Main render
    return (
        <div className="goals-company-dashboard">
            {/* Data Status Component */}
            {window.GoalsDataStatus && (
                <window.GoalsDataStatus onRefresh={fetchAllClientsData} />
            )}
            
            {/* Company Overview */}
            <CompanyOverviewChart />
            
            {/* Client Performance Table */}
            <ClientPerformanceTable />
            
            {/* Goal Editor Modal */}
            <GoalEditorModal />
        </div>
    );
}

// Export the component
window.GoalsCompanyDashboard = GoalsCompanyDashboard;