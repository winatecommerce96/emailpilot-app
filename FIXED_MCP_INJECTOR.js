// Fixed MCP Injector - Uses Cloud Function URLs directly
// Paste this in browser console at https://emailpilot.ai

(function() {
    console.log('🚀 Injecting Fixed MCP Management...');
    
    // CORRECT Cloud Function URLs - NO RELATIVE PATHS!
    const DEFAULT_ENDPOINTS = {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    };
    
    // Set global config
    window.MCP_ENDPOINTS = DEFAULT_ENDPOINTS;
    
    // Create MCP component (inline to avoid script loading issues)
    const MCPManagement = ({ isOpen, onClose, endpoints = DEFAULT_ENDPOINTS }) => {
        const [models, setModels] = React.useState([]);
        const [clients, setClients] = React.useState([]);
        const [health, setHealth] = React.useState(null);
        const [loading, setLoading] = React.useState(true);
        const [error, setError] = React.useState(null);

        React.useEffect(() => {
            if (isOpen) {
                loadMCPData();
            }
        }, [isOpen]);

        const loadMCPData = async () => {
            setLoading(true);
            setError(null);
            
            console.log('Loading from Cloud Functions:', endpoints);
            
            try {
                // Direct Cloud Function calls - no proxies!
                const responses = await Promise.all([
                    fetch(endpoints.models, { mode: 'cors' }),
                    fetch(endpoints.clients, { mode: 'cors' }),
                    fetch(endpoints.health, { mode: 'cors' })
                ]);
                
                const [modelsData, clientsData, healthData] = await Promise.all(
                    responses.map(r => r.json())
                );
                
                setModels(modelsData);
                setClients(clientsData);
                setHealth(healthData);
                console.log('✅ Data loaded:', { models: modelsData.length, clients: clientsData.length });
            } catch (err) {
                console.error('❌ Load failed:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        if (!isOpen) return null;

        return React.createElement('div', {
            style: {
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.5)',
                zIndex: 100000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            },
            onClick: onClose
        },
            React.createElement('div', {
                style: {
                    background: 'white',
                    width: '90%',
                    maxWidth: '1200px',
                    maxHeight: '90vh',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
                },
                onClick: (e) => e.stopPropagation()
            },
                React.createElement('div', {
                    style: {
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white',
                        padding: '20px 30px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }
                },
                    React.createElement('h1', { style: { margin: 0 } }, '🤖 MCP Management'),
                    React.createElement('button', {
                        onClick: onClose,
                        style: {
                            background: 'none',
                            border: 'none',
                            color: 'white',
                            fontSize: '30px',
                            cursor: 'pointer'
                        }
                    }, '×')
                ),
                React.createElement('div', {
                    style: {
                        padding: '30px',
                        overflowY: 'auto',
                        maxHeight: 'calc(90vh - 80px)'
                    }
                },
                    error ? 
                        React.createElement('div', {
                            style: {
                                padding: '20px',
                                background: '#fee',
                                color: '#c00',
                                borderRadius: '8px',
                                marginBottom: '20px'
                            }
                        }, 
                            React.createElement('strong', {}, 'Error: '),
                            error,
                            React.createElement('br'),
                            React.createElement('br'),
                            'Cloud Functions URLs:',
                            React.createElement('ul', {},
                                Object.entries(endpoints).map(([key, url]) =>
                                    React.createElement('li', { key }, `${key}: ${url}`)
                                )
                            )
                        ) :
                    loading ? 
                        React.createElement('div', { 
                            style: { textAlign: 'center', padding: '40px' }
                        }, 'Loading MCP data from Cloud Functions...') :
                        React.createElement('div', {},
                            React.createElement('div', {
                                style: {
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                    gap: '20px',
                                    marginBottom: '30px'
                                }
                            },
                                React.createElement('div', {
                                    style: {
                                        background: '#f0fdf4',
                                        padding: '20px',
                                        borderRadius: '8px'
                                    }
                                },
                                    React.createElement('div', { style: { color: '#166534', fontSize: '14px' } }, 'System Status'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#22c55e' }
                                    }, health?.status === 'healthy' ? '✅ Active' : '⚠️ Issues')
                                ),
                                React.createElement('div', {
                                    style: {
                                        background: '#fef3c7',
                                        padding: '20px',
                                        borderRadius: '8px'
                                    }
                                },
                                    React.createElement('div', { style: { color: '#78350f', fontSize: '14px' } }, 'Available Models'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#f59e0b' }
                                    }, models.length)
                                ),
                                React.createElement('div', {
                                    style: {
                                        background: '#ede9fe',
                                        padding: '20px',
                                        borderRadius: '8px'
                                    }
                                },
                                    React.createElement('div', { style: { color: '#4c1d95', fontSize: '14px' } }, 'Active Clients'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#8b5cf6' }
                                    }, clients.length)
                                )
                            ),
                            React.createElement('h2', { style: { marginBottom: '20px' } }, 'Available AI Models'),
                            React.createElement('div', { style: { display: 'grid', gap: '15px' } },
                                models.map(model => 
                                    React.createElement('div', {
                                        key: model.id,
                                        style: {
                                            padding: '20px',
                                            background: '#f8fafc',
                                            borderRadius: '8px',
                                            border: '1px solid #e2e8f0',
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center'
                                        }
                                    },
                                        React.createElement('div', {},
                                            React.createElement('h3', { 
                                                style: { margin: '0 0 10px 0' }
                                            }, model.display_name),
                                            React.createElement('p', { 
                                                style: { margin: 0, color: '#64748b' }
                                            }, `Provider: ${model.provider} | Model: ${model.model_name}`)
                                        ),
                                        React.createElement('div', {
                                            style: {
                                                padding: '6px 12px',
                                                background: '#dcfce7',
                                                color: '#166534',
                                                borderRadius: '20px',
                                                fontSize: '12px',
                                                fontWeight: '600'
                                            }
                                        }, 'ACTIVE')
                                    )
                                )
                            ),
                            React.createElement('div', { style: { marginTop: '30px' } },
                                React.createElement('button', {
                                    onClick: loadMCPData,
                                    style: {
                                        padding: '10px 20px',
                                        background: '#667eea',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        marginRight: '10px'
                                    }
                                }, '🔄 Refresh Data'),
                                React.createElement('button', {
                                    onClick: () => {
                                        console.log('Endpoints:', endpoints);
                                        console.log('Models:', models);
                                        console.log('Health:', health);
                                    },
                                    style: {
                                        padding: '10px 20px',
                                        background: '#10b981',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer'
                                    }
                                }, '📋 Log to Console')
                            )
                        )
                )
            )
        );
    };
    
    // Store component globally
    window.MCPManagement = MCPManagement;
    
    // Create button component
    const MCPButton = () => {
        const [showMCP, setShowMCP] = React.useState(false);
        
        return React.createElement(React.Fragment, {},
            React.createElement('button', {
                onClick: () => setShowMCP(true),
                style: {
                    position: 'fixed',
                    top: '20px',
                    right: '20px',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    border: 'none',
                    padding: '12px 24px',
                    borderRadius: '8px',
                    fontSize: '16px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    zIndex: 99999,
                    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
                    transition: 'transform 0.2s'
                },
                onMouseOver: (e) => e.target.style.transform = 'scale(1.05)',
                onMouseOut: (e) => e.target.style.transform = 'scale(1)'
            }, '🤖 MCP Management'),
            React.createElement(MCPManagement, {
                isOpen: showMCP,
                onClose: () => setShowMCP(false),
                endpoints: DEFAULT_ENDPOINTS
            })
        );
    };
    
    // Mount the button
    function mountMCP() {
        // Remove existing if any
        const existing = document.getElementById('mcp-root');
        if (existing) {
            existing.remove();
        }
        
        // Create mount point
        const mount = document.createElement('div');
        mount.id = 'mcp-root';
        document.body.appendChild(mount);
        
        // Check React version and mount appropriately
        if (window.React && window.ReactDOM) {
            if (ReactDOM.createRoot) {
                // React 18
                ReactDOM.createRoot(mount).render(React.createElement(MCPButton));
                console.log('✅ MCP mounted with React 18');
            } else {
                // React 17 or earlier
                ReactDOM.render(React.createElement(MCPButton), mount);
                console.log('✅ MCP mounted with React 17');
            }
        } else {
            console.error('❌ React not found! Make sure React is loaded on the page.');
        }
    }
    
    // Wait for React if needed
    if (typeof React === 'undefined' || typeof ReactDOM === 'undefined') {
        console.log('⏳ Waiting for React...');
        let attempts = 0;
        const waitForReact = setInterval(() => {
            attempts++;
            if (window.React && window.ReactDOM) {
                clearInterval(waitForReact);
                mountMCP();
            } else if (attempts > 20) {
                clearInterval(waitForReact);
                console.error('❌ React not found after 10 seconds');
            }
        }, 500);
    } else {
        mountMCP();
    }
    
    console.log('📍 Cloud Function endpoints configured:');
    console.log('  Models:', DEFAULT_ENDPOINTS.models);
    console.log('  Clients:', DEFAULT_ENDPOINTS.clients);
    console.log('  Health:', DEFAULT_ENDPOINTS.health);
})();