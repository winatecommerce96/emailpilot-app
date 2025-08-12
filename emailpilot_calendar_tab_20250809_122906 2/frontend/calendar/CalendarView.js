// Integrated Calendar View Component for EmailPilot
const { useState, useEffect } = React;

function CalendarView() {
    const [clients, setClients] = useState([]);
    const [selectedClient, setSelectedClient] = useState(null);
    const [showEventModal, setShowEventModal] = useState(false);
    const [currentEvent, setCurrentEvent] = useState(null);
    const [initialDate, setInitialDate] = useState(null);
    const [loading, setLoading] = useState(true);

    // Load clients on component mount
    useEffect(() => {
        loadClients();
    }, []);

    const loadClients = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_BASE_URL}/api/clients/`, { 
                withCredentials: true 
            });
            setClients(response.data);
            
            // Auto-select first client if available
            if (response.data.length > 0 && !selectedClient) {
                setSelectedClient(response.data[0]);
            }
        } catch (error) {
            console.error('Failed to load clients:', error);
        } finally {
            setLoading(false);
        }
    };

    // Handle client selection
    const handleClientChange = (clientId) => {
        const client = clients.find(c => c.id === parseInt(clientId));
        setSelectedClient(client);
    };

    // Handle event click
    const handleEventClick = (event) => {
        setCurrentEvent(event);
        setInitialDate(null);
        setShowEventModal(true);
    };

    // Handle create event
    const handleCreateEvent = (date) => {
        setCurrentEvent(null);
        setInitialDate(date);
        setShowEventModal(true);
    };

    // Handle save event
    const handleSaveEvent = async (eventData) => {
        try {
            if (eventData.id) {
                // Update existing event
                await axios.put(
                    `${API_BASE_URL}/api/firebase-calendar/events/${eventData.id}`,
                    eventData,
                    { withCredentials: true }
                );
            } else {
                // Create new event
                await axios.post(
                    `${API_BASE_URL}/api/firebase-calendar/events`,
                    { ...eventData, client_id: selectedClient.id },
                    { withCredentials: true }
                );
            }
            return true;
        } catch (error) {
            console.error('Error saving event:', error);
            return false;
        }
    };

    // Handle delete event
    const handleDeleteEvent = async (eventId) => {
        try {
            await axios.delete(`${API_BASE_URL}/api/firebase-calendar/events/${eventId}`, {
                withCredentials: true
            });
            return true;
        } catch (error) {
            console.error('Error deleting event:', error);
            return false;
        }
    };

    // Handle duplicate event
    const handleDuplicateEvent = async (eventId) => {
        try {
            await axios.post(
                `${API_BASE_URL}/api/firebase-calendar/events/${eventId}/duplicate`,
                {},
                { withCredentials: true }
            );
            return true;
        } catch (error) {
            console.error('Error duplicating event:', error);
            return false;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    <p className="mt-2 text-sm text-gray-500">Loading calendar...</p>
                </div>
            </div>
        );
    }

    if (clients.length === 0) {
        return (
            <div className="text-center py-12">
                <div className="text-gray-500 mb-4">No clients available</div>
                <p className="text-sm text-gray-400">
                    Please add a client in the Clients section to use the calendar.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header with Client Selection */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Campaign Calendar</h2>
                
                <div className="flex items-center space-x-4">
                    <label className="text-sm font-medium text-gray-700">
                        Select Client:
                    </label>
                    <select
                        value={selectedClient?.id || ''}
                        onChange={(e) => handleClientChange(e.target.value)}
                        className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        {clients.map(client => (
                            <option key={client.id} value={client.id}>
                                {client.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {selectedClient && (
                <>
                    {/* Calendar Component */}
                    <Calendar
                        key={selectedClient.id} // Force re-render when client changes
                        clientId={selectedClient.id}
                        onEventClick={handleEventClick}
                        onEventCreate={handleCreateEvent}
                    />

                    {/* AI Chat Component */}
                    <CalendarChat
                        clientId={selectedClient.id}
                        onEventAction={() => {
                            // Force calendar refresh by updating key
                            setSelectedClient({ ...selectedClient });
                        }}
                    />

                    {/* Event Modal */}
                    {showEventModal && (
                        <EventModal
                            isOpen={showEventModal}
                            onClose={() => {
                                setShowEventModal(false);
                                setCurrentEvent(null);
                                setInitialDate(null);
                            }}
                            event={currentEvent}
                            onSave={handleSaveEvent}
                            onDelete={handleDeleteEvent}
                            onDuplicate={handleDuplicateEvent}
                            initialDate={initialDate}
                        />
                    )}

                    {/* Calendar Stats */}
                    <CalendarStats clientId={selectedClient.id} />
                </>
            )}
        </div>
    );
}

// Calendar Stats Component
function CalendarStats({ clientId }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadStats();
    }, [clientId]);

    const loadStats = async () => {
        try {
            setLoading(true);
            const response = await axios.get(
                `${API_BASE_URL}/api/firebase-calendar/client/${clientId}/stats`,
                { withCredentials: true }
            );
            setStats(response.data);
        } catch (error) {
            console.error('Error loading calendar stats:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="bg-white rounded-xl shadow-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Loading statistics...</h3>
            </div>
        );
    }

    if (!stats) return null;

    return (
        <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Calendar Statistics</h3>
            
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <StatCard
                    title="Total Events"
                    value={stats.total_events}
                    icon="📅"
                    color="blue"
                />
                <StatCard
                    title="This Month"
                    value={stats.events_this_month}
                    icon="📊"
                    color="green"
                />
                <StatCard
                    title="Next Month"
                    value={stats.events_next_month}
                    icon="📈"
                    color="purple"
                />
                <StatCard
                    title="Upcoming"
                    value={stats.upcoming_events.length}
                    icon="⏰"
                    color="orange"
                />
            </div>

            {/* Event Types Breakdown */}
            {Object.keys(stats.event_types).length > 0 && (
                <div className="mb-6">
                    <h4 className="font-medium text-gray-900 mb-3">Campaign Types</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {Object.entries(stats.event_types).map(([type, count]) => (
                            <div key={type} className="bg-gray-50 rounded-lg p-3">
                                <div className="text-sm font-medium text-gray-900">{type}</div>
                                <div className="text-lg font-bold text-indigo-600">{count}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upcoming Events */}
            {stats.upcoming_events.length > 0 && (
                <div>
                    <h4 className="font-medium text-gray-900 mb-3">Upcoming Events</h4>
                    <div className="space-y-2">
                        {stats.upcoming_events.map(event => (
                            <div key={event.id} className="flex justify-between items-center bg-gray-50 rounded-lg p-3">
                                <div>
                                    <div className="font-medium text-gray-900">{event.title}</div>
                                    <div className="text-sm text-gray-500">
                                        {new Date(event.event_date).toLocaleDateString()} 
                                        {event.event_type && ` • ${event.event_type}`}
                                    </div>
                                </div>
                                <div className="text-xs text-gray-400">
                                    {Math.ceil((new Date(event.event_date) - new Date()) / (1000 * 60 * 60 * 24))} days
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Export Button */}
            <div className="mt-6 pt-4 border-t border-gray-200">
                <ExportButton clientId={clientId} />
            </div>
        </div>
    );
}

// Stat Card Component
function StatCard({ title, value, icon, color }) {
    const colorClasses = {
        blue: 'text-blue-600',
        green: 'text-green-600',
        purple: 'text-purple-600',
        orange: 'text-orange-600'
    };

    return (
        <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center">
                <div className="text-2xl mr-3">{icon}</div>
                <div>
                    <p className="text-sm font-medium text-gray-600">{title}</p>
                    <p className={`text-xl font-bold ${colorClasses[color]}`}>{value}</p>
                </div>
            </div>
        </div>
    );
}

// Export Button Component
function ExportButton({ clientId }) {
    const [exporting, setExporting] = useState(false);

    const handleExport = async (format = 'json') => {
        try {
            setExporting(true);
            const response = await axios.get(
                `${API_BASE_URL}/api/firebase-calendar/export/${clientId}`,
                { 
                    params: { format },
                    withCredentials: true 
                }
            );

            // Create downloadable file
            const blob = new Blob([JSON.stringify(response.data, null, 2)], {
                type: 'application/json'
            });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `calendar-export-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Error exporting calendar:', error);
            alert('Export failed: ' + (error.response?.data?.detail || 'Unknown error'));
        } finally {
            setExporting(false);
        }
    };

    return (
        <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="px-4 py-2 bg-gray-600 text-white text-sm font-medium rounded-md hover:bg-gray-700 disabled:opacity-50"
        >
            {exporting ? 'Exporting...' : 'Export Calendar Data'}
        </button>
    );
}