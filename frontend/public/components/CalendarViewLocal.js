// Local Development Calendar Component
// This component integrates the local calendar into the EmailPilot SPA

const { useState, useEffect } = React;

function CalendarViewLocal() {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        // Check if API is available
        fetch('http://127.0.0.1:8000/api/calendar/health')
            .then(response => response.json())
            .then(data => {
                console.log('Calendar API health:', data);
                setLoading(false);
            })
            .catch(err => {
                console.error('Calendar API error:', err);
                setError('Calendar API not available. Is the server running?');
                setLoading(false);
            });
    }, []);
    
    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading calendar...</p>
                </div>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className="p-8">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-red-800 mb-2">Calendar Error</h3>
                    <p className="text-red-700">{error}</p>
                    <p className="text-sm text-red-600 mt-4">
                        Make sure the server is running: <code className="bg-red-100 px-2 py-1 rounded">uvicorn app.main:app --reload</code>
                    </p>
                </div>
            </div>
        );
    }
    
    // Load calendar in iframe for isolation
    return (
        <div className="h-full">
            <iframe 
                src="/calendar-local"
                className="w-full h-screen border-0"
                title="EmailPilot Calendar"
            />
        </div>
    );
}

// Alternative: Direct embed version (not using iframe)
function CalendarViewDirect() {
    const [clients, setClients] = useState([]);
    const [selectedClient, setSelectedClient] = useState(null);
    const [events, setEvents] = useState([]);
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [showEventModal, setShowEventModal] = useState(false);
    const [currentEvent, setCurrentEvent] = useState(null);
    const [goalData, setGoalData] = useState(null);
    
    const API_BASE = 'http://127.0.0.1:8000';
    
    // Load clients on mount
    useEffect(() => {
        loadClients();
    }, []);
    
    // Load events when client changes
    useEffect(() => {
        if (selectedClient) {
            loadEvents();
            loadDashboard();
        }
    }, [selectedClient, currentMonth]);
    
    const loadClients = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/calendar/clients`);
            const data = await response.json();
            setClients(Array.isArray(data) ? data : []);
            if (data.length > 0 && !selectedClient) {
                setSelectedClient(data[0]);
            }
        } catch (error) {
            console.error('Failed to load clients:', error);
            setClients([
                { id: 'demo1', name: 'Demo Client 1' },
                { id: 'demo2', name: 'Demo Client 2' }
            ]);
        }
    };
    
    const loadEvents = async () => {
        if (!selectedClient) return;
        try {
            const response = await fetch(`${API_BASE}/api/calendar/events?client_id=${selectedClient.id}`);
            const data = await response.json();
            setEvents(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Failed to load events:', error);
            setEvents([]);
        }
    };
    
    const loadDashboard = async () => {
        if (!selectedClient) return;
        try {
            const response = await fetch(`${API_BASE}/api/calendar/dashboard/${selectedClient.id}`);
            const data = await response.json();
            setGoalData(data);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
    };
    
    const createClient = async () => {
        const name = prompt('Enter client name:');
        if (!name) return;
        
        try {
            const response = await fetch(`${API_BASE}/api/calendar/clients`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const newClient = await response.json();
            await loadClients();
            setSelectedClient(newClient);
        } catch (error) {
            console.error('Failed to create client:', error);
        }
    };
    
    const handleEventClick = (date, event = null) => {
        setCurrentEvent(event);
        setShowEventModal(true);
    };
    
    const saveEvent = async (eventData) => {
        try {
            const url = eventData.id 
                ? `${API_BASE}/api/calendar/events/${eventData.id}`
                : `${API_BASE}/api/calendar/events`;
            
            const response = await fetch(url, {
                method: eventData.id ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...eventData,
                    client_id: selectedClient.id
                })
            });
            
            if (response.ok) {
                setShowEventModal(false);
                await loadEvents();
                await loadDashboard();
            }
        } catch (error) {
            console.error('Failed to save event:', error);
        }
    };
    
    const deleteEvent = async (eventId) => {
        if (!confirm('Delete this event?')) return;
        
        try {
            const response = await fetch(`${API_BASE}/api/calendar/events/${eventId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                setShowEventModal(false);
                await loadEvents();
                await loadDashboard();
            }
        } catch (error) {
            console.error('Failed to delete event:', error);
        }
    };
    
    const renderCalendarGrid = () => {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        const days = [];
        
        // Empty cells for days before month starts
        for (let i = 0; i < firstDay; i++) {
            days.push(<div key={`empty-${i}`} className="min-h-24 p-2"></div>);
        }
        
        // Days of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayEvents = events.filter(e => e.date === dateStr);
            
            days.push(
                <div 
                    key={day}
                    className="min-h-24 p-2 border border-gray-200 rounded hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleEventClick(dateStr)}
                >
                    <div className="font-semibold text-gray-700">{day}</div>
                    {dayEvents.map(event => (
                        <div 
                            key={event.id}
                            className="text-xs p-1 mt-1 rounded truncate bg-blue-100 text-blue-800"
                            onClick={(e) => {
                                e.stopPropagation();
                                handleEventClick(dateStr, event);
                            }}
                        >
                            {event.title}
                        </div>
                    ))}
                </div>
            );
        }
        
        return days;
    };
    
    return (
        <div className="p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h1 className="text-2xl font-bold text-gray-800 mb-4">📅 Campaign Calendar</h1>
                
                <div className="flex gap-2">
                    <select 
                        value={selectedClient?.id || ''}
                        onChange={(e) => setSelectedClient(clients.find(c => c.id === e.target.value))}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                    >
                        <option value="">Select a client...</option>
                        {clients.map(client => (
                            <option key={client.id} value={client.id}>
                                {client.name || client.id}
                            </option>
                        ))}
                    </select>
                    <button 
                        onClick={createClient}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                    >
                        + New Client
                    </button>
                </div>
            </div>
            
            {/* Goals Dashboard */}
            {goalData && (
                <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Revenue Goals</h2>
                    <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                            <p className="text-sm text-gray-600">Goal</p>
                            <p className="text-2xl font-bold">${(goalData.goal || 0).toLocaleString()}</p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-600">Current</p>
                            <p className="text-2xl font-bold">${(goalData.current_revenue || 0).toLocaleString()}</p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-600">Progress</p>
                            <p className="text-2xl font-bold">{Math.round(goalData.achievement_percentage || 0)}%</p>
                        </div>
                    </div>
                </div>
            )}
            
            {/* Calendar */}
            <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold">
                        {currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                    </h2>
                    <div className="flex gap-2">
                        <button 
                            onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))}
                            className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300"
                        >
                            ←
                        </button>
                        <button 
                            onClick={() => setCurrentMonth(new Date())}
                            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Today
                        </button>
                        <button 
                            onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))}
                            className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300"
                        >
                            →
                        </button>
                    </div>
                </div>
                
                {/* Calendar Grid */}
                <div className="grid grid-cols-7 gap-1">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                        <div key={day} className="text-center font-semibold p-2 text-gray-600">
                            {day}
                        </div>
                    ))}
                    {renderCalendarGrid()}
                </div>
            </div>
            
            {/* Event Modal */}
            {showEventModal && (
                <EventModal 
                    event={currentEvent}
                    onSave={saveEvent}
                    onDelete={deleteEvent}
                    onClose={() => setShowEventModal(false)}
                />
            )}
        </div>
    );
}

// Simple Event Modal Component
function EventModal({ event, onSave, onDelete, onClose }) {
    const [title, setTitle] = useState(event?.title || '');
    const [date, setDate] = useState(event?.date || new Date().toISOString().split('T')[0]);
    const [eventType, setEventType] = useState(event?.event_type || 'general');
    
    const handleSave = () => {
        onSave({
            id: event?.id,
            title,
            date,
            event_type: eventType
        });
    };
    
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <h3 className="text-xl font-semibold mb-4">
                    {event ? 'Edit Event' : 'New Event'}
                </h3>
                
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Title</label>
                    <input 
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                        placeholder="Campaign name..."
                    />
                </div>
                
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
                    <input 
                        type="date"
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                </div>
                
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Type</label>
                    <select 
                        value={eventType}
                        onChange={(e) => setEventType(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    >
                        <option value="general">General</option>
                        <option value="cheese-club">Cheese Club (2x)</option>
                        <option value="rrb">RRB (1.5x)</option>
                        <option value="sms">SMS (1.3x)</option>
                    </select>
                </div>
                
                <div className="flex justify-between">
                    {event && (
                        <button 
                            onClick={() => onDelete(event.id)}
                            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                        >
                            Delete
                        </button>
                    )}
                    <div className="flex gap-2 ml-auto">
                        <button 
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                        >
                            Cancel
                        </button>
                        <button 
                            onClick={handleSave}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Register components globally
window.CalendarView = CalendarViewDirect;
window.CalendarViewLocal = CalendarViewLocal;
window.CalendarViewDirect = CalendarViewDirect;

console.log('[CalendarViewLocal] Components registered:', {
    CalendarView: typeof window.CalendarView,
    CalendarViewLocal: typeof window.CalendarViewLocal,
    CalendarViewDirect: typeof window.CalendarViewDirect
});