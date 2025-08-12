// Calendar Component with drag-and-drop functionality
const { useState, useEffect, useCallback, useRef } = React;

// Color classes for different campaign types
const CAMPAIGN_COLORS = {
    'RRB Promotion': 'bg-red-300 text-red-800',
    'Cheese Club': 'bg-green-200 text-green-800',
    'Nurturing/Education': 'bg-blue-200 text-blue-800',
    'Community/Lifestyle': 'bg-purple-200 text-purple-800',
    'Re-engagement': 'bg-yellow-200 text-yellow-800',
    'SMS Alert': 'bg-orange-300 text-orange-800',
    'default': 'bg-gray-200 text-gray-800'
};

function Calendar({ clientId, onEventClick, onEventCreate }) {
    const [currentDate, setCurrentDate] = useState(new Date(2025, 8, 1)); // September 2025
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);
    const [draggedEvent, setDraggedEvent] = useState(null);
    const [undoStack, setUndoStack] = useState([]);

    // Fetch events for the current client
    const fetchEvents = useCallback(async () => {
        if (!clientId) return;
        
        setLoading(true);
        try {
            const response = await axios.get(`${API_BASE_URL}/api/firebase-calendar/events`, {
                params: { client_id: clientId },
                withCredentials: true
            });
            setEvents(response.data);
        } catch (error) {
            console.error('Error fetching calendar events:', error);
        } finally {
            setLoading(false);
        }
    }, [clientId]);

    // Load events when client changes
    useEffect(() => {
        fetchEvents();
    }, [fetchEvents]);

    // Save event changes
    const saveEvent = async (eventData) => {
        try {
            if (eventData.id) {
                // Update existing event
                const response = await axios.put(
                    `${API_BASE_URL}/api/firebase-calendar/events/${eventData.id}`,
                    eventData,
                    { withCredentials: true }
                );
                
                setEvents(prev => prev.map(event => 
                    event.id === eventData.id ? response.data : event
                ));
            } else {
                // Create new event
                const response = await axios.post(
                    `${API_BASE_URL}/api/firebase-calendar/events`,
                    { ...eventData, client_id: clientId },
                    { withCredentials: true }
                );
                
                setEvents(prev => [...prev, response.data]);
            }
            
            return true;
        } catch (error) {
            console.error('Error saving event:', error);
            return false;
        }
    };

    // Delete event
    const deleteEvent = async (eventId) => {
        try {
            await axios.delete(`${API_BASE_URL}/api/firebase-calendar/events/${eventId}`, {
                withCredentials: true
            });
            
            setEvents(prev => prev.filter(event => event.id !== eventId));
            return true;
        } catch (error) {
            console.error('Error deleting event:', error);
            return false;
        }
    };

    // Duplicate event
    const duplicateEvent = async (eventId) => {
        try {
            const response = await axios.post(
                `${API_BASE_URL}/api/firebase-calendar/events/${eventId}/duplicate`,
                {},
                { withCredentials: true }
            );
            
            setEvents(prev => [...prev, response.data]);
            return true;
        } catch (error) {
            console.error('Error duplicating event:', error);
            return false;
        }
    };

    // Handle month navigation
    const navigateMonth = (direction) => {
        setCurrentDate(prev => {
            const newDate = new Date(prev);
            newDate.setMonth(prev.getMonth() + direction);
            return newDate;
        });
    };

    // Handle drag start
    const handleDragStart = (e, event) => {
        setDraggedEvent(event);
        e.dataTransfer.effectAllowed = 'move';
        e.target.classList.add('opacity-50');
    };

    // Handle drag end
    const handleDragEnd = (e) => {
        e.target.classList.remove('opacity-50');
        setDraggedEvent(null);
    };

    // Handle drop on calendar day
    const handleDrop = async (e, targetDate) => {
        e.preventDefault();
        
        if (!draggedEvent) return;
        
        // Push to undo stack
        setUndoStack(prev => [...prev.slice(-19), events]); // Keep last 20 states
        
        // Update event date
        const updatedEvent = {
            ...draggedEvent,
            event_date: targetDate
        };
        
        const success = await saveEvent(updatedEvent);
        if (!success) {
            // Revert on failure
            fetchEvents();
        }
    };

    // Handle drag over
    const handleDragOver = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    // Generate calendar days
    const generateCalendarDays = () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - firstDay.getDay());
        
        const days = [];
        const currentDay = new Date(startDate);
        
        // Generate 42 days (6 weeks)
        for (let i = 0; i < 42; i++) {
            const dateString = currentDay.toISOString().split('T')[0];
            const isCurrentMonth = currentDay.getMonth() === month;
            const dayEvents = events.filter(event => event.event_date === dateString);
            
            days.push({
                date: new Date(currentDay),
                dateString,
                dayNumber: currentDay.getDate(),
                isCurrentMonth,
                events: dayEvents
            });
            
            currentDay.setDate(currentDay.getDate() + 1);
        }
        
        return days;
    };

    const calendarDays = generateCalendarDays();

    return (
        <div className="bg-white rounded-xl shadow-lg">
            {/* Calendar Header */}
            <CalendarHeader 
                currentDate={currentDate}
                onNavigate={navigateMonth}
                clientId={clientId}
                onRefresh={fetchEvents}
            />

            {/* Campaign Type Legend */}
            <div className="p-4 border-b border-gray-200">
                <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
                    {Object.entries(CAMPAIGN_COLORS).filter(([key]) => key !== 'default').map(([type, colorClass]) => (
                        <div key={type} className="flex items-center space-x-2">
                            <div className={`w-4 h-4 rounded-full ${colorClass.split(' ')[0]}`}></div>
                            <span className="text-xs text-gray-600 font-medium">{type}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Calendar Grid */}
            <div className="p-4">
                {loading ? (
                    <div className="text-center py-8">Loading calendar...</div>
                ) : (
                    <div>
                        {/* Day Headers */}
                        <div className="grid grid-cols-7 mb-2">
                            {['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'].map(day => (
                                <div key={day} className="text-center text-xs font-semibold text-gray-600 py-2">
                                    {day}
                                </div>
                            ))}
                        </div>

                        {/* Calendar Days */}
                        <div className="grid grid-cols-7 gap-1">
                            {calendarDays.map((day, index) => (
                                <CalendarDay
                                    key={index}
                                    day={day}
                                    onDrop={handleDrop}
                                    onDragOver={handleDragOver}
                                    onEventClick={onEventClick}
                                    onEventCreate={onEventCreate}
                                    onDragStart={handleDragStart}
                                    onDragEnd={handleDragEnd}
                                />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// Calendar Header Component
function CalendarHeader({ currentDate, onNavigate, clientId, onRefresh }) {
    const [importing, setImporting] = useState(false);

    const handleGoogleDocImport = async () => {
        if (!clientId) {
            alert('Please select a client first');
            return;
        }

        setImporting(true);
        try {
            // In a real implementation, you would use Google's OAuth flow here
            const docId = prompt('Enter Google Doc ID:');
            const accessToken = prompt('Enter access token (in production, this would be handled by OAuth):');
            
            if (docId && accessToken) {
                await axios.post(`${API_BASE_URL}/api/firebase-calendar/import/google-doc`, {
                    client_id: clientId,
                    doc_id: docId,
                    access_token: accessToken
                }, { withCredentials: true });
                
                alert('Import started! Please check back in a moment.');
                onRefresh();
            }
        } catch (error) {
            alert('Import failed: ' + (error.response?.data?.detail || 'Unknown error'));
        } finally {
            setImporting(false);
        }
    };

    return (
        <div className="p-6 border-b border-gray-200">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">
                    {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                </h1>
                
                <div className="flex items-center space-x-2">
                    <button
                        onClick={handleGoogleDocImport}
                        disabled={importing || !clientId}
                        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
                    >
                        {importing ? 'Importing...' : 'Import from Google Doc'}
                    </button>
                    
                    <button
                        onClick={() => onNavigate(-1)}
                        className="p-2 rounded-full text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path>
                        </svg>
                    </button>
                    
                    <button
                        onClick={() => onNavigate(1)}
                        className="p-2 rounded-full text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}

// Calendar Day Component
function CalendarDay({ 
    day, 
    onDrop, 
    onDragOver, 
    onEventClick, 
    onEventCreate,
    onDragStart,
    onDragEnd 
}) {
    const [showAddButton, setShowAddButton] = useState(false);

    const handleAddEvent = () => {
        onEventCreate(day.dateString);
    };

    return (
        <div
            className={`border border-gray-200 min-h-[120px] p-1 relative transition-colors ${
                day.isCurrentMonth 
                    ? 'bg-white hover:bg-gray-50' 
                    : 'bg-gray-50 text-gray-400'
            }`}
            onMouseEnter={() => setShowAddButton(true)}
            onMouseLeave={() => setShowAddButton(false)}
            onDrop={(e) => onDrop(e, day.dateString)}
            onDragOver={onDragOver}
        >
            {/* Day Number */}
            <div className="text-sm font-medium mb-1">
                {day.dayNumber}
            </div>

            {/* Add Event Button */}
            {showAddButton && day.isCurrentMonth && (
                <button
                    onClick={handleAddEvent}
                    className="absolute top-1 right-1 w-5 h-5 text-gray-400 hover:text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Add Event"
                >
                    <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd"></path>
                    </svg>
                </button>
            )}

            {/* Events */}
            <div className="space-y-1">
                {day.events.map(event => (
                    <CalendarEvent
                        key={event.id}
                        event={event}
                        onClick={() => onEventClick(event)}
                        onDragStart={onDragStart}
                        onDragEnd={onDragEnd}
                    />
                ))}
            </div>
        </div>
    );
}

// Calendar Event Component
function CalendarEvent({ event, onClick, onDragStart, onDragEnd }) {
    const colorClass = CAMPAIGN_COLORS[event.event_type] || CAMPAIGN_COLORS.default;

    return (
        <div
            draggable
            onClick={(e) => {
                e.stopPropagation();
                onClick();
            }}
            onDragStart={(e) => onDragStart(e, event)}
            onDragEnd={onDragEnd}
            className={`${colorClass} text-xs px-2 py-1 rounded cursor-pointer hover:shadow-md transition-all duration-200 truncate`}
            title={event.title}
        >
            {event.title}
        </div>
    );
}