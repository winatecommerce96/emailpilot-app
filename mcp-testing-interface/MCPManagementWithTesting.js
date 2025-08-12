// Enhanced MCP Management Component with Testing Interface
// This version includes a button to launch the production testing interface

const MCPManagementWithTesting = () => {
    const [clients, setClients] = React.useState([]);
    const [models, setModels] = React.useState([]);
    const [selectedClient, setSelectedClient] = React.useState(null);
    const [showAddModal, setShowAddModal] = React.useState(false);
    const [showEditModal, setShowEditModal] = React.useState(false);
    const [showTestModal, setShowTestModal] = React.useState(false);
    const [showTestingInterface, setShowTestingInterface] = React.useState(false);
    const [loading, setLoading] = React.useState(false);
    const [testResults, setTestResults] = React.useState({});
    const [usageStats, setUsageStats] = React.useState(null);

    // Form state for new/edit client
    const [formData, setFormData] = React.useState({
        name: '',
        account_id: '',
        klaviyo_api_key: '',
        openai_api_key: '',
        gemini_api_key: '',
        enabled: true,
        read_only: true,
        default_model_provider: 'claude',
        rate_limit_requests_per_minute: 60,
        rate_limit_tokens_per_day: 1000000,
        webhook_url: '',
        custom_settings: {}
    });

    React.useEffect(() => {
        loadClients();
        loadModels();
        // Load testing interface component if needed
        if (!window.MCPTestingInterface) {
            const script = document.createElement('script');
            script.src = 'components/MCPTestingInterface.js';
            document.head.appendChild(script);
        }
    }, []);

    const loadClients = async () => {
        try {
            const response = await fetch('/api/mcp/clients', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            if (response.ok) {
                const data = await response.json();
                setClients(data);
            }
        } catch (error) {
            console.error('Error loading MCP clients:', error);
        }
    };

    const loadModels = async () => {
        try {
            const response = await fetch('/api/mcp/models', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            if (response.ok) {
                const data = await response.json();
                setModels(data);
            }
        } catch (error) {
            console.error('Error loading models:', error);
        }
    };

    const loadUsageStats = async (clientId) => {
        try {
            const response = await fetch(`/api/mcp/usage/${clientId}/stats?period=weekly`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            if (response.ok) {
                const data = await response.json();
                setUsageStats(data);
            }
        } catch (error) {
            console.error('Error loading usage stats:', error);
        }
    };

    const handleAddClient = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/mcp/clients', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                await loadClients();
                setShowAddModal(false);
                resetForm();
                alert('MCP client created successfully!');
            } else {
                const error = await response.json();
                alert(`Error: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error creating client:', error);
            alert('Failed to create client');
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateClient = async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/mcp/clients/${selectedClient.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                await loadClients();
                setShowEditModal(false);
                resetForm();
                alert('MCP client updated successfully!');
            } else {
                const error = await response.json();
                alert(`Error: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error updating client:', error);
            alert('Failed to update client');
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteClient = async (clientId) => {
        if (!confirm('Are you sure you want to delete this client?')) return;

        try {
            const response = await fetch(`/api/mcp/clients/${clientId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                await loadClients();
                alert('Client deleted successfully!');
            }
        } catch (error) {
            console.error('Error deleting client:', error);
            alert('Failed to delete client');
        }
    };

    const testConnection = async (clientId, provider) => {
        setLoading(true);
        try {
            const response = await fetch(`/api/mcp/clients/${clientId}/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    client_id: clientId,
                    model_provider: provider,
                    test_query: 'List available tools'
                })
            });

            const result = await response.json();
            setTestResults(prev => ({
                ...prev,
                [`${clientId}:${provider}`]: result
            }));
        } catch (error) {
            console.error('Error testing connection:', error);
            setTestResults(prev => ({
                ...prev,
                [`${clientId}:${provider}`]: { success: false, error: error.message }
            }));
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({
            name: '',
            account_id: '',
            klaviyo_api_key: '',
            openai_api_key: '',
            gemini_api_key: '',
            enabled: true,
            read_only: true,
            default_model_provider: 'claude',
            rate_limit_requests_per_minute: 60,
            rate_limit_tokens_per_day: 1000000,
            webhook_url: '',
            custom_settings: {}
        });
        setSelectedClient(null);
    };

    const openEditModal = (client) => {
        setSelectedClient(client);
        setFormData({
            ...client,
            klaviyo_api_key: '',
            openai_api_key: '',
            gemini_api_key: ''
        });
        setShowEditModal(true);
    };

    const openTestModal = async (client) => {
        setSelectedClient(client);
        setShowTestModal(true);
        await loadUsageStats(client.id);
    };

    // If showing testing interface, render it instead
    if (showTestingInterface && window.MCPTestingInterface) {
        return (
            <div>
                <div className="mb-4">
                    <button
                        onClick={() => setShowTestingInterface(false)}
                        className="text-blue-600 hover:text-blue-800 flex items-center"
                    >
                        ← Back to MCP Management
                    </button>
                </div>
                <window.MCPTestingInterface />
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">MCP Client Management</h2>
                <div className="flex space-x-3">
                    <button
                        onClick={() => setShowTestingInterface(true)}
                        className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 flex items-center"
                    >
                        🧪 Production Testing
                    </button>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    >
                        Add New Client
                    </button>
                </div>
            </div>

            {/* Quick Test Status Banner */}
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4 mb-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h3 className="font-semibold text-gray-900">System Status</h3>
                        <p className="text-sm text-gray-600 mt-1">
                            {clients.length} active clients • {models.length} models available
                        </p>
                    </div>
                    <button
                        onClick={async () => {
                            const response = await fetch('/api/mcp/health', {
                                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                            });
                            if (response.ok) {
                                alert('✅ MCP System is healthy and operational!');
                            } else {
                                alert('⚠️ MCP System health check failed. Run production tests for details.');
                            }
                        }}
                        className="px-4 py-2 bg-white border border-purple-300 text-purple-700 rounded hover:bg-purple-50"
                    >
                        🏥 Quick Health Check
                    </button>
                </div>
            </div>

            {/* Clients Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Account ID
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Status
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Default Provider
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                API Keys
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Usage
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {clients.map(client => (
                            <tr key={client.id}>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-sm font-medium text-gray-900">{client.name}</div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-sm text-gray-500">{client.account_id}</div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                        client.enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                    }`}>
                                        {client.enabled ? 'Enabled' : 'Disabled'}
                                    </span>
                                    {client.read_only && (
                                        <span className="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                                            Read-Only
                                        </span>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-sm text-gray-900">{client.default_model_provider}</div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex space-x-2">
                                        {client.has_klaviyo_key && (
                                            <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                                                Klaviyo
                                            </span>
                                        )}
                                        {client.has_openai_key && (
                                            <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                                                OpenAI
                                            </span>
                                        )}
                                        {client.has_gemini_key && (
                                            <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                                Gemini
                                            </span>
                                        )}
                                    </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-sm text-gray-500">
                                        {client.total_requests} requests
                                        <br />
                                        {(client.total_tokens_used / 1000).toFixed(1)}k tokens
                                    </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                    <button
                                        onClick={() => openTestModal(client)}
                                        className="text-indigo-600 hover:text-indigo-900 mr-3"
                                    >
                                        Test
                                    </button>
                                    <button
                                        onClick={() => openEditModal(client)}
                                        className="text-blue-600 hover:text-blue-900 mr-3"
                                    >
                                        Edit
                                    </button>
                                    <button
                                        onClick={() => handleDeleteClient(client.id)}
                                        className="text-red-600 hover:text-red-900"
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Add/Edit Modal */}
            {(showAddModal || showEditModal) && (
                <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-medium mb-4">
                            {showAddModal ? 'Add New MCP Client' : 'Edit MCP Client'}
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Account ID</label>
                                <input
                                    type="text"
                                    value={formData.account_id}
                                    onChange={(e) => setFormData({...formData, account_id: e.target.value})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                    disabled={showEditModal}
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Klaviyo API Key {showEditModal && '(leave empty to keep current)'}
                                </label>
                                <input
                                    type="password"
                                    value={formData.klaviyo_api_key}
                                    onChange={(e) => setFormData({...formData, klaviyo_api_key: e.target.value})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                    placeholder="pk_..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    OpenAI API Key (Optional)
                                </label>
                                <input
                                    type="password"
                                    value={formData.openai_api_key}
                                    onChange={(e) => setFormData({...formData, openai_api_key: e.target.value})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                    placeholder="sk-..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Gemini API Key (Optional)
                                </label>
                                <input
                                    type="password"
                                    value={formData.gemini_api_key}
                                    onChange={(e) => setFormData({...formData, gemini_api_key: e.target.value})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Default Model Provider</label>
                                <select
                                    value={formData.default_model_provider}
                                    onChange={(e) => setFormData({...formData, default_model_provider: e.target.value})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                >
                                    <option value="claude">Claude</option>
                                    <option value="openai">OpenAI</option>
                                    <option value="gemini">Gemini</option>
                                </select>
                            </div>

                            <div className="flex space-x-4">
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={formData.enabled}
                                        onChange={(e) => setFormData({...formData, enabled: e.target.checked})}
                                        className="mr-2"
                                    />
                                    <span className="text-sm">Enabled</span>
                                </label>

                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={formData.read_only}
                                        onChange={(e) => setFormData({...formData, read_only: e.target.checked})}
                                        className="mr-2"
                                    />
                                    <span className="text-sm">Read-Only Mode</span>
                                </label>
                            </div>
                        </div>

                        <div className="mt-6 flex justify-end space-x-3">
                            <button
                                onClick={() => {
                                    setShowAddModal(false);
                                    setShowEditModal(false);
                                    resetForm();
                                }}
                                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={showAddModal ? handleAddClient : handleUpdateClient}
                                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                                disabled={loading}
                            >
                                {loading ? 'Saving...' : (showAddModal ? 'Add Client' : 'Update Client')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Test Modal */}
            {showTestModal && selectedClient && (
                <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-medium mb-4">
                            Test MCP Connections - {selectedClient.name}
                        </h3>
                        
                        {/* Quick link to full testing interface */}
                        <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded">
                            <p className="text-sm text-purple-700">
                                For comprehensive testing, use the{' '}
                                <button
                                    onClick={() => {
                                        setShowTestModal(false);
                                        setShowTestingInterface(true);
                                    }}
                                    className="underline font-semibold"
                                >
                                    Production Testing Interface
                                </button>
                            </p>
                        </div>

                        {/* Rest of test modal content... */}
                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={() => {
                                    setShowTestModal(false);
                                    setSelectedClient(null);
                                    setUsageStats(null);
                                }}
                                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

// Export component
window.MCPManagementWithTesting = MCPManagementWithTesting;