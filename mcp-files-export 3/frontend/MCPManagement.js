// MCP Management Component - Updated for Cloud Functions
// Uses Cloud Function endpoints instead of local /api/mcp/* endpoints

const MCPManagement = () => {
    const [clients, setClients] = React.useState([]);
    const [models, setModels] = React.useState([]);
    const [selectedClient, setSelectedClient] = React.useState(null);
    const [showAddModal, setShowAddModal] = React.useState(false);
    const [showEditModal, setShowEditModal] = React.useState(false);
    const [showTestModal, setShowTestModal] = React.useState(false);
    const [loading, setLoading] = React.useState(false);
    const [testResults, setTestResults] = React.useState({});
    const [usageStats, setUsageStats] = React.useState(null);
    const [connectionStatus, setConnectionStatus] = React.useState('checking');

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
        initializeComponent();
    }, []);

    const initializeComponent = async () => {
        // Load MCP config if not already loaded
        if (!window.MCPConfig) {
            const script = document.createElement('script');
            script.src = 'components/mcp-config.js';
            script.onload = () => {
                checkCloudFunctionConnection();
                loadClients();
                loadModels();
            };
            document.head.appendChild(script);
        } else {
            checkCloudFunctionConnection();
            loadClients();
            loadModels();
        }
    };

    const checkCloudFunctionConnection = async () => {
        try {
            setConnectionStatus('checking');
            await window.MCPConfig.api.checkHealth();
            setConnectionStatus('connected');
            console.log('✅ Cloud Functions are accessible');
        } catch (error) {
            setConnectionStatus('error');
            console.error('❌ Cloud Functions connection failed:', error);
        }
    };

    const loadClients = async () => {
        try {
            const data = await window.MCPConfig.api.getClients();
            setClients(data);
        } catch (error) {
            console.error('Error loading MCP clients:', error);
            // Show user-friendly error
            if (error.message.includes('CORS') || error.message.includes('network')) {
                alert('Unable to connect to MCP system. Please check if Cloud Functions are accessible.');
            }
        }
    };

    const loadModels = async () => {
        try {
            const data = await window.MCPConfig.api.getModels();
            setModels(data);
        } catch (error) {
            console.error('Error loading models:', error);
        }
    };

    const loadUsageStats = async (clientId) => {
        try {
            const data = await window.MCPConfig.api.getUsageStats(clientId);
            setUsageStats(data);
        } catch (error) {
            console.error('Error loading usage stats:', error);
        }
    };

    const handleAddClient = () => {
        // Load the unified client form if not already loaded
        if (!window.UnifiedClientForm) {
            const script = document.createElement('script');
            script.src = 'components/UnifiedClientForm.js';
            script.onload = () => {
                setShowAddModal(true);
                setSelectedClient(null);
            };
            document.head.appendChild(script);
        } else {
            setShowAddModal(true);
            setSelectedClient(null);
        }
    };

    const handleCreateClient = async () => {
        setLoading(true);
        try {
            await window.MCPConfig.api.createClient(formData);
            await loadClients();
            setShowAddModal(false);
            resetForm();
            alert('MCP client created successfully!');
        } catch (error) {
            console.error('Error creating client:', error);
            alert(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateClient = async () => {
        setLoading(true);
        try {
            await window.MCPConfig.api.updateClient(selectedClient.id, formData);
            await loadClients();
            setShowEditModal(false);
            resetForm();
            alert('MCP client updated successfully!');
        } catch (error) {
            console.error('Error updating client:', error);
            alert(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteClient = async (clientId) => {
        if (!confirm('Are you sure you want to delete this client?')) return;

        try {
            await window.MCPConfig.api.deleteClient(clientId);
            await loadClients();
            alert('Client deleted successfully!');
        } catch (error) {
            console.error('Error deleting client:', error);
            alert(`Failed to delete client: ${error.message}`);
        }
    };

    const testConnection = async (clientId, provider) => {
        setLoading(true);
        try {
            const result = await window.MCPConfig.api.testClient(clientId, {
                client_id: clientId,
                model_provider: provider,
                test_query: 'List available tools'
            });

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

    const executeToolTest = async (clientId, provider, model) => {
        setLoading(true);
        try {
            const result = await window.MCPConfig.api.executeTool({
                client_id: clientId,
                tool_name: 'get_campaigns',
                parameters: { limit: 5 },
                provider: provider,
                model: model
            });

            alert(`Tool execution ${result.success ? 'successful' : 'failed'}: ${JSON.stringify(result.result || result.detail)}`);
        } catch (error) {
            console.error('Error executing tool:', error);
            alert(`Failed to execute tool: ${error.message}`);
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
        // Load the unified client form if not already loaded
        if (!window.UnifiedClientForm) {
            const script = document.createElement('script');
            script.src = 'components/UnifiedClientForm.js';
            script.onload = () => {
                setSelectedClient(client);
                setShowEditModal(true);
            };
            document.head.appendChild(script);
        } else {
            setSelectedClient(client);
            setShowEditModal(true);
        }
    };

    const openTestModal = async (client) => {
        setSelectedClient(client);
        setShowTestModal(true);
        await loadUsageStats(client.id);
    };

    const getConnectionStatusIndicator = () => {
        switch (connectionStatus) {
            case 'connected':
                return <span className="text-green-600">🟢 Cloud Functions Connected</span>;
            case 'error':
                return <span className="text-red-600">🔴 Cloud Functions Disconnected</span>;
            case 'checking':
                return <span className="text-yellow-600">🟡 Checking Connection...</span>;
            default:
                return <span className="text-gray-600">⚪ Unknown Status</span>;
        }
    };

    // Load Firestore sync component if not already loaded
    React.useEffect(() => {
        if (!window.MCPFirestoreSync) {
            const script = document.createElement('script');
            script.src = 'components/MCPFirestoreSync.js';
            document.head.appendChild(script);
        }
    }, []);

    return (
        <div className="p-6">
            {/* Connection Status Banner */}
            <div className="mb-4 p-3 border rounded-lg bg-gray-50">
                <div className="flex justify-between items-center">
                    <div>
                        <strong>MCP System Status:</strong> {getConnectionStatusIndicator()}
                        <div className="text-sm text-gray-600 mt-1">
                            Using Cloud Functions: {window.MCPConfig?.endpoints?.clients || 'Loading...'}
                        </div>
                    </div>
                    <button
                        onClick={checkCloudFunctionConnection}
                        className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                        disabled={connectionStatus === 'checking'}
                    >
                        {connectionStatus === 'checking' ? 'Checking...' : 'Refresh Status'}
                    </button>
                </div>
            </div>

            {/* Firestore Sync Component */}
            {window.MCPFirestoreSync && <window.MCPFirestoreSync />}
            
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">MCP Client Management</h2>
                <button
                    onClick={handleAddClient}
                    className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    disabled={connectionStatus !== 'connected'}
                >
                    Add New Client
                </button>
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
                        {clients.length === 0 && connectionStatus === 'connected' ? (
                            <tr>
                                <td colSpan="7" className="px-6 py-4 text-center text-gray-500">
                                    No clients found. Create your first MCP client to get started.
                                </td>
                            </tr>
                        ) : clients.length === 0 && connectionStatus === 'error' ? (
                            <tr>
                                <td colSpan="7" className="px-6 py-4 text-center text-red-500">
                                    Unable to load clients. Please check Cloud Functions connection.
                                </td>
                            </tr>
                        ) : (
                            clients.map(client => (
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
                                            {client.total_requests || 0} requests
                                            <br />
                                            {((client.total_tokens_used || 0) / 1000).toFixed(1)}k tokens
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                        <button
                                            onClick={() => openTestModal(client)}
                                            className="text-indigo-600 hover:text-indigo-900 mr-3"
                                            disabled={connectionStatus !== 'connected'}
                                        >
                                            Test
                                        </button>
                                        <button
                                            onClick={() => openEditModal(client)}
                                            className="text-blue-600 hover:text-blue-900 mr-3"
                                            disabled={connectionStatus !== 'connected'}
                                        >
                                            Edit
                                        </button>
                                        <button
                                            onClick={() => handleDeleteClient(client.id)}
                                            className="text-red-600 hover:text-red-900"
                                            disabled={connectionStatus !== 'connected'}
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Add/Edit Modal - Use Unified Form */}
            {(showAddModal || showEditModal) && window.UnifiedClientForm ? (
                <window.UnifiedClientForm
                    mcpClient={showEditModal ? selectedClient : null}
                    onClose={() => {
                        setShowAddModal(false);
                        setShowEditModal(false);
                        setSelectedClient(null);
                        resetForm();
                    }}
                    onSave={() => {
                        loadClients();
                        setShowAddModal(false);
                        setShowEditModal(false);
                        setSelectedClient(null);
                        resetForm();
                    }}
                    mode="mcp"
                />
            ) : (showAddModal || showEditModal) && !window.UnifiedClientForm ? (
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

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Rate Limit (requests/min)</label>
                                <input
                                    type="number"
                                    value={formData.rate_limit_requests_per_minute}
                                    onChange={(e) => setFormData({...formData, rate_limit_requests_per_minute: parseInt(e.target.value)})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                    min="1"
                                    max="1000"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Daily Token Limit</label>
                                <input
                                    type="number"
                                    value={formData.rate_limit_tokens_per_day}
                                    onChange={(e) => setFormData({...formData, rate_limit_tokens_per_day: parseInt(e.target.value)})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                    min="1000"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">Webhook URL (Optional)</label>
                                <input
                                    type="text"
                                    value={formData.webhook_url}
                                    onChange={(e) => setFormData({...formData, webhook_url: e.target.value})}
                                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
                                    placeholder="https://..."
                                />
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
                                onClick={showAddModal ? handleCreateClient : handleUpdateClient}
                                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                                disabled={loading}
                            >
                                {loading ? 'Saving...' : (showAddModal ? 'Add Client' : 'Update Client')}
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}

            {/* Test Modal */}
            {showTestModal && selectedClient && (
                <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                        <h3 className="text-lg font-medium mb-4">
                            Test MCP Connections - {selectedClient.name}
                        </h3>

                        <div className="space-y-6">
                            {/* Connection Tests */}
                            <div>
                                <h4 className="font-medium mb-3">Test Connections</h4>
                                <div className="grid grid-cols-3 gap-4">
                                    {['claude', 'openai', 'gemini'].map(provider => {
                                        const testKey = `${selectedClient.id}:${provider}`;
                                        const result = testResults[testKey];
                                        const hasKey = provider === 'claude' ? selectedClient.has_klaviyo_key :
                                                      provider === 'openai' ? selectedClient.has_openai_key :
                                                      selectedClient.has_gemini_key;

                                        return (
                                            <div key={provider} className="border rounded-lg p-4">
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className="font-medium capitalize">{provider}</span>
                                                    {hasKey ? (
                                                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                                            Key Configured
                                                        </span>
                                                    ) : (
                                                        <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                                            No Key
                                                        </span>
                                                    )}
                                                </div>

                                                {result && (
                                                    <div className={`text-sm mb-2 ${result.success ? 'text-green-600' : 'text-red-600'}`}>
                                                        {result.success ? result.response : result.error}
                                                    </div>
                                                )}

                                                <button
                                                    onClick={() => testConnection(selectedClient.id, provider)}
                                                    className="w-full px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                                                    disabled={!hasKey || loading}
                                                >
                                                    Test Connection
                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Model Testing */}
                            <div>
                                <h4 className="font-medium mb-3">Test Model Execution</h4>
                                <div className="space-y-2">
                                    {models.filter(m => 
                                        (m.provider === 'claude' && selectedClient.has_klaviyo_key) ||
                                        (m.provider === 'openai' && selectedClient.has_openai_key) ||
                                        (m.provider === 'gemini' && selectedClient.has_gemini_key)
                                    ).map(model => (
                                        <div key={model.id} className="flex items-center justify-between border rounded p-3">
                                            <div>
                                                <span className="font-medium">{model.display_name}</span>
                                                <span className="text-sm text-gray-500 ml-2">({model.provider})</span>
                                                <div className="text-xs text-gray-400">
                                                    ${model.input_cost_per_1k}/1k in, ${model.output_cost_per_1k}/1k out
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => executeToolTest(selectedClient.id, model.provider, model.model_name)}
                                                className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600"
                                                disabled={loading}
                                            >
                                                Test Tool
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Usage Statistics */}
                            {usageStats && (
                                <div>
                                    <h4 className="font-medium mb-3">Weekly Usage Statistics</h4>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="bg-gray-50 rounded p-3">
                                            <div className="text-sm text-gray-500">Total Requests</div>
                                            <div className="text-xl font-bold">{usageStats.total_requests}</div>
                                        </div>
                                        <div className="bg-gray-50 rounded p-3">
                                            <div className="text-sm text-gray-500">Total Tokens</div>
                                            <div className="text-xl font-bold">{(usageStats.total_tokens / 1000).toFixed(1)}k</div>
                                        </div>
                                        <div className="bg-gray-50 rounded p-3">
                                            <div className="text-sm text-gray-500">Total Cost</div>
                                            <div className="text-xl font-bold">${usageStats.total_cost.toFixed(2)}</div>
                                        </div>
                                        <div className="bg-gray-50 rounded p-3">
                                            <div className="text-sm text-gray-500">Success Rate</div>
                                            <div className="text-xl font-bold">{usageStats.success_rate.toFixed(1)}%</div>
                                        </div>
                                    </div>

                                    {usageStats.top_tools && usageStats.top_tools.length > 0 && (
                                        <div className="mt-4">
                                            <h5 className="text-sm font-medium mb-2">Top Tools</h5>
                                            <div className="space-y-1">
                                                {usageStats.top_tools.map(tool => (
                                                    <div key={tool.tool} className="flex justify-between text-sm">
                                                        <span>{tool.tool}</span>
                                                        <span className="text-gray-500">{tool.count} calls ({tool.percentage.toFixed(1)}%)</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

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
window.MCPManagement = MCPManagement;
console.log('✅ MCPManagement component loaded with Cloud Function support');