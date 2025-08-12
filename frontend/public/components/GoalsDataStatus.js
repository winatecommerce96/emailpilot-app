// Goals Data Status Component - Provides feedback on data completeness and next steps
const { useState, useEffect, useMemo } = React;

function GoalsDataStatus({ onRefresh }) {
    const [dataStatus, setDataStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showDetails, setShowDetails] = useState(false);

    useEffect(() => {
        checkDataStatus();
    }, []);

    const checkDataStatus = async () => {
        try {
            setLoading(true);
            
            const response = await fetch('/api/goals/data-status', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const status = await response.json();
                setDataStatus(status);
            } else {
                throw new Error('Failed to check data status');
            }
        } catch (error) {
            console.error('Error checking data status:', error);
            setDataStatus({
                status: 'error',
                message: 'Unable to check data status',
                hasPerformanceData: false,
                hasGoals: false
            });
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div className="flex items-center">
                    <div className="animate-spin h-5 w-5 border-b-2 border-blue-600 rounded-full mr-3"></div>
                    <p className="text-blue-700">Checking data status...</p>
                </div>
            </div>
        );
    }

    if (!dataStatus) return null;

    const getStatusConfig = () => {
        if (dataStatus.status === 'complete') {
            return {
                bgColor: 'bg-green-50',
                borderColor: 'border-green-200',
                textColor: 'text-green-800',
                iconColor: 'text-green-600',
                icon: '✅'
            };
        } else if (dataStatus.status === 'partial') {
            return {
                bgColor: 'bg-yellow-50',
                borderColor: 'border-yellow-200',
                textColor: 'text-yellow-800',
                iconColor: 'text-yellow-600',
                icon: '⚠️'
            };
        } else {
            return {
                bgColor: 'bg-red-50',
                borderColor: 'border-red-200',
                textColor: 'text-red-800',
                iconColor: 'text-red-600',
                icon: '❌'
            };
        }
    };

    const statusConfig = getStatusConfig();

    return (
        <div className={`${statusConfig.bgColor} ${statusConfig.borderColor} border rounded-lg p-6 mb-6`}>
            <div className="flex items-start justify-between">
                <div className="flex items-start">
                    <div className={`text-2xl ${statusConfig.iconColor} mr-3`}>
                        {statusConfig.icon}
                    </div>
                    <div className="flex-1">
                        <h3 className={`text-lg font-semibold ${statusConfig.textColor} mb-2`}>
                            Goals Data Status: {dataStatus.status.charAt(0).toUpperCase() + dataStatus.status.slice(1)}
                        </h3>
                        <p className={`${statusConfig.textColor} mb-4`}>
                            {dataStatus.message}
                        </p>

                        {/* Data Summary */}
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div className="flex items-center">
                                <div className={`w-3 h-3 rounded-full mr-2 ${dataStatus.hasGoals ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                <span className={`text-sm ${statusConfig.textColor}`}>
                                    Goals Data: {dataStatus.hasGoals ? 'Available' : 'Missing'}
                                </span>
                            </div>
                            <div className="flex items-center">
                                <div className={`w-3 h-3 rounded-full mr-2 ${dataStatus.hasPerformanceData ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                <span className={`text-sm ${statusConfig.textColor}`}>
                                    Performance Data: {dataStatus.hasPerformanceData ? 'Available' : 'Missing'}
                                </span>
                            </div>
                        </div>

                        {/* Detailed Information */}
                        {showDetails && (
                            <div className="mt-4 space-y-3">
                                <div className="text-sm space-y-2">
                                    <div>
                                        <strong className={statusConfig.textColor}>Clients with Goals:</strong>
                                        <span className={`ml-2 ${statusConfig.textColor}`}>
                                            {dataStatus.goalsCount} clients
                                        </span>
                                    </div>
                                    <div>
                                        <strong className={statusConfig.textColor}>Performance Records:</strong>
                                        <span className={`ml-2 ${statusConfig.textColor}`}>
                                            {dataStatus.performanceRecords} records
                                        </span>
                                    </div>
                                    <div>
                                        <strong className={statusConfig.textColor}>Latest Performance Data:</strong>
                                        <span className={`ml-2 ${statusConfig.textColor}`}>
                                            {dataStatus.latestPerformanceDate || 'None'}
                                        </span>
                                    </div>
                                </div>
                                
                                {dataStatus.missingData && dataStatus.missingData.length > 0 && (
                                    <div>
                                        <strong className={`${statusConfig.textColor} block mb-2`}>Missing Data:</strong>
                                        <ul className={`list-disc list-inside text-sm ${statusConfig.textColor} space-y-1`}>
                                            {dataStatus.missingData.map((item, index) => (
                                                <li key={index}>{item}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Action Items */}
                        {dataStatus.status !== 'complete' && (
                            <div className="mt-4">
                                <h4 className={`font-medium ${statusConfig.textColor} mb-2`}>
                                    Next Steps to Complete Goals Setup:
                                </h4>
                                <ul className={`list-disc list-inside text-sm ${statusConfig.textColor} space-y-1`}>
                                    {!dataStatus.hasPerformanceData && (
                                        <>
                                            <li>Run historical performance data collection from Klaviyo API</li>
                                            <li>Execute: <code className="bg-white bg-opacity-50 px-1 rounded">python3 collect_performance_history.py</code></li>
                                        </>
                                    )}
                                    {!dataStatus.hasGoals && (
                                        <>
                                            <li>Generate AI-suggested goals based on performance data</li>
                                            <li>Execute: <code className="bg-white bg-opacity-50 px-1 rounded">python3 resumable_goal_generator.py</code></li>
                                        </>
                                    )}
                                    {dataStatus.hasGoals && dataStatus.hasPerformanceData && (
                                        <li>Sync local JSON goal data with Firestore database</li>
                                    )}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
                <div className="flex items-center space-x-2">
                    <button
                        onClick={() => setShowDetails(!showDetails)}
                        className={`px-3 py-1 text-sm font-medium rounded-md ${statusConfig.textColor} hover:bg-white hover:bg-opacity-50`}
                    >
                        {showDetails ? 'Hide' : 'Show'} Details
                    </button>
                    <button
                        onClick={() => {
                            checkDataStatus();
                            if (onRefresh) onRefresh();
                        }}
                        className={`px-3 py-1 text-sm font-medium rounded-md ${statusConfig.textColor} hover:bg-white hover:bg-opacity-50`}
                    >
                        Refresh
                    </button>
                </div>
            </div>

            {/* Quick Actions */}
            {dataStatus.status !== 'complete' && (
                <div className="mt-4 pt-4 border-t border-opacity-30 border-current">
                    <div className="flex items-center justify-between">
                        <span className={`text-sm font-medium ${statusConfig.textColor}`}>
                            Quick Actions:
                        </span>
                        <div className="flex space-x-2">
                            {!dataStatus.hasPerformanceData && (
                                <button className={`px-3 py-1 text-xs font-medium rounded-md ${statusConfig.textColor} hover:bg-white hover:bg-opacity-50 border border-current border-opacity-30`}>
                                    Collect Performance Data
                                </button>
                            )}
                            {dataStatus.hasPerformanceData && !dataStatus.hasGoals && (
                                <button className={`px-3 py-1 text-xs font-medium rounded-md ${statusConfig.textColor} hover:bg-white hover:bg-opacity-50 border border-current border-opacity-30`}>
                                    Generate Goals
                                </button>
                            )}
                            <button 
                                onClick={() => window.open('/admin', '_blank')}
                                className={`px-3 py-1 text-xs font-medium rounded-md ${statusConfig.textColor} hover:bg-white hover:bg-opacity-50 border border-current border-opacity-30`}
                            >
                                Open Admin Panel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Export the component
window.GoalsDataStatus = GoalsDataStatus;