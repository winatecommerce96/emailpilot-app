// EmailPilot Calendar Tab Integration Component
// This component integrates the Firebase calendar into the existing EmailPilot.ai Calendar tab

const { useState, useEffect, useMemo } = React;

function EmailPilotCalendarTab({ 
    selectedClient, 
    user, 
    authToken,
    onClientChange,
    theme = 'light' 
}) {
    const [activeView, setActiveView] = useState('calendar'); // 'calendar', 'chat', 'stats'
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // API configuration for EmailPilot.ai
    const API_CONFIG = useMemo(() => ({
        baseURL: window.location.origin,
        headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        }
    }), [authToken]);

    // Fetch clients on component mount
    useEffect(() => {
        fetchClients();
    }, []);

    const fetchClients = async () => {
        if (!authToken) return;
        
        try {
            setLoading(true);
            const response = await fetch(`${API_CONFIG.baseURL}/api/firebase-calendar/clients`, {
                headers: API_CONFIG.headers
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const clientData = await response.json();
            setClients(clientData);
        } catch (err) {
            console.error('Error fetching clients:', err);
            setError('Failed to load clients');
        } finally {
            setLoading(false);
        }
    };

    // Handle client selection
    const handleClientSelect = (clientId) => {
        const client = clients.find(c => c.id === clientId);
        if (client && onClientChange) {
            onClientChange(client);
        }
    };

    // Render client selector
    const ClientSelector = () => (
        <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Client
            </label>
            <select 
                value={selectedClient?.id || ''} 
                onChange={(e) => handleClientSelect(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
                <option value="">Choose a client...</option>
                {clients.map(client => (
                    <option key={client.id} value={client.id}>
                        {client.name}
                    </option>
                ))}
            </select>
        </div>
    );

    // Render view tabs
    const ViewTabs = () => (
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-6">
            {[
                { id: 'calendar', label: '📅 Calendar', icon: '📅' },
                { id: 'chat', label: '💬 AI Assistant', icon: '🤖' },
                { id: 'stats', label: '📊 Statistics', icon: '📈' }
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
    if (loading && clients.length === 0) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="animate-spin h-8 w-8 border-b-2 border-blue-600 rounded-full mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading calendar...</p>
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
                    onClick={() => { setError(null); fetchClients(); }}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
                >
                    Try Again
                </button>
            </div>
        );
    }

    return (
        <div className="emailpilot-calendar-tab max-w-7xl mx-auto p-6">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            📅 Campaign Calendar
                        </h1>
                        <p className="text-gray-600 mt-1">
                            Plan and manage your email campaigns with AI assistance
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-gray-500">Welcome, {user?.name}</p>
                        <p className="text-xs text-gray-400">
                            Firebase-powered • Real-time sync
                        </p>
                    </div>
                </div>
                
                {/* Client Selector */}
                <ClientSelector />
                
                {/* View Tabs */}
                <ViewTabs />
            </div>

            {/* Main Content */}
            {!selectedClient ? (
                <div className="text-center py-16">
                    <div className="text-gray-400 text-6xl mb-4">📅</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                        Select a Client to Get Started
                    </h3>
                    <p className="text-gray-600">
                        Choose a client from the dropdown above to view their campaign calendar
                    </p>
                </div>
            ) : (
                <div className="calendar-content">
                    {/* Calendar View */}
                    {activeView === 'calendar' && (
                        <div className="space-y-6">
                            {/* Calendar Component */}
                            <div className="bg-white rounded-lg border shadow-sm">
                                <CalendarView 
                                    clientId={selectedClient.id}
                                    clientName={selectedClient.name}
                                    apiConfig={API_CONFIG}
                                    theme={theme}
                                />
                            </div>
                        </div>
                    )}
                    
                    {/* Chat View */}
                    {activeView === 'chat' && (
                        <div className="bg-white rounded-lg border shadow-sm p-6">
                            <div className="mb-4">
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                    🤖 AI Calendar Assistant
                                </h3>
                                <p className="text-gray-600 text-sm">
                                    Ask questions about your campaigns, get suggestions, or request actions
                                </p>
                            </div>
                            <CalendarChat 
                                clientId={selectedClient.id}
                                apiConfig={API_CONFIG}
                                theme={theme}
                            />
                        </div>
                    )}
                    
                    {/* Stats View */}
                    {activeView === 'stats' && (
                        <div className="bg-white rounded-lg border shadow-sm p-6">
                            <CalendarStats 
                                clientId={selectedClient.id}
                                clientName={selectedClient.name}
                                apiConfig={API_CONFIG}
                            />
                        </div>
                    )}
                </div>
            )}

            {/* Footer */}
            <div className="mt-12 pt-6 border-t border-gray-200 text-center">
                <p className="text-xs text-gray-500">
                    🔥 Powered by Firebase • 🤖 AI by Gemini • 📊 Real-time Analytics
                </p>
            </div>
        </div>
    );
}

// Calendar Statistics Component
function CalendarStats({ clientId, clientName, apiConfig }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, [clientId]);

    const fetchStats = async () => {
        if (!clientId) return;
        
        try {
            setLoading(true);
            const response = await fetch(
                `${apiConfig.baseURL}/api/firebase-calendar/client/${clientId}/stats`,
                { headers: apiConfig.headers }
            );
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            setStats(data);
        } catch (err) {
            console.error('Error fetching stats:', err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="animate-pulse">Loading statistics...</div>;
    }

    if (!stats) {
        return <div className="text-gray-500">No statistics available</div>;
    }

    return (
        <div>
            <h3 className="text-lg font-semibold mb-4">📊 Calendar Statistics for {clientName}</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">{stats.total_events}</div>
                    <div className="text-blue-700 text-sm">Total Campaigns</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">{stats.events_this_month}</div>
                    <div className="text-green-700 text-sm">This Month</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">{stats.events_next_month}</div>
                    <div className="text-purple-700 text-sm">Next Month</div>
                </div>
            </div>

            {/* Campaign Types Breakdown */}
            {stats.event_types && Object.keys(stats.event_types).length > 0 && (
                <div className="mb-6">
                    <h4 className="font-semibold mb-3">Campaign Types</h4>
                    <div className="space-y-2">
                        {Object.entries(stats.event_types).map(([type, count]) => (
                            <div key={type} className="flex justify-between items-center bg-gray-50 px-3 py-2 rounded">
                                <span>{type}</span>
                                <span className="font-semibold">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upcoming Events */}
            {stats.upcoming_events && stats.upcoming_events.length > 0 && (
                <div>
                    <h4 className="font-semibold mb-3">Upcoming Campaigns</h4>
                    <div className="space-y-2">
                        {stats.upcoming_events.map((event, index) => (
                            <div key={index} className="border rounded-lg p-3">
                                <div className="font-medium">{event.title}</div>
                                <div className="text-sm text-gray-600">{event.event_date}</div>
                                <div className="text-xs text-gray-500">{event.event_type}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// Export the component
window.EmailPilotCalendarTab = EmailPilotCalendarTab;