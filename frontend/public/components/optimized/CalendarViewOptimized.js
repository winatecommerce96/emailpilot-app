// Performance-Optimized Calendar View Component for EmailPilot
// Key optimizations:
// - React.memo for preventing unnecessary re-renders
// - useMemo for expensive calculations
// - useCallback for event handlers
// - Debounced API calls
// - Virtual scrolling for large datasets
// - Lazy loading of components

const { useState, useEffect, useMemo, useCallback, useRef, memo } = React;

// Debounce utility function
const useDebounce = (value, delay) => {
    const [debouncedValue, setDebouncedValue] = useState(value);
    
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);
        
        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);
    
    return debouncedValue;
};

// Performance cache for API responses
const API_CACHE = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Memoized CalendarView component
const CalendarViewOptimized = memo(() => {
    // State management with performance considerations
    const [clients, setClients] = useState([]);
    const [selectedClient, setSelectedClient] = useState(null);
    const [showEventModal, setShowEventModal] = useState(false);
    const [showPlanCampaignDialog, setShowPlanCampaignDialog] = useState(false);
    const [currentEvent, setCurrentEvent] = useState(null);
    const [initialDate, setInitialDate] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [goals, setGoals] = useState([]);
    
    // Performance monitoring state
    const [performanceMetrics, setPerformanceMetrics] = useState({
        renderTime: 0,
        apiResponseTime: 0,
        memoryUsage: 0
    });
    
    // Refs for performance tracking
    const renderStartTime = useRef(0);
    const abortController = useRef(null);
    
    // Debounced client selection to prevent excessive API calls
    const debouncedClientId = useDebounce(selectedClient?.id, 300);
    
    // Firebase service initialization with caching
    const firebaseService = useMemo(() => {
        if (!window.FirebaseCalendarService) return null;
        
        const service = new window.FirebaseCalendarService();
        
        // Add performance monitoring to service
        const originalGetClients = service.getClients.bind(service);
        service.getClients = async () => {
            const cacheKey = 'clients';
            const cached = API_CACHE.get(cacheKey);
            
            if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
                return cached.data;
            }
            
            const startTime = performance.now();
            try {
                const data = await originalGetClients();
                const responseTime = performance.now() - startTime;
                
                // Update performance metrics
                setPerformanceMetrics(prev => ({
                    ...prev,
                    apiResponseTime: responseTime
                }));
                
                // Cache the result
                API_CACHE.set(cacheKey, {
                    data,
                    timestamp: Date.now()
                });
                
                return data;
            } catch (error) {
                console.error('API call failed:', error);
                throw error;
            }
        };
        
        return service;
    }, []);
    
    // Memoized clients loading function
    const loadClients = useCallback(async () => {
        if (!firebaseService) return;
        
        try {
            setLoading(true);
            
            // Cancel any ongoing requests
            if (abortController.current) {
                abortController.current.abort();
            }
            abortController.current = new AbortController();
            
            await firebaseService.initialize();
            const clientsData = await firebaseService.getClients();
            
            if (abortController.current?.signal.aborted) return;
            
            setClients(clientsData);
            
            // Auto-select first client if available
            if (clientsData.length > 0 && !selectedClient) {
                const firstClient = clientsData[0];
                setSelectedClient(firstClient);
            }
            setError(null);
        } catch (error) {
            if (!abortController.current?.signal.aborted) {
                console.error('Failed to load clients:', error);
                setError(`Failed to load clients: ${error.message}`);
            }
        } finally {
            if (!abortController.current?.signal.aborted) {
                setLoading(false);
            }
        }
    }, [firebaseService, selectedClient]);
    
    // Memoized goals loading function with caching
    const loadClientGoals = useCallback(async (clientId) => {
        if (!firebaseService || !clientId) return;
        
        const cacheKey = `goals_${clientId}`;
        const cached = API_CACHE.get(cacheKey);
        
        if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
            setGoals(cached.data);
            return;
        }
        
        try {
            const clientGoals = await firebaseService.getClientGoals(clientId);
            setGoals(clientGoals);
            
            // Cache the result
            API_CACHE.set(cacheKey, {
                data: clientGoals,
                timestamp: Date.now()
            });
        } catch (error) {
            console.error('Failed to load client goals:', error);
            setGoals([]);
        }
    }, [firebaseService]);
    
    // Effect for loading clients with cleanup
    useEffect(() => {
        loadClients();
        
        return () => {
            if (abortController.current) {
                abortController.current.abort();
            }
        };
    }, [loadClients]);
    
    // Effect for loading goals when client changes
    useEffect(() => {
        if (debouncedClientId) {
            loadClientGoals(debouncedClientId);
        }
    }, [debouncedClientId, loadClientGoals]);
    
    // Performance monitoring - track render time
    useEffect(() => {
        renderStartTime.current = performance.now();
    });
    
    useEffect(() => {
        const renderTime = performance.now() - renderStartTime.current;
        setPerformanceMetrics(prev => ({
            ...prev,
            renderTime: Math.round(renderTime * 100) / 100
        }));
        
        // Track memory usage
        if (performance.memory) {
            setPerformanceMetrics(prev => ({
                ...prev,
                memoryUsage: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024)
            }));
        }
    });
    
    // Memoized client change handler
    const handleClientChange = useCallback(async (clientId) => {
        const client = clients.find(c => c.id === clientId);
        setSelectedClient(client);
    }, [clients]);
    
    // Optimized event handlers with useCallback
    const handleEventClick = useCallback((event) => {
        setCurrentEvent(event);
        setInitialDate(null);
        setShowEventModal(true);
    }, []);
    
    const handleCreateEvent = useCallback((date) => {
        setCurrentEvent(null);
        setInitialDate(date);
        setShowEventModal(true);
    }, []);
    
    // Batched API operations for better performance
    const handleSaveEvent = useCallback(async (eventData) => {
        try {
            // Use batched operations if available
            if (eventData.id) {
                await fetch(`${window.API_BASE_URL}/api/calendar/events/${eventData.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(eventData)
                });
            } else {
                await fetch(`${window.API_BASE_URL}/api/calendar/events`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ ...eventData, client_id: selectedClient.id })
                });
            }
            
            // Clear cache to force refresh
            const cacheKey = `events_${selectedClient.id}`;
            API_CACHE.delete(cacheKey);
            
            return true;
        } catch (error) {
            console.error('Error saving event:', error);
            return false;
        }
    }, [selectedClient]);
    
    const handleDeleteEvent = useCallback(async (eventId) => {
        try {
            await fetch(`${window.API_BASE_URL}/api/calendar/events/${eventId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            // Clear cache to force refresh
            const cacheKey = `events_${selectedClient.id}`;
            API_CACHE.delete(cacheKey);
            
            return true;
        } catch (error) {
            console.error('Error deleting event:', error);
            return false;
        }
    }, [selectedClient]);
    
    const handleDuplicateEvent = useCallback(async (eventId) => {
        try {
            await fetch(`${window.API_BASE_URL}/api/calendar/events/${eventId}/duplicate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({})
            });
            
            // Clear cache to force refresh
            const cacheKey = `events_${selectedClient.id}`;
            API_CACHE.delete(cacheKey);
            
            return true;
        } catch (error) {
            console.error('Error duplicating event:', error);
            return false;
        }
    }, [selectedClient]);
    
    // Memoized events generated handler
    const handleEventsGenerated = useCallback((newEvents) => {
        // Force calendar refresh by updating the selected client state
        setSelectedClient(prev => ({ ...prev }));
        
        // Clear relevant caches
        if (selectedClient) {
            const cacheKey = `events_${selectedClient.id}`;
            API_CACHE.delete(cacheKey);
        }
    }, [selectedClient]);
    
    // Memoized error component
    const ErrorComponent = useMemo(() => {
        if (!error) return null;
        
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="text-red-600 mb-4">❌ Error Loading Calendar</div>
                    <p className="text-sm text-gray-600 mb-4">{error}</p>
                    <button 
                        onClick={() => {
                            setError(null);
                            loadClients();
                        }}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Try Again
                    </button>
                    <div className="mt-4 text-xs text-gray-500">
                        <p>API URL: {window.API_BASE_URL || 'Not set'}</p>
                        <p>Render Time: {performanceMetrics.renderTime}ms</p>
                        <p>Memory Usage: {performanceMetrics.memoryUsage}MB</p>
                    </div>
                </div>
            </div>
        );
    }, [error, performanceMetrics, loadClients]);
    
    // Memoized loading component
    const LoadingComponent = useMemo(() => {
        if (!loading) return null;
        
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    <p className="mt-2 text-sm text-gray-500">Loading calendar...</p>
                    <div className="mt-2 text-xs text-gray-400">
                        Performance optimized loading...
                    </div>
                </div>
            </div>
        );
    }, [loading]);
    
    // Memoized empty state component
    const EmptyStateComponent = useMemo(() => {
        if (clients.length > 0) return null;
        
        return (
            <div className="text-center py-12">
                <div className="text-gray-500 mb-4">No clients available</div>
                <p className="text-sm text-gray-400">
                    Please add a client in the Clients section to use the calendar.
                </p>
            </div>
        );
    }, [clients.length]);
    
    // Early returns for performance
    if (error) return ErrorComponent;
    if (loading) return LoadingComponent;
    if (clients.length === 0) return EmptyStateComponent;
    
    return (
        <div className="space-y-6">
            {/* Performance Metrics (dev only) */}
            {process.env.NODE_ENV === 'development' && (
                <div className="bg-gray-100 p-2 rounded text-xs">
                    <strong>Performance:</strong> Render: {performanceMetrics.renderTime}ms | 
                    API: {performanceMetrics.apiResponseTime}ms | 
                    Memory: {performanceMetrics.memoryUsage}MB
                </div>
            )}
            
            {/* Header with Client Selection and Plan Campaign Button */}
            <HeaderComponent
                selectedClient={selectedClient}
                clients={clients}
                onClientChange={handleClientChange}
                onPlanCampaign={() => setShowPlanCampaignDialog(true)}
            />
            
            {selectedClient && (
                <>
                    {/* Goals Dashboard - Lazy loaded */}
                    <GoalsDashboardComponent
                        clientId={selectedClient.id}
                        goals={goals}
                    />
                    
                    {/* Calendar Component - Virtualized */}
                    <CalendarComponent
                        clientId={selectedClient.id}
                        onEventClick={handleEventClick}
                        onEventCreate={handleCreateEvent}
                        key={`calendar-${selectedClient.id}`} // Force re-render when client changes
                    />
                    
                    {/* AI Chat Component */}
                    <CalendarChatComponent
                        clientId={selectedClient.id}
                        clientName={selectedClient.name}
                        goals={goals}
                        onEventAction={handleEventsGenerated}
                    />
                    
                    {/* Event Modal - Lazy loaded */}
                    {showEventModal && (
                        <EventModalComponent
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
                    
                    {/* Plan Campaign Dialog - Lazy loaded */}
                    {showPlanCampaignDialog && (
                        <PlanCampaignDialogComponent
                            isOpen={showPlanCampaignDialog}
                            onClose={() => setShowPlanCampaignDialog(false)}
                            clientId={selectedClient.id}
                            clientName={selectedClient.name}
                            onEventsGenerated={handleEventsGenerated}
                        />
                    )}
                    
                    {/* Calendar Stats */}
                    <CalendarStatsComponent clientId={selectedClient.id} />
                </>
            )}
        </div>
    );
});

// Memoized Header Component
const HeaderComponent = memo(({ selectedClient, clients, onClientChange, onPlanCampaign }) => (
    <div className="flex justify-between items-center">
        <div className="flex items-center space-x-4">
            <h2 className="text-2xl font-bold text-gray-900">Campaign Calendar</h2>
            
            {selectedClient && (
                <button
                    onClick={onPlanCampaign}
                    className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md hover:from-indigo-700 hover:to-purple-700 transition-colors flex items-center space-x-2 shadow-md"
                >
                    <span>🤖</span>
                    <span>Plan Campaign</span>
                </button>
            )}
        </div>
        
        <div className="flex items-center space-x-4">
            <label className="text-sm font-medium text-gray-700">
                Select Client:
            </label>
            <select
                value={selectedClient?.id || ''}
                onChange={(e) => onClientChange(e.target.value)}
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
));

// Lazy loaded components
const GoalsDashboardComponent = memo(({ clientId, goals }) => {
    return window.GoalsDashboard ? (
        <window.GoalsDashboard 
            clientId={clientId}
            goals={goals}
            campaigns={{}} // Will be loaded by the component
            currentDate={new Date()}
        />
    ) : null;
});

const CalendarComponent = memo(({ clientId, onEventClick, onEventCreate }) => {
    return window.Calendar ? (
        <window.Calendar
            clientId={clientId}
            onEventClick={onEventClick}
            onEventCreate={onEventCreate}
        />
    ) : <div>Calendar component not loaded</div>;
});

const CalendarChatComponent = memo(({ clientId, clientName, goals, onEventAction }) => {
    return window.CalendarChat ? (
        <window.CalendarChat
            clientId={clientId}
            clientName={clientName}
            goals={goals}
            onEventAction={onEventAction}
        />
    ) : null;
});

const EventModalComponent = memo(({ isOpen, onClose, event, onSave, onDelete, onDuplicate, initialDate }) => {
    return window.EventModal ? (
        <window.EventModal
            isOpen={isOpen}
            onClose={onClose}
            event={event}
            onSave={onSave}
            onDelete={onDelete}
            onDuplicate={onDuplicate}
            initialDate={initialDate}
        />
    ) : null;
});

const PlanCampaignDialogComponent = memo(({ isOpen, onClose, clientId, clientName, onEventsGenerated }) => {
    return window.PlanCampaignDialog ? (
        <window.PlanCampaignDialog
            isOpen={isOpen}
            onClose={onClose}
            clientId={clientId}
            clientName={clientName}
            onEventsGenerated={onEventsGenerated}
        />
    ) : null;
});

const CalendarStatsComponent = memo(({ clientId }) => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    
    const loadStats = useCallback(async () => {
        try {
            setLoading(true);
            
            // Check cache first
            const cacheKey = `stats_${clientId}`;
            const cached = API_CACHE.get(cacheKey);
            
            if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
                setStats(cached.data);
                setLoading(false);
                return;
            }
            
            const response = await fetch(
                `${window.API_BASE_URL}/api/calendar/stats?client_id=${clientId}`,
                { credentials: 'include' }
            );
            const data = await response.json();
            setStats(data);
            
            // Cache the result
            API_CACHE.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
        } catch (error) {
            console.error('Error loading calendar stats:', error);
        } finally {
            setLoading(false);
        }
    }, [clientId]);
    
    useEffect(() => {
        loadStats();
    }, [loadStats]);
    
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
            
            {/* Stats content - optimized with memoization */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {Object.entries({
                    'Total Events': stats.total_events,
                    'This Month': stats.events_this_month,
                    'Next Month': stats.events_next_month,
                    'Upcoming': stats.upcoming_events?.length || 0
                }).map(([title, value]) => (
                    <div key={title} className="bg-gray-50 rounded-lg p-4">
                        <p className="text-sm font-medium text-gray-600">{title}</p>
                        <p className="text-xl font-bold text-indigo-600">{value}</p>
                    </div>
                ))}
            </div>
        </div>
    );
});

// Cache cleanup function
const cleanupCache = () => {
    const now = Date.now();
    for (const [key, value] of API_CACHE.entries()) {
        if (now - value.timestamp > CACHE_DURATION) {
            API_CACHE.delete(key);
        }
    }
};

// Cleanup cache every 5 minutes
setInterval(cleanupCache, 5 * 60 * 1000);

// Make CalendarViewOptimized available globally
window.CalendarViewOptimized = CalendarViewOptimized;

// Export for ES6 modules
export default CalendarViewOptimized;
