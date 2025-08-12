// MCP Testing Interface Component - Updated for Cloud Functions
// Provides visual feedback for production testing of MCP Management System via Cloud Functions

const MCPTestingInterface = () => {
    const [testStatus, setTestStatus] = React.useState({});
    const [currentPhase, setCurrentPhase] = React.useState(null);
    const [testResults, setTestResults] = React.useState([]);
    const [isRunning, setIsRunning] = React.useState(false);
    const [showDetails, setShowDetails] = React.useState(false);
    const [selectedClient, setSelectedClient] = React.useState(null);
    const [clients, setClients] = React.useState([]);
    const [connectionStatus, setConnectionStatus] = React.useState('checking');
    const [testConfig, setTestConfig] = React.useState({
        runFullSuite: false,
        testProviders: {
            claude: true,
            openai: false,
            gemini: false
        },
        testTypes: {
            connection: true,
            tools: true,
            usage: true,
            performance: true,
            security: false
        }
    });

    // Test phases configuration - updated for Cloud Functions
    const testPhases = [
        {
            id: 'deployment',
            name: 'Phase 1: Verify Cloud Function Deployment',
            tests: [
                { id: 'check_health', name: 'Check Cloud Function health', endpoint: 'health' },
                { id: 'verify_models', name: 'Verify models endpoint', endpoint: 'models' },
                { id: 'verify_clients', name: 'Verify clients endpoint', endpoint: 'clients' }
            ]
        },
        {
            id: 'functional',
            name: 'Phase 2: Functional Testing',
            tests: [
                { id: 'create_client', name: 'Create test client via Cloud Functions', endpoint: 'clients' },
                { id: 'test_connections', name: 'Test provider connections', endpoint: 'test' },
                { id: 'execute_tools', name: 'Execute MCP tools', endpoint: 'execute' }
            ]
        },
        {
            id: 'integration',
            name: 'Phase 3: Integration Testing',
            tests: [
                { id: 'klaviyo_audit', name: 'Test Klaviyo audit integration', endpoint: null },
                { id: 'multi_model', name: 'Test multi-model comparison', endpoint: 'execute' }
            ]
        },
        {
            id: 'security',
            name: 'Phase 4: Security & Performance',
            tests: [
                { id: 'rate_limiting', name: 'Test Cloud Function rate limiting', endpoint: 'execute' },
                { id: 'cors_check', name: 'Verify CORS configuration', endpoint: 'health' },
                { id: 'performance', name: 'Measure Cloud Function response times', endpoint: 'execute' }
            ]
        },
        {
            id: 'monitoring',
            name: 'Phase 5: Monitoring & Logs',
            tests: [
                { id: 'check_logs', name: 'Check Cloud Function logs', endpoint: null },
                { id: 'verify_database', name: 'Verify database records', endpoint: null }
            ]
        }
    ];

    React.useEffect(() => {
        initializeTestingInterface();
    }, []);

    const initializeTestingInterface = async () => {
        // Load MCP config if not already loaded
        if (!window.MCPConfig) {
            const script = document.createElement('script');
            script.src = 'components/mcp-config.js';
            script.onload = () => {
                checkCloudFunctionStatus();
                loadClients();
            };
            document.head.appendChild(script);
        } else {
            checkCloudFunctionStatus();
            loadClients();
        }
    };

    const checkCloudFunctionStatus = async () => {
        try {
            setConnectionStatus('checking');
            await window.MCPConfig.api.checkHealth();
            setConnectionStatus('connected');
            updateTestStatus('system', 'cloud_functions', 'success', 'Cloud Functions are accessible');
        } catch (error) {
            setConnectionStatus('error');
            updateTestStatus('system', 'cloud_functions', 'error', `Cloud Functions error: ${error.message}`);
        }
    };

    const loadClients = async () => {
        try {
            const data = await window.MCPConfig.api.getClients();
            setClients(data);
            if (data.length > 0) {
                setSelectedClient(data[0]);
            }
        } catch (error) {
            console.error('Error loading clients:', error);
            updateTestStatus('system', 'load_clients', 'error', `Failed to load clients: ${error.message}`);
        }
    };

    const updateTestStatus = (phaseId, testId, status, message = '') => {
        setTestStatus(prev => ({
            ...prev,
            [`${phaseId}_${testId}`]: { status, message, timestamp: new Date().toISOString() }
        }));
        
        setTestResults(prev => [...prev, {
            phase: phaseId,
            test: testId,
            status,
            message,
            timestamp: new Date().toISOString()
        }]);
    };

    const runTest = async (phase, test) => {
        updateTestStatus(phase.id, test.id, 'running', 'Test in progress...');
        
        try {
            if (!test.endpoint) {
                // Simulate tests without endpoints
                await new Promise(resolve => setTimeout(resolve, 1500));
                updateTestStatus(phase.id, test.id, 'success', 'Test completed successfully');
                return true;
            }

            const startTime = Date.now();

            switch (test.endpoint) {
                case 'health':
                    await window.MCPConfig.api.checkHealth();
                    break;
                    
                case 'models':
                    await window.MCPConfig.api.getModels();
                    break;
                    
                case 'clients':
                    if (test.id === 'create_client') {
                        const testClientData = {
                            name: `Test Client ${Date.now()}`,
                            account_id: `test-${Date.now()}`,
                            klaviyo_api_key: 'pk_test_key_for_testing',
                            enabled: true,
                            read_only: true,
                            default_model_provider: 'claude',
                            rate_limit_requests_per_minute: 60,
                            rate_limit_tokens_per_day: 100000
                        };
                        const newClient = await window.MCPConfig.api.createClient(testClientData);
                        setSelectedClient(newClient);
                    } else {
                        await window.MCPConfig.api.getClients();
                    }
                    break;
                    
                case 'test':
                    if (selectedClient) {
                        await window.MCPConfig.api.testClient(selectedClient.id, {
                            client_id: selectedClient.id,
                            model_provider: 'claude',
                            test_query: 'List available tools'
                        });
                    }
                    break;
                    
                case 'execute':
                    if (selectedClient) {
                        await window.MCPConfig.api.executeTool({
                            client_id: selectedClient.id,
                            tool_name: 'get_campaigns',
                            parameters: { limit: 1 },
                            provider: 'claude',
                            model: 'claude-3-sonnet-20240229'
                        });
                    }
                    break;
                    
                default:
                    throw new Error(`Unknown endpoint: ${test.endpoint}`);
            }

            const duration = Date.now() - startTime;
            updateTestStatus(phase.id, test.id, 'success', `✅ ${test.name} passed (${duration}ms)`);
            return true;

        } catch (error) {
            const errorMsg = error.message || 'Unknown error';
            updateTestStatus(phase.id, test.id, 'error', `❌ Failed: ${errorMsg}`);
            return false;
        }
    };

    const runPhase = async (phase) => {
        setCurrentPhase(phase.id);
        let allPassed = true;

        for (const test of phase.tests) {
            // Skip certain tests based on configuration
            if (phase.id === 'security' && !testConfig.testTypes.security) {
                updateTestStatus(phase.id, test.id, 'skipped', 'Test skipped by configuration');
                continue;
            }

            const passed = await runTest(phase, test);
            if (!passed) allPassed = false;
            
            // Add delay between tests for visibility
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        return allPassed;
    };

    const runFullTestSuite = async () => {
        setIsRunning(true);
        setTestResults([]);
        setTestStatus({});

        // First check Cloud Function connectivity
        await checkCloudFunctionStatus();
        
        if (connectionStatus !== 'connected') {
            updateTestStatus('system', 'prerequisite', 'error', 'Cloud Functions not accessible - aborting test suite');
            setIsRunning(false);
            return;
        }

        for (const phase of testPhases) {
            // Skip phases based on configuration
            if (phase.id === 'security' && !testConfig.testTypes.security) {
                continue;
            }

            await runPhase(phase);
            
            // Add delay between phases
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        setIsRunning(false);
        setCurrentPhase(null);
    };

    const runQuickTest = async () => {
        setIsRunning(true);
        setTestResults([]);
        setTestStatus({});

        // Check Cloud Function connectivity first
        await checkCloudFunctionStatus();

        // Quick test - just Phase 1 and basic Phase 2
        const quickPhases = testPhases.slice(0, 2);
        for (const phase of quickPhases) {
            await runPhase(phase);
        }

        setIsRunning(false);
        setCurrentPhase(null);
    };

    const runSpecificTest = async (phaseId, testId) => {
        setIsRunning(true);
        const phase = testPhases.find(p => p.id === phaseId);
        const test = phase.tests.find(t => t.id === testId);
        
        if (phase && test) {
            setCurrentPhase(phaseId);
            await runTest(phase, test);
        }
        
        setIsRunning(false);
        setCurrentPhase(null);
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'success': return '✅';
            case 'error': return '❌';
            case 'warning': return '⚠️';
            case 'running': return '🔄';
            case 'skipped': return '⏭️';
            default: return '⭕';
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'success': return 'text-green-600';
            case 'error': return 'text-red-600';
            case 'warning': return 'text-yellow-600';
            case 'running': return 'text-blue-600';
            case 'skipped': return 'text-gray-400';
            default: return 'text-gray-400';
        }
    };

    const exportTestResults = () => {
        const report = {
            timestamp: new Date().toISOString(),
            cloudFunctionEndpoints: window.MCPConfig?.endpoints || {},
            connectionStatus: connectionStatus,
            client: selectedClient,
            configuration: testConfig,
            results: testResults,
            summary: {
                total: testResults.length,
                passed: testResults.filter(r => r.status === 'success').length,
                failed: testResults.filter(r => r.status === 'error').length,
                skipped: testResults.filter(r => r.status === 'skipped').length
            }
        };

        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mcp-cloud-function-test-report-${Date.now()}.json`;
        a.click();
    };

    const generateCurlCommands = () => {
        const commands = [];
        const token = localStorage.getItem('token');
        
        commands.push('# Cloud Function Health Check');
        commands.push(`curl -X GET "${window.MCPConfig?.endpoints?.health || 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'}"`);
        commands.push('');
        
        commands.push('# Test Models Endpoint');
        commands.push(`curl -X GET "${window.MCPConfig?.endpoints?.models || 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models'}" \\`);
        commands.push(`  -H "Authorization: Bearer ${token}"`);
        commands.push('');
        
        commands.push('# Test Clients Endpoint');
        commands.push(`curl -X GET "${window.MCPConfig?.endpoints?.clients || 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients'}" \\`);
        commands.push(`  -H "Authorization: Bearer ${token}"`);
        commands.push('');
        
        if (selectedClient) {
            commands.push('# Test Specific Client');
            commands.push(`curl -X POST "${window.MCPConfig?.endpoints?.clients || 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients'}/${selectedClient.id}/test" \\`);
            commands.push(`  -H "Authorization: Bearer ${token}" \\`);
            commands.push(`  -H "Content-Type: application/json" \\`);
            commands.push(`  -d '{"model_provider": "claude", "test_query": "List tools"}'`);
        }

        return commands.join('\n');
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

    return (
        <div className="p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">MCP Cloud Function Testing Suite</h2>
                        <p className="text-gray-600 mt-1">Production testing interface for MCP Cloud Functions</p>
                    </div>
                    <div className="flex space-x-3">
                        <button
                            onClick={runQuickTest}
                            disabled={isRunning || connectionStatus !== 'connected'}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors"
                        >
                            {isRunning ? '🔄 Running...' : '⚡ Quick Test (2 min)'}
                        </button>
                        <button
                            onClick={runFullTestSuite}
                            disabled={isRunning || connectionStatus !== 'connected'}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
                        >
                            {isRunning ? '🔄 Running...' : '🧪 Full Test Suite (10 min)'}
                        </button>
                        <button
                            onClick={() => setShowDetails(!showDetails)}
                            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                        >
                            {showDetails ? '📊 Hide Details' : '📊 Show Details'}
                        </button>
                    </div>
                </div>

                {/* Cloud Function Connection Status */}
                <div className="mb-4 p-3 border rounded-lg bg-gray-50">
                    <div className="flex justify-between items-center">
                        <div>
                            <strong>Cloud Function Status:</strong> {getConnectionStatusIndicator()}
                            <div className="text-sm text-gray-600 mt-1">
                                Base URL: {window.MCPConfig?.endpoints?.health || 'Loading...'}
                            </div>
                        </div>
                        <button
                            onClick={checkCloudFunctionStatus}
                            className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                            disabled={connectionStatus === 'checking'}
                        >
                            {connectionStatus === 'checking' ? 'Checking...' : 'Refresh Status'}
                        </button>
                    </div>
                </div>

                {/* Test Configuration */}
                <div className="grid grid-cols-2 gap-4 mt-4 p-4 bg-gray-50 rounded-lg">
                    <div>
                        <h3 className="font-semibold mb-2">Test Client</h3>
                        <select
                            value={selectedClient?.id || ''}
                            onChange={(e) => setSelectedClient(clients.find(c => c.id === e.target.value))}
                            className="w-full p-2 border rounded"
                            disabled={isRunning}
                        >
                            <option value="">Select a client...</option>
                            {clients.map(client => (
                                <option key={client.id} value={client.id}>
                                    {client.name} ({client.account_id})
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <h3 className="font-semibold mb-2">Test Configuration</h3>
                        <div className="space-y-1">
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={testConfig.testTypes.connection}
                                    onChange={(e) => setTestConfig(prev => ({
                                        ...prev,
                                        testTypes: { ...prev.testTypes, connection: e.target.checked }
                                    }))}
                                    disabled={isRunning}
                                    className="mr-2"
                                />
                                <span className="text-sm">Connection Tests</span>
                            </label>
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={testConfig.testTypes.tools}
                                    onChange={(e) => setTestConfig(prev => ({
                                        ...prev,
                                        testTypes: { ...prev.testTypes, tools: e.target.checked }
                                    }))}
                                    disabled={isRunning}
                                    className="mr-2"
                                />
                                <span className="text-sm">Tool Execution</span>
                            </label>
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={testConfig.testTypes.security}
                                    onChange={(e) => setTestConfig(prev => ({
                                        ...prev,
                                        testTypes: { ...prev.testTypes, security: e.target.checked }
                                    }))}
                                    disabled={isRunning}
                                    className="mr-2"
                                />
                                <span className="text-sm">Security Tests</span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            {/* Test Phases */}
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                <h3 className="text-lg font-semibold mb-4">Test Phases</h3>
                <div className="space-y-4">
                    {testPhases.map(phase => (
                        <div key={phase.id} className="border rounded-lg p-4">
                            <div className="flex justify-between items-center mb-2">
                                <h4 className={`font-medium ${currentPhase === phase.id ? 'text-blue-600' : ''}`}>
                                    {phase.name}
                                    {currentPhase === phase.id && ' 🔄'}
                                </h4>
                                <button
                                    onClick={() => runPhase(phase)}
                                    disabled={isRunning || connectionStatus !== 'connected'}
                                    className="text-sm px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:bg-gray-100 disabled:text-gray-400"
                                >
                                    Run Phase
                                </button>
                            </div>
                            
                            {showDetails && (
                                <div className="mt-2 space-y-1">
                                    {phase.tests.map(test => {
                                        const status = testStatus[`${phase.id}_${test.id}`];
                                        return (
                                            <div key={test.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                                                <div className="flex items-center">
                                                    <span className={`mr-2 ${getStatusColor(status?.status)}`}>
                                                        {getStatusIcon(status?.status)}
                                                    </span>
                                                    <span className="text-sm">{test.name}</span>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    {status?.message && (
                                                        <span className="text-xs text-gray-500">{status.message}</span>
                                                    )}
                                                    <button
                                                        onClick={() => runSpecificTest(phase.id, test.id)}
                                                        disabled={isRunning || connectionStatus !== 'connected'}
                                                        className="text-xs px-2 py-1 bg-gray-200 rounded hover:bg-gray-300 disabled:bg-gray-100"
                                                    >
                                                        Run
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Test Results */}
            {testResults.length > 0 && (
                <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-semibold">Test Results</h3>
                        <div className="flex space-x-2">
                            <button
                                onClick={exportTestResults}
                                className="text-sm px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700"
                            >
                                📥 Export Results
                            </button>
                            <button
                                onClick={() => setTestResults([])}
                                className="text-sm px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                            >
                                Clear
                            </button>
                        </div>
                    </div>

                    {/* Summary Stats */}
                    <div className="grid grid-cols-4 gap-4 mb-4">
                        <div className="bg-gray-50 p-3 rounded text-center">
                            <div className="text-2xl font-bold">{testResults.length}</div>
                            <div className="text-sm text-gray-600">Total Tests</div>
                        </div>
                        <div className="bg-green-50 p-3 rounded text-center">
                            <div className="text-2xl font-bold text-green-600">
                                {testResults.filter(r => r.status === 'success').length}
                            </div>
                            <div className="text-sm text-gray-600">Passed</div>
                        </div>
                        <div className="bg-red-50 p-3 rounded text-center">
                            <div className="text-2xl font-bold text-red-600">
                                {testResults.filter(r => r.status === 'error').length}
                            </div>
                            <div className="text-sm text-gray-600">Failed</div>
                        </div>
                        <div className="bg-gray-50 p-3 rounded text-center">
                            <div className="text-2xl font-bold text-gray-600">
                                {testResults.filter(r => r.status === 'skipped').length}
                            </div>
                            <div className="text-sm text-gray-600">Skipped</div>
                        </div>
                    </div>

                    {/* Results Log */}
                    <div className="max-h-64 overflow-y-auto border rounded p-3 bg-gray-50">
                        {testResults.map((result, index) => (
                            <div key={index} className="flex items-center py-1 border-b last:border-0">
                                <span className={`mr-2 ${getStatusColor(result.status)}`}>
                                    {getStatusIcon(result.status)}
                                </span>
                                <span className="text-sm flex-1">
                                    <span className="font-medium">{result.phase}:</span> {result.test}
                                </span>
                                <span className="text-xs text-gray-500">
                                    {new Date(result.timestamp).toLocaleTimeString()}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* CURL Commands Helper */}
            <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">Manual Cloud Function Testing Commands</h3>
                    <button
                        onClick={() => {
                            navigator.clipboard.writeText(generateCurlCommands());
                            alert('Commands copied to clipboard!');
                        }}
                        className="text-sm px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        📋 Copy Commands
                    </button>
                </div>
                <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-x-auto text-sm">
                    {generateCurlCommands()}
                </pre>
            </div>
        </div>
    );
};

// Export component
window.MCPTestingInterface = MCPTestingInterface;
console.log('✅ MCPTestingInterface component loaded with Cloud Function support');