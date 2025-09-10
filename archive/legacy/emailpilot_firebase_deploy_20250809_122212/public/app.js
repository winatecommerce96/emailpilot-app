// EmailPilot React Application
const { useState, useEffect } = React;

// API Configuration
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8080' 
    : 'https://emailpilot.ai';

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
                {currentView === 'calendar' && <CalendarView />}
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
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">EmailPilot</h1>
                    <p className="text-gray-600">Klaviyo Automation Platform</p>
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
        <nav className="bg-white shadow-lg">
            <div className="container mx-auto px-4">
                <div className="flex justify-between items-center h-16">
                    <div className="flex items-center space-x-8">
                        <h1 className="text-xl font-bold text-gray-900">EmailPilot</h1>
                        
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
                        </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                        <span className="text-gray-700">Hello, {user.name}</span>
                        <button
                            onClick={onLogout}
                            className="text-red-600 hover:text-red-800"
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
            className={`px-3 py-2 rounded-md text-sm font-medium ${
                active 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
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
    const [viewMode, setViewMode] = useState('overview'); // 'overview', 'client-detail'

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
        'manual': '👤 Manual',
        'historical': '📊 Historical'
    };

    return (
        <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-start mb-3">
                <h4 className="font-semibold text-gray-900">
                    {monthNames[goal.month - 1]} {goal.year}
                </h4>
                <button
                    onClick={() => onEdit(goal)}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                >
                    Edit
                </button>
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
ReactDOM.render(<App />, document.getElementById('root'));