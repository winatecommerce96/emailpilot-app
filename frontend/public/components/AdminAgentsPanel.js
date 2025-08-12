// Admin Agents Panel - Multi-Agent Configuration Interface
const { useState, useEffect, useCallback } = React;

const AdminAgentsPanel = () => {
    const [activeTab, setActiveTab] = useState('overview');
    const [agents, setAgents] = useState({});
    const [selectedAgent, setSelectedAgent] = useState(null);
    const [editMode, setEditMode] = useState(false);
    const [testMode, setTestMode] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [config, setConfig] = useState({});
    const [templates, setTemplates] = useState({});
    const [metrics, setMetrics] = useState({});

    // Fetch agent configuration
    const fetchConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/agents/admin/config');
            if (response.ok) {
                const data = await response.json();
                setConfig(data.custom_config || data.default_config || {});
                setAgents(data.custom_config?.agents || data.default_config?.agents || {});
            }
        } catch (error) {
            console.error('Error fetching config:', error);
            setMessage({ type: 'error', text: 'Failed to load configuration' });
        } finally {
            setLoading(false);
        }
    };

    // Fetch templates
    const fetchTemplates = async () => {
        try {
            const response = await fetch('/api/agents/admin/templates');
            if (response.ok) {
                const data = await response.json();
                setTemplates(data);
            }
        } catch (error) {
            console.error('Error fetching templates:', error);
        }
    };

    // Fetch performance metrics
    const fetchMetrics = async () => {
        try {
            const response = await fetch('/api/agents/admin/performance');
            if (response.ok) {
                const data = await response.json();
                setMetrics(data);
            }
        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    };

    useEffect(() => {
        fetchConfig();
        fetchTemplates();
        fetchMetrics();
    }, []);

    // Save agent configuration
    const saveConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/agents/admin/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...config, agents })
            });
            
            if (response.ok) {
                setMessage({ type: 'success', text: 'Configuration saved successfully!' });
                setEditMode(false);
            } else {
                throw new Error('Failed to save configuration');
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to save configuration' });
        } finally {
            setLoading(false);
        }
    };

    // Update specific agent instructions
    const updateAgentInstructions = async (agentName, instructions) => {
        setLoading(true);
        try {
            const response = await fetch(`/api/agents/admin/instructions/${agentName}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(instructions)
            });
            
            if (response.ok) {
                setMessage({ type: 'success', text: `${agentName} instructions updated!` });
                fetchConfig(); // Reload configuration
            } else {
                throw new Error('Failed to update instructions');
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to update instructions' });
        } finally {
            setLoading(false);
        }
    };

    // Apply template
    const applyTemplate = async (templateName) => {
        if (!confirm(`Apply ${templateName} template? This will update agent instructions.`)) {
            return;
        }
        
        setLoading(true);
        try {
            const response = await fetch('/api/agents/admin/templates/apply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_name: templateName })
            });
            
            if (response.ok) {
                setMessage({ type: 'success', text: `Template ${templateName} applied!` });
                fetchConfig(); // Reload configuration
            } else {
                throw new Error('Failed to apply template');
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to apply template' });
        } finally {
            setLoading(false);
        }
    };

    // Test agent configuration
    const testConfiguration = async () => {
        setLoading(true);
        try {
            const testData = {
                campaign_type: "promotional",
                target_audience: "test audience",
                objectives: ["increase_sales", "drive_engagement"]
            };
            
            const response = await fetch('/api/agents/admin/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(testData)
            });
            
            if (response.ok) {
                const result = await response.json();
                setMessage({ type: 'success', text: 'Test completed successfully!' });
                console.log('Test result:', result);
                // You could show test results in a modal
            } else {
                throw new Error('Test failed');
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Test failed' });
        } finally {
            setLoading(false);
        }
    };

    // Reset to defaults
    const resetToDefaults = async () => {
        if (!confirm('Reset all instructions to defaults? This cannot be undone.')) {
            return;
        }
        
        setLoading(true);
        try {
            const response = await fetch('/api/agents/admin/reset', {
                method: 'POST'
            });
            
            if (response.ok) {
                setMessage({ type: 'success', text: 'Reset to defaults successful!' });
                fetchConfig();
            } else {
                throw new Error('Reset failed');
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to reset' });
        } finally {
            setLoading(false);
        }
    };

    // Agent card component
    const AgentCard = ({ name, agent }) => (
        <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900">{name}</h3>
                    <p className="text-sm text-gray-600">{agent.role}</p>
                </div>
                <button
                    onClick={() => {
                        setSelectedAgent({ name, ...agent });
                        setEditMode(true);
                    }}
                    className="text-blue-600 hover:text-blue-800"
                >
                    <i className="fas fa-edit"></i>
                </button>
            </div>
            
            <div className="space-y-2">
                <div className="text-sm">
                    <span className="font-medium text-gray-700">Expertise:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                        {agent.expertise?.map((exp, i) => (
                            <span key={i} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                                {exp}
                            </span>
                        ))}
                    </div>
                </div>
                
                {agent.responsibilities && (
                    <div className="text-sm">
                        <span className="font-medium text-gray-700">Responsibilities:</span>
                        <ul className="list-disc list-inside text-gray-600 text-xs mt-1">
                            {agent.responsibilities.slice(0, 3).map((resp, i) => (
                                <li key={i}>{resp}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
            
            {metrics.by_agent?.[name] && (
                <div className="mt-4 pt-4 border-t">
                    <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                            <span className="text-gray-500">Executions:</span>
                            <p className="font-semibold">{metrics.by_agent[name].executions || 0}</p>
                        </div>
                        <div>
                            <span className="text-gray-500">Confidence:</span>
                            <p className="font-semibold">{(metrics.by_agent[name].average_confidence || 0).toFixed(2)}</p>
                        </div>
                        <div>
                            <span className="text-gray-500">Avg Time:</span>
                            <p className="font-semibold">{(metrics.by_agent[name].average_time || 0).toFixed(1)}s</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );

    // Edit modal component
    const EditModal = () => {
        const [instructions, setInstructions] = useState(
            JSON.stringify(selectedAgent || {}, null, 2)
        );

        if (!selectedAgent) return null;

        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
                    <div className="p-6 border-b">
                        <div className="flex justify-between items-center">
                            <h2 className="text-xl font-semibold">
                                Edit Agent: {selectedAgent.name}
                            </h2>
                            <button
                                onClick={() => {
                                    setSelectedAgent(null);
                                    setEditMode(false);
                                }}
                                className="text-gray-500 hover:text-gray-700"
                            >
                                <i className="fas fa-times text-xl"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 200px)' }}>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Agent Instructions (JSON)
                            </label>
                            <textarea
                                value={instructions}
                                onChange={(e) => setInstructions(e.target.value)}
                                className="w-full h-96 p-3 border rounded-lg font-mono text-sm"
                                spellCheck="false"
                            />
                        </div>
                        
                        <div className="text-sm text-gray-600 mb-4">
                            <p className="font-medium mb-2">Available Fields:</p>
                            <ul className="list-disc list-inside space-y-1">
                                <li><code>role</code> - Agent's primary role</li>
                                <li><code>expertise</code> - Array of expertise areas</li>
                                <li><code>responsibilities</code> - Array of key responsibilities</li>
                                <li><code>output_format</code> - Expected output structure</li>
                                <li><code>collaboration_with</code> - Other agents to work with</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div className="p-6 border-t flex justify-end space-x-3">
                        <button
                            onClick={() => {
                                setSelectedAgent(null);
                                setEditMode(false);
                            }}
                            className="px-4 py-2 text-gray-700 bg-gray-200 rounded hover:bg-gray-300"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => {
                                try {
                                    const parsed = JSON.parse(instructions);
                                    updateAgentInstructions(selectedAgent.name, parsed);
                                    setSelectedAgent(null);
                                    setEditMode(false);
                                } catch (error) {
                                    alert('Invalid JSON format');
                                }
                            }}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                            disabled={loading}
                        >
                            Save Changes
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white shadow-sm border-b">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center py-4">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">
                                Email/SMS Multi-Agent Configuration
                            </h1>
                            <p className="text-sm text-gray-600 mt-1">
                                Manage agent instructions and test campaign creation
                            </p>
                        </div>
                        <div className="flex space-x-3">
                            <button
                                onClick={testConfiguration}
                                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                                disabled={loading}
                            >
                                <i className="fas fa-play mr-2"></i>
                                Test Agents
                            </button>
                            <button
                                onClick={resetToDefaults}
                                className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                                disabled={loading}
                            >
                                <i className="fas fa-undo mr-2"></i>
                                Reset to Defaults
                            </button>
                            <button
                                onClick={saveConfig}
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                disabled={loading}
                            >
                                <i className="fas fa-save mr-2"></i>
                                Save All Changes
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="bg-white border-b">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex space-x-8">
                        <button
                            onClick={() => setActiveTab('overview')}
                            className={`py-3 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'overview' 
                                    ? 'border-blue-500 text-blue-600' 
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            <i className="fas fa-th-large mr-2"></i>
                            Overview
                        </button>
                        <button
                            onClick={() => setActiveTab('agents')}
                            className={`py-3 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'agents' 
                                    ? 'border-blue-500 text-blue-600' 
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            <i className="fas fa-robot mr-2"></i>
                            Agents
                        </button>
                        <button
                            onClick={() => setActiveTab('templates')}
                            className={`py-3 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'templates' 
                                    ? 'border-blue-500 text-blue-600' 
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            <i className="fas fa-file-alt mr-2"></i>
                            Templates
                        </button>
                        <button
                            onClick={() => setActiveTab('metrics')}
                            className={`py-3 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'metrics' 
                                    ? 'border-blue-500 text-blue-600' 
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            <i className="fas fa-chart-line mr-2"></i>
                            Metrics
                        </button>
                    </div>
                </div>
            </div>

            {/* Messages */}
            {message && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
                    <div className={`p-4 rounded-lg ${
                        message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                        {message.text}
                        <button
                            onClick={() => setMessage(null)}
                            className="float-right"
                        >
                            <i className="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {loading && (
                    <div className="text-center py-12">
                        <i className="fas fa-spinner fa-spin text-4xl text-blue-600"></i>
                        <p className="mt-4 text-gray-600">Loading...</p>
                    </div>
                )}

                {!loading && activeTab === 'overview' && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center">
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">Total Agents</p>
                                        <p className="text-2xl font-bold text-gray-900">
                                            {Object.keys(agents).length}
                                        </p>
                                    </div>
                                    <i className="fas fa-robot text-3xl text-blue-500"></i>
                                </div>
                            </div>
                            
                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center">
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">Total Campaigns</p>
                                        <p className="text-2xl font-bold text-gray-900">
                                            {metrics.overall?.total_campaigns || 0}
                                        </p>
                                    </div>
                                    <i className="fas fa-envelope text-3xl text-green-500"></i>
                                </div>
                            </div>
                            
                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center">
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">Avg Confidence</p>
                                        <p className="text-2xl font-bold text-gray-900">
                                            {(metrics.overall?.average_confidence || 0).toFixed(2)}
                                        </p>
                                    </div>
                                    <i className="fas fa-chart-line text-3xl text-purple-500"></i>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-lg shadow p-6">
                            <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <button
                                    onClick={() => setActiveTab('agents')}
                                    className="p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition"
                                >
                                    <i className="fas fa-edit text-blue-600 text-xl mb-2"></i>
                                    <p className="text-sm font-medium">Edit Agents</p>
                                </button>
                                <button
                                    onClick={() => setActiveTab('templates')}
                                    className="p-4 bg-green-50 rounded-lg hover:bg-green-100 transition"
                                >
                                    <i className="fas fa-file-import text-green-600 text-xl mb-2"></i>
                                    <p className="text-sm font-medium">Apply Template</p>
                                </button>
                                <button
                                    onClick={testConfiguration}
                                    className="p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition"
                                >
                                    <i className="fas fa-vial text-purple-600 text-xl mb-2"></i>
                                    <p className="text-sm font-medium">Test Config</p>
                                </button>
                                <button
                                    onClick={() => setActiveTab('metrics')}
                                    className="p-4 bg-yellow-50 rounded-lg hover:bg-yellow-100 transition"
                                >
                                    <i className="fas fa-chart-bar text-yellow-600 text-xl mb-2"></i>
                                    <p className="text-sm font-medium">View Metrics</p>
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {!loading && activeTab === 'agents' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {Object.entries(agents).map(([name, agent]) => (
                            <AgentCard key={name} name={name} agent={agent} />
                        ))}
                    </div>
                )}

                {!loading && activeTab === 'templates' && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {Object.entries(templates).map(([name, template]) => (
                            <div key={name} className="bg-white rounded-lg shadow p-6">
                                <h3 className="text-lg font-semibold mb-2">{template.name}</h3>
                                <p className="text-sm text-gray-600 mb-4">{template.description}</p>
                                <button
                                    onClick={() => applyTemplate(name)}
                                    className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                >
                                    Apply Template
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {!loading && activeTab === 'metrics' && (
                    <div className="space-y-6">
                        <div className="bg-white rounded-lg shadow p-6">
                            <h2 className="text-lg font-semibold mb-4">Performance by Agent</h2>
                            <div className="overflow-x-auto">
                                <table className="min-w-full">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Agent
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Executions
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Avg Confidence
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Avg Time
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {Object.entries(metrics.by_agent || {}).map(([name, data]) => (
                                            <tr key={name}>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                    {name}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {data.executions || 0}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {(data.average_confidence || 0).toFixed(2)}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {(data.average_time || 0).toFixed(1)}s
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Edit Modal */}
            {editMode && <EditModal />}
        </div>
    );
};

// Make component available globally
window.AdminAgentsPanel = AdminAgentsPanel;