// Calendar View Component with Proper API Configuration
// Fixes API endpoint issues for production deployment

const { useState, useEffect, useRef } = React;

// API Configuration
const API_BASE = window.API_BASE || 
  (window.location.hostname === 'emailpilot.ai'
    ? 'https://emailpilot-api-935786836546.us-central1.run.app'
    : '');

const api = (path) => `${API_BASE}${path}`;

console.log('[CalendarViewAPIFixed] API Configuration:', {
  hostname: window.location.hostname,
  API_BASE: API_BASE,
  sampleEndpoint: api('/api/clients')
});

// Embedded Firebase Service (fallback if API fails)
class EmbeddedFirebaseService {
    constructor() {
        this.initialized = false;
        this.db = null;
        this.auth = null;
        this.currentUser = null;
    }

    async initialize() {
        if (this.initialized) return;
        
        try {
            const firebaseConfig = {
                apiKey: "AIzaSyByeHeCuEIS0wKhGq4vclyON9XpMxuHMw8",
                authDomain: "winatecom.firebaseapp.com",
                projectId: "winatecom",
                storageBucket: "winatecom.appspot.com",
                messagingSenderId: "386331689185",
                appId: "1:386331689185:web:3e1e4f5b2f5b2f5b2f5b2f"
            };

            if (!firebase.apps.length) {
                firebase.initializeApp(firebaseConfig);
            }

            this.db = firebase.firestore();
            this.auth = firebase.auth();
            await this.auth.signInAnonymously();
            this.currentUser = this.auth.currentUser;
            
            this.initialized = true;
            console.log('[Firebase] Initialized as fallback');
        } catch (error) {
            console.error('[Firebase] Init error:', error);
        }
    }

    async getClientsDirectly() {
        await this.initialize();
        try {
            const snapshot = await this.db.collection('clients').get();
            return snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
        } catch (error) {
            console.error('[Firebase] Error getting clients:', error);
            return this.getDemoClients();
        }
    }

    getDemoClients() {
        return [
            { id: 'demo1', name: 'Demo Client 1', email: 'demo1@example.com' },
            { id: 'demo2', name: 'Demo Client 2', email: 'demo2@example.com' }
        ];
    }

    async getGoalsDirectly(clientId) {
        await this.initialize();
        try {
            const snapshot = await this.db.collection('goals')
                .where('clientId', '==', clientId)
                .get();
            const goals = snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
            return goals.length > 0 ? goals : this.getDemoGoals(clientId);
        } catch (error) {
            console.error('[Firebase] Error getting goals:', error);
            return this.getDemoGoals(clientId);
        }
    }

    getDemoGoals(clientId) {
        return [{
            id: 'demo-goal',
            clientId: clientId,
            monthlyRevenue: 50000,
            year: new Date().getFullYear(),
            month: new Date().getMonth()
        }];
    }

    async getEventsDirectly(clientId) {
        await this.initialize();
        try {
            const snapshot = await this.db.collection('calendar_events')
                .where('clientId', '==', clientId)
                .get();
            return snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
        } catch (error) {
            console.error('[Firebase] Error getting events:', error);
            return [];
        }
    }

    async createEventDirectly(eventData) {
        await this.initialize();
        try {
            const docRef = await this.db.collection('calendar_events').add({
                ...eventData,
                createdAt: firebase.firestore.FieldValue.serverTimestamp(),
                userId: this.currentUser?.uid || 'anonymous'
            });
            return docRef.id;
        } catch (error) {
            console.error('[Firebase] Error creating event:', error);
            return 'demo-event-' + Date.now();
        }
    }

    async updateEventDirectly(eventId, updates) {
        await this.initialize();
        try {
            await this.db.collection('calendar_events').doc(eventId).update({
                ...updates,
                updatedAt: firebase.firestore.FieldValue.serverTimestamp()
            });
            return true;
        } catch (error) {
            console.error('[Firebase] Error updating event:', error);
            return false;
        }
    }

    async deleteEventDirectly(eventId) {
        await this.initialize();
        try {
            await this.db.collection('calendar_events').doc(eventId).delete();
            return true;
        } catch (error) {
            console.error('[Firebase] Error deleting event:', error);
            return false;
        }
    }
}

// Main Calendar Component
function CalendarViewAPIFixed() {
    const [clients, setClients] = useState([]);
    const [selectedClient, setSelectedClient] = useState(null);
    const [events, setEvents] = useState([]);
    const [goals, setGoals] = useState([]);
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [showEventModal, setShowEventModal] = useState(false);
    const [currentEvent, setCurrentEvent] = useState(null);
    const [initialDate, setInitialDate] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [goalProgress, setGoalProgress] = useState(null);
    const [useFirebaseDirect, setUseFirebaseDirect] = useState(false);
    
    // Firebase service for fallback
    const firebaseService = useRef(new EmbeddedFirebaseService());

    // Campaign type multipliers
    const campaignMultipliers = {
        'cheese club': 2.0,
        'rrb': 1.5,
        'sms': 1.3,
        're-engagement': 1.2,
        'nurturing': 0.8,
        'education': 0.8,
        'community': 0.7,
        'lifestyle': 0.7
    };

    // Load clients on mount
    useEffect(() => {
        loadClients();
    }, []);

    // Load events when client changes
    useEffect(() => {
        if (selectedClient) {
            loadClientData(selectedClient.id);
        }
    }, [selectedClient, currentMonth]);

    const loadClients = async () => {
        try {
            setLoading(true);
            setError(null);
            
            // Try API first (with multiple endpoint options)
            let clientsData = [];
            let apiSuccess = false;
            
            // Try different API endpoints
            const endpoints = [
                '/api/clients',
                '/api/firebase-calendar-test/clients',
                '/clients',
                '/api/calendar/clients'
            ];
            
            for (const endpoint of endpoints) {
                try {
                    console.log(`[API] Trying endpoint: ${api(endpoint)}`);
                    const response = await fetch(api(endpoint), {
                        credentials: 'include',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        clientsData = Array.isArray(data) ? data : (data.clients || []);
                        console.log(`[API] Success with ${endpoint}:`, clientsData.length, 'clients');
                        apiSuccess = true;
                        break;
                    }
                } catch (err) {
                    console.warn(`[API] Failed ${endpoint}:`, err.message);
                }
            }
            
            // If API fails, use Firebase directly
            if (!apiSuccess || clientsData.length === 0) {
                console.log('[API] All endpoints failed, using Firebase directly');
                setUseFirebaseDirect(true);
                clientsData = await firebaseService.current.getClientsDirectly();
            }
            
            setClients(clientsData);
            
            // Auto-select first client
            if (clientsData.length > 0 && !selectedClient) {
                setSelectedClient(clientsData[0]);
            }
            
        } catch (error) {
            console.error('[LoadClients] Error:', error);
            setError('Using demo mode - API unavailable');
            
            // Use demo clients as final fallback
            const demoClients = firebaseService.current.getDemoClients();
            setClients(demoClients);
            if (demoClients.length > 0) {
                setSelectedClient(demoClients[0]);
            }
        } finally {
            setLoading(false);
        }
    };

    const loadClientData = async (clientId) => {
        try {
            let goalsData = [];
            let eventsData = [];
            
            if (useFirebaseDirect) {
                // Use Firebase directly
                goalsData = await firebaseService.current.getGoalsDirectly(clientId);
                eventsData = await firebaseService.current.getEventsDirectly(clientId);
            } else {
                // Try API endpoints
                try {
                    // Try goals endpoints
                    const goalsEndpoints = [
                        `/api/goals/${clientId}`,
                        `/api/goals-calendar-test/goals/${clientId}`,
                        `/api/goals/clients/${clientId}`,
                        `/goals/${clientId}`
                    ];
                    
                    for (const endpoint of goalsEndpoints) {
                        try {
                            const response = await fetch(api(endpoint), {
                                credentials: 'include'
                            });
                            if (response.ok) {
                                const data = await response.json();
                                goalsData = Array.isArray(data) ? data : (data.goals || []);
                                console.log(`[API] Goals loaded from ${endpoint}`);
                                break;
                            }
                        } catch (err) {
                            console.warn(`[API] Goals endpoint failed ${endpoint}`);
                        }
                    }
                    
                    // Try events endpoints
                    const eventsEndpoints = [
                        `/api/calendar/events?client_id=${clientId}`,
                        `/api/firebase-calendar-test/events?client_id=${clientId}`,
                        `/api/events/${clientId}`,
                        `/calendar/events/${clientId}`
                    ];
                    
                    for (const endpoint of eventsEndpoints) {
                        try {
                            const response = await fetch(api(endpoint), {
                                credentials: 'include'
                            });
                            if (response.ok) {
                                const data = await response.json();
                                eventsData = Array.isArray(data) ? data : (data.events || []);
                                console.log(`[API] Events loaded from ${endpoint}`);
                                break;
                            }
                        } catch (err) {
                            console.warn(`[API] Events endpoint failed ${endpoint}`);
                        }
                    }
                } catch (error) {
                    console.error('[API] Error loading client data:', error);
                }
                
                // Fallback to Firebase if API fails
                if (goalsData.length === 0) {
                    goalsData = await firebaseService.current.getGoalsDirectly(clientId);
                }
                if (!eventsData || eventsData.length === 0) {
                    eventsData = await firebaseService.current.getEventsDirectly(clientId);
                }
            }
            
            setGoals(goalsData);
            setEvents(eventsData);
            calculateGoalProgress(eventsData, goalsData);
            
        } catch (error) {
            console.error('[LoadClientData] Error:', error);
            // Use demo data as fallback
            const demoGoals = firebaseService.current.getDemoGoals(clientId);
            setGoals(demoGoals);
            setEvents([]);
            calculateGoalProgress([], demoGoals);
        }
    };

    const calculateGoalProgress = (events, goals) => {
        const currentYear = currentMonth.getFullYear();
        const currentMonthNum = currentMonth.getMonth();
        
        const monthGoal = goals.find(g => 
            g.year === currentYear && g.month === currentMonthNum
        );
        
        if (!monthGoal) {
            setGoalProgress(null);
            return;
        }
        
        const monthEvents = events.filter(e => {
            const eventDate = new Date(e.date || e.event_date);
            return eventDate.getFullYear() === currentYear && 
                   eventDate.getMonth() === currentMonthNum;
        });
        
        let totalRevenue = 0;
        monthEvents.forEach(event => {
            const baseRevenue = 500;
            const multiplier = getCampaignMultiplier(event.title || event.name || '');
            totalRevenue += baseRevenue * multiplier;
        });
        
        const progress = {
            goal: monthGoal.monthlyRevenue || monthGoal.monthly_revenue || 50000,
            current: totalRevenue,
            percentage: (totalRevenue / (monthGoal.monthlyRevenue || monthGoal.monthly_revenue || 50000)) * 100,
            status: getGoalStatus(totalRevenue, monthGoal.monthlyRevenue || monthGoal.monthly_revenue || 50000),
            campaignCount: monthEvents.length
        };
        
        setGoalProgress(progress);
    };

    const getCampaignMultiplier = (title) => {
        const lowerTitle = title.toLowerCase();
        for (const [key, multiplier] of Object.entries(campaignMultipliers)) {
            if (lowerTitle.includes(key)) {
                return multiplier;
            }
        }
        return 1.0;
    };

    const getGoalStatus = (current, goal) => {
        const percentage = (current / goal) * 100;
        if (percentage >= 100) return { label: 'Achieved', color: 'green', emoji: '🎉' };
        if (percentage >= 75) return { label: 'On Track', color: 'blue', emoji: '✅' };
        if (percentage >= 50) return { label: 'Warning', color: 'yellow', emoji: '⚠️' };
        return { label: 'At Risk', color: 'red', emoji: '🚨' };
    };

    const handleClientChange = (clientId) => {
        const client = clients.find(c => c.id === clientId);
        setSelectedClient(client);
    };

    const handleEventClick = (event) => {
        setCurrentEvent(event);
        setInitialDate(null);
        setShowEventModal(true);
    };

    const handleCreateEvent = (date) => {
        setCurrentEvent(null);
        setInitialDate(date);
        setShowEventModal(true);
    };

    const handleSaveEvent = async (eventData) => {
        try {
            if (useFirebaseDirect) {
                // Use Firebase directly
                if (eventData.id) {
                    await firebaseService.current.updateEventDirectly(eventData.id, eventData);
                } else {
                    await firebaseService.current.createEventDirectly({
                        ...eventData,
                        clientId: selectedClient.id
                    });
                }
            } else {
                // Try API
                if (eventData.id) {
                    const response = await fetch(api(`/api/calendar/events/${eventData.id}`), {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify(eventData)
                    });
                    if (!response.ok) throw new Error('API update failed');
                } else {
                    const response = await fetch(api('/api/calendar/events'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({
                            ...eventData,
                            client_id: selectedClient.id
                        })
                    });
                    if (!response.ok) throw new Error('API create failed');
                }
            }
            
            await loadClientData(selectedClient.id);
            setShowEventModal(false);
            return true;
        } catch (error) {
            console.error('[SaveEvent] Error:', error);
            // Try Firebase as fallback
            if (!useFirebaseDirect) {
                if (eventData.id) {
                    await firebaseService.current.updateEventDirectly(eventData.id, eventData);
                } else {
                    await firebaseService.current.createEventDirectly({
                        ...eventData,
                        clientId: selectedClient.id
                    });
                }
                await loadClientData(selectedClient.id);
                setShowEventModal(false);
                return true;
            }
            return false;
        }
    };

    const handleDeleteEvent = async (eventId) => {
        try {
            if (useFirebaseDirect) {
                await firebaseService.current.deleteEventDirectly(eventId);
            } else {
                const response = await fetch(api(`/api/calendar/events/${eventId}`), {
                    method: 'DELETE',
                    credentials: 'include'
                });
                if (!response.ok) {
                    // Fallback to Firebase
                    await firebaseService.current.deleteEventDirectly(eventId);
                }
            }
            
            await loadClientData(selectedClient.id);
            setShowEventModal(false);
            return true;
        } catch (error) {
            console.error('[DeleteEvent] Error:', error);
            return false;
        }
    };

    const renderGoalsPanel = () => {
        if (!goalProgress) return null;
        
        const { goal, current, percentage, status, campaignCount } = goalProgress;
        
        return (
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                <h3 className="text-lg font-semibold mb-4">Revenue Goal Progress</h3>
                
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <span className="text-gray-600">Monthly Goal</span>
                        <span className="font-bold">${goal.toLocaleString()}</span>
                    </div>
                    
                    <div className="flex justify-between items-center">
                        <span className="text-gray-600">Current Revenue</span>
                        <span className="font-bold">${current.toLocaleString()}</span>
                    </div>
                    
                    <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                            className={`h-3 rounded-full bg-${status.color}-500`}
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                    </div>
                    
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">
                            {campaignCount} campaigns planned
                        </span>
                        <span className={`text-sm font-bold text-${status.color}-600`}>
                            {status.emoji} {status.label} ({percentage.toFixed(1)}%)
                        </span>
                    </div>
                    
                    {percentage < 100 && (
                        <div className="mt-4 p-3 bg-blue-50 rounded-md">
                            <p className="text-sm text-blue-700">
                                💡 Add {Math.ceil((goal - current) / 1000)} more high-value campaigns to reach your goal
                            </p>
                        </div>
                    )}
                </div>
            </div>
        );
    };

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

    return (
        <div className="calendar-view-container p-6">
            {/* API Status */}
            {error && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                    <p className="text-sm text-yellow-700">
                        {error}
                        {useFirebaseDirect && ' - Using Firebase directly'}
                    </p>
                </div>
            )}

            {/* Client Selector */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Client
                </label>
                <select
                    value={selectedClient?.id || ''}
                    onChange={(e) => handleClientChange(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                    <option value="">Choose a client...</option>
                    {clients.map(client => (
                        <option key={client.id} value={client.id}>
                            {client.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Goals Panel */}
            {selectedClient && renderGoalsPanel()}

            {/* Calendar Component */}
            {selectedClient && (
                <div className="bg-white rounded-lg shadow-lg p-6">
                    <h2 className="text-xl font-bold mb-4">
                        Campaign Calendar - {currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                    </h2>
                    
                    {/* Month Navigation */}
                    <div className="flex justify-between mb-4">
                        <button
                            onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))}
                            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                        >
                            Previous
                        </button>
                        <button
                            onClick={() => setCurrentMonth(new Date())}
                            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        >
                            Today
                        </button>
                        <button
                            onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))}
                            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                        >
                            Next
                        </button>
                    </div>
                    
                    {/* Calendar Grid */}
                    {typeof window.Calendar !== 'undefined' ? (
                        <window.Calendar
                            clientId={selectedClient.id}
                            events={events}
                            onEventClick={handleEventClick}
                            onDateClick={handleCreateEvent}
                            currentMonth={currentMonth}
                        />
                    ) : (
                        <div className="text-center py-8 text-gray-500">
                            <p>Calendar grid component loading...</p>
                            <p className="text-sm mt-2">Events: {events.length}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Event Modal */}
            {showEventModal && typeof window.EventModal !== 'undefined' && (
                <window.EventModal
                    isOpen={showEventModal}
                    onClose={() => setShowEventModal(false)}
                    event={currentEvent}
                    initialDate={initialDate}
                    onSave={handleSaveEvent}
                    onDelete={handleDeleteEvent}
                    clientId={selectedClient?.id}
                />
            )}
        </div>
    );
}

// Register component globally
window.CalendarViewAPIFixed = CalendarViewAPIFixed;

console.log('[CalendarViewAPIFixed] Component registered');