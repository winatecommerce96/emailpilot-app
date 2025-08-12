// Enhanced CalendarView Component - Deep Firebase Integration for EmailPilot
const { useState, useEffect } = React;

// Firebase Calendar Service (inline for React)
class FirebaseCalendarServiceInline {
    constructor() {
        this.db = null;
        this.auth = null;
        this.initialized = false;
        this.firebaseConfig = {
            apiKey: "AIzaSyB0RrH7hbER2R-SzXfNmFe0O32HhH7HBEM",
            authDomain: "emailpilot-438321.firebaseapp.com",
            projectId: "emailpilot-438321",
            storageBucket: "emailpilot-438321.appspot.com",
            messagingSenderId: "104067375141",
            appId: "1:104067375141:web:2b65c86eec8e8c8b4c9f3a"
        };
    }

    async initialize() {
        if (this.initialized) return true;

        try {
            // Firebase is loaded via CDN in the main app
            if (typeof firebase !== 'undefined') {
                // Initialize Firebase if not already done
                if (!firebase.apps.length) {
                    firebase.initializeApp(this.firebaseConfig);
                }
                
                this.db = firebase.firestore();
                await firebase.auth().signInAnonymously();
                this.initialized = true;
                console.log('Firebase Calendar Service initialized');
                return true;
            } else {
                console.error('Firebase not available - please ensure Firebase SDK is loaded');
                return false;
            }
        } catch (error) {
            console.error('Error initializing Firebase Calendar Service:', error);
            return false;
        }
    }

    async getClients() {
        if (!this.initialized) await this.initialize();
        
        try {
            const snapshot = await this.db.collection('clients').get();
            const clients = [];
            snapshot.forEach(doc => {
                clients.push({ id: doc.id, ...doc.data() });
            });
            return clients;
        } catch (error) {
            console.error('Error fetching clients:', error);
            return [];
        }
    }

    async getClientData(clientId) {
        if (!this.initialized) await this.initialize();
        
        try {
            const doc = await this.db.collection('clients').doc(clientId).get();
            return doc.exists ? doc.data() : null;
        } catch (error) {
            console.error('Error fetching client data:', error);
            return null;
        }
    }

    async saveClientData(clientId, data) {
        if (!this.initialized) await this.initialize();
        
        try {
            await this.db.collection('clients').doc(clientId).set({
                ...data,
                lastModified: new Date().toISOString()
            }, { merge: true });
            return true;
        } catch (error) {
            console.error('Error saving client data:', error);
            return false;
        }
    }

    async getClientGoals(clientId) {
        if (!this.initialized) await this.initialize();
        
        try {
            const snapshot = await this.db.collection('goals')
                .where('client_id', '==', clientId)
                .orderBy('created_at', 'desc')
                .get();
            
            const goals = [];
            snapshot.forEach(doc => {
                goals.push({ id: doc.id, ...doc.data() });
            });
            return goals;
        } catch (error) {
            console.error('Error fetching goals (may need Firebase index):', error);
            return [];
        }
    }
}

// Initialize service
const firebaseService = new FirebaseCalendarServiceInline();

// Campaign colors
const CAMPAIGN_COLORS = {
    'RRB Promotion': 'bg-red-300 text-red-800',
    'Cheese Club': 'bg-green-200 text-green-800',
    'Nurturing/Education': 'bg-blue-200 text-blue-800',
    'Community/Lifestyle': 'bg-purple-200 text-purple-800',
    'Re-engagement': 'bg-yellow-200 text-yellow-800',
    'SMS Alert': 'bg-orange-300 text-orange-800',
    'default': 'bg-gray-200 text-gray-800'
};

function CalendarViewEnhanced() {
    const [clients, setClients] = useState([]);
    const [selectedClient, setSelectedClient] = useState(null);
    const [goals, setGoals] = useState([]);
    const [campaigns, setCampaigns] = useState({});
    const [currentDate, setCurrentDate] = useState(new Date(2025, 8, 1));
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Initialize on mount
    useEffect(() => {
        loadClients();
    }, []);

    const loadClients = async () => {
        try {
            setLoading(true);
            await firebaseService.initialize();
            const clientsData = await firebaseService.getClients();
            setClients(clientsData);
            
            if (clientsData.length > 0) {
                const firstClient = clientsData[0];
                setSelectedClient(firstClient);
                await loadClientData(firstClient.id);
            }
            setError(null);
        } catch (error) {
            console.error('Failed to load clients:', error);
            setError(`Failed to load clients: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const loadClientData = async (clientId) => {
        try {
            // Load campaigns
            const clientData = await firebaseService.getClientData(clientId);
            const campaignData = clientData?.campaignData || {};
            setCampaigns(campaignData);
            
            // Convert to events array
            const eventsArray = Object.entries(campaignData).map(([id, data]) => ({
                id,
                ...data,
                event_date: data.date
            }));
            setEvents(eventsArray);

            // Load goals
            const goals = await firebaseService.getClientGoals(clientId);
            setGoals(goals);
        } catch (error) {
            console.error('Error loading client data:', error);
        }
    };

    const handleClientChange = async (clientId) => {
        const client = clients.find(c => c.id === clientId);
        setSelectedClient(client);
        if (client) {
            await loadClientData(client.id);
        }
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

    // Goals dashboard component
    const GoalsDashboard = () => {
        if (!goals.length) return null;

        const currentMonthGoal = goals.find(g => 
            g.year === currentDate.getFullYear() && 
            g.month === currentDate.getMonth() + 1
        );

        const currentMonthCampaigns = Object.entries(campaigns).filter(([id, campaign]) => {
            const campaignDate = new Date(campaign.date);
            return campaignDate.getMonth() === currentDate.getMonth() && 
                   campaignDate.getFullYear() === currentDate.getFullYear();
        });

        const estimatedRevenue = currentMonthCampaigns.length * 500; // Simple estimation

        return (
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
                <h2 className="text-xl font-bold text-gray-800 mb-4">Revenue Goals & Progress</h2>
                
                {currentMonthGoal ? (
                    <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex justify-between items-start mb-3">
                            <div>
                                <h3 className="font-semibold text-gray-900">
                                    {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })} Goal
                                </h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    Target: ${currentMonthGoal.revenue_goal?.toLocaleString() || '0'} | 
                                    Estimated: ${estimatedRevenue.toLocaleString()}
                                </p>
                            </div>
                            <div className="text-right">
                                <span className="text-2xl font-bold text-blue-600">
                                    {Math.round((estimatedRevenue / (currentMonthGoal.revenue_goal || 1)) * 100)}%
                                </span>
                            </div>
                        </div>
                        <div className="text-sm text-gray-600">
                            <p>Campaigns scheduled: {currentMonthCampaigns.length}</p>
                        </div>
                    </div>
                ) : (
                    <p className="text-gray-500">No goals set for this month</p>
                )}
            </div>
        );
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    <p className="mt-2 text-sm text-gray-500">Loading Firebase calendar...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-center">
                    <div className="text-red-600 mb-4">❌ Error Loading Calendar</div>
                    <p className="text-sm text-gray-600 mb-4">{error}</p>
                    <button 
                        onClick={loadClients}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header with Client Selection */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Firebase Campaign Calendar</h2>
                
                {clients.length > 0 && (
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
                )}
            </div>

            {selectedClient && (
                <>
                    {/* Goals Dashboard */}
                    <GoalsDashboard />

                    {/* Calendar */}
                    <div className="bg-white rounded-xl shadow-lg">
                        {/* Calendar Header */}
                        <div className="p-6 border-b border-gray-200">
                            <div className="flex justify-between items-center">
                                <h1 className="text-2xl font-bold text-gray-800">
                                    {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                                </h1>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => {
                                            const newDate = new Date(currentDate);
                                            newDate.setMonth(newDate.getMonth() - 1);
                                            setCurrentDate(newDate);
                                        }}
                                        className="p-2 rounded-full text-gray-500 hover:bg-gray-100"
                                    >
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path>
                                        </svg>
                                    </button>
                                    <button
                                        onClick={() => {
                                            const newDate = new Date(currentDate);
                                            newDate.setMonth(newDate.getMonth() + 1);
                                            setCurrentDate(newDate);
                                        }}
                                        className="p-2 rounded-full text-gray-500 hover:bg-gray-100"
                                    >
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>

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
                                    <div
                                        key={index}
                                        className={`border border-gray-200 min-h-[120px] p-1 relative ${
                                            day.isCurrentMonth 
                                                ? 'bg-white hover:bg-gray-50' 
                                                : 'bg-gray-50 text-gray-400'
                                        }`}
                                    >
                                        <div className="text-sm font-medium mb-1">
                                            {day.dayNumber}
                                        </div>
                                        <div className="space-y-1">
                                            {day.events.map(event => (
                                                <div
                                                    key={event.id}
                                                    className={`${event.color || 'bg-gray-200 text-gray-800'} text-xs px-2 py-1 rounded cursor-pointer hover:shadow-md transition-all duration-200 truncate`}
                                                    title={event.title}
                                                >
                                                    {event.title}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Firebase Integration Status */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-center">
                            <div className="text-green-600 mr-2">✅</div>
                            <div>
                                <h4 className="text-sm font-medium text-green-900">Firebase Integration Active</h4>
                                <p className="text-xs text-green-700 mt-1">
                                    Connected to EmailPilot project (emailpilot-438321) • 
                                    {events.length} campaigns loaded • 
                                    {goals.length} goals available
                                </p>
                            </div>
                        </div>
                    </div>
                </>
            )}

            {clients.length === 0 && !loading && (
                <div className="text-center py-12">
                    <div className="text-gray-500 mb-4">No clients found in Firebase</div>
                    <p className="text-sm text-gray-400">
                        Please add clients to the Firebase 'clients' collection to use the calendar.
                    </p>
                </div>
            )}
        </div>
    );
}

// Make available globally
window.CalendarViewEnhanced = CalendarViewEnhanced;