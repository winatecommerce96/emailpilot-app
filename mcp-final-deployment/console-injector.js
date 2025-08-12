// MCP Management System - Console Injector
// FIXED VERSION - Uses Cloud Function URLs directly, not relative paths
// Paste this entire script in browser console at https://emailpilot.ai

(function() {
    console.log('🚀 Injecting MCP Management System (FIXED VERSION)...');
    console.log('📍 Using Cloud Function URLs directly (not /api/mcp/*)');
    
    // CRITICAL FIX: Direct Cloud Function URLs - NO RELATIVE PATHS!
    const MCP_ENDPOINTS = {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients', 
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    };
    
    // Store globally for debugging
    window.MCP_ENDPOINTS = MCP_ENDPOINTS;
    
    console.log('🔧 Configured endpoints:');
    Object.entries(MCP_ENDPOINTS).forEach(([key, url]) => {
        console.log(`  ${key}: ${url}`);
    });
    
    // MCP Management Component (fixed version)
    const MCPManagement = ({ isOpen, onClose }) => {
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
            
            console.log('📡 Loading MCP data from Cloud Functions...');
            console.log('🎯 Endpoints:', MCP_ENDPOINTS);
            
            try {
                // CRITICAL FIX: Direct Cloud Function calls with proper CORS
                const requests = [
                    fetch(MCP_ENDPOINTS.models, {
                        method: 'GET',
                        mode: 'cors',  // CRITICAL: Proper CORS mode
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }
                    }),
                    fetch(MCP_ENDPOINTS.clients, {
                        method: 'GET', 
                        mode: 'cors',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }
                    }),
                    fetch(MCP_ENDPOINTS.health, {
                        method: 'GET',
                        mode: 'cors',
                        headers: {
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        }
                    })
                ];
                
                console.log('⏳ Executing parallel requests...');
                const responses = await Promise.all(requests);
                
                // Check response status
                for (let i = 0; i < responses.length; i++) {
                    const response = responses[i];
                    const endpoint = Object.keys(MCP_ENDPOINTS)[i];
                    
                    if (!response.ok) {
                        throw new Error(`${endpoint} API failed: ${response.status} ${response.statusText}`);
                    }
                    console.log(`✅ ${endpoint}: ${response.status} OK`);
                }
                
                // Parse JSON responses
                const [modelsData, clientsData, healthData] = await Promise.all(
                    responses.map(response => response.json())
                );
                
                setModels(Array.isArray(modelsData) ? modelsData : []);
                setClients(Array.isArray(clientsData) ? clientsData : []);
                setHealth(healthData || { status: 'unknown' });
                
                console.log('✅ MCP data loaded successfully:');
                console.log(`  📊 Models: ${modelsData.length || 0}`);
                console.log(`  👥 Clients: ${clientsData.length || 0}`);
                console.log(`  💚 Health: ${healthData?.status || 'unknown'}`);
                
            } catch (error) {
                console.error('❌ MCP data loading failed:', error);
                console.error('🔍 Error details:', {
                    message: error.message,
                    stack: error.stack,
                    endpoints: MCP_ENDPOINTS
                });
                setError(`Failed to load MCP data: ${error.message}`);
            } finally {
                setLoading(false);
            }
        };

        if (!isOpen) return null;

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
                        alignItems: 'center',
                        justifyContent: 'space-between'
                    }
                },
                    React.createElement('h1', { 
                        style: { margin: 0, fontSize: '24px' } 
                    }, '🤖 MCP Management System'),
                    React.createElement('button', {
                        onClick: onClose,
                        style: {
                            background: 'none',
                            border: 'none',
                            color: 'white',
                            fontSize: '30px',
                            cursor: 'pointer',
                            padding: '0',
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        },
                        onMouseOver: (e) => e.target.style.background = 'rgba(255,255,255,0.2)',
                        onMouseOut: (e) => e.target.style.background = 'none'
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
                    // Error State
                    error ? 
                        React.createElement('div', {
                            style: {
                                padding: '20px',
                                background: '#fef2f2',
                                color: '#dc2626',
                                borderRadius: '8px',
                                marginBottom: '20px',
                                border: '1px solid #fecaca'
                            }
                        }, 
                            React.createElement('div', { 
                                style: { fontWeight: 'bold', marginBottom: '10px' }
                            }, '❌ Error Loading MCP Data'),
                            React.createElement('div', { 
                                style: { marginBottom: '15px' }
                            }, error),
                            React.createElement('div', { 
                                style: { fontSize: '14px', color: '#991b1b' }
                            }, 'Endpoints being called:'),
                            React.createElement('ul', { style: { margin: '5px 0', paddingLeft: '20px' } },
                                Object.entries(MCP_ENDPOINTS).map(([key, url]) =>
                                    React.createElement('li', { 
                                        key, 
                                        style: { fontSize: '12px', marginBottom: '2px' }
                                    }, `${key}: ${url}`)
                                )
                            ),
                            React.createElement('button', {
                                onClick: loadMCPData,
                                style: {
                                    marginTop: '10px',
                                    padding: '8px 16px',
                                    background: '#dc2626',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }
                            }, '🔄 Retry')
                        ) :
                    
                    // Loading State
                    loading ? 
                        React.createElement('div', { 
                            style: { 
                                textAlign: 'center', 
                                padding: '60px',
                                color: '#64748b'
                            }
                        }, 
                            React.createElement('div', { 
                                style: { fontSize: '18px', marginBottom: '10px' }
                            }, '⏳ Loading MCP data...'),
                            React.createElement('div', { 
                                style: { fontSize: '14px' }
                            }, 'Connecting to Cloud Functions')
                        ) :
                    
                    // Success State
                        React.createElement('div', {},
                            // Status Cards
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
                                        border: '1px solid #bbf7d0'
                                    }
                                },
                                    React.createElement('div', { 
                                        style: { color: '#166534', fontSize: '14px', fontWeight: '600' }
                                    }, 'System Status'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#22c55e', marginTop: '5px' }
                                    }, health?.status === 'healthy' ? '✅ Healthy' : '⚠️ Issues')
                                ),
                                React.createElement('div', {
                                    style: {
                                        background: '#fefbeb',
                                        padding: '20px',
                                        borderRadius: '8px',
                                        border: '1px solid #fed7aa'
                                    }
                                },
                                    React.createElement('div', { 
                                        style: { color: '#92400e', fontSize: '14px', fontWeight: '600' }
                                    }, 'AI Models'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#f59e0b', marginTop: '5px' }
                                    }, models.length || 0)
                                ),
                                React.createElement('div', {
                                    style: {
                                        background: '#faf5ff',
                                        padding: '20px',
                                        borderRadius: '8px',
                                        border: '1px solid #e9d5ff'
                                    }
                                },
                                    React.createElement('div', { 
                                        style: { color: '#6b21a8', fontSize: '14px', fontWeight: '600' }
                                    }, 'Active Clients'),
                                    React.createElement('div', { 
                                        style: { fontSize: '24px', fontWeight: 'bold', color: '#8b5cf6', marginTop: '5px' }
                                    }, clients.length || 0)
                                )
                            ),
                            
                            // Models List
                            React.createElement('h2', { 
                                style: { marginBottom: '20px', color: '#1f2937' }
                            }, '🤖 Available AI Models'),
                            React.createElement('div', { 
                                style: { display: 'grid', gap: '15px', marginBottom: '30px' }
                            },
                                models.length > 0 ? models.map((model, index) => 
                                    React.createElement('div', {
                                        key: model.id || index,
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
                                                style: { margin: '0 0 8px 0', color: '#1f2937' }
                                            }, model.display_name || model.name || 'Unknown Model'),
                                            React.createElement('p', { 
                                                style: { margin: 0, color: '#64748b', fontSize: '14px' }
                                            }, `Provider: ${model.provider || 'Unknown'} | Model: ${model.model_name || model.model || 'Unknown'}`)
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
                                ) : 
                                React.createElement('div', {
                                    style: {
                                        padding: '20px',
                                        textAlign: 'center',
                                        color: '#64748b',
                                        background: '#f9fafb',
                                        borderRadius: '8px',
                                        border: '1px solid #e5e7eb'
                                    }
                                }, 'No models found')
                            ),
                            
                            // Action Buttons
                            React.createElement('div', { 
                                style: { 
                                    display: 'flex',
                                    gap: '10px',
                                    flexWrap: 'wrap'
                                }
                            },
                                React.createElement('button', {
                                    onClick: loadMCPData,
                                    style: {
                                        padding: '12px 24px',
                                        background: '#667eea',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '600'
                                    }
                                }, '🔄 Refresh Data'),
                                React.createElement('button', {
                                    onClick: () => {
                                        console.log('📊 MCP Debug Information:');
                                        console.log('Endpoints:', MCP_ENDPOINTS);
                                        console.log('Models:', models);
                                        console.log('Clients:', clients);
                                        console.log('Health:', health);
                                    },
                                    style: {
                                        padding: '12px 24px',
                                        background: '#10b981',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '600'
                                    }
                                }, '📋 Debug Info'),
                                React.createElement('button', {
                                    onClick: () => {
                                        // Test each endpoint individually
                                        Object.entries(MCP_ENDPOINTS).forEach(async ([name, url]) => {
                                            try {
                                                const response = await fetch(url, { mode: 'cors' });
                                                console.log(`✅ ${name}: ${response.status} ${response.statusText}`);
                                            } catch (error) {
                                                console.error(`❌ ${name}:`, error);
                                            }
                                        });
                                    },
                                    style: {
                                        padding: '12px 24px',
                                        background: '#f59e0b',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '600'
                                    }
                                }, '🔍 Test Endpoints')
                            )
                        )
                )
            )
        );
    };
    
    // Store component globally
    window.MCPManagement = MCPManagement;
    
    // MCP Button Component
    const MCPButton = () => {
        const [showMCP, setShowMCP] = React.useState(false);
        
        return React.createElement(React.Fragment, {},
            React.createElement('button', {
                id: 'mcp-toggle-button',
                onClick: () => {
                    console.log('🤖 Opening MCP Management...');
                    setShowMCP(true);
                },
                style: {
                    position: 'fixed',
                    top: '20px',
                    right: '20px',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    border: 'none',
                    padding: '12px 20px',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    zIndex: 99999,
                    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
                    transition: 'all 0.2s ease'
                },
                onMouseOver: (e) => {
                    e.target.style.transform = 'scale(1.05)';
                    e.target.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
                },
                onMouseOut: (e) => {
                    e.target.style.transform = 'scale(1)';
                    e.target.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
                }
            }, '🤖 MCP Management'),
            React.createElement(MCPManagement, {
                isOpen: showMCP,
                onClose: () => {
                    console.log('🤖 Closing MCP Management...');
                    setShowMCP(false);
                }
            })
        );
    };
    
    // Mount function with React version detection
    function mountMCP() {
        // Remove existing if any
        const existing = document.getElementById('mcp-root');
        if (existing) {
            existing.remove();
            console.log('🗑️ Removed existing MCP mount');
        }
        
        // Create mount point
        const mount = document.createElement('div');
        mount.id = 'mcp-root';
        document.body.appendChild(mount);
        
        // Mount with appropriate React version
        if (window.React && window.ReactDOM) {
            try {
                if (ReactDOM.createRoot) {
                    // React 18+
                    const root = ReactDOM.createRoot(mount);
                    root.render(React.createElement(MCPButton));
                    console.log('✅ MCP mounted with React 18');
                } else {
                    // React 17 and earlier
                    ReactDOM.render(React.createElement(MCPButton), mount);
                    console.log('✅ MCP mounted with React 17');
                }
                console.log('🎯 MCP Management button added to page');
            } catch (error) {
                console.error('❌ Failed to mount MCP:', error);
            }
        } else {
            console.error('❌ React not found! Make sure you\'re on a page with React loaded.');
        }
    }
    
    // Wait for React if needed
    if (typeof React === 'undefined' || typeof ReactDOM === 'undefined') {
        console.log('⏳ Waiting for React to load...');
        let attempts = 0;
        const maxAttempts = 30; // 15 seconds max wait
        
        const waitForReact = setInterval(() => {
            attempts++;
            console.log(`  Attempt ${attempts}/${maxAttempts} - Checking for React...`);
            
            if (window.React && window.ReactDOM) {
                clearInterval(waitForReact);
                console.log('✅ React found! Mounting MCP...');
                mountMCP();
            } else if (attempts >= maxAttempts) {
                clearInterval(waitForReact);
                console.error('❌ React not found after 15 seconds. Are you on the right page?');
                console.log('💡 Try running this script on https://emailpilot.ai');
            }
        }, 500);
    } else {
        console.log('✅ React detected, mounting MCP immediately...');
        mountMCP();
    }
    
    // Final success message
    console.log('🎉 MCP Management System injection complete!');
    console.log('📍 Configured Cloud Function endpoints:');
    Object.entries(MCP_ENDPOINTS).forEach(([key, url]) => {
        console.log(`  ${key}: ${url}`);
    });
    console.log('👀 Look for the "🤖 MCP Management" button in the top-right corner');
    
})();