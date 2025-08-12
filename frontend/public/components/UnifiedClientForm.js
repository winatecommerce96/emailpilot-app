// Unified Client Form Component
// Handles both standard client creation and MCP client configuration
const UnifiedClientForm = ({ client, mcpClient, onClose, onSave, mode = 'standard' }) => {
    const [activeTab, setActiveTab] = React.useState('basic');
    const [formData, setFormData] = React.useState({
        // Basic client data
        name: client?.name || mcpClient?.name || '',
        metric_id: client?.metric_id || '',
        is_active: client?.is_active ?? true,
        
        // MCP-specific data
        account_id: mcpClient?.account_id || '',
        klaviyo_api_key: mcpClient?.klaviyo_api_key || '',
        klaviyo_private_key: client?.klaviyo_private_key || '',
        placed_order_metric_id: client?.placed_order_metric_id || '',
        
        // AI API Keys
        openai_api_key: mcpClient?.openai_api_key || '',
        gemini_api_key: mcpClient?.gemini_api_key || '',
        
        // MCP Settings
        enabled: mcpClient?.enabled ?? true,
        read_only: mcpClient?.read_only ?? true,
        default_model_provider: mcpClient?.default_model_provider || 'claude',
        rate_limit_requests_per_minute: mcpClient?.rate_limit_requests_per_minute || 60,
        rate_limit_tokens_per_day: mcpClient?.rate_limit_tokens_per_day || 1000000,
        webhook_url: mcpClient?.webhook_url || '',
        custom_settings: mcpClient?.custom_settings || {}
    });
    
    const [saving, setSaving] = React.useState(false);
    const [testingConnection, setTestingConnection] = React.useState(false);
    const [connectionStatus, setConnectionStatus] = React.useState({});

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);

        try {
            // Prepare data based on mode
            let clientData = {};
            let mcpData = {};
            
            // Basic client data (always included)
            clientData = {
                name: formData.name,
                metric_id: formData.metric_id,
                is_active: formData.is_active,
                klaviyo_private_key: formData.klaviyo_api_key || formData.klaviyo_private_key,
                placed_order_metric_id: formData.placed_order_metric_id || formData.metric_id
            };
            
            // MCP-specific data (if MCP is enabled)
            if (mode === 'mcp' || formData.klaviyo_api_key) {
                mcpData = {
                    name: formData.name,
                    account_id: formData.account_id || formData.name.toLowerCase().replace(/\s+/g, '_'),
                    klaviyo_api_key: formData.klaviyo_api_key || formData.klaviyo_private_key,
                    openai_api_key: formData.openai_api_key,
                    gemini_api_key: formData.gemini_api_key,
                    enabled: formData.enabled,
                    read_only: formData.read_only,
                    default_model_provider: formData.default_model_provider,
                    rate_limit_requests_per_minute: formData.rate_limit_requests_per_minute,
                    rate_limit_tokens_per_day: formData.rate_limit_tokens_per_day,
                    webhook_url: formData.webhook_url,
                    custom_settings: formData.custom_settings
                };
            }
            
            // Save standard client first
            let clientId = client?.id;
            if (client) {
                // Update existing client
                await axios.put(
                    `${API_BASE_URL}/api/clients/${client.id}`, 
                    clientData,
                    { withCredentials: true }
                );
            } else {
                // Create new client
                const response = await axios.post(
                    `${API_BASE_URL}/api/clients/`, 
                    clientData,
                    { withCredentials: true }
                );
                clientId = response.data.id;
            }
            
            // Save MCP client if API keys are provided
            if (formData.klaviyo_api_key || mcpClient) {
                mcpData.client_id = clientId; // Link to standard client
                
                if (mcpClient) {
                    // Update existing MCP client
                    await fetch(`/api/mcp/clients/${mcpClient.id}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('token')}`
                        },
                        body: JSON.stringify(mcpData)
                    });
                } else {
                    // Create new MCP client
                    await fetch('/api/mcp/clients', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('token')}`
                        },
                        body: JSON.stringify(mcpData)
                    });
                }
            }
            
            alert('Client saved successfully!');
            onSave();
        } catch (error) {
            alert('Failed to save client: ' + (error.response?.data?.detail || error.message || 'Unknown error'));
        } finally {
            setSaving(false);
        }
    };
    
    const testKlaviyoConnection = async () => {
        if (!formData.klaviyo_api_key && !formData.klaviyo_private_key) {
            alert('Please enter a Klaviyo API key first');
            return;
        }
        
        setTestingConnection(true);
        try {
            const response = await fetch('/api/mcp/test-klaviyo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    api_key: formData.klaviyo_api_key || formData.klaviyo_private_key
                })
            });
            
            const result = await response.json();
            setConnectionStatus({
                klaviyo: result.success ? 'success' : 'error',
                message: result.message || (result.success ? 'Connection successful!' : 'Connection failed')
            });
        } catch (error) {
            setConnectionStatus({
                klaviyo: 'error',
                message: 'Failed to test connection'
            });
        } finally {
            setTestingConnection(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">
                        {client || mcpClient ? 'Edit Client' : 'Add New Client'}
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        ✕
                    </button>
                </div>

                {/* Tab Navigation */}
                <div className="border-b border-gray-200 mb-4">
                    <nav className="-mb-px flex space-x-8">
                        <button
                            onClick={() => setActiveTab('basic')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'basic'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            Basic Information
                        </button>
                        <button
                            onClick={() => setActiveTab('klaviyo')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'klaviyo'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            Klaviyo Integration
                        </button>
                        <button
                            onClick={() => setActiveTab('ai')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'ai'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            AI Configuration
                        </button>
                        <button
                            onClick={() => setActiveTab('advanced')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'advanced'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            Advanced Settings
                        </button>
                    </nav>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Basic Information Tab */}
                    {activeTab === 'basic' && (
                        <>
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
                                    Account ID (optional)
                                </label>
                                <input
                                    type="text"
                                    value={formData.account_id}
                                    onChange={(e) => setFormData({...formData, account_id: e.target.value})}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="Auto-generated from name if empty"
                                />
                            </div>

                            <div className="flex items-center">
                                <input
                                    type="checkbox"
                                    id="is_active"
                                    checked={formData.is_active}
                                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                                    className="mr-2"
                                />
                                <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
                                    Active Client
                                </label>
                            </div>
                        </>
                    )}

                    {/* Klaviyo Integration Tab */}
                    {activeTab === 'klaviyo' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Klaviyo Private API Key *
                                </label>
                                <input
                                    type="password"
                                    value={formData.klaviyo_api_key || formData.klaviyo_private_key}
                                    onChange={(e) => setFormData({
                                        ...formData, 
                                        klaviyo_api_key: e.target.value,
                                        klaviyo_private_key: e.target.value
                                    })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="pk_..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Placed Order Metric ID
                                </label>
                                <input
                                    type="text"
                                    value={formData.placed_order_metric_id || formData.metric_id}
                                    onChange={(e) => setFormData({
                                        ...formData, 
                                        placed_order_metric_id: e.target.value,
                                        metric_id: e.target.value
                                    })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="e.g., WcPnCp"
                                />
                            </div>

                            <div className="flex items-center space-x-3">
                                <button
                                    type="button"
                                    onClick={testKlaviyoConnection}
                                    disabled={testingConnection}
                                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                                >
                                    {testingConnection ? 'Testing...' : 'Test Connection'}
                                </button>
                                {connectionStatus.klaviyo && (
                                    <span className={`text-sm ${
                                        connectionStatus.klaviyo === 'success' ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                        {connectionStatus.message}
                                    </span>
                                )}
                            </div>

                            <div className="flex items-center">
                                <input
                                    type="checkbox"
                                    id="enabled"
                                    checked={formData.enabled}
                                    onChange={(e) => setFormData({...formData, enabled: e.target.checked})}
                                    className="mr-2"
                                />
                                <label htmlFor="enabled" className="text-sm font-medium text-gray-700">
                                    Enable MCP Integration
                                </label>
                            </div>

                            <div className="flex items-center">
                                <input
                                    type="checkbox"
                                    id="read_only"
                                    checked={formData.read_only}
                                    onChange={(e) => setFormData({...formData, read_only: e.target.checked})}
                                    className="mr-2"
                                />
                                <label htmlFor="read_only" className="text-sm font-medium text-gray-700">
                                    Read-Only Access (Recommended)
                                </label>
                            </div>
                        </>
                    )}

                    {/* AI Configuration Tab */}
                    {activeTab === 'ai' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Default AI Model
                                </label>
                                <select
                                    value={formData.default_model_provider}
                                    onChange={(e) => setFormData({...formData, default_model_provider: e.target.value})}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                >
                                    <option value="claude">Claude (Recommended)</option>
                                    <option value="openai">OpenAI GPT-4</option>
                                    <option value="gemini">Google Gemini</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    OpenAI API Key (Optional)
                                </label>
                                <input
                                    type="password"
                                    value={formData.openai_api_key}
                                    onChange={(e) => setFormData({...formData, openai_api_key: e.target.value})}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="sk-..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Gemini API Key (Optional)
                                </label>
                                <input
                                    type="password"
                                    value={formData.gemini_api_key}
                                    onChange={(e) => setFormData({...formData, gemini_api_key: e.target.value})}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="AI..."
                                />
                            </div>
                        </>
                    )}

                    {/* Advanced Settings Tab */}
                    {activeTab === 'advanced' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Rate Limit (Requests per Minute)
                                </label>
                                <input
                                    type="number"
                                    value={formData.rate_limit_requests_per_minute}
                                    onChange={(e) => setFormData({...formData, rate_limit_requests_per_minute: parseInt(e.target.value)})}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    min="1"
                                    max="1000"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Daily Token Limit
                                </label>
                                <input
                                    type="number"
                                    value={formData.rate_limit_tokens_per_day}
                                    onChange={(e) => setFormData({...formData, rate_limit_tokens_per_day: parseInt(e.target.value)})}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    min="1000"
                                    max="10000000"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Webhook URL (Optional)
                                </label>
                                <input
                                    type="url"
                                    value={formData.webhook_url}
                                    onChange={(e) => setFormData({...formData, webhook_url: e.target.value})}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                                    placeholder="https://..."
                                />
                            </div>
                        </>
                    )}

                    <div className="flex justify-end space-x-3 border-t pt-4">
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
                            {saving ? 'Saving...' : 'Save Client'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// Export for global use
window.UnifiedClientForm = UnifiedClientForm;