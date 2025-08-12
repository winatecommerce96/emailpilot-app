// MCP Management Component - Standalone Fixed Version
// This is the clean, standalone component with proper error handling and Cloud Function URLs

// Configuration - FIXED Cloud Function URLs
const MCP_CONFIG = {
    endpoints: {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    },
    timeout: 10000, // 10 second timeout
    retryAttempts: 3
};

// MCP Management Main Component
const MCPManagement = ({ isOpen, onClose, config = MCP_CONFIG }) => {
    const [state, setState] = React.useState({
        models: [],
        clients: [],
        health: null,
        loading: true,
        error: null,
        lastUpdated: null
    });

    // Load MCP data from Cloud Functions
    const loadMCPData = React.useCallback(async () => {
        setState(prev => ({ ...prev, loading: true, error: null }));
        
        console.log('📡 Loading MCP data from Cloud Functions...');
        console.log('🎯 Using endpoints:', config.endpoints);
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), config.timeout);
            
            // Parallel requests to all endpoints
            const requests = Object.entries(config.endpoints).map(([name, url]) => 
                fetch(url, {
                    method: 'GET',
                    mode: 'cors',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    signal: controller.signal
                }).then(response => {
                    if (!response.ok) {
                        throw new Error(`${name} endpoint failed: ${response.status} ${response.statusText}`);
                    }
                    return response.json().then(data => ({ name, data, status: response.status }));
                }).catch(error => {
                    console.error(`❌ ${name} endpoint error:`, error);
                    return { name, error: error.message, data: null };
                })
            );
            
            const results = await Promise.all(requests);
            clearTimeout(timeoutId);
            
            // Process results
            const newState = {
                models: [],
                clients: [],
                health: { status: 'unknown' },
                loading: false,
                error: null,
                lastUpdated: new Date()
            };
            
            let hasErrors = false;
            
            results.forEach(result => {
                if (result.error) {
                    hasErrors = true;
                    console.error(`❌ ${result.name} failed:`, result.error);
                } else {
                    console.log(`✅ ${result.name} loaded successfully (${result.status})`);
                    
                    switch (result.name) {
                        case 'models':
                            newState.models = Array.isArray(result.data) ? result.data : [];
                            break;
                        case 'clients':
                            newState.clients = Array.isArray(result.data) ? result.data : [];
                            break;
                        case 'health':
                            newState.health = result.data || { status: 'unknown' };
                            break;
                    }
                }
            });
            
            if (hasErrors) {
                const errorResults = results.filter(r => r.error);
                newState.error = `Failed to load: ${errorResults.map(r => r.name).join(', ')}`;
            }
            
            setState(newState);
            
            console.log('📊 MCP Data Summary:');
            console.log(`  Models: ${newState.models.length}`);
            console.log(`  Clients: ${newState.clients.length}`);
            console.log(`  Health: ${newState.health.status}`);
            
        } catch (error) {
            console.error('❌ MCP data loading failed:', error);
            setState(prev => ({
                ...prev,
                loading: false,
                error: error.name === 'AbortError' ? 'Request timeout' : error.message
            }));
        }
    }, [config]);

    // Load data when modal opens
    React.useEffect(() => {
        if (isOpen && !state.lastUpdated) {
            loadMCPData();
        }
    }, [isOpen, loadMCPData, state.lastUpdated]);

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
            justifyContent: 'center',
            animation: 'fadeIn 0.2s ease-out'
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
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                animation: 'slideIn 0.3s ease-out'
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
                React.createElement('div', {},
                    React.createElement('h1', { 
                        style: { margin: 0, fontSize: '24px', fontWeight: '700' } 
                    }, '🤖 MCP Management System'),
                    state.lastUpdated && React.createElement('div', {
                        style: { fontSize: '12px', opacity: 0.8, marginTop: '4px' }
                    }, `Last updated: ${state.lastUpdated.toLocaleTimeString()}`)
                ),
                React.createElement('button', {
                    onClick: onClose,
                    style: {
                        background: 'rgba(255, 255, 255, 0.2)',
                        border: 'none',
                        color: 'white',
                        fontSize: '24px',
                        cursor: 'pointer',
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'background 0.2s'
                    },
                    onMouseOver: (e) => e.target.style.background = 'rgba(255, 255, 255, 0.3)',
                    onMouseOut: (e) => e.target.style.background = 'rgba(255, 255, 255, 0.2)'
                }, '×')
            ),
            
            // Content
            React.createElement('div', {
                style: {
                    padding: '30px',
                    overflowY: 'auto',
                    maxHeight: 'calc(90vh - 100px)'
                }
            },
                // Error State
                state.error ? 
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
                            style: { fontWeight: 'bold', marginBottom: '10px', display: 'flex', alignItems: 'center' }
                        }, 
                            React.createElement('span', { style: { marginRight: '8px' } }, '❌'),
                            'Connection Error'
                        ),
                        React.createElement('div', { style: { marginBottom: '15px' } }, state.error),
                        React.createElement('details', { style: { fontSize: '14px', color: '#991b1b' } },
                            React.createElement('summary', { style: { cursor: 'pointer', marginBottom: '10px' } }, 'Endpoint Details'),
                            React.createElement('div', { style: { paddingLeft: '20px' } },
                                Object.entries(config.endpoints).map(([key, url]) =>
                                    React.createElement('div', { key, style: { marginBottom: '5px' } },
                                        React.createElement('strong', {}, `${key}: `),
                                        React.createElement('code', { style: { fontSize: '12px' } }, url)
                                    )
                                )
                            )
                        ),
                        React.createElement('button', {
                            onClick: loadMCPData,
                            style: {
                                marginTop: '15px',
                                padding: '10px 20px',
                                background: '#dc2626',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '14px',
                                fontWeight: '600'
                            }
                        }, '🔄 Retry Connection')
                    ) :
                
                // Loading State
                state.loading ? 
                    React.createElement('div', { 
                        style: { 
                            textAlign: 'center', 
                            padding: '80px 20px',
                            color: '#64748b'
                        }
                    },
                        React.createElement('div', { 
                            style: { fontSize: '48px', marginBottom: '20px' }
                        }, '⏳'),
                        React.createElement('div', { 
                            style: { fontSize: '18px', fontWeight: '600', marginBottom: '10px' }
                        }, 'Loading MCP Data'),
                        React.createElement('div', { 
                            style: { fontSize: '14px' }
                        }, 'Connecting to Cloud Functions...')
                    ) :
                
                // Success State
                React.createElement('div', {},
                    // Status Dashboard
                    React.createElement('div', {
                        style: {
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                            gap: '20px',
                            marginBottom: '40px'
                        }
                    },
                        React.createElement('div', {
                            style: {
                                background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
                                padding: '24px',
                                borderRadius: '12px',
                                border: '1px solid #bbf7d0'
                            }
                        },
                            React.createElement('div', { 
                                style: { 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    marginBottom: '10px' 
                                }
                            },
                                React.createElement('div', { 
                                    style: { fontSize: '32px', marginRight: '12px' }
                                }, state.health?.status === 'healthy' ? '✅' : '⚠️'),
                                React.createElement('div', {},
                                    React.createElement('div', { 
                                        style: { color: '#166534', fontSize: '14px', fontWeight: '600' }
                                    }, 'System Status'),
                                    React.createElement('div', { 
                                        style: { color: '#22c55e', fontSize: '18px', fontWeight: 'bold' }
                                    }, state.health?.status === 'healthy' ? 'Healthy' : 'Issues')
                                )
                            )
                        ),
                        React.createElement('div', {
                            style: {
                                background: 'linear-gradient(135deg, #fefbeb 0%, #fef3c7 100%)',
                                padding: '24px',
                                borderRadius: '12px',
                                border: '1px solid #fed7aa'
                            }
                        },
                            React.createElement('div', { 
                                style: { 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    marginBottom: '10px' 
                                }
                            },
                                React.createElement('div', { 
                                    style: { fontSize: '32px', marginRight: '12px' }
                                }, '🤖'),
                                React.createElement('div', {},
                                    React.createElement('div', { 
                                        style: { color: '#92400e', fontSize: '14px', fontWeight: '600' }
                                    }, 'AI Models'),
                                    React.createElement('div', { 
                                        style: { color: '#f59e0b', fontSize: '18px', fontWeight: 'bold' }
                                    }, state.models.length)
                                )
                            )
                        ),
                        React.createElement('div', {
                            style: {
                                background: 'linear-gradient(135deg, #faf5ff 0%, #ede9fe 100%)',
                                padding: '24px',
                                borderRadius: '12px',
                                border: '1px solid #e9d5ff'
                            }
                        },
                            React.createElement('div', { 
                                style: { 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    marginBottom: '10px' 
                                }
                            },
                                React.createElement('div', { 
                                    style: { fontSize: '32px', marginRight: '12px' }
                                }, '👥'),
                                React.createElement('div', {},
                                    React.createElement('div', { 
                                        style: { color: '#6b21a8', fontSize: '14px', fontWeight: '600' }
                                    }, 'Active Clients'),
                                    React.createElement('div', { 
                                        style: { color: '#8b5cf6', fontSize: '18px', fontWeight: 'bold' }
                                    }, state.clients.length)
                                )
                            )
                        )
                    ),
                    
                    // Models Section
                    React.createElement('div', { style: { marginBottom: '40px' } },
                        React.createElement('h2', { 
                            style: { 
                                marginBottom: '24px', 
                                color: '#1f2937',
                                fontSize: '20px',
                                fontWeight: '700',
                                display: 'flex',
                                alignItems: 'center'
                            }
                        }, 
                            React.createElement('span', { style: { marginRight: '8px' } }, '🤖'),
                            'Available AI Models'
                        ),
                        
                        state.models.length > 0 ? 
                            React.createElement('div', { 
                                style: { 
                                    display: 'grid', 
                                    gap: '16px'
                                }
                            },
                                state.models.map((model, index) => 
                                    React.createElement('div', {
                                        key: model.id || index,
                                        style: {
                                            padding: '24px',
                                            background: '#f8fafc',
                                            borderRadius: '12px',
                                            border: '1px solid #e2e8f0',
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            transition: 'all 0.2s',
                                            cursor: 'default'
                                        },
                                        onMouseOver: (e) => {
                                            e.target.style.background = '#f1f5f9';
                                            e.target.style.borderColor = '#cbd5e1';
                                        },
                                        onMouseOut: (e) => {
                                            e.target.style.background = '#f8fafc';
                                            e.target.style.borderColor = '#e2e8f0';
                                        }
                                    },
                                        React.createElement('div', {},
                                            React.createElement('h3', { 
                                                style: { 
                                                    margin: '0 0 8px 0', 
                                                    color: '#1f2937',
                                                    fontSize: '16px',
                                                    fontWeight: '600'
                                                }
                                            }, model.display_name || model.name || 'Unknown Model'),
                                            React.createElement('p', { 
                                                style: { 
                                                    margin: 0, 
                                                    color: '#64748b', 
                                                    fontSize: '14px'
                                                }
                                            }, `${model.provider || 'Unknown'} • ${model.model_name || model.model || 'Unknown'}`)
                                        ),
                                        React.createElement('div', {
                                            style: {
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px'
                                            }
                                        },
                                            React.createElement('div', {
                                                style: {
                                                    padding: '6px 12px',
                                                    background: '#dcfce7',
                                                    color: '#166534',
                                                    borderRadius: '20px',
                                                    fontSize: '12px',
                                                    fontWeight: '600'
                                                }
                                            }, 'ACTIVE'),
                                            React.createElement('div', {
                                                style: {
                                                    width: '8px',
                                                    height: '8px',
                                                    borderRadius: '50%',
                                                    background: '#22c55e'
                                                }
                                            })
                                        )
                                    )
                                )
                            ) :
                            React.createElement('div', {
                                style: {
                                    padding: '40px 20px',
                                    textAlign: 'center',
                                    color: '#64748b',
                                    background: '#f9fafb',
                                    borderRadius: '12px',
                                    border: '2px dashed #d1d5db'
                                }
                            },
                                React.createElement('div', { style: { fontSize: '48px', marginBottom: '16px' } }, '🔍'),
                                React.createElement('div', { style: { fontSize: '16px', fontWeight: '600' } }, 'No Models Found'),
                                React.createElement('div', { style: { fontSize: '14px', marginTop: '8px' } }, 'Try refreshing the data or check the Cloud Functions')
                            )
                    ),
                    
                    // Action Buttons
                    React.createElement('div', { 
                        style: { 
                            display: 'flex',
                            gap: '12px',
                            flexWrap: 'wrap',
                            paddingTop: '20px',
                            borderTop: '1px solid #e5e7eb'
                        }
                    },
                        React.createElement('button', {
                            onClick: loadMCPData,
                            disabled: state.loading,
                            style: {
                                padding: '12px 24px',
                                background: state.loading ? '#9ca3af' : '#667eea',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: state.loading ? 'not-allowed' : 'pointer',
                                fontSize: '14px',
                                fontWeight: '600',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                transition: 'all 0.2s'
                            }
                        }, 
                            React.createElement('span', {}, state.loading ? '⏳' : '🔄'),
                            state.loading ? 'Loading...' : 'Refresh Data'
                        ),
                        React.createElement('button', {
                            onClick: () => {
                                console.group('📊 MCP Debug Information');
                                console.log('Config:', config);
                                console.log('State:', state);
                                console.log('Endpoints:', config.endpoints);
                                console.log('Models:', state.models);
                                console.log('Clients:', state.clients);
                                console.log('Health:', state.health);
                                console.groupEnd();
                            },
                            style: {
                                padding: '12px 24px',
                                background: '#10b981',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontSize: '14px',
                                fontWeight: '600'
                            }
                        }, '📋 Debug Console'),
                        React.createElement('button', {
                            onClick: () => {
                                const testWindow = window.open('', '_blank', 'width=800,height=600');
                                testWindow.document.write(`
                                    <html><head><title>MCP Endpoint Test</title></head>
                                    <body style="font-family: Arial, sans-serif; margin: 20px;">
                                        <h1>MCP Cloud Function Test</h1>
                                        <div id="results"></div>
                                        <script>
                                            const endpoints = ${JSON.stringify(config.endpoints)};
                                            const results = document.getElementById('results');
                                            
                                            Object.entries(endpoints).forEach(async ([name, url]) => {
                                                const div = document.createElement('div');
                                                div.style.marginBottom = '10px';
                                                div.innerHTML = \`<strong>\${name}:</strong> Testing \${url}...\`;
                                                results.appendChild(div);
                                                
                                                try {
                                                    const response = await fetch(url, { mode: 'cors' });
                                                    const data = await response.json();
                                                    div.innerHTML = \`<strong>\${name}:</strong> ✅ \${response.status} - \${JSON.stringify(data).substring(0, 100)}...\`;
                                                } catch (error) {
                                                    div.innerHTML = \`<strong>\${name}:</strong> ❌ \${error.message}\`;
                                                }
                                            });
                                        </script>
                                    </body></html>
                                `);
                            },
                            style: {
                                padding: '12px 24px',
                                background: '#f59e0b',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
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

// Export the component
if (typeof window !== 'undefined') {
    window.MCPManagement = MCPManagement;
    window.MCP_CONFIG = MCP_CONFIG;
}