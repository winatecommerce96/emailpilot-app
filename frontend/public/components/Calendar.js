// Enhanced Firebase-Integrated Calendar Component
const { useState, useEffect, useCallback, useRef } = React;

// Firebase service initialization - defer until needed
let firebaseService = null;
let geminiService = null;

function getFirebaseService() {
    if (!firebaseService && window.FirebaseCalendarService) {
        firebaseService = new window.FirebaseCalendarService();
    }
    return firebaseService;
}

function getGeminiService() {
    if (!geminiService && window.GeminiChatService && getFirebaseService()) {
        geminiService = new window.GeminiChatService(getFirebaseService());
    }
    return geminiService;
}

// Color classes for different campaign types
const CAMPAIGN_COLORS = window.CAMPAIGN_COLORS;

function Calendar({ clientId, onEventClick, onEventCreate }) {
    const [currentDate, setCurrentDate] = useState(new Date(2025, 8, 1)); // September 2025
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);
    const [draggedEvent, setDraggedEvent] = useState(null);
    const [undoStack, setUndoStack] = useState([]);
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, event: null });
    const [isDragging, setIsDragging] = useState(false);
    const [showEventModal, setShowEventModal] = useState(false);
    const [eventModalMode, setEventModalMode] = useState('view'); // 'view', 'edit', 'create'

    // Fetch events for the current client using Firebase
    const fetchEvents = useCallback(async () => {
        if (!clientId) return;
        
        setLoading(true);
        try {
            const clientData = await getFirebaseService().getClientData(clientId);
            if (clientData && clientData.campaignData) {
                // Convert campaign data to events array
                const eventsArray = Object.entries(clientData.campaignData).map(([id, data]) => ({
                    id,
                    ...data,
                    event_date: data.date // Normalize field name
                }));
                setEvents(eventsArray);
            } else {
                setEvents([]);
            }
        } catch (error) {
            console.error('Error fetching calendar events:', error);
            setEvents([]);
        } finally {
            setLoading(false);
        }
    }, [clientId]);

    // Load events when client changes
    useEffect(() => {
        fetchEvents();
    }, [fetchEvents]);

    // Save event changes using Firebase
    const saveEvent = async (eventData) => {
        try {
            // Get current client data
            const clientData = await getFirebaseService().getClientData(clientId);
            const campaigns = clientData?.campaignData || {};
            
            if (eventData.id) {
                // Update existing event
                campaigns[eventData.id] = {
                    ...campaigns[eventData.id],
                    title: eventData.title,
                    content: eventData.content,
                    date: eventData.event_date || eventData.date
                };
            } else {
                // Create new event
                const newId = 'event-' + Date.now();
                const campaignType = getFirebaseService().detectCampaignType(eventData.title, eventData.content);
                campaigns[newId] = {
                    date: eventData.event_date || eventData.date,
                    title: eventData.title,
                    content: eventData.content,
                    color: CAMPAIGN_COLORS[campaignType] || CAMPAIGN_COLORS.default
                };
            }
            
            // Save to Firebase
            const success = await getFirebaseService().saveClientData(clientId, {
                ...clientData,
                campaignData: campaigns
            });
            
            if (success) {
                await fetchEvents(); // Refresh events
            }
            
            return success;
        } catch (error) {
            console.error('Error saving event:', error);
            return false;
        }
    };

    // Delete event using Firebase
    const deleteEvent = async (eventId) => {
        try {
            const clientData = await getFirebaseService().getClientData(clientId);
            const campaigns = clientData?.campaignData || {};
            
            delete campaigns[eventId];
            
            const success = await getFirebaseService().saveClientData(clientId, {
                ...clientData,
                campaignData: campaigns
            });
            
            if (success) {
                await fetchEvents(); // Refresh events
            }
            
            return success;
        } catch (error) {
            console.error('Error deleting event:', error);
            return false;
        }
    };

    // Duplicate event using Firebase
    const duplicateEvent = async (eventId) => {
        try {
            const clientData = await getFirebaseService().getClientData(clientId);
            const campaigns = clientData?.campaignData || {};
            
            const originalEvent = campaigns[eventId];
            if (originalEvent) {
                const newId = 'event-dupe-' + Date.now();
                campaigns[newId] = {
                    ...originalEvent,
                    title: `${originalEvent.title} (Copy)`
                };
                
                const success = await getFirebaseService().saveClientData(clientId, {
                    ...clientData,
                    campaignData: campaigns
                });
                
                if (success) {
                    await fetchEvents(); // Refresh events
                }
                
                return success;
            }
            return false;
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

    // Handle drag start with enhanced visual feedback
    const handleDragStart = (e, event) => {
        setDraggedEvent(event);
        setIsDragging(true);
        e.dataTransfer.effectAllowed = 'move';
        e.target.classList.add('opacity-50', 'transform', 'rotate-2');
        
        // Set drag image
        const dragImage = e.target.cloneNode(true);
        dragImage.style.transform = 'rotate(5deg)';
        dragImage.style.opacity = '0.8';
        e.dataTransfer.setDragImage(dragImage, 50, 15);
        
        // Change cursor
        document.body.style.cursor = 'grabbing';
    };

    // Handle drag end with enhanced cleanup
    const handleDragEnd = (e) => {
        e.target.classList.remove('opacity-50', 'transform', 'rotate-2');
        setDraggedEvent(null);
        setIsDragging(false);
        document.body.style.cursor = 'default';
        
        // Hide all drop zones after a brief delay for smooth animation
        setTimeout(() => {
            const dropZones = document.querySelectorAll('.drop-zone-active');
            dropZones.forEach(zone => zone.classList.remove('drop-zone-active'));
        }, 200);
    };

    // Handle drop on calendar day with animation and validation
    const handleDrop = async (e, targetDate) => {
        e.preventDefault();
        
        if (!draggedEvent) return;
        
        // Validate drop (prevent dropping outside calendar bounds)
        const currentMonth = currentDate.getMonth();
        const currentYear = currentDate.getFullYear();
        const targetDateObj = new Date(targetDate);
        
        // Allow drops within ±2 months for flexibility
        const monthDiff = (targetDateObj.getFullYear() - currentYear) * 12 + (targetDateObj.getMonth() - currentMonth);
        if (Math.abs(monthDiff) > 2) {
            // Show error feedback
            const dropZone = e.target.closest('.calendar-day');
            if (dropZone) {
                dropZone.classList.add('drop-invalid');
                setTimeout(() => dropZone.classList.remove('drop-invalid'), 1000);
            }
            return;
        }
        
        // Push to undo stack
        setUndoStack(prev => [...prev.slice(-19), events]); // Keep last 20 states
        
        // Add smooth drop animation
        const dropZone = e.target.closest('.calendar-day');
        if (dropZone) {
            dropZone.classList.add('drop-success');
            setTimeout(() => dropZone.classList.remove('drop-success'), 600);
        }
        
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

    // Handle drag over with visual drop zone feedback
    const handleDragOver = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        if (isDragging && draggedEvent) {
            const dropZone = e.target.closest('.calendar-day');
            if (dropZone && !dropZone.classList.contains('drop-zone-active')) {
                // Remove active state from all other drop zones
                const otherZones = document.querySelectorAll('.drop-zone-active');
                otherZones.forEach(zone => zone.classList.remove('drop-zone-active'));
                
                // Add active state to current drop zone
                dropZone.classList.add('drop-zone-active');
            }
        }
    };
    
    // Handle drag leave to clean up drop zone styling
    const handleDragLeave = (e) => {
        if (isDragging && !e.target.closest('.calendar-day').contains(e.relatedTarget)) {
            e.target.closest('.calendar-day')?.classList.remove('drop-zone-active');
        }
    };

    // Handle keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e) => {
            // Delete key to delete selected event
            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (selectedEvent && !showEventModal) {
                    e.preventDefault();
                    handleDeleteEvent(selectedEvent.id);
                }
            }
            // Escape key to clear selection or close context menu
            if (e.key === 'Escape') {
                setSelectedEvent(null);
                setContextMenu({ visible: false, x: 0, y: 0, event: null });
            }
        };
        
        const handleClickOutside = () => {
            setContextMenu({ visible: false, x: 0, y: 0, event: null });
        };
        
        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('click', handleClickOutside);
        
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.removeEventListener('click', handleClickOutside);
        };
    }, [selectedEvent, showEventModal]);
    
    // Handle event context menu (right-click)
    const handleEventContextMenu = (e, event) => {
        e.preventDefault();
        e.stopPropagation();
        
        setContextMenu({
            visible: true,
            x: e.clientX,
            y: e.clientY,
            event: event
        });
        setSelectedEvent(event);
    };
    
    // Handle event double-click for editing
    const handleEventDoubleClick = (event) => {
        setSelectedEvent(event);
        setEventModalMode('edit');
        setShowEventModal(true);
        setContextMenu({ visible: false, x: 0, y: 0, event: null });
    };
    
    // Handle delete event with confirmation
    const handleDeleteEvent = async (eventId) => {
        const event = events.find(e => e.id === eventId);
        if (!event) return;
        
        // Show confirmation dialog
        const confirmed = window.confirm(`Are you sure you want to delete "${event.title}"?\n\nThis action cannot be undone.`);
        
        if (confirmed) {
            const success = await deleteEvent(eventId);
            if (success) {
                setSelectedEvent(null);
                setContextMenu({ visible: false, x: 0, y: 0, event: null });
            }
        }
    };
    
    // Handle duplicate event
    const handleDuplicateEvent = async (eventId) => {
        try {
            // Call the API endpoint to duplicate the event
            const response = await fetch(`/api/calendar/events/${eventId}/duplicate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({}) // Empty body, uses original date by default
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Event duplicated:', result);
                
                // Refresh events to show the duplicate
                await fetchEvents();
                setContextMenu({ visible: false, x: 0, y: 0, event: null });
                
                // Show success feedback
                const successMessage = `Event "${result.duplicate_event?.title || 'Event'}" duplicated successfully!`;
                alert(successMessage);
            } else {
                const error = await response.json();
                console.error('Error duplicating event:', error);
                alert(`Failed to duplicate event: ${error.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Network error duplicating event:', error);
            alert('Failed to duplicate event: Network error');
        }
    };
    
    // Handle edit event
    const handleEditEvent = (event) => {
        setSelectedEvent(event);
        setEventModalMode('edit');
        setShowEventModal(true);
        setContextMenu({ visible: false, x: 0, y: 0, event: null });
    };
    
    // Handle event modal close
    const handleEventModalClose = () => {
        setShowEventModal(false);
        setSelectedEvent(null);
        setEventModalMode('view');
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
                                    onDragLeave={handleDragLeave}
                                    onEventClick={onEventClick}
                                    onEventCreate={onEventCreate}
                                    onDragStart={handleDragStart}
                                    onDragEnd={handleDragEnd}
                                    onEventContextMenu={handleEventContextMenu}
                                    onEventDoubleClick={handleEventDoubleClick}
                                    selectedEvent={selectedEvent}
                                />
                            ))}
                        </div>
                    </div>
                )}
            </div>
            
            {/* Context Menu */}
            {contextMenu.visible && (
                <ContextMenu
                    x={contextMenu.x}
                    y={contextMenu.y}
                    event={contextMenu.event}
                    onEdit={() => handleEditEvent(contextMenu.event)}
                    onDuplicate={() => handleDuplicateEvent(contextMenu.event.id)}
                    onDelete={() => handleDeleteEvent(contextMenu.event.id)}
                    onClose={() => setContextMenu({ visible: false, x: 0, y: 0, event: null })}
                />
            )}
            
            {/* Event Modal */}
            {showEventModal && window.EventModal && (
                <window.EventModal
                    isOpen={showEventModal}
                    onClose={handleEventModalClose}
                    event={eventModalMode === 'edit' ? selectedEvent : null}
                    onSave={saveEvent}
                    onDelete={deleteEvent}
                    onDuplicate={handleDuplicateEvent}
                    initialDate={eventModalMode === 'create' ? null : undefined}
                />
            )}
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
    onDragLeave,
    onEventClick, 
    onEventCreate,
    onDragStart,
    onDragEnd,
    onEventContextMenu,
    onEventDoubleClick,
    selectedEvent
}) {
    const [showAddButton, setShowAddButton] = useState(false);

    const handleAddEvent = () => {
        onEventCreate(day.dateString);
    };

    return (
        <div
            className={`calendar-day border border-gray-200 min-h-[120px] p-1 relative transition-colors ${
                day.isCurrentMonth 
                    ? 'bg-white hover:bg-gray-50' 
                    : 'bg-gray-50 text-gray-400'
            }`}
            onMouseEnter={() => setShowAddButton(true)}
            onMouseLeave={() => setShowAddButton(false)}
            onDrop={(e) => onDrop(e, day.dateString)}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
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
                        isSelected={selectedEvent && selectedEvent.id === event.id}
                        onClick={() => onEventClick(event)}
                        onContextMenu={(e) => onEventContextMenu(e, event)}
                        onDoubleClick={() => onEventDoubleClick(event)}
                        onDragStart={onDragStart}
                        onDragEnd={onDragEnd}
                    />
                ))}
            </div>
        </div>
    );
}

// Calendar Event Component
function CalendarEvent({ 
    event, 
    isSelected = false, 
    onClick, 
    onContextMenu, 
    onDoubleClick, 
    onDragStart, 
    onDragEnd 
}) {
    const colorClass = CAMPAIGN_COLORS[event.event_type] || CAMPAIGN_COLORS.default;

    return (
        <div
            draggable
            onClick={(e) => {
                e.stopPropagation();
                onClick();
            }}
            onContextMenu={onContextMenu}
            onDoubleClick={onDoubleClick}
            onDragStart={(e) => onDragStart(e, event)}
            onDragEnd={onDragEnd}
            className={`${colorClass} text-xs px-2 py-1 rounded cursor-pointer hover:shadow-md transition-all duration-200 truncate select-none ${
                isSelected ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
            }`}
            title={`${event.title}\n\nRight-click for options\nDouble-click to edit\nPress Delete to remove`}
        >
            {event.title}
        </div>
    );
}

// Context Menu Component
function ContextMenu({ x, y, event, onEdit, onDuplicate, onDelete, onClose }) {
    const menuRef = useRef(null);
    
    // Position the menu within screen bounds
    useEffect(() => {
        if (menuRef.current) {
            const menu = menuRef.current;
            const rect = menu.getBoundingClientRect();
            const screenWidth = window.innerWidth;
            const screenHeight = window.innerHeight;
            
            let adjustedX = x;
            let adjustedY = y;
            
            // Adjust horizontal position if menu would go off-screen
            if (x + rect.width > screenWidth) {
                adjustedX = screenWidth - rect.width - 10;
            }
            
            // Adjust vertical position if menu would go off-screen
            if (y + rect.height > screenHeight) {
                adjustedY = screenHeight - rect.height - 10;
            }
            
            menu.style.left = `${Math.max(10, adjustedX)}px`;
            menu.style.top = `${Math.max(10, adjustedY)}px`;
        }
    }, [x, y]);
    
    // Handle clicks outside the menu
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                onClose();
            }
        };
        
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);
    
    // Handle keyboard navigation
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };
        
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);
    
    return (
        <div
            ref={menuRef}
            className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[160px] animate-in fade-in zoom-in duration-200"
            style={{
                left: `${x}px`,
                top: `${y}px`,
            }}
            onClick={e => e.stopPropagation()}
        >
            <div className="px-3 py-2 text-xs font-medium text-gray-500 border-b border-gray-100 truncate">
                {event?.title || 'Event Options'}
            </div>
            
            <button
                onClick={() => {
                    onEdit();
                    onClose();
                }}
                className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2 transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                </svg>
                Edit
            </button>
            
            <button
                onClick={() => {
                    onDuplicate();
                    onClose();
                }}
                className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2 transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                </svg>
                Duplicate
            </button>
            
            <div className="border-t border-gray-100 my-1"></div>
            
            <button
                onClick={() => {
                    onDelete();
                    onClose();
                }}
                className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
                Delete
            </button>
        </div>
    );
}

// Make Calendar available globally
window.Calendar = Calendar;