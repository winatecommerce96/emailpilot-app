// CalendarViewFirebase - Drop-in Firebase Calendar for React
const { useState, useEffect } = React;

// Firebase initialization (assumes Firebase is loaded globally)
function initializeFirebase() {
    if (typeof firebase !== 'undefined' && !firebase.apps.length) {
        const firebaseConfig = {
            apiKey: "AIzaSyB0RrH7hbER2R-SzXfNmFe0O32HhH7HBEM",
            authDomain: "emailpilot-438321.firebaseapp.com",
            projectId: "emailpilot-438321",
            storageBucket: "emailpilot-438321.appspot.com",
            messagingSenderId: "104067375141",
            appId: "1:104067375141:web:2b65c86eec8e8c8b4c9f3a"
        };
        firebase.initializeApp(firebaseConfig);
    }
    return firebase.firestore();
}

const CAMPAIGN_COLORS = {
    'RRB Promotion': 'bg-red-300 text-red-800',
    'Cheese Club': 'bg-green-200 text-green-800',
    'Nurturing/Education': 'bg-blue-200 text-blue-800',
    'Community/Lifestyle': 'bg-purple-200 text-purple-800',
    'Re-engagement': 'bg-yellow-200 text-yellow-800',
    'SMS Alert': 'bg-orange-300 text-orange-800',
    'default': 'bg-gray-200 text-gray-800'
};

function CalendarViewFirebase() {
    const [clients, setClients] = useState([]);
    const [selectedClient, setSelectedClient] = useState(null);
    const [goals, setGoals] = useState([]);
    const [campaigns, setCampaigns] = useState({});
    const [currentDate, setCurrentDate] = useState(new Date(2025, 8, 1));
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [db, setDb] = useState(null);

    // Initialize Firebase and load data
    useEffect(() => {
        const initializeAndLoad = async () => {
            try {
                setLoading(true);
                
                // Initialize Firebase
                const database = initializeFirebase();
                setDb(database);
                
                // Sign in anonymously
                await firebase.auth().signInAnonymously();
                
                // Load clients
                const snapshot = await database.collection('clients').get();
                const clientsData = [];
                snapshot.forEach(doc => {
                    clientsData.push({ id: doc.id, ...doc.data() });
                });
                
                setClients(clientsData);
                
                if (clientsData.length > 0) {
                    const firstClient = clientsData[0];
                    setSelectedClient(firstClient);
                    await loadClientData(database, firstClient.id);
                }
                
                setError(null);
            } catch (err) {
                console.error('Firebase initialization error:', err);
                setError(`Failed to initialize: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };

        initializeAndLoad();
    }, []);

    const loadClientData = async (database, clientId) => {
        try {
            // Load campaign data
            const clientDoc = await database.collection('clients').doc(clientId).get();
            const campaignData = clientDoc.exists ? (clientDoc.data().campaignData || {}) : {};
            setCampaigns(campaignData);

            // Load goals (with error handling for missing index)
            try {
                const goalsSnapshot = await database.collection('goals')
                    .where('client_id', '==', clientId)
                    .get();
                
                const goalsData = [];
                goalsSnapshot.forEach(doc => {
                    goalsData.push({ id: doc.id, ...doc.data() });
                });
                setGoals(goalsData);
            } catch (goalsError) {
                console.log('Goals query needs index:', goalsError.message);
                setGoals([]);
            }
        } catch (err) {
            console.error('Error loading client data:', err);
        }
    };

    const handleClientChange = async (clientId) => {
        const client = clients.find(c => c.id === clientId);
        setSelectedClient(client);
        if (client && db) {
            await loadClientData(db, client.id);
        }
    };

    const createClient = async () => {
        if (!db) return;
        
        const name = prompt('Enter client name:');
        if (name && name.trim()) {
            try {
                const clientId = name.toLowerCase().replace(/\s+/g, '-') + '-' + Date.now();
                await db.collection('clients').doc(clientId).set({
                    name: name.trim(),
                    campaignData: {},
                    created: new Date().toISOString()
                });
                
                // Reload clients
                const snapshot = await db.collection('clients').get();
                const clientsData = [];
                snapshot.forEach(doc => {
                    clientsData.push({ id: doc.id, ...doc.data() });
                });
                
                setClients(clientsData);
                const newClient = { id: clientId, name: name.trim() };
                setSelectedClient(newClient);
                await loadClientData(db, clientId);
            } catch (err) {
                alert(`Failed to create client: ${err.message}`);
            }
        }
    };

    const generateCalendarDays = () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        const firstDay = new Date(year, month, 1);
        const startDate = new Date(firstDay);
        startDate.setDate(startDate.getDate() - firstDay.getDay());
        
        const days = [];
        const currentDay = new Date(startDate);
        
        for (let i = 0; i < 42; i++) {
            const dateString = currentDay.toISOString().split('T')[0];
            const isCurrentMonth = currentDay.getMonth() === month;
            const dayEvents = Object.entries(campaigns).filter(([id, campaign]) => campaign.date === dateString);
            
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

    const handleEventClick = (eventId, eventData) => {
        const newTitle = prompt('Edit campaign title:', eventData.title);
        if (newTitle !== null && newTitle.trim() && db && selectedClient) {
            const updatedCampaigns = {
                ...campaigns,
                [eventId]: {
                    ...eventData,
                    title: newTitle.trim()
                }
            };
            
            setCampaigns(updatedCampaigns);
            
            // Save to Firebase
            db.collection('clients').doc(selectedClient.id).set({
                name: selectedClient.name,
                campaignData: updatedCampaigns,
                lastModified: new Date().toISOString()
            }, { merge: true }).catch(err => {
                console.error('Save error:', err);
                setCampaigns(campaigns); // Revert on error
            });
        }
    };

    const handleDayClick = (dateString) => {
        const title = prompt('Enter campaign title:');
        if (title && title.trim() && db && selectedClient) {
            const eventId = 'event-' + Date.now();
            const campaignType = detectCampaignType(title);
            
            const updatedCampaigns = {
                ...campaigns,
                [eventId]: {
                    date: dateString,
                    title: title.trim(),
                    content: '',
                    color: CAMPAIGN_COLORS[campaignType] || CAMPAIGN_COLORS.default
                }
            };
            
            setCampaigns(updatedCampaigns);
            
            // Save to Firebase
            db.collection('clients').doc(selectedClient.id).set({
                name: selectedClient.name,
                campaignData: updatedCampaigns,
                lastModified: new Date().toISOString()
            }, { merge: true }).catch(err => {
                console.error('Save error:', err);
                setCampaigns(campaigns); // Revert on error
            });
        }
    };

    const detectCampaignType = (title) => {
        const text = title.toLowerCase();
        if (text.includes('rrb') || text.includes('promotion')) return 'RRB Promotion';
        if (text.includes('cheese club')) return 'Cheese Club';
        if (text.includes('nurturing') || text.includes('education')) return 'Nurturing/Education';
        if (text.includes('community') || text.includes('lifestyle')) return 'Community/Lifestyle';
        if (text.includes('re-engagement')) return 'Re-engagement';
        if (text.includes('sms')) return 'SMS Alert';
        return 'default';
    };

    const calendarDays = generateCalendarDays();

    // Goals Dashboard Component
    const GoalsDashboard = () => {
        if (!goals.length) return null;

        const currentMonthGoal = goals.find(g => 
            g.year === currentDate.getFullYear() && 
            g.month === currentDate.getMonth() + 1
        );

        const currentMonthCampaigns = Object.values(campaigns).filter(campaign => {
            const campaignDate = new Date(campaign.date);
            return campaignDate.getMonth() === currentDate.getMonth() && 
                   campaignDate.getFullYear() === currentDate.getFullYear();
        });

        const estimatedRevenue = currentMonthCampaigns.length * 500;

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
                        <div className="bg-gray-200 rounded-full h-2 mb-3">
                            <div 
                                className="bg-gradient-to-r from-blue-500 to-green-500 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${Math.min((estimatedRevenue / (currentMonthGoal.revenue_goal || 1)) * 100, 100)}%` }}
                            ></div>
                        </div>
                        <p className="text-sm text-gray-600">
                            Campaigns scheduled: {currentMonthCampaigns.length}
                        </p>
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
                    <p className="text-xs text-gray-500">
                        Make sure Firebase SDK is loaded in your app
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
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
                        <button
                            onClick={createClient}
                            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
                        >
                            Add Client
                        </button>
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
                                        className={`border border-gray-200 min-h-[120px] p-1 relative cursor-pointer ${
                                            day.isCurrentMonth 
                                                ? 'bg-white hover:bg-gray-50' 
                                                : 'bg-gray-50 text-gray-400'
                                        }`}
                                        onClick={() => handleDayClick(day.dateString)}
                                    >
                                        <div className="text-sm font-medium mb-1">
                                            {day.dayNumber}
                                        </div>
                                        <div className="space-y-1">
                                            {day.events.map(([eventId, event]) => (
                                                <div
                                                    key={eventId}
                                                    className={`${event.color || 'bg-gray-200 text-gray-800'} text-xs px-2 py-1 rounded cursor-pointer hover:shadow-md transition-all duration-200 truncate`}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleEventClick(eventId, event);
                                                    }}
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

                    {/* Firebase Status */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-center">
                            <div className="text-green-600 mr-2">✅</div>
                            <div>
                                <h4 className="text-sm font-medium text-green-900">Firebase Integration Active</h4>
                                <p className="text-xs text-green-700 mt-1">
                                    Connected to EmailPilot project (emailpilot-438321) • 
                                    {Object.keys(campaigns).length} campaigns loaded • 
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
                    <button
                        onClick={createClient}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                    >
                        Create First Client
                    </button>
                </div>
            )}
        </div>
    );
}

// Make available globally
window.CalendarViewFirebase = CalendarViewFirebase;