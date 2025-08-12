// EmailPilot React Application
const { useState, useEffect } = React;

// API Configuration
// In production, the API is served from the same domain
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8080' 
    : window.location.origin; // Use the same origin as the frontend

// Make API_BASE_URL available globally for components
window.API_BASE_URL = API_BASE_URL;

// Calendar wrapper component that waits for CalendarView to load
function CalendarWrapper() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [retryCount, setRetryCount] = useState(0);
    
    useEffect(() => {
        let checkCount = 0;
        // Check if CalendarView is loaded
        const checkInterval = setInterval(() => {
            checkCount++;
            if (window.CalendarView) {
                setIsLoaded(true);
                clearInterval(checkInterval);
            } else if (checkCount > 30) { // Stop after 3 seconds
                clearInterval(checkInterval);
                setRetryCount(prev => prev + 1);
            }
        }, 100);
        
        // Cleanup
        return () => clearInterval(checkInterval);
    }, [retryCount]);
    
    if (!isLoaded && retryCount < 3) {
        return (
            <div className="p-8 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                <p className="text-sm text-gray-600">Loading Calendar components... (attempt {retryCount + 1})</p>
            </div>
        );
    }
    
    if (!isLoaded) {
        // Fallback: Use simple calendar if available
        if (window.CalendarViewSimple) {
            return <window.CalendarViewSimple />;
        }
        
        return (
            <div className="p-8">
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <h3 className="text-lg font-semibold text-yellow-800 mb-2">Calendar Loading Issue</h3>
                    <p className="text-sm text-yellow-700 mb-4">
                        The calendar components are having trouble loading. This might be due to:
                    </p>
                    <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1 mb-4">
                        <li>Script loading order issues</li>
                        <li>Network connectivity problems</li>
                        <li>Browser compatibility</li>
                    </ul>
                    <div className="flex gap-4">
                        <button 
                            onClick={() => window.location.reload()}
                            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                        >
                            Reload Page
                        </button>
                        <button 
                            onClick={() => setRetryCount(0)}
                            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
                <div className="mt-4 text-xs text-gray-500">
                    <p>Debug: Components loaded:</p>
                    <ul>
                        <li>CalendarViewSimple: {window.CalendarViewSimple ? '✅' : '❌'}</li>
                        <li>CalendarView: {window.CalendarView ? '✅' : '❌'}</li>
                        <li>Calendar: {window.Calendar ? '✅' : '❌'}</li>
                        <li>EventModal: {window.EventModal ? '✅' : '❌'}</li>
                        <li>CalendarChat: {window.CalendarChat ? '✅' : '❌'}</li>
                    </ul>
                </div>
            </div>
        );
    }
    
    return <window.CalendarView />;
}

// Main App Component
function App() {
    const [user, setUser] = useState(null);
    const [currentView, setCurrentView] = useState('dashboard');
    const [loading, setLoading] = useState(false);

    // Google OAuth login function
    const loginWithGoogle = async (googleUser) => {
        try {
            setLoading(true);
            const response = await axios.post(`${API_BASE_URL}/api/auth/google/callback`, {
                email: googleUser.email,
                name: googleUser.name,
                picture: googleUser.picture
            });
            
            const { user: userData } = response.data;
            setUser(userData);
            
        } catch (error) {
            alert('Login failed: ' + (error.response?.data?.detail || 'Unknown error'));
        } finally {
            setLoading(false);
        }
    };

    // Check for existing session on load
    useEffect(() => {
        axios.get(`${API_BASE_URL}/api/auth/me`, { withCredentials: true })
            .then(response => setUser(response.data))
            .catch(() => {
                // No active session
            });
    }, []);

    if (!user) {
        return <LoginScreen onGoogleLogin={loginWithGoogle} loading={loading} />;
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <Navigation 
                user={user} 
                currentView={currentView}
                onViewChange={setCurrentView}
                onLogout={async () => {
                    await axios.post(`${API_BASE_URL}/api/auth/logout`, {}, { withCredentials: true });
                    setUser(null);
                }}
            />
            <main className="container mx-auto px-4 py-8">
                {currentView === 'dashboard' && <Dashboard onViewChange={setCurrentView} />}
                {currentView === 'reports' && <ReportsView />}
                {currentView === 'goals' && <GoalsView />}
                {currentView === 'clients' && <ClientsView />}
                {currentView === 'calendar' && <CalendarWrapper />}
                {currentView === 'admin' && <AdminView user={user} />}
            </main>
        </div>
    );
}

// Login Screen Component with Google OAuth
function LoginScreen({ onGoogleLogin, loading }) {
    const handleGoogleLogin = () => {
        // Simple demo - in production you'd use Google OAuth library
        const mockGoogleUser = {
            email: prompt("Enter your email to simulate Google login:"),
            name: "Demo User",
            picture: ""
        };
        
        if (mockGoogleUser.email) {
            onGoogleLogin(mockGoogleUser);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 to-purple-900">
            <div className="bg-white p-8 rounded-lg shadow-xl w-96">
                <div className="text-center mb-8">
                    <img 
                        src="/logo2.png" 
                        alt="EmailPilot Logo" 
                        className="w-auto mx-auto mb-4"
                        style={{height: '140px'}}
                        onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'block';
                        }}
                    />
                    <div style={{display: 'none'}}>
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">EmailPilot</h1>
                        <p className="text-gray-600">Klaviyo Automation Platform</p>
                    </div>
                </div>
                
                <div className="space-y-6">
                    <button
                        onClick={handleGoogleLogin}
                        disabled={loading}
                        className="w-full bg-red-600 text-white py-3 px-4 rounded-md hover:bg-red-700 focus:ring-2 focus:ring-red-500 disabled:opacity-50 flex items-center justify-center space-x-2"
                    >
                        <svg className="w-5 h-5" viewBox="0 0 24 24">
                            <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        <span>{loading ? 'Signing in...' : 'Continue with Google'}</span>
                    </button>
                </div>
                
                <div className="mt-6 text-xs text-gray-500 text-center">
                    <p className="mb-2">Approved emails only:</p>
                    <p>• damon@winatecommerce.com</p>
                    <p>• admin@emailpilot.ai</p>
                    <p className="mt-2 text-blue-600">Contact admin to add your email</p>
                </div>
            </div>
        </div>
    );
}

// Navigation Component
function Navigation({ user, currentView, onViewChange, onLogout }) {
    return (
        <nav className="animated-gradient-nav shadow-lg">
            <div className="container mx-auto px-4">
                <div className="flex justify-between items-center" style={{minHeight: '180px', paddingTop: '10px', paddingBottom: '10px'}}>
                    <div className="flex items-center space-x-8">
                        <div className="flex items-center">
                            <img 
                                src="https://storage.googleapis.com/emailpilot-438321-public/logo.png" 
                                alt="EmailPilot Logo" 
                                style={{height: '160px !important', width: '160px !important', objectFit: 'contain', minHeight: '160px', minWidth: '160px', maxWidth: 'none !important'}}
                                onError={(e) => {
                                    e.target.style.display = 'none';
                                    e.target.nextSibling.style.display = 'block';
                                }}
                            />
                            <h1 className="text-xl font-bold text-white" style={{display: 'none'}}>EmailPilot</h1>
                        </div>
                        
                        <div className="flex space-x-4">
                            <NavItem 
                                label="Dashboard" 
                                active={currentView === 'dashboard'}
                                onClick={() => onViewChange('dashboard')}
                            />
                            <NavItem 
                                label="Reports" 
                                active={currentView === 'reports'}
                                onClick={() => onViewChange('reports')}
                            />
                            <NavItem 
                                label="Goals" 
                                active={currentView === 'goals'}
                                onClick={() => onViewChange('goals')}
                            />
                            <NavItem 
                                label="Clients" 
                                active={currentView === 'clients'}
                                onClick={() => onViewChange('clients')}
                            />
                            <NavItem 
                                label="Calendar" 
                                active={currentView === 'calendar'}
                                onClick={() => onViewChange('calendar')}
                            />
                            {user.email === 'damon@winatecommerce.com' || user.email === 'admin@emailpilot.ai' ? (
                                <NavItem 
                                    label="Admin" 
                                    active={currentView === 'admin'}
                                    onClick={() => onViewChange('admin')}
                                />
                            ) : null}
                        </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                        <span className="text-white">Hello, {user.name}</span>
                        <button
                            onClick={onLogout}
                            className="text-white hover:bg-white hover:bg-opacity-20 px-3 py-1 rounded transition-all"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    );
}

// Navigation Item Component
function NavItem({ label, active, onClick }) {
    return (
        <button
            onClick={onClick}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-all ${
                active 
                    ? 'bg-white bg-opacity-30 text-white' 
                    : 'text-white text-opacity-80 hover:text-white hover:bg-white hover:bg-opacity-20'
            }`}
        >
            {label}
        </button>
    );
}

// Dashboard Component
function Dashboard({ onViewChange }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Simulate API call
        setTimeout(() => {
            setStats({
                totalClients: 7,
                activeReports: 12,
                monthlyGoals: 84,
                lastReportDate: '2025-08-07'
            });
            setLoading(false);
        }, 1000);
    }, []);

    if (loading) {
        return <div className="text-center py-8">Loading dashboard...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
                <div className="flex space-x-4">
                    <ActionButton 
                        label="Generate Weekly Report" 
                        onClick={() => generateReport('weekly')}
                        variant="primary"
                    />
                    <ActionButton 
                        label="Generate Monthly Report" 
                        onClick={() => generateReport('monthly')}
                        variant="secondary"
                    />
                </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatCard 
                    title="Total Clients" 
                    value={stats.totalClients} 
                    icon="👥" 
                    onClick={() => onViewChange('clients')}
                    clickable={true}
                />
                <StatCard 
                    title="Active Reports" 
                    value={stats.activeReports} 
                    icon="📊" 
                    onClick={() => onViewChange('reports')}
                    clickable={true}
                />
                <StatCard 
                    title="Monthly Goals" 
                    value={stats.monthlyGoals} 
                    icon="🎯" 
                    onClick={() => onViewChange('goals')}
                    clickable={true}
                />
                <StatCard 
                    title="Last Report" 
                    value={stats.lastReportDate} 
                    icon="📅" 
                    onClick={() => onViewChange('reports')}
                    clickable={true}
                />
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <QuickAction 
                        title="View Goals"
                        description="Manage revenue goals for all clients"
                        icon="🎯"
                        onClick={() => onViewChange('goals')}
                    />
                    <QuickAction 
                        title="Client Reports"
                        description="View performance reports by client"
                        icon="📈"
                        onClick={() => onViewChange('reports')}
                    />
                    <QuickAction 
                        title="Slack Integration"
                        description="Configure Slack notifications"
                        icon="💬"
                        onClick={() => onViewChange('reports')}
                    />
                </div>
            </div>
        </div>
    );
}

// Generate report function
function generateReport(type) {
    const endpoint = type === 'weekly' ? '/api/reports/weekly/generate' : '/api/reports/monthly/generate';
    
    axios.post(`${API_BASE_URL}${endpoint}`, {}, { withCredentials: true })
        .then(response => {
            alert(`${type.charAt(0).toUpperCase() + type.slice(1)} report generation started!`);
        })
        .catch(error => {
            alert('Failed to generate report: ' + (error.response?.data?.detail || 'Unknown error'));
        });
}

// Stat Card Component
function StatCard({ title, value, icon, onClick, clickable = false }) {
    const baseClasses = "bg-white rounded-lg shadow p-6";
    const clickableClasses = clickable 
        ? "cursor-pointer hover:shadow-lg hover:bg-gray-50 transition-all duration-200" 
        : "";
    
    const handleClick = () => {
        if (clickable && onClick) {
            onClick();
        }
    };

    return (
        <div 
            className={`${baseClasses} ${clickableClasses}`}
            onClick={handleClick}
            title={clickable ? `Click to view ${title.toLowerCase()}` : ''}
        >
            <div className="flex items-center">
                <div className="text-2xl mr-4">{icon}</div>
                <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600">{title}</p>
                    <p className="text-2xl font-bold text-gray-900">{value}</p>
                </div>
                {clickable && (
                    <div className="text-gray-400 text-sm">
                        →
                    </div>
                )}
            </div>
        </div>
    );
}

// Quick Action Component
function QuickAction({ title, description, icon, onClick }) {
    return (
        <div 
            className="border rounded-lg p-4 hover:bg-gray-50 hover:border-gray-300 cursor-pointer transition-all duration-200"
            onClick={onClick}
        >
            <div className="text-2xl mb-2">{icon}</div>
            <h4 className="font-semibold text-gray-900 mb-1">{title}</h4>
            <p className="text-sm text-gray-600">{description}</p>
        </div>
    );
}

// Action Button Component
function ActionButton({ label, onClick, variant = 'primary' }) {
    const baseClass = "px-4 py-2 rounded-md font-medium";
    const variants = {
        primary: "bg-blue-600 text-white hover:bg-blue-700",
        secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300"
    };
    
    return (
        <button
            onClick={onClick}
            className={`${baseClass} ${variants[variant]}`}
        >
            {label}
        </button>
    );
}

// Placeholder components for other views
function ReportsView() {
    return (
        <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">Reports</h2>
            <p className="text-gray-600">Reports management coming soon...</p>
        </div>
    );
}

function GoalsView() {
    const [clients, setClients] = useState([]);
    const [selectedClient, setSelectedClient] = useState(null);
    const [clientGoals, setClientGoals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [goalsLoading, setGoalsLoading] = useState(false);
    const [showGoalForm, setShowGoalForm] = useState(false);
    const [editingGoal, setEditingGoal] = useState(null);
    const [viewMode, setViewMode] = useState('enhanced'); // 'enhanced', 'overview', 'client-detail', 'accuracy'
    const [accuracyData, setAccuracyData] = useState(null);
    const [useEnhanced, setUseEnhanced] = useState(true);

    // Load clients with goal summaries
    useEffect(() => {
        loadClientsWithGoals();
    }, []);

    const loadClientsWithGoals = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_BASE_URL}/api/goals/clients`, { 
                withCredentials: true 
            });
            setClients(response.data);
        } catch (error) {
            console.error('Failed to load clients with goals:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadClientGoals = async (clientId) => {
        try {
            setGoalsLoading(true);
            const response = await axios.get(`${API_BASE_URL}/api/goals/${clientId}`, {
                withCredentials: true
            });
            setClientGoals(response.data);
        } catch (error) {
            console.error('Failed to load client goals:', error);
        } finally {
            setGoalsLoading(false);
        }
    };

    const handleClientSelect = (client) => {
        setSelectedClient(client);
        setViewMode('client-detail');
        loadClientGoals(client.id);
    };

    const loadAccuracyData = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_BASE_URL}/api/goals/accuracy/comparison`, {
                withCredentials: true
            });
            setAccuracyData(response.data);
            setViewMode('accuracy');
        } catch (error) {
            console.error('Failed to load accuracy data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleBackToOverview = () => {
        setViewMode('overview');
        setSelectedClient(null);
        setClientGoals([]);
    };

    const handleAddGoal = () => {
        setEditingGoal(null);
        setShowGoalForm(true);
    };

    const handleEditGoal = (goal) => {
        setEditingGoal(goal);
        setShowGoalForm(true);
    };

    if (loading) {
        return <div className="text-center py-8">Loading goals data...</div>;
    }

    // Company-Wide Goals Dashboard View (Default)
    if (viewMode === 'enhanced' && window.GoalsCompanyDashboard) {
        return (
            <div className="space-y-6">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Goals & Performance Dashboard</h2>
                        <p className="text-gray-600 mt-1">Company-wide view with all clients' MTD performance</p>
                    </div>
                    <div className="flex space-x-2">
                        <button
                            onClick={() => setViewMode('single-client')}
                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                        >
                            Single Client View
                        </button>
                        <button
                            onClick={() => setViewMode('overview')}
                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                        >
                            Classic View
                        </button>
                    </div>
                </div>
                <window.GoalsCompanyDashboard
                    user={{ email: 'user@emailpilot.ai' }}
                    authToken={'session'}
                />
            </div>
        );
    }
    
    // Single Client Enhanced View
    if (viewMode === 'single-client' && window.GoalsEnhancedDashboard) {
        return (
            <div className="space-y-6">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Single Client Goals View</h2>
                        <p className="text-gray-600 mt-1">Detailed view for individual client performance</p>
                    </div>
                    <div className="flex space-x-2">
                        <select 
                            value={selectedClient?.id || ''}
                            onChange={(e) => {
                                const client = clients.find(c => c.id === e.target.value);
                                setSelectedClient(client);
                            }}
                            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Select Client</option>
                            {clients.map(client => (
                                <option key={client.id} value={client.id}>
                                    {client.name}
                                </option>
                            ))}
                        </select>
                        <button
                            onClick={() => setViewMode('enhanced')}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                        >
                            Company View
                        </button>
                        <button
                            onClick={() => setViewMode('overview')}
                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                        >
                            Classic View
                        </button>
                    </div>
                </div>
                {selectedClient ? (
                    <window.GoalsEnhancedDashboard
                        selectedClient={selectedClient}
                        user={{ email: 'user@emailpilot.ai' }}
                        authToken={'session'}
                        onClientChange={setSelectedClient}
                    />
                ) : (
                    <div className="text-center py-16 bg-white rounded-lg shadow">
                        <p className="text-gray-600">Please select a client to view their goals and performance</p>
                    </div>
                )}
            </div>
        );
    }

    if (viewMode === 'client-detail' && selectedClient) {
        return (
            <ClientGoalsDetailView
                client={selectedClient}
                goals={clientGoals}
                loading={goalsLoading}
                onBack={handleBackToOverview}
                onAddGoal={handleAddGoal}
                onEditGoal={handleEditGoal}
                showGoalForm={showGoalForm}
                editingGoal={editingGoal}
                onCloseForm={() => setShowGoalForm(false)}
                onGoalSaved={() => {
                    loadClientGoals(selectedClient.id);
                    setShowGoalForm(false);
                }}
            />
        );
    }

    if (viewMode === 'accuracy' && accuracyData) {
        return (
            <AccuracyComparisonView 
                data={accuracyData}
                onBack={handleBackToOverview}
            />
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Goals Management</h2>
                    <p className="text-gray-600 mt-1">Manage revenue goals for all clients with AI-generated insights</p>
                </div>
                <div className="flex space-x-3">
                    <button
                        onClick={() => setViewMode('overview')}
                        className={`px-4 py-2 rounded-md font-medium ${
                            viewMode === 'overview' 
                                ? 'bg-blue-600 text-white' 
                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                    >
                        Overview
                    </button>
                    <button
                        onClick={loadAccuracyData}
                        className={`px-4 py-2 rounded-md font-medium ${
                            viewMode === 'accuracy' 
                                ? 'bg-orange-600 text-white' 
                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                    >
                        📊 AI vs Human
                    </button>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <div className="text-2xl mr-4">🎯</div>
                        <div>
                            <p className="text-sm font-medium text-gray-600">Total Goals</p>
                            <p className="text-2xl font-bold text-gray-900">
                                {clients.reduce((sum, client) => sum + (client.goals_count || 0), 0)}
                            </p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <div className="text-2xl mr-4">💰</div>
                        <div>
                            <p className="text-sm font-medium text-gray-600">Avg Monthly Target</p>
                            <p className="text-2xl font-bold text-gray-900">
                                ${clients.length > 0 ? Math.round(clients.reduce((sum, client) => sum + (client.avg_goal || 0), 0) / clients.length).toLocaleString() : 0}
                            </p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <div className="text-2xl mr-4">👥</div>
                        <div>
                            <p className="text-sm font-medium text-gray-600">Clients with Goals</p>
                            <p className="text-2xl font-bold text-gray-900">
                                {clients.filter(client => client.goals_count > 0).length}
                            </p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <div className="text-2xl mr-4">🤖</div>
                        <div>
                            <p className="text-sm font-medium text-gray-600">AI Generated</p>
                            <p className="text-2xl font-bold text-blue-600">Active</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Company-wide Goals Chart */}
            <GoalsLineChart clients={clients} viewType="company" />

            {/* Clients Goals Overview */}
            <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900">Goals by Client</h3>
                    <p className="text-sm text-gray-600 mt-1">Click on any client to view detailed monthly goals</p>
                </div>
                <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {clients.map(client => (
                            <ClientGoalCard
                                key={client.id}
                                client={client}
                                onClick={() => handleClientSelect(client)}
                            />
                        ))}
                    </div>
                    {clients.length === 0 && (
                        <div className="text-center py-12">
                            <div className="text-gray-500 mb-4">No client goals found</div>
                            <p className="text-sm text-gray-400">Goals should have been imported during data migration</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function ClientsView() {
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddForm, setShowAddForm] = useState(false);
    const [editingClient, setEditingClient] = useState(null);
    const [selectedClient, setSelectedClient] = useState(null);

    // Load clients
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
        } catch (error) {
            console.error('Failed to load clients:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddClient = () => {
        setShowAddForm(true);
        setEditingClient(null);
    };

    const handleEditClient = (client) => {
        setEditingClient(client);
        setShowAddForm(true);
    };

    const handleViewClient = async (clientId) => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/clients/${clientId}`, {
                withCredentials: true
            });
            setSelectedClient(response.data);
        } catch (error) {
            console.error('Failed to load client details:', error);
        }
    };

    const handleDeactivateClient = async (clientId) => {
        if (confirm('Are you sure you want to deactivate this client?')) {
            try {
                await axios.delete(`${API_BASE_URL}/api/clients/${clientId}`, {
                    withCredentials: true
                });
                loadClients(); // Refresh list
                alert('Client deactivated successfully');
            } catch (error) {
                alert('Failed to deactivate client: ' + (error.response?.data?.detail || 'Unknown error'));
            }
        }
    };

    if (loading) {
        return <div className="text-center py-8">Loading clients...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Clients</h2>
                <button
                    onClick={handleAddClient}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                    Add New Client
                </button>
            </div>

            {/* Clients Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {clients.map(client => (
                    <ClientCard
                        key={client.id}
                        client={client}
                        onEdit={handleEditClient}
                        onView={handleViewClient}
                        onDeactivate={handleDeactivateClient}
                    />
                ))}
            </div>

            {clients.length === 0 && (
                <div className="text-center py-12">
                    <div className="text-gray-500 mb-4">No clients found</div>
                    <button
                        onClick={handleAddClient}
                        className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                    >
                        Add Your First Client
                    </button>
                </div>
            )}

            {/* Add/Edit Client Modal */}
            {showAddForm && (
                <ClientForm
                    client={editingClient}
                    onClose={() => setShowAddForm(false)}
                    onSave={() => {
                        loadClients();
                        setShowAddForm(false);
                    }}
                />
            )}

            {/* Client Details Modal */}
            {selectedClient && (
                <ClientDetailsModal
                    client={selectedClient}
                    onClose={() => setSelectedClient(null)}
                />
            )}
        </div>
    );
}

// Client Card Component
function ClientCard({ client, onEdit, onView, onDeactivate }) {
    return (
        <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6">
            <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-semibold text-gray-900">{client.name}</h3>
                <div className="flex space-x-2">
                    <button
                        onClick={() => onView(client.id)}
                        className="text-blue-600 hover:text-blue-800"
                        title="View Details"
                    >
                        👁️
                    </button>
                    <button
                        onClick={() => onEdit(client)}
                        className="text-green-600 hover:text-green-800"
                        title="Edit Client"
                    >
                        ✏️
                    </button>
                    <button
                        onClick={() => onDeactivate(client.id)}
                        className="text-red-600 hover:text-red-800"
                        title="Deactivate Client"
                    >
                        🗑️
                    </button>
                </div>
            </div>
            
            <div className="space-y-2 text-sm text-gray-600">
                <div className="flex justify-between">
                    <span>Status:</span>
                    <span className={`px-2 py-1 rounded-full text-xs ${
                        client.is_active 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                    }`}>
                        {client.is_active ? 'Active' : 'Inactive'}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span>Metric ID:</span>
                    <span>{client.metric_id || 'Not set'}</span>
                </div>
                <div className="flex justify-between">
                    <span>Created:</span>
                    <span>{new Date(client.created_at).toLocaleDateString()}</span>
                </div>
            </div>
        </div>
    );
}

// Client Form Component (Modal)
function ClientForm({ client, onClose, onSave }) {
    const [formData, setFormData] = useState({
        name: client?.name || '',
        metric_id: client?.metric_id || '',
        is_active: client?.is_active ?? true
    });
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);

        try {
            if (client) {
                // Update existing client
                await axios.put(
                    `${API_BASE_URL}/api/clients/${client.id}`, 
                    formData,
                    { withCredentials: true }
                );
                alert('Client updated successfully');
            } else {
                // Create new client
                await axios.post(
                    `${API_BASE_URL}/api/clients/`, 
                    formData,
                    { withCredentials: true }
                );
                alert('Client created successfully');
            }
            onSave();
        } catch (error) {
            alert('Failed to save client: ' + (error.response?.data?.detail || 'Unknown error'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">
                        {client ? 'Edit Client' : 'Add New Client'}
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        ✕
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Client Name *
                        </label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({...formData, name: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Klaviyo Metric ID
                        </label>
                        <input
                            type="text"
                            value={formData.metric_id}
                            onChange={(e) => setFormData({...formData, metric_id: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            placeholder="e.g., metric_12345"
                        />
                    </div>

                    {client && (
                        <div className="flex items-center">
                            <input
                                type="checkbox"
                                id="is_active"
                                checked={formData.is_active}
                                onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                                className="mr-2"
                            />
                            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                                Active
                            </label>
                        </div>
                    )}

                    <div className="flex justify-end space-x-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// Client Details Modal
function ClientDetailsModal({ client, onClose }) {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-96 overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">{client.name} - Details</h3>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        ✕
                    </button>
                </div>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-500">Status</label>
                            <div className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                                client.is_active 
                                    ? 'bg-green-100 text-green-800' 
                                    : 'bg-red-100 text-red-800'
                            }`}>
                                {client.is_active ? 'Active' : 'Inactive'}
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-500">Metric ID</label>
                            <div className="text-sm text-gray-900">{client.metric_id || 'Not set'}</div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-500">Created At</label>
                            <div className="text-sm text-gray-900">
                                {new Date(client.created_at).toLocaleString()}
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-500">Updated At</label>
                            <div className="text-sm text-gray-900">
                                {new Date(client.updated_at).toLocaleString()}
                            </div>
                        </div>
                    </div>

                    {client.stats && (
                        <div className="border-t pt-4">
                            <h4 className="text-md font-medium text-gray-900 mb-3">Statistics</h4>
                            <div className="grid grid-cols-3 gap-4">
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-blue-600">{client.stats.goals_count}</div>
                                    <div className="text-sm text-gray-500">Goals</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-green-600">{client.stats.reports_count}</div>
                                    <div className="text-sm text-gray-500">Reports</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-sm text-gray-900">
                                        {client.stats.latest_report 
                                            ? new Date(client.stats.latest_report).toLocaleDateString()
                                            : 'Never'
                                        }
                                    </div>
                                    <div className="text-sm text-gray-500">Latest Report</div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="flex justify-end mt-6">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

// Client Goal Card Component
function ClientGoalCard({ client, onClick }) {
    return (
        <div 
            className="bg-gray-50 rounded-lg p-4 cursor-pointer hover:bg-gray-100 transition-colors duration-200"
            onClick={onClick}
        >
            <div className="flex justify-between items-start mb-3">
                <h4 className="font-semibold text-gray-900">{client.name}</h4>
                <span className="text-sm text-gray-500">
                    {client.goals_count || 0} goals
                </span>
            </div>
            <div className="space-y-2">
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Avg Monthly Goal:</span>
                    <span className="font-medium">
                        ${client.avg_goal ? Math.round(client.avg_goal).toLocaleString() : '0'}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Last Updated:</span>
                    <span className="text-gray-500">
                        {client.latest_goal_update 
                            ? new Date(client.latest_goal_update).toLocaleDateString()
                            : 'Never'
                        }
                    </span>
                </div>
            </div>
            <div className="mt-3 flex justify-end">
                <span className="text-blue-600 text-sm font-medium">
                    View Details →
                </span>
            </div>
        </div>
    );
}

// Client Goals Detail View Component
function ClientGoalsDetailView({ 
    client, 
    goals, 
    loading, 
    onBack, 
    onAddGoal, 
    onEditGoal,
    showGoalForm,
    editingGoal,
    onCloseForm,
    onGoalSaved
}) {
    const currentYear = new Date().getFullYear();
    const [selectedYear, setSelectedYear] = useState(currentYear);
    
    // Group goals by year
    const goalsByYear = goals.reduce((acc, goal) => {
        if (!acc[goal.year]) acc[goal.year] = [];
        acc[goal.year].push(goal);
        return acc;
    }, {});
    
    // Get available years
    const availableYears = Object.keys(goalsByYear).map(Number).sort((a, b) => b - a);
    const yearGoals = goalsByYear[selectedYear] || [];
    
    // Sort goals by month
    yearGoals.sort((a, b) => a.month - b.month);

    if (loading) {
        return (
            <div className="space-y-6">
                <button onClick={onBack} className="text-blue-600 hover:text-blue-800">
                    ← Back to Goals Overview
                </button>
                <div className="text-center py-8">Loading goals for {client.name}...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div className="flex items-center space-x-4">
                    <button 
                        onClick={onBack}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                        ← Back to Overview
                    </button>
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">{client.name} Goals</h2>
                        <p className="text-gray-600">Monthly revenue goals and performance tracking</p>
                    </div>
                </div>
                <button
                    onClick={onAddGoal}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                    Add Goal
                </button>
            </div>

            {/* Year Selector */}
            <div className="flex space-x-2">
                {availableYears.map(year => (
                    <button
                        key={year}
                        onClick={() => setSelectedYear(year)}
                        className={`px-4 py-2 rounded-md font-medium ${
                            selectedYear === year
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                    >
                        {year}
                    </button>
                ))}
            </div>

            {/* Client Goals Chart */}
            <GoalsLineChart client={client} goals={goals} viewType="client" />

            {/* Goals Grid */}
            <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900">
                        {selectedYear} Monthly Goals
                    </h3>
                </div>
                <div className="p-6">
                    {yearGoals.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {yearGoals.map(goal => (
                                <MonthlyGoalCard
                                    key={`${goal.year}-${goal.month}`}
                                    goal={goal}
                                    onEdit={onEditGoal}
                                />
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <div className="text-gray-500 mb-4">No goals set for {selectedYear}</div>
                            <button
                                onClick={onAddGoal}
                                className="text-blue-600 hover:text-blue-800"
                            >
                                Add your first goal for this year
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Goal Form Modal */}
            {showGoalForm && (
                <GoalFormModal
                    client={client}
                    goal={editingGoal}
                    onClose={onCloseForm}
                    onSave={onGoalSaved}
                />
            )}
        </div>
    );
}

// Monthly Goal Card Component
function MonthlyGoalCard({ goal, onEdit }) {
    const [showVersions, setShowVersions] = useState(false);
    const [versions, setVersions] = useState([]);
    
    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const confidenceColors = {
        'high': 'bg-green-100 text-green-800',
        'medium': 'bg-yellow-100 text-yellow-800',
        'low': 'bg-red-100 text-red-800'
    };

    const methodLabels = {
        'ai_suggested': '🤖 AI Generated',
        'ai_generated': '🤖 AI Generated',
        'manual': '👤 Manual',
        'human_override': '👤 Human Override',
        'historical': '📊 Historical'
    };

    const loadVersions = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/goals/${goal.id}/versions`, {
                withCredentials: true
            });
            setVersions(response.data.versions);
            setShowVersions(true);
        } catch (error) {
            console.error('Error loading versions:', error);
        }
    };

    return (
        <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-start mb-3">
                <h4 className="font-semibold text-gray-900">
                    {monthNames[goal.month - 1]} {goal.year}
                </h4>
                <div className="flex gap-2">
                    {goal.human_override && (
                        <button
                            onClick={loadVersions}
                            className="text-orange-600 hover:text-orange-800 text-sm"
                            title="View AI vs Human versions"
                        >
                            📊 Versions
                        </button>
                    )}
                    <button
                        onClick={() => onEdit(goal)}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                        Edit
                    </button>
                </div>
            </div>
            
            <div className="space-y-2">
                <div className="text-2xl font-bold text-blue-600">
                    ${Number(goal.revenue_goal).toLocaleString()}
                </div>
                
                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Method:</span>
                    <span className="text-gray-900">
                        {methodLabels[goal.calculation_method] || goal.calculation_method}
                    </span>
                </div>
                
                {goal.human_override && (
                    <div className="bg-orange-50 border border-orange-200 rounded p-2 text-xs">
                        <div className="font-medium text-orange-800">Human Override</div>
                        <div className="text-orange-600">
                            By: {goal.human_override_by}<br/>
                            At: {new Date(goal.human_override_at).toLocaleDateString()}
                        </div>
                    </div>
                )}
                
                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Confidence:</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        confidenceColors[goal.confidence] || 'bg-gray-100 text-gray-800'
                    }`}>
                        {goal.confidence || 'medium'}
                    </span>
                </div>
                
                {goal.notes && (
                    <div className="text-xs text-gray-500 mt-2 truncate" title={goal.notes}>
                        {goal.notes}
                    </div>
                )}
                
                <div className="text-xs text-gray-400 mt-2">
                    Updated: {new Date(goal.updated_at).toLocaleDateString()}
                </div>
            </div>

            {/* Version History Modal */}
            {showVersions && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-96 overflow-y-auto">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold">
                                Goal Versions - {monthNames[goal.month - 1]} {goal.year}
                            </h3>
                            <button
                                onClick={() => setShowVersions(false)}
                                className="text-gray-500 hover:text-gray-700"
                            >
                                ✕
                            </button>
                        </div>
                        
                        <div className="space-y-4">
                            {versions.map((version, index) => (
                                <div key={index} className={`border rounded-lg p-4 ${
                                    version.is_current ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                                }`}>
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium">
                                                ${Number(version.revenue_goal).toLocaleString()}
                                            </span>
                                            {version.is_current && (
                                                <span className="bg-blue-500 text-white px-2 py-1 rounded text-xs">
                                                    Current
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-sm text-gray-600">
                                            {methodLabels[version.calculation_method] || version.calculation_method}
                                        </span>
                                    </div>
                                    
                                    {version.notes && (
                                        <div className="text-sm text-gray-600 mb-2">
                                            {version.notes}
                                        </div>
                                    )}
                                    
                                    <div className="text-xs text-gray-500">
                                        {version.version_type === 'ai_original' && 'Original AI Version - '}
                                        {version.human_override_by && `Modified by ${version.human_override_by} - `}
                                        {new Date(version.created_at || version.preserved_at).toLocaleDateString()}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Goal Form Modal Component
function GoalFormModal({ client, goal, onClose, onSave }) {
    const [formData, setFormData] = useState({
        year: goal?.year || new Date().getFullYear(),
        month: goal?.month || new Date().getMonth() + 1,
        revenue_goal: goal?.revenue_goal || '',
        calculation_method: goal?.calculation_method || 'manual',
        notes: goal?.notes || '',
        confidence: goal?.confidence || 'medium'
    });
    const [saving, setSaving] = useState(false);

    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);

        try {
            const endpoint = goal 
                ? `${API_BASE_URL}/api/goals/${goal.id}`
                : `${API_BASE_URL}/api/goals/${client.id}`;
            
            const method = goal ? 'PUT' : 'POST';
            
            await axios({
                method,
                url: endpoint,
                data: formData,
                withCredentials: true
            });
            
            alert(`Goal ${goal ? 'updated' : 'created'} successfully`);
            onSave();
        } catch (error) {
            alert(`Failed to ${goal ? 'update' : 'create'} goal: ` + (error.response?.data?.detail || 'Unknown error'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">
                        {goal ? 'Edit Goal' : 'Add New Goal'} - {client.name}
                    </h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        ✕
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Year
                            </label>
                            <select
                                value={formData.year}
                                onChange={(e) => setFormData({...formData, year: parseInt(e.target.value)})}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                required
                            >
                                {[2024, 2025, 2026].map(year => (
                                    <option key={year} value={year}>{year}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Month
                            </label>
                            <select
                                value={formData.month}
                                onChange={(e) => setFormData({...formData, month: parseInt(e.target.value)})}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                required
                            >
                                {monthNames.map((month, index) => (
                                    <option key={index + 1} value={index + 1}>{month}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Revenue Goal ($)
                        </label>
                        <input
                            type="number"
                            value={formData.revenue_goal}
                            onChange={(e) => setFormData({...formData, revenue_goal: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            placeholder="25000"
                            required
                            min="0"
                            step="100"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Calculation Method
                        </label>
                        <select
                            value={formData.calculation_method}
                            onChange={(e) => setFormData({...formData, calculation_method: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="manual">Manual</option>
                            <option value="ai_suggested">AI Suggested</option>
                            <option value="historical">Historical</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Confidence Level
                        </label>
                        <select
                            value={formData.confidence}
                            onChange={(e) => setFormData({...formData, confidence: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Notes (Optional)
                        </label>
                        <textarea
                            value={formData.notes}
                            onChange={(e) => setFormData({...formData, notes: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                            rows="3"
                            placeholder="Additional notes about this goal..."
                        />
                    </div>

                    <div className="flex justify-end space-x-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                            {saving ? 'Saving...' : 'Save Goal'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// Render the app
// Goals Line Chart Component
function GoalsLineChart({ clients, client, goals, viewType }) {
    const chartRef = React.useRef(null);
    const chartInstance = React.useRef(null);
    const [companyData, setCompanyData] = useState(null);

    React.useEffect(() => {
        if (viewType === 'company') {
            loadCompanyData();
        }
    }, [viewType]);

    React.useEffect(() => {
        if (!chartRef.current) return;

        // Destroy existing chart
        if (chartInstance.current) {
            chartInstance.current.destroy();
        }

        const ctx = chartRef.current.getContext('2d');
        
        if (viewType === 'company') {
            createCompanyChart(ctx);
        } else if (viewType === 'client') {
            createClientChart(ctx);
        }

        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
            }
        };
    }, [clients, client, goals, viewType, companyData]);

    const loadCompanyData = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/goals/company/aggregated`, {
                withCredentials: true
            });
            setCompanyData(response.data);
        } catch (error) {
            console.error('Error loading company goals data:', error);
        }
    };

    const createCompanyChart = (ctx) => {
        if (!companyData || !companyData.monthly_totals) return;

        const monthlyData = companyData.monthly_totals;
        const sortedMonths = Object.keys(monthlyData).sort();
        const labels = sortedMonths.map(month => {
            const [year, monthNum] = month.split('-');
            const date = new Date(year, monthNum - 1);
            return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        });

        // Create dataset for total company goals
        const totalData = sortedMonths.map(month => monthlyData[month].total);

        chartInstance.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Total Company Goals',
                    data: totalData,
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#3B82F6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Company-wide Revenue Goals by Month',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + (value / 1000).toFixed(0) + 'K';
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    };

    const createClientChart = (ctx) => {
        if (!goals || goals.length === 0) return;

        // Group goals by year and month
        const monthlyData = {};
        goals.forEach(goal => {
            const monthKey = `${goal.year}-${String(goal.month).padStart(2, '0')}`;
            monthlyData[monthKey] = goal;
        });

        const sortedMonths = Object.keys(monthlyData).sort();
        const labels = sortedMonths.map(month => {
            const [year, monthNum] = month.split('-');
            const date = new Date(year, monthNum - 1);
            return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        });

        const data = sortedMonths.map(month => monthlyData[month].revenue_goal);
        const backgroundColors = sortedMonths.map(month => {
            const goal = monthlyData[month];
            if (goal.human_override) return 'rgba(249, 115, 22, 0.1)'; // Orange for human override
            if (goal.calculation_method === 'ai_suggested' || goal.calculation_method === 'ai_generated') {
                return 'rgba(59, 130, 246, 0.1)'; // Blue for AI
            }
            return 'rgba(107, 114, 128, 0.1)'; // Gray for manual
        });

        const borderColors = sortedMonths.map(month => {
            const goal = monthlyData[month];
            if (goal.human_override) return '#F97316'; // Orange
            if (goal.calculation_method === 'ai_suggested' || goal.calculation_method === 'ai_generated') {
                return '#3B82F6'; // Blue
            }
            return '#6B7280'; // Gray
        });

        chartInstance.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Revenue Goal',
                    data,
                    borderColor: borderColors[0] || '#3B82F6',
                    backgroundColor: backgroundColors[0] || 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: borderColors,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    segment: {
                        borderColor: (ctx) => {
                            const goal = monthlyData[sortedMonths[ctx.p0DataIndex]];
                            if (goal?.human_override) return '#F97316';
                            if (goal?.calculation_method === 'ai_suggested' || goal?.calculation_method === 'ai_generated') {
                                return '#3B82F6';
                            }
                            return '#6B7280';
                        }
                    }
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: `${client?.name} Revenue Goals by Month`,
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const goal = monthlyData[sortedMonths[context.dataIndex]];
                                const value = '$' + Number(context.parsed.y).toLocaleString();
                                let method = '';
                                if (goal.human_override) method = ' (Human Override)';
                                else if (goal.calculation_method === 'ai_suggested' || goal.calculation_method === 'ai_generated') {
                                    method = ' (AI Generated)';
                                }
                                return value + method;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + (value / 1000).toFixed(0) + 'K';
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    };

    // Generate mock data for company chart (replace with real API call)
    const generateMockGoalsForChart = (clientName, index) => {
        const baseAmount = [15000, 25000, 35000, 20000, 30000, 18000, 22000][index] || 20000;
        const variation = baseAmount * 0.2;
        
        return Array.from({ length: 12 }, (_, monthIndex) => ({
            year: 2025,
            month: monthIndex + 1,
            revenue_goal: baseAmount + (Math.random() - 0.5) * variation,
            calculation_method: Math.random() > 0.7 ? 'human_override' : 'ai_suggested'
        }));
    };

    if (viewType === 'company' && (!companyData || !companyData.monthly_totals)) {
        return (
            <div className="bg-white rounded-lg shadow p-6">
                <div className="text-center py-8 text-gray-500">
                    Loading company goals data...
                </div>
            </div>
        );
    }

    if (viewType === 'client' && (!goals || goals.length === 0)) {
        return (
            <div className="bg-white rounded-lg shadow p-6">
                <div className="text-center py-8 text-gray-500">
                    No goals data available for this client
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <canvas ref={chartRef} style={{ maxHeight: '400px' }}></canvas>
            
            {viewType === 'client' && (
                <div className="mt-4 flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center">
                        <div className="w-3 h-3 rounded-full bg-blue-500 mr-2"></div>
                        <span>AI Generated</span>
                    </div>
                    <div className="flex items-center">
                        <div className="w-3 h-3 rounded-full bg-orange-500 mr-2"></div>
                        <span>Human Override</span>
                    </div>
                    <div className="flex items-center">
                        <div className="w-3 h-3 rounded-full bg-gray-500 mr-2"></div>
                        <span>Manual Entry</span>
                    </div>
                </div>
            )}
        </div>
    );
}

// AI vs Human Accuracy Comparison View Component
function AccuracyComparisonView({ data, onBack }) {
    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <button
                        onClick={onBack}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium mb-2"
                    >
                        ← Back to Goals Overview
                    </button>
                    <h2 className="text-2xl font-bold text-gray-900">AI vs Human Goal Accuracy</h2>
                    <p className="text-gray-600 mt-1">Compare the accuracy of AI-generated vs human-overridden goals</p>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center">
                        <div className="p-2 bg-orange-100 rounded-lg">
                            <span className="text-2xl">🔄</span>
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">Total Overrides</p>
                            <p className="text-2xl font-semibold text-gray-900">{data.total_overrides}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center">
                        <div className="p-2 bg-blue-100 rounded-lg">
                            <span className="text-2xl">👥</span>
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">Clients with Overrides</p>
                            <p className="text-2xl font-semibold text-gray-900">{data.clients_with_overrides}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center">
                        <div className="p-2 bg-green-100 rounded-lg">
                            <span className="text-2xl">📊</span>
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">Average Difference</p>
                            <p className="text-2xl font-semibold text-gray-900">{data.average_difference}%</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center">
                        <div className="p-2 bg-purple-100 rounded-lg">
                            <span className="text-2xl">📅</span>
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">Months with Data</p>
                            <p className="text-2xl font-semibold text-gray-900">
                                {Object.keys(data.monthly_breakdown).length}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Override Details */}
            {data.override_details.length > 0 && (
                <div className="bg-white rounded-lg shadow">
                    <div className="px-6 py-4 border-b border-gray-200">
                        <h3 className="text-lg font-semibold text-gray-900">Override Details</h3>
                        <p className="text-sm text-gray-600">
                            Detailed comparison of AI predictions vs human adjustments
                        </p>
                    </div>
                    
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Date
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Client
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        AI Goal
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Human Goal
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Difference
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Override By
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {data.override_details.map((override, index) => (
                                    <tr key={index}>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {override.year}-{String(override.month).padStart(2, '0')}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            Client {override.client_id.slice(-6)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            ${Number(override.ai_goal).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            ${Number(override.human_goal).toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <span className={`text-sm font-medium ${
                                                    override.difference_pct > 20 
                                                        ? 'text-red-600' 
                                                        : override.difference_pct > 10 
                                                            ? 'text-yellow-600' 
                                                            : 'text-green-600'
                                                }`}>
                                                    {override.difference_pct}%
                                                </span>
                                                <span className="text-xs text-gray-500 ml-2">
                                                    (${Number(override.difference).toLocaleString()})
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {override.override_by}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {data.total_overrides === 0 && (
                <div className="bg-white rounded-lg shadow p-8 text-center">
                    <div className="text-6xl mb-4">🤖</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No Human Overrides Yet</h3>
                    <p className="text-gray-600">
                        All goals are currently using AI-generated values. 
                        Start editing goals to see accuracy comparisons.
                    </p>
                </div>
            )}
        </div>
    );
}

// Enhanced Admin View Component with Slack Testing and Environment Variables
function AdminView({ user }) {
    const [activeTab, setActiveTab] = useState('overview');
    const [slackTestResult, setSlackTestResult] = useState(null);
    const [slackTesting, setSlackTesting] = useState(false);
    const [envVars, setEnvVars] = useState({});
    const [envLoading, setEnvLoading] = useState(false);
    const [restarting, setRestarting] = useState(false);
    const [systemStatus, setSystemStatus] = useState(null);
    const [showEnvVarForm, setShowEnvVarForm] = useState(false);
    const [envFormData, setEnvFormData] = useState({});
    const [mcpLoaded, setMcpLoaded] = useState(false);
    
    // Upload functionality state
    const [uploadFile, setUploadFile] = useState(null);
    const [uploadName, setUploadName] = useState('');
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState(null);
    const [packages, setPackages] = useState([]);
    const [packagesLoading, setPackagesLoading] = useState(false);

    useEffect(() => {
        if (activeTab === 'overview') {
            loadSystemStatus();
        } else if (activeTab === 'environment') {
            loadEnvironmentVariables();
        } else if (activeTab === 'packages') {
            loadPackages();
        } else if (activeTab === 'mcp' && !mcpLoaded) {
            // Load MCP component dynamically
            loadMCPComponent();
        }
    }, [activeTab, mcpLoaded]);

    const loadSystemStatus = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/admin/system/status`, {
                withCredentials: true
            });
            setSystemStatus(response.data);
        } catch (error) {
            console.error('Failed to load system status:', error);
        }
    };

    const loadEnvironmentVariables = async () => {
        try {
            setEnvLoading(true);
            console.log('Loading environment variables from:', `${API_BASE_URL}/api/admin/environment`);
            const response = await axios.get(`${API_BASE_URL}/api/admin/environment`, {
                withCredentials: true
            });
            console.log('Environment variables response:', response.data);
            setEnvVars(response.data.variables || {});
        } catch (error) {
            console.error('Failed to load environment variables:', {
                message: error.message,
                response: error.response?.data,
                status: error.response?.status,
                url: `${API_BASE_URL}/api/admin/environment`
            });
            
            // More detailed error message
            let errorMsg = 'Failed to load environment variables: ';
            if (error.response?.status === 404) {
                errorMsg += 'Endpoint not found. The backend may not be properly deployed.';
            } else if (error.response?.status === 403) {
                errorMsg += 'Access denied. Please ensure you have admin privileges.';
            } else if (error.code === 'ERR_NETWORK') {
                errorMsg += 'Network error. Please check if the backend is running.';
            } else {
                errorMsg += error.response?.data?.detail || error.message || 'Unknown error';
            }
            
            alert(errorMsg);
            setEnvVars({});
        } finally {
            setEnvLoading(false);
        }
    };

    const handleSlackTest = async () => {
        try {
            setSlackTesting(true);
            setSlackTestResult(null);

            const response = await axios.post(`${API_BASE_URL}/api/admin/slack/test`, {}, {
                withCredentials: true
            });

            setSlackTestResult({
                status: 'success',
                message: response.data.message,
                details: response.data
            });

        } catch (error) {
            setSlackTestResult({
                status: 'error',
                message: error.response?.data?.detail || 'Slack test failed',
                details: error.response?.data
            });
        } finally {
            setSlackTesting(false);
        }
    };

    const handleEditEnvVar = (key) => {
        const envVar = envVars[key];
        setEnvFormData({ [key]: envVar.is_sensitive ? '' : envVar.value });
        setShowEnvVarForm(true);
    };

    const handleSaveEnvVars = async () => {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/admin/environment`, {
                variables: envFormData
            }, {
                withCredentials: true
            });

            alert('Environment variables updated successfully!\n\n' + response.data.note);
            setShowEnvVarForm(false);
            setEnvFormData({});
            loadEnvironmentVariables(); // Reload to see changes

        } catch (error) {
            alert('Failed to update environment variables: ' + (error.response?.data?.detail || 'Unknown error'));
        }
    };

    const handleRestartServer = async () => {
        if (!confirm('Are you sure you want to restart the server? The application will be unavailable for a few seconds.')) {
            return;
        }

        try {
            setRestarting(true);
            const response = await axios.post(`${API_BASE_URL}/api/admin/restart`, {}, {
                withCredentials: true
            });

            alert(response.data.message + '\n\n' + response.data.note);
            
            // Wait a few seconds then reload the page
            setTimeout(() => {
                window.location.reload();
            }, 5000);

        } catch (error) {
            // If the error is due to connection reset, that's expected during restart
            if (error.code === 'ERR_NETWORK' || error.message.includes('Network')) {
                alert('Server is restarting. The page will reload automatically in a few seconds.');
                setTimeout(() => {
                    window.location.reload();
                }, 5000);
            } else {
                alert('Failed to restart server: ' + (error.response?.data?.detail || 'Unknown error'));
                setRestarting(false);
            }
        }
    };

    // Load MCP component dynamically
    const loadMCPComponent = () => {
        // Check if MCPManagement component is already loaded
        if (window.MCPManagement) {
            setMcpLoaded(true);
        } else {
            // Try to load the component
            const script = document.createElement('script');
            script.src = 'components/MCPManagement.js';
            script.type = 'text/babel';
            script.onload = () => {
                // Give Babel time to process the script
                setTimeout(() => {
                    if (window.MCPManagement) {
                        setMcpLoaded(true);
                    }
                }, 500);
            };
            document.head.appendChild(script);
        }
    };

    // Upload functionality functions
    const loadPackages = async () => {
        try {
            setPackagesLoading(true);
            const response = await axios.get(`${API_BASE_URL}/api/admin/packages`, {
                withCredentials: true
            });
            setPackages(response.data.packages);
        } catch (error) {
            console.error('Failed to load packages:', error);
            alert('Failed to load packages: ' + (error.response?.data?.detail || 'Unknown error'));
        } finally {
            setPackagesLoading(false);
        }
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            setUploadFile(file);
            if (!uploadName) {
                // Extract name from filename
                const nameWithoutExtension = file.name.replace(/\.[^/.]+$/, "");
                setUploadName(nameWithoutExtension);
            }
        }
    };

    const handleUploadPackage = async () => {
        if (!uploadFile || !uploadName.trim()) {
            alert('Please select a file and provide a package name');
            return;
        }

        try {
            setUploading(true);
            setUploadResult(null);

            const formData = new FormData();
            formData.append('package', uploadFile);
            formData.append('name', uploadName.trim());

            const response = await axios.post(`${API_BASE_URL}/api/admin/upload-package`, formData, {
                withCredentials: true,
                headers: {
                    'Content-Type': 'multipart/form-data',
                }
            });

            setUploadResult({
                status: 'success',
                message: response.data.message,
                details: response.data
            });

            // Reset form
            setUploadFile(null);
            setUploadName('');
            // Clear the file input
            const fileInput = document.getElementById('packageFile');
            if (fileInput) fileInput.value = '';

            // Reload packages list
            loadPackages();

        } catch (error) {
            setUploadResult({
                status: 'error',
                message: error.response?.data?.detail || 'Upload failed',
                details: error.response?.data
            });
        } finally {
            setUploading(false);
        }
    };

    const handleDeployPackage = async (packageId) => {
        if (!confirm('Are you sure you want to deploy this package?')) {
            return;
        }

        try {
            const response = await axios.post(`${API_BASE_URL}/api/admin/deploy-package/${packageId}`, {}, {
                withCredentials: true
            });

            alert(`Deployment successful: ${response.data.message}`);
            loadPackages(); // Reload to update status

        } catch (error) {
            alert('Deployment failed: ' + (error.response?.data?.detail || 'Unknown error'));
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'online':
            case 'connected':
            case 'configured':
            case 'healthy':
                return 'text-green-600 bg-green-100';
            case 'not_configured':
                return 'text-yellow-600 bg-yellow-100';
            case 'error':
            case 'failed':
                return 'text-red-600 bg-red-100';
            default:
                return 'text-gray-600 bg-gray-100';
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Admin Dashboard</h2>
                    <p className="text-gray-600 mt-1">System management and configuration</p>
                </div>
                <div className="text-sm text-gray-500">
                    Welcome, {user.name}
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="border-b border-gray-200">
                <nav className="-mb-px flex space-x-8">
                    {[
                        { id: 'overview', label: 'Overview', icon: '🏠' },
                        { id: 'mcp', label: 'MCP Management', icon: '🤖' },
                        { id: 'slack', label: 'Slack Integration', icon: '💬' },
                        { id: 'environment', label: 'Environment Variables', icon: '⚙️' },
                        { id: 'packages', label: 'Package Upload', icon: '📦' }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === tab.id
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            {tab.icon} {tab.label}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Overview Tab */}
            {activeTab === 'overview' && (
                <div className="space-y-6">
                    {systemStatus && (
                        <div className="bg-white rounded-lg shadow p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {Object.entries(systemStatus.components).map(([component, info]) => (
                                    <div key={component} className="border rounded-lg p-4">
                                        <div className="flex justify-between items-center mb-2">
                                            <h4 className="font-medium text-gray-900 capitalize">
                                                {component.replace('_', ' ')}
                                            </h4>
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(info.status)}`}>
                                                {info.status}
                                            </span>
                                        </div>
                                        <p className="text-sm text-gray-600">{info.details}</p>
                                    </div>
                                ))}
                            </div>

                            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                                <div className="flex justify-between items-center">
                                    <div className="text-sm text-gray-600">
                                        <strong>Environment:</strong> {systemStatus.environment} | 
                                        <strong> Debug:</strong> {systemStatus.debug ? 'Enabled' : 'Disabled'}
                                    </div>
                                    <button
                                        onClick={handleRestartServer}
                                        disabled={restarting}
                                        className="px-4 py-2 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                    >
                                        {restarting ? (
                                            <>
                                                <svg className="animate-spin h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                                Restarting...
                                            </>
                                        ) : (
                                            <>🔄 Restart Server</>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Quick Actions */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                            <button
                                onClick={() => setActiveTab('slack')}
                                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 text-center"
                            >
                                <div className="text-2xl mb-2">💬</div>
                                <div className="font-medium text-gray-900">Test Slack</div>
                                <div className="text-sm text-gray-500">Send a test message</div>
                            </button>

                            <button
                                onClick={() => setActiveTab('environment')}
                                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 text-center"
                            >
                                <div className="text-2xl mb-2">⚙️</div>
                                <div className="font-medium text-gray-900">Configure</div>
                                <div className="text-sm text-gray-500">Update environment variables</div>
                            </button>

                            <button
                                onClick={() => setActiveTab('packages')}
                                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 text-center"
                            >
                                <div className="text-2xl mb-2">📦</div>
                                <div className="font-medium text-gray-900">Upload Package</div>
                                <div className="text-sm text-gray-500">Deploy new features</div>
                            </button>

                            <button
                                onClick={loadSystemStatus}
                                className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 text-center"
                            >
                                <div className="text-2xl mb-2">🔃</div>
                                <div className="font-medium text-gray-900">Refresh Status</div>
                                <div className="text-sm text-gray-500">Update system info</div>
                            </button>
                            <button
                                onClick={handleRestartServer}
                                disabled={restarting}
                                className="p-4 border-2 border-dashed border-red-300 rounded-lg hover:border-red-400 hover:bg-red-50 text-center disabled:opacity-50"
                            >
                                <div className="text-2xl mb-2">🔄</div>
                                <div className="font-medium text-red-900">Restart Server</div>
                                <div className="text-sm text-red-600">{restarting ? 'Restarting...' : 'Restart application'}</div>
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Slack Integration Tab */}
            {activeTab === 'slack' && (
                <div className="space-y-6">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">🔗 Slack Integration Test</h3>
                        
                        <div className="space-y-4">
                            <p className="text-gray-600">
                                Test your Slack webhook integration by sending a test message to your configured channel.
                            </p>

                            <button
                                onClick={handleSlackTest}
                                disabled={slackTesting}
                                className="bg-green-600 text-white px-6 py-3 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {slackTesting ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Sending Test Message...
                                    </>
                                ) : (
                                    <>
                                        🧪 Send Test Message
                                    </>
                                )}
                            </button>

                            {/* Test Result */}
                            {slackTestResult && (
                                <div className={`p-4 rounded-md border ${
                                    slackTestResult.status === 'success' 
                                        ? 'bg-green-50 border-green-200' 
                                        : 'bg-red-50 border-red-200'
                                }`}>
                                    <div className={`font-medium ${
                                        slackTestResult.status === 'success' 
                                            ? 'text-green-800' 
                                            : 'text-red-800'
                                    }`}>
                                        {slackTestResult.status === 'success' ? '✅' : '❌'} {slackTestResult.message}
                                    </div>
                                    
                                    {slackTestResult.details?.webhook_url && (
                                        <div className="mt-2 text-sm text-gray-600">
                                            <strong>Webhook URL:</strong> {slackTestResult.details.webhook_url.replace(/\/[^\/]*$/, '/***')}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Instructions */}
                            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                                <h4 className="font-medium text-blue-900 mb-2">📝 Setup Instructions</h4>
                                <div className="text-sm text-blue-800 space-y-1">
                                    <p>1. Create a Slack webhook URL in your Slack workspace</p>
                                    <p>2. Set the <code>SLACK_WEBHOOK_URL</code> environment variable</p>
                                    <p>3. Use the "Environment Variables" tab to configure it</p>
                                    <p>4. Click "Send Test Message" to verify the connection</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Environment Variables Tab */}
            {activeTab === 'environment' && (
                <div className="space-y-6">
                    <div className="bg-white rounded-lg shadow">
                        <div className="p-6 border-b border-gray-200">
                            <div className="flex justify-between items-center">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900">Environment Variables</h3>
                                    <p className="text-sm text-gray-600 mt-1">
                                        Manage important system configuration variables
                                    </p>
                                </div>
                                <button
                                    onClick={loadEnvironmentVariables}
                                    disabled={envLoading}
                                    className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                >
                                    {envLoading ? '⏳ Loading...' : '🔄 Refresh'}
                                </button>
                            </div>
                        </div>

                        <div className="p-6">
                            {envLoading ? (
                                <div className="text-center py-8 text-gray-500">Loading environment variables...</div>
                            ) : Object.keys(envVars).length === 0 ? (
                                <div className="text-center py-8 text-gray-500">No environment variables found</div>
                            ) : (
                                <div className="space-y-4">
                                    {Object.entries(envVars).map(([key, config]) => (
                                        <div key={key} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <h4 className="font-medium text-gray-900">{key}</h4>
                                                        {config.required && (
                                                            <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded-full">
                                                                Required
                                                            </span>
                                                        )}
                                                        {config.is_sensitive && (
                                                            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full">
                                                                Sensitive
                                                            </span>
                                                        )}
                                                        <span className={`text-xs px-2 py-1 rounded-full ${
                                                            config.is_set 
                                                                ? 'bg-green-100 text-green-800' 
                                                                : 'bg-gray-100 text-gray-800'
                                                        }`}>
                                                            {config.is_set ? 'Set' : 'Not Set'}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-gray-600 mb-2">{config.description}</p>
                                                    <div className="text-sm">
                                                        <strong>Current:</strong> 
                                                        <code className="ml-2 px-2 py-1 bg-gray-100 rounded text-xs">
                                                            {config.value || '(empty)'}
                                                        </code>
                                                    </div>
                                                    {config.example && (
                                                        <div className="text-sm mt-1">
                                                            <strong>Example:</strong> 
                                                            <code className="ml-2 px-2 py-1 bg-blue-50 text-blue-800 rounded text-xs">
                                                                {config.example}
                                                            </code>
                                                        </div>
                                                    )}
                                                </div>
                                                <button
                                                    onClick={() => handleEditEnvVar(key)}
                                                    className="ml-4 text-blue-600 hover:text-blue-800 text-sm font-medium"
                                                >
                                                    Edit
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Environment Variable Edit Modal */}
                    {showEnvVarForm && (
                        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-lg font-semibold">Update Environment Variables</h3>
                                    <button
                                        onClick={() => setShowEnvVarForm(false)}
                                        className="text-gray-400 hover:text-gray-600"
                                    >
                                        ✕
                                    </button>
                                </div>

                                <div className="space-y-4">
                                    {Object.entries(envFormData).map(([key, value]) => (
                                        <div key={key}>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                {key}
                                            </label>
                                            <input
                                                type={envVars[key]?.is_sensitive ? 'password' : 'text'}
                                                value={value}
                                                onChange={(e) => setEnvFormData({
                                                    ...envFormData,
                                                    [key]: e.target.value
                                                })}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                                placeholder={envVars[key]?.example || `Enter ${key}`}
                                            />
                                            <p className="text-xs text-gray-500 mt-1">
                                                {envVars[key]?.description}
                                            </p>
                                        </div>
                                    ))}
                                </div>

                                <div className="flex justify-end space-x-3 mt-6">
                                    <button
                                        onClick={() => setShowEnvVarForm(false)}
                                        className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSaveEnvVars}
                                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                                    >
                                        Save Changes
                                    </button>
                                </div>

                                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                                    <p className="text-xs text-green-800">
                                        <strong>✅ Persistence:</strong> Changes are automatically saved to .env file 
                                        and will persist across server restarts.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Environment Variables Instructions */}
                    <div className="bg-amber-50 rounded-lg p-6">
                        <h4 className="font-medium text-amber-900 mb-2">⚠️ Important Notes</h4>
                        <div className="text-sm text-amber-800 space-y-2">
                            <p>• Environment variable changes only affect the current application instance</p>
                            <p>• For permanent changes, update your deployment configuration or .env file</p>
                            <p>• Sensitive values (like API keys) are masked in the display for security</p>
                            <p>• Some changes may require an application restart to take full effect</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Package Upload Tab */}
            {activeTab === 'packages' && (
                <div className="space-y-6">
                    {/* Upload New Package */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">📦 Upload New Package</h3>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Package Name
                                </label>
                                <input
                                    type="text"
                                    value={uploadName}
                                    onChange={(e) => setUploadName(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="Enter package name (e.g., calendar-integration)"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Package File (.zip)
                                </label>
                                <input
                                    type="file"
                                    id="packageFile"
                                    accept=".zip"
                                    onChange={handleFileUpload}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                />
                                {uploadFile && (
                                    <p className="text-sm text-gray-600 mt-1">
                                        Selected: {uploadFile.name} ({(uploadFile.size / 1024 / 1024).toFixed(2)} MB)
                                    </p>
                                )}
                            </div>

                            <button
                                onClick={handleUploadPackage}
                                disabled={uploading || !uploadFile || !uploadName.trim()}
                                className="bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {uploading ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Uploading...
                                    </>
                                ) : (
                                    <>
                                        📤 Upload Package
                                    </>
                                )}
                            </button>

                            {/* Upload Result */}
                            {uploadResult && (
                                <div className={`p-4 rounded-md border ${
                                    uploadResult.status === 'success' 
                                        ? 'bg-green-50 border-green-200' 
                                        : 'bg-red-50 border-red-200'
                                }`}>
                                    <div className={`font-medium ${
                                        uploadResult.status === 'success' 
                                            ? 'text-green-800' 
                                            : 'text-red-800'
                                    }`}>
                                        {uploadResult.status === 'success' ? '✅' : '❌'} {uploadResult.message}
                                    </div>
                                    
                                    {uploadResult.details?.next_steps && (
                                        <div className="mt-2 text-sm text-gray-600">
                                            <strong>Next Steps:</strong>
                                            <ul className="list-disc list-inside mt-1">
                                                {uploadResult.details.next_steps.map((step, index) => (
                                                    <li key={index}>{step}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Uploaded Packages List */}
                    <div className="bg-white rounded-lg shadow">
                        <div className="p-6 border-b border-gray-200">
                            <div className="flex justify-between items-center">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900">Uploaded Packages</h3>
                                    <p className="text-sm text-gray-600 mt-1">
                                        Manage and deploy uploaded packages
                                    </p>
                                </div>
                                <button
                                    onClick={loadPackages}
                                    disabled={packagesLoading}
                                    className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                >
                                    {packagesLoading ? '⏳ Loading...' : '🔄 Refresh'}
                                </button>
                            </div>
                        </div>

                        <div className="p-6">
                            {packagesLoading ? (
                                <div className="text-center py-8 text-gray-500">Loading packages...</div>
                            ) : packages.length === 0 ? (
                                <div className="text-center py-8 text-gray-500">No packages uploaded yet</div>
                            ) : (
                                <div className="space-y-4">
                                    {packages.map((pkg) => (
                                        <div key={pkg.id} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <h4 className="font-medium text-gray-900">{pkg.package_name}</h4>
                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                                            pkg.status === 'deployed' 
                                                                ? 'bg-green-100 text-green-800'
                                                                : 'bg-blue-100 text-blue-800'
                                                        }`}>
                                                            {pkg.status}
                                                        </span>
                                                    </div>
                                                    
                                                    <div className="text-sm text-gray-600 space-y-1">
                                                        <p><strong>Uploaded by:</strong> {pkg.uploaded_by}</p>
                                                        <p><strong>Uploaded at:</strong> {new Date(pkg.uploaded_at).toLocaleString()}</p>
                                                        <p><strong>File path:</strong> <code className="bg-gray-100 px-1 rounded text-xs">{pkg.file_path}</code></p>
                                                        {pkg.extract_path && (
                                                            <p><strong>Extracted to:</strong> <code className="bg-gray-100 px-1 rounded text-xs">{pkg.extract_path}</code></p>
                                                        )}
                                                    </div>
                                                </div>
                                                
                                                <div className="flex flex-col gap-2">
                                                    {pkg.status !== 'deployed' && (
                                                        <button
                                                            onClick={() => handleDeployPackage(pkg.id)}
                                                            className="bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700 text-sm"
                                                        >
                                                            🚀 Deploy
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Package Upload Instructions */}
                    <div className="bg-blue-50 rounded-lg p-6">
                        <h4 className="font-medium text-blue-900 mb-2">📋 Upload Instructions</h4>
                        <div className="text-sm text-blue-800 space-y-2">
                            <p>• Package files must be in ZIP format</p>
                            <p>• Include all necessary files (Python scripts, frontend components, etc.)</p>
                            <p>• Use descriptive package names for easy identification</p>
                            <p>• Uploaded packages are automatically extracted and made available for deployment</p>
                            <p>• Only admin users can upload and deploy packages</p>
                        </div>
                    </div>
                </div>
            )}

            {/* MCP Management Tab */}
            {activeTab === 'mcp' && (
                <div className="space-y-6">
                    {!mcpLoaded ? (
                        <div className="bg-white rounded-lg shadow p-6">
                            <div className="flex items-center justify-center">
                                <div className="text-center">
                                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                                    <p className="text-sm text-gray-600">Loading MCP Management...</p>
                                </div>
                            </div>
                        </div>
                    ) : window.MCPManagement ? (
                        <window.MCPManagement />
                    ) : (
                        <div className="bg-white rounded-lg shadow p-6">
                            <div className="text-center text-gray-500">
                                <p>MCP Management component could not be loaded.</p>
                                <button
                                    onClick={() => loadMCPComponent()}
                                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                >
                                    Retry Loading
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

ReactDOM.render(<App />, document.getElementById('root'));