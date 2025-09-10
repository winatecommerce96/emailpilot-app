// Self-Contained Enhanced Calendar View Component for EmailPilot SPA
// This version includes all Firebase functionality internally to avoid dependency issues

const { useState, useEffect, useRef } = React;

// Embedded Firebase Service Class
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
            // Firebase configuration
            const firebaseConfig = {
                apiKey: "AIzaSyByeHeCuEIS0wKhGq4vclyON9XpMxuHMw8",
                authDomain: "winatecom.firebaseapp.com",
                projectId: "winatecom",
                storageBucket: "winatecom.appspot.com",
                messagingSenderId: "386331689185",
                appId: "1:386331689185:web:3e1e4f5b2f5b2f5b2f5b2f"
            };

            // Initialize Firebase if not already initialized
            if (!firebase.apps.length) {
                firebase.initializeApp(firebaseConfig);
            }

            this.db = firebase.firestore();
            this.auth = firebase.auth();
            
            // Sign in anonymously for demo
            await this.auth.signInAnonymously();
            this.currentUser = this.auth.currentUser;
            
            this.initialized = true;
            console.log('[EmbeddedFirebaseService] Initialized successfully');
        } catch (error) {
            console.error('[EmbeddedFirebaseService] Initialization error:', error);
            throw error;
        }
    }

    async getClients() {
        try {
            await this.initialize();
            const snapshot = await this.db.collection('clients').get();
            return snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
        } catch (error) {
            console.error('[EmbeddedFirebaseService] Error getting clients:', error);
            // Return mock data as fallback
            return [
                { id: 'client1', name: 'Demo Client', email: 'demo@example.com' }
            ];
        }
    }

    async getClientGoals(clientId) {
        try {
            await this.initialize();
            const snapshot = await this.db.collection('goals')
                .where('clientId', '==', clientId)
                .get();
            return snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
        } catch (error) {
            console.error('[EmbeddedFirebaseService] Error getting goals:', error);
            // Return mock goals as fallback
            return [{
                id: 'goal1',
                clientId: clientId,
                monthlyRevenue: 50000,
                year: new Date().getFullYear(),
                month: new Date().getMonth()
            }];
        }
    }

    async getClientEvents(clientId) {
        try {
            await this.initialize();
            const snapshot = await this.db.collection('calendar_events')
                .where('clientId', '==', clientId)
                .get();
            return snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
        } catch (error) {
            console.error('[EmbeddedFirebaseService] Error getting events:', error);
            return [];
        }
    }

    async createEvent(eventData) {
        try {
            await this.initialize();
            const docRef = await this.db.collection('calendar_events').add({
                ...eventData,
                createdAt: firebase.firestore.FieldValue.serverTimestamp(),
                userId: this.currentUser?.uid
            });
            return docRef.id;
        } catch (error) {
            console.error('[EmbeddedFirebaseService] Error creating event:', error);
            throw error;
        }
    }

    async updateEvent(eventId, updates) {
        try {
            await this.initialize();
            await this.db.collection('calendar_events').doc(eventId).update({
                ...updates,
                updatedAt: firebase.firestore.FieldValue.serverTimestamp()
            });
            return true;
        } catch (error) {
            console.error('[EmbeddedFirebaseService] Error updating event:', error);
            throw error;
        }
    }

    async deleteEvent(eventId) {
        try {
            await this.initialize();
            await this.db.collection('calendar_events').doc(eventId).delete();
            return true;
        } catch (error) {
            console.error('[EmbeddedFirebaseService] Error deleting event:', error);
            throw error;
        }
    }
}

// Main Calendar Component
function CalendarViewFixed() {
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
    
    // Initialize service as ref to persist across renders
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
            const clientsData = await firebaseService.current.getClients();
            setClients(clientsData);
            
            // Auto-select first client
            if (clientsData.length > 0 && !selectedClient) {
                setSelectedClient(clientsData[0]);
            }
            setError(null);
        } catch (error) {
            console.error('Failed to load clients:', error);
            setError('Failed to load clients. Using demo mode.');
            // Set demo client as fallback
            const demoClient = { id: 'demo', name: 'Demo Client' };
            setClients([demoClient]);
            setSelectedClient(demoClient);
        } finally {
            setLoading(false);
        }
    };

    const loadClientData = async (clientId) => {
        try {
            // Load goals
            const goalsData = await firebaseService.current.getClientGoals(clientId);
            setGoals(goalsData);
            
            // Load events
            const eventsData = await firebaseService.current.getClientEvents(clientId);
            setEvents(eventsData);
            
            // Calculate progress
            calculateGoalProgress(eventsData, goalsData);
        } catch (error) {
            console.error('Failed to load client data:', error);
        }
    };

    const calculateGoalProgress = (events, goals) => {
        const currentYear = currentMonth.getFullYear();
        const currentMonthNum = currentMonth.getMonth();
        
        // Find goal for current month
        const monthGoal = goals.find(g => 
            g.year === currentYear && g.month === currentMonthNum
        );
        
        if (!monthGoal) {
            setGoalProgress(null);
            return;
        }
        
        // Calculate revenue from events
        const monthEvents = events.filter(e => {
            const eventDate = new Date(e.date);
            return eventDate.getFullYear() === currentYear && 
                   eventDate.getMonth() === currentMonthNum;
        });
        
        let totalRevenue = 0;
        monthEvents.forEach(event => {
            const baseRevenue = 500; // Base revenue per campaign
            const multiplier = getCampaignMultiplier(event.title);
            totalRevenue += baseRevenue * multiplier;
        });
        
        const progress = {
            goal: monthGoal.monthlyRevenue,
            current: totalRevenue,
            percentage: (totalRevenue / monthGoal.monthlyRevenue) * 100,
            status: getGoalStatus(totalRevenue, monthGoal.monthlyRevenue),
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
            if (eventData.id) {
                await firebaseService.current.updateEvent(eventData.id, eventData);
            } else {
                await firebaseService.current.createEvent({
                    ...eventData,
                    clientId: selectedClient.id,
                    date: eventData.date
                });
            }
            await loadClientData(selectedClient.id);
            setShowEventModal(false);
            return true;
        } catch (error) {
            console.error('Error saving event:', error);
            return false;
        }
    };

    const handleDeleteEvent = async (eventId) => {
        try {
            await firebaseService.current.deleteEvent(eventId);
            await loadClientData(selectedClient.id);
            setShowEventModal(false);
            return true;
        } catch (error) {
            console.error('Error deleting event:', error);
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
                            Calendar component loading...
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

            {/* Error Display */}
            {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-red-700">{error}</p>
                </div>
            )}
        </div>
    );
}

// Register component globally
window.CalendarViewFixed = CalendarViewFixed;