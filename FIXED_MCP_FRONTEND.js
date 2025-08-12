// Fixed MCP Management Component - Direct Cloud Function URLs
// This version uses Cloud Function URLs directly, not relative paths

const MCPManagement = ({ isOpen, onClose, endpoints }) => {
    // Default to Cloud Function endpoints - NO RELATIVE PATHS!
    const DEFAULT_ENDPOINTS = {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    };
    
    // Use passed endpoints, window config, env vars, or defaults
    const MCP_ENDPOINTS = endpoints || 
                          window.MCP_ENDPOINTS || 
                          (typeof process !== 'undefined' && process.env ? {
                              models: process.env.REACT_APP_MCP_MODELS || DEFAULT_ENDPOINTS.models,
                              clients: process.env.REACT_APP_MCP_CLIENTS || DEFAULT_ENDPOINTS.clients,
                              health: process.env.REACT_APP_MCP_HEALTH || DEFAULT_ENDPOINTS.health
                          } : DEFAULT_ENDPOINTS);
    
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
        
        console.log('Loading MCP data from:', MCP_ENDPOINTS);
        
        try {
            // Use the ACTUAL Cloud Function URLs, not /api/mcp/*
            const [modelsRes, clientsRes, healthRes] = await Promise.all([
                fetch(MCP_ENDPOINTS.models, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    mode: 'cors'
                }),
                fetch(MCP_ENDPOINTS.clients, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    mode: 'cors'
                }),
                fetch(MCP_ENDPOINTS.health, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    mode: 'cors'
                })
            ]);
            
            if (!modelsRes.ok) throw new Error(`Models API failed: ${modelsRes.status}`);
            if (!clientsRes.ok) throw new Error(`Clients API failed: ${clientsRes.status}`);
            if (!healthRes.ok) throw new Error(`Health API failed: ${healthRes.status}`);
            
            const modelsData = await modelsRes.json();
            const clientsData = await clientsRes.json();
            const healthData = await healthRes.json();
            
            setModels(modelsData);
            setClients(clientsData);
            setHealth(healthData);
            
            console.log('✅ MCP data loaded successfully');
        } catch (error) {
            console.error('❌ Error loading MCP data:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return React.createElement('div', {
        className: 'mcp-overlay',
        onClick: onClose,
        style: {
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        }
    },
        React.createElement('div', {
            className: 'mcp-modal',
            onClick: (e) => e.stopPropagation(),
            style: {
                background: 'white',
                width: '90%',
                maxWidth: '1200px',
                maxHeight: '90vh',
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
            }
        },
            React.createElement('div', {
                style: {
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    padding: '20px 30px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
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
                            borderRadius: '8px'
                        }
                    }, `Error: ${error}`) :
                loading ? 
                    React.createElement('div', {}, 'Loading MCP data...') :
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
                                React.createElement('div', {}, 'System Status'),
                                React.createElement('div', { 
                                    style: { fontSize: '24px', fontWeight: 'bold' } 
                                }, health?.status === 'healthy' ? '✅ Active' : '⚠️ Issues')
                            ),
                            React.createElement('div', {
                                style: {
                                    background: '#fef3c7',
                                    padding: '20px',
                                    borderRadius: '8px'
                                }
                            },
                                React.createElement('div', {}, 'Available Models'),
                                React.createElement('div', { 
                                    style: { fontSize: '24px', fontWeight: 'bold' } 
                                }, models.length)
                            ),
                            React.createElement('div', {
                                style: {
                                    background: '#ede9fe',
                                    padding: '20px',
                                    borderRadius: '8px'
                                }
                            },
                                React.createElement('div', {}, 'Active Clients'),
                                React.createElement('div', { 
                                    style: { fontSize: '24px', fontWeight: 'bold' } 
                                }, clients.length)
                            )
                        ),
                        React.createElement('h2', {}, 'Available AI Models'),
                        React.createElement('div', { style: { display: 'grid', gap: '15px' } },
                            models.map(model => 
                                React.createElement('div', {
                                    key: model.id,
                                    style: {
                                        padding: '20px',
                                        background: '#f8fafc',
                                        borderRadius: '8px',
                                        border: '1px solid #e2e8f0'
                                    }
                                },
                                    React.createElement('h3', {}, model.display_name),
                                    React.createElement('p', {}, `Provider: ${model.provider} | Model: ${model.model_name}`)
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
                                    cursor: 'pointer'
                                }
                            }, 'Refresh Data')
                        )
                    )
            )
        )
    );
};

// Export for use
if (typeof window !== 'undefined') {
    window.MCPManagement = MCPManagement;
}