// Goal Generator Panel Component
const { useState, useEffect } = React;

const GoalGeneratorPanel = () => {
    const [showGenerator, setShowGenerator] = useState(false);
    const [targetYear, setTargetYear] = useState(new Date().getFullYear() + 1);
    const [selectedMonths, setSelectedMonths] = useState([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]); // All months by default
    const [selectAllMonths, setSelectAllMonths] = useState(true);
    const [selectedClients, setSelectedClients] = useState([]);
    const [allClients, setAllClients] = useState([]);
    const [selectAll, setSelectAll] = useState(true);
    const [currentSession, setCurrentSession] = useState(null);
    const [progress, setProgress] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showHistory, setShowHistory] = useState(false);
    const [sessionResults, setSessionResults] = useState(null);

    // API configuration
    const API_CONFIG = {
        baseURL: window.location.hostname === 'localhost' 
            ? 'http://localhost:8080' 
            : 'https://emailpilot-app-p3cxgvcsla-uc.a.run.app',
        headers: {
            'Content-Type': 'application/json'
        }
    };

    // Load clients on mount
    useEffect(() => {
        fetchClients();
        fetchHistory();
    }, []);

    // Poll for progress when session is active
    useEffect(() => {
        if (currentSession && progress?.status === 'running') {
            const interval = setInterval(() => {
                fetchProgress(currentSession);
            }, 2000); // Poll every 2 seconds

            return () => clearInterval(interval);
        }
    }, [currentSession, progress?.status]);

    const fetchClients = async () => {
        try {
            // Use the goals/clients endpoint which doesn't require auth
            const response = await fetch(`${API_CONFIG.baseURL}/api/goals/clients`, {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                // Data already filtered for active clients in the backend
                setAllClients(data);
                setSelectedClients(data.map(c => c.id));
            } else {
                console.error('Failed to fetch clients:', response.status);
            }
        } catch (err) {
            console.error('Error fetching clients:', err);
        }
    };

    const fetchHistory = async () => {
        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/goals/generate/history`, {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                setHistory(data.sessions || []);
            }
        } catch (err) {
            console.error('Error fetching history:', err);
        }
    };

    const fetchProgress = async (sessionId) => {
        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/goals/generate/progress/${sessionId}`, {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                setProgress(data);
                
                // If completed, fetch results
                if (data.status === 'completed') {
                    fetchResults(sessionId);
                }
            }
        } catch (err) {
            console.error('Error fetching progress:', err);
        }
    };

    const fetchResults = async (sessionId) => {
        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/goals/generate/results/${sessionId}`, {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                setSessionResults(data);
            }
        } catch (err) {
            console.error('Error fetching results:', err);
        }
    };

    const startGeneration = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const clientIds = selectAll ? null : selectedClients;
            
            const response = await fetch(`${API_CONFIG.baseURL}/api/goals/generate/batch`, {
                method: 'POST',
                headers: API_CONFIG.headers,
                credentials: 'include',
                body: JSON.stringify({
                    target_year: targetYear,
                    client_ids: clientIds,
                    selected_months: selectAllMonths ? null : selectedMonths
                })
            });

            if (response.ok) {
                const data = await response.json();
                setCurrentSession(data.session_id);
                setProgress({
                    status: 'running',
                    completed_count: 0,
                    total_count: selectAll ? allClients.length : selectedClients.length
                });
                
                // Start polling for progress
                fetchProgress(data.session_id);
            } else {
                throw new Error('Failed to start generation');
            }
        } catch (err) {
            console.error('Error starting generation:', err);
            setError('Failed to start goal generation');
        } finally {
            setLoading(false);
        }
    };

    const pauseGeneration = async () => {
        if (!currentSession) return;
        
        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/goals/generate/pause/${currentSession}`, {
                method: 'POST',
                credentials: 'include'
            });
            
            if (response.ok) {
                setProgress(prev => ({ ...prev, status: 'paused' }));
            }
        } catch (err) {
            console.error('Error pausing generation:', err);
        }
    };

    const resumeGeneration = async () => {
        if (!currentSession) return;
        
        try {
            const response = await fetch(`${API_CONFIG.baseURL}/api/goals/generate/resume/${currentSession}`, {
                method: 'POST',
                credentials: 'include'
            });
            
            if (response.ok) {
                setProgress(prev => ({ ...prev, status: 'running' }));
                fetchProgress(currentSession);
            }
        } catch (err) {
            console.error('Error resuming generation:', err);
        }
    };

    const toggleClientSelection = (clientId) => {
        setSelectedClients(prev => {
            if (prev.includes(clientId)) {
                return prev.filter(id => id !== clientId);
            } else {
                return [...prev, clientId];
            }
        });
        setSelectAll(false);
    };

    const toggleMonthSelection = (month) => {
        setSelectedMonths(prev => {
            if (prev.includes(month)) {
                return prev.filter(m => m !== month);
            } else {
                return [...prev, month].sort((a, b) => a - b);
            }
        });
        setSelectAllMonths(false);
    };

    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    };

    const formatDate = (date) => {
        if (!date) return 'N/A';
        return new Date(date).toLocaleString();
    };

    return (
        <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">AI Goal Generator</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        Generate AI-powered revenue goals with resume capability
                    </p>
                </div>
                <button
                    onClick={() => setShowGenerator(!showGenerator)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                    {showGenerator ? 'Hide Generator' : 'Open Generator'}
                </button>
            </div>

            {showGenerator && (
                <div className="space-y-6">
                    {/* Generation Controls */}
                    {!currentSession && (
                        <div className="border rounded-lg p-4 bg-gray-50">
                            <h3 className="font-semibold text-gray-900 mb-4">New Goal Generation</h3>
                            
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Target Year
                                    </label>
                                    <select
                                        value={targetYear}
                                        onChange={(e) => setTargetYear(parseInt(e.target.value))}
                                        className="w-full p-2 border rounded-lg"
                                    >
                                        {[0, 1, 2].map(offset => {
                                            const year = new Date().getFullYear() + offset;
                                            return (
                                                <option key={year} value={year}>{year}</option>
                                            );
                                        })}
                                    </select>
                                </div>
                                
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Client Selection
                                    </label>
                                    <div className="flex items-center space-x-4">
                                        <label className="flex items-center">
                                            <input
                                                type="radio"
                                                checked={selectAll}
                                                onChange={() => {
                                                    setSelectAll(true);
                                                    setSelectedClients(allClients.map(c => c.id));
                                                }}
                                                className="mr-2"
                                            />
                                            All Clients ({allClients.length})
                                        </label>
                                        <label className="flex items-center">
                                            <input
                                                type="radio"
                                                checked={!selectAll}
                                                onChange={() => setSelectAll(false)}
                                                className="mr-2"
                                            />
                                            Select Clients
                                        </label>
                                    </div>
                                </div>
                            </div>

                            {/* Month Selection */}
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Month Selection
                                </label>
                                <div className="flex items-center space-x-4 mb-2">
                                    <label className="flex items-center">
                                        <input
                                            type="radio"
                                            checked={selectAllMonths}
                                            onChange={() => {
                                                setSelectAllMonths(true);
                                                setSelectedMonths([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
                                            }}
                                            className="mr-2"
                                        />
                                        All Months (12)
                                    </label>
                                    <label className="flex items-center">
                                        <input
                                            type="radio"
                                            checked={!selectAllMonths}
                                            onChange={() => setSelectAllMonths(false)}
                                            className="mr-2"
                                        />
                                        Select Months
                                    </label>
                                </div>
                                
                                {!selectAllMonths && (
                                    <div className="grid grid-cols-4 gap-2">
                                        {monthNames.map((monthName, index) => {
                                            const monthNumber = index + 1;
                                            return (
                                                <label key={monthNumber} className="flex items-center p-1 text-xs">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedMonths.includes(monthNumber)}
                                                        onChange={() => toggleMonthSelection(monthNumber)}
                                                        className="mr-1 scale-75"
                                                    />
                                                    <span>{monthName.substring(0, 3)}</span>
                                                </label>
                                            );
                                        })}
                                    </div>
                                )}
                                
                                {!selectAllMonths && (
                                    <div className="text-xs text-gray-600 mt-1">
                                        Selected: {selectedMonths.length} months
                                        {selectedMonths.length > 0 && (
                                            <span className="ml-2">
                                                ({selectedMonths.map(m => monthNames[m-1].substring(0, 3)).join(', ')})
                                            </span>
                                        )}
                                    </div>
                                )}
                            </div>

                            {!selectAll && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Select Clients ({selectedClients.length} selected)
                                    </label>
                                    <div className="max-h-40 overflow-y-auto border rounded-lg p-2 bg-white">
                                        {allClients.map(client => (
                                            <label key={client.id} className="flex items-center p-1 hover:bg-gray-50">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedClients.includes(client.id)}
                                                    onChange={() => toggleClientSelection(client.id)}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm">{client.name}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <button
                                onClick={startGeneration}
                                disabled={
                                    loading || 
                                    (!selectAll && selectedClients.length === 0) ||
                                    (!selectAllMonths && selectedMonths.length === 0)
                                }
                                className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors"
                            >
                                {loading ? 'Starting...' : 
                                 selectAllMonths ? `Generate Goals for All Months of ${targetYear}` :
                                 `Generate Goals for ${selectedMonths.length} Month${selectedMonths.length !== 1 ? 's' : ''} of ${targetYear}`}
                            </button>
                        </div>
                    )}

                    {/* Progress Display */}
                    {progress && (
                        <div className="border rounded-lg p-4">
                            <h3 className="font-semibold text-gray-900 mb-4">Generation Progress</h3>
                            
                            <div className="mb-4">
                                <div className="flex justify-between text-sm text-gray-600 mb-1">
                                    <span>Progress: {progress.completed_count || 0} / {progress.total_count || 0}</span>
                                    <span>{Math.round(((progress.completed_count || 0) / (progress.total_count || 1)) * 100)}%</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-3">
                                    <div
                                        className="bg-blue-600 h-3 rounded-full transition-all duration-500"
                                        style={{ width: `${((progress.completed_count || 0) / (progress.total_count || 1)) * 100}%` }}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-3 gap-4 mb-4">
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-green-600">
                                        {progress.completed_count || 0}
                                    </div>
                                    <div className="text-sm text-gray-600">Completed</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-red-600">
                                        {progress.failed_count || 0}
                                    </div>
                                    <div className="text-sm text-gray-600">Failed</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-yellow-600">
                                        {(progress.total_count || 0) - (progress.completed_count || 0) - (progress.failed_count || 0)}
                                    </div>
                                    <div className="text-sm text-gray-600">Remaining</div>
                                </div>
                            </div>

                            {progress.current_client && (
                                <div className="text-sm text-gray-600 mb-4">
                                    Currently processing: <span className="font-medium">{progress.current_client}</span>
                                </div>
                            )}

                            <div className="flex space-x-2">
                                {progress.status === 'running' && (
                                    <button
                                        onClick={pauseGeneration}
                                        className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
                                    >
                                        Pause
                                    </button>
                                )}
                                {progress.status === 'paused' && (
                                    <button
                                        onClick={resumeGeneration}
                                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                                    >
                                        Resume
                                    </button>
                                )}
                                {progress.status === 'completed' && (
                                    <button
                                        onClick={() => {
                                            setCurrentSession(null);
                                            setProgress(null);
                                            setSessionResults(null);
                                            fetchHistory();
                                        }}
                                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                                    >
                                        Start New Generation
                                    </button>
                                )}
                            </div>

                            {/* Status Badge */}
                            <div className="mt-4">
                                <span className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                                    progress.status === 'running' ? 'bg-green-100 text-green-800' :
                                    progress.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                                    progress.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                                    'bg-gray-100 text-gray-800'
                                }`}>
                                    Status: {progress.status}
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Results Summary */}
                    {sessionResults && (
                        <div className="border rounded-lg p-4 bg-green-50">
                            <h3 className="font-semibold text-gray-900 mb-4">Generation Results</h3>
                            
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <div className="text-sm text-gray-600">Total Revenue Target</div>
                                    <div className="text-2xl font-bold text-green-600">
                                        {formatCurrency(sessionResults.summary?.total_yearly_revenue || 0)}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-sm text-gray-600">Success Rate</div>
                                    <div className="text-2xl font-bold">
                                        {Math.round((sessionResults.summary?.successful || 0) / (sessionResults.summary?.total_clients || 1) * 100)}%
                                    </div>
                                </div>
                            </div>

                            {sessionResults.results && sessionResults.results.length > 0 && (
                                <div className="mt-4">
                                    <h4 className="text-sm font-medium text-gray-700 mb-2">Client Results:</h4>
                                    <div className="max-h-60 overflow-y-auto">
                                        {sessionResults.results.map((result, idx) => (
                                            <div key={idx} className="flex items-center justify-between p-2 hover:bg-white rounded">
                                                <span className="text-sm">{result.client}</span>
                                                <div className="flex items-center space-x-2">
                                                    <span className="text-sm font-medium">
                                                        {formatCurrency(result.total_yearly_goal || 0)}
                                                    </span>
                                                    {result.status === 'success' ? (
                                                        <span className="text-green-600">✓</span>
                                                    ) : (
                                                        <span className="text-red-600">✗</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Generation History */}
                    <div className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-semibold text-gray-900">Generation History</h3>
                            <button
                                onClick={() => setShowHistory(!showHistory)}
                                className="text-sm text-blue-600 hover:text-blue-700"
                            >
                                {showHistory ? 'Hide' : 'Show'} History
                            </button>
                        </div>
                        
                        {showHistory && history.length > 0 && (
                            <div className="space-y-2">
                                {history.map(session => (
                                    <div key={session.session_id} className="p-3 bg-gray-50 rounded-lg">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <div className="text-sm font-medium">
                                                    Year {session.target_year}
                                                </div>
                                                <div className="text-xs text-gray-600">
                                                    {formatDate(session.started_at)}
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm">
                                                    {session.completed_count}/{session.total_count} clients
                                                </div>
                                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                                                    session.status === 'completed' ? 'bg-green-100 text-green-800' :
                                                    session.status === 'running' ? 'bg-blue-100 text-blue-800' :
                                                    session.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                                                    'bg-gray-100 text-gray-800'
                                                }`}>
                                                    {session.status}
                                                </span>
                                            </div>
                                        </div>
                                        {session.status === 'paused' && (
                                            <button
                                                onClick={() => {
                                                    setCurrentSession(session.session_id);
                                                    setProgress(session);
                                                    resumeGeneration();
                                                }}
                                                className="mt-2 text-sm text-blue-600 hover:text-blue-700"
                                            >
                                                Resume this session →
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                        
                        {showHistory && history.length === 0 && (
                            <p className="text-sm text-gray-500">No generation history available</p>
                        )}
                    </div>

                    {/* Error Display */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                            <div className="text-red-800">{error}</div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

// Export the component
window.GoalGeneratorPanel = GoalGeneratorPanel;
