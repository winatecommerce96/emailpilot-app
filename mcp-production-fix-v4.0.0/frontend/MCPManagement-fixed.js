// MCP Management Component - FIXED VERSION 4.0
// This version uses DIRECT Cloud Function URLs - NO PROXY DEPENDENCIES

(function(global) {
    'use strict';
    
    // CRITICAL FIX: Use direct Cloud Function URLs, not /api/* paths
    const CLOUD_FUNCTION_ENDPOINTS = {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    };
    
    // Component definition
    const MCPManagement = ({ isOpen, onClose }) => {
        // Use environment variables if available, otherwise use Cloud Functions directly
        const endpoints = (typeof process !== 'undefined' && process.env) ? {
            models: process.env.REACT_APP_MCP_MODELS_URL || CLOUD_FUNCTION_ENDPOINTS.models,
            clients: process.env.REACT_APP_MCP_CLIENTS_URL || CLOUD_FUNCTION_ENDPOINTS.clients,
            health: process.env.REACT_APP_MCP_HEALTH_URL || CLOUD_FUNCTION_ENDPOINTS.health
        } : CLOUD_FUNCTION_ENDPOINTS;
        
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
            
            console.log('MCP: Loading data from Cloud Functions:', endpoints);
            
            try {
                // CRITICAL: Use full URLs with CORS mode
                const [modelsRes, clientsRes, healthRes] = await Promise.all([
                    fetch(endpoints.models, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        },
                        mode: 'cors' // CRITICAL for cross-origin
                    }),
                    fetch(endpoints.clients, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        },
                        mode: 'cors'
                    }),
                    fetch(endpoints.health, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        },
                        mode: 'cors'
                    })
                ]);
                
                // Check responses
                if (!modelsRes.ok) {
                    throw new Error(`Models API failed: ${modelsRes.status} ${modelsRes.statusText}`);
                }
                if (!clientsRes.ok) {
                    throw new Error(`Clients API failed: ${clientsRes.status} ${clientsRes.statusText}`);
                }
                if (!healthRes.ok) {
                    throw new Error(`Health API failed: ${healthRes.status} ${healthRes.statusText}`);
                }
                
                // Parse JSON
                const modelsData = await modelsRes.json();
                const clientsData = await clientsRes.json();
                const healthData = await healthRes.json();
                
                setModels(modelsData);
                setClients(clientsData);
                setHealth(healthData);
                
                console.log('MCP: Data loaded successfully', {
                    models: modelsData.length,
                    clients: clientsData.length,
                    health: healthData.status
                });
            } catch (err) {
                console.error('MCP: Error loading data:', err);
                setError(`Failed to load MCP data: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };
        
        if (!isOpen) return null;
        
        // Render UI
        return React.createElement('div', {
            className: 'mcp-overlay',
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
                className: 'mcp-modal',
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
                // Header
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
                // Content
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
                                background: '#fef2f2',
                                color: '#991b1b',
                                borderRadius: '8px',
                                border: '1px solid #ef4444'
                            }
                        }, 
                            React.createElement('strong', {}, '⚠️ Error: '),
                            error,
                            React.createElement('br'),
                            React.createElement('br'),
                            'Please check the browser console for details.'
                        ) :
                    loading ? 
                        React.createElement('div', {
                            style: { textAlign: 'center', padding: '40px' }
                        }, 'Loading MCP data from Cloud Functions...') :
                        React.createElement('div', {},
                            // Stats Grid
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
                                        borderRadius: '8px',
                                        border: '1px solid #86efac'
                                    }
                                },
                                    React.createElement('div', { 
                                        style: { color: '#166534', fontSize: '14px' }
                                    }, 'System Status'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#22c55e' }
                                    }, health?.status === 'healthy' ? '✅ Active' : '⚠️ Issues')
                                ),
                                React.createElement('div', {
                                    style: {
                                        background: '#fef3c7',
                                        padding: '20px',
                                        borderRadius: '8px',
                                        border: '1px solid #fde047'
                                    }
                                },
                                    React.createElement('div', { 
                                        style: { color: '#78350f', fontSize: '14px' }
                                    }, 'Available Models'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#f59e0b' }
                                    }, models.length)
                                ),
                                React.createElement('div', {
                                    style: {
                                        background: '#ede9fe',
                                        padding: '20px',
                                        borderRadius: '8px',
                                        border: '1px solid #c4b5fd'
                                    }
                                },
                                    React.createElement('div', { 
                                        style: { color: '#4c1d95', fontSize: '14px' }
                                    }, 'Active Clients'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#8b5cf6' }
                                    }, clients.length)
                                )
                            ),
                            // Models List
                            React.createElement('h2', { style: { marginBottom: '20px' } }, 'Available AI Models'),
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
                                        React.createElement('h3', { 
                                            style: { margin: '0 0 10px 0' }
                                        }, model.display_name),
                                        React.createElement('p', { 
                                            style: { margin: 0, color: '#64748b' }
                                        }, `Provider: ${model.provider} | Model: ${model.model_name}`)
                                    )
                                )
                            ),
                            // Action Buttons
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
                                }, '🔄 Refresh Data')
                            )
                        )
                )
            )
        );
    };
    
    // Export for various environments
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = MCPManagement;
    }
    if (typeof window !== 'undefined') {
        window.MCPManagement = MCPManagement;
    }
    
})(typeof window !== 'undefined' ? window : global);