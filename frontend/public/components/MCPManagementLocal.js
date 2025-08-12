// MCP Management Component for Local Development
const MCPManagement = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [models, setModels] = React.useState([]);
  const [clients, setClients] = React.useState([]);
  const [health, setHealth] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState('models');

  // Use local API endpoints for development
  const MCP_ENDPOINTS = {
    models: '/api/mcp/models',
    clients: '/api/mcp/clients',
    health: '/api/mcp/health'
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [modelsRes, clientsRes, healthRes] = await Promise.all([
        fetch(MCP_ENDPOINTS.models),
        fetch(MCP_ENDPOINTS.clients),
        fetch(MCP_ENDPOINTS.health)
      ]);
      
      if (!modelsRes.ok || !clientsRes.ok || !healthRes.ok) {
        throw new Error('Failed to fetch MCP data');
      }
      
      const [modelsData, clientsData, healthData] = await Promise.all([
        modelsRes.json(),
        clientsRes.json(),
        healthRes.json()
      ]);
      
      setModels(modelsData);
      setClients(clientsData);
      setHealth(healthData);
    } catch (err) {
      setError(err.message);
      console.error('MCP data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleModel = async (modelId, currentStatus) => {
    try {
      const res = await fetch(`/api/mcp/models/${modelId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentStatus })
      });
      
      if (res.ok) {
        await loadData(); // Reload data
      }
    } catch (err) {
      console.error('Failed to toggle model:', err);
    }
  };

  const testModel = async (modelId) => {
    try {
      const res = await fetch(`/api/mcp/models/${modelId}/test`, {
        method: 'POST'
      });
      
      if (res.ok) {
        const result = await res.json();
        alert(`Test Result: ${result.test_result}\nResponse Time: ${result.response_time_ms}ms`);
      }
    } catch (err) {
      console.error('Failed to test model:', err);
    }
  };

  React.useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  return React.createElement(React.Fragment, null,
    // Toggle Button
    React.createElement('button', {
      onClick: () => setIsOpen(true),
      style: {
        position: 'fixed',
        top: '80px',
        right: '20px',
        background: 'linear-gradient(135deg, #667eea, #764ba2)',
        color: 'white',
        border: 'none',
        padding: '12px 24px',
        borderRadius: '8px',
        fontSize: '16px',
        fontWeight: '600',
        cursor: 'pointer',
        zIndex: 999,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
      }
    }, '🤖 MCP Management'),

    // Modal
    isOpen && React.createElement('div', {
      style: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.5)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      },
      onClick: () => setIsOpen(false)
    },
      React.createElement('div', {
        style: {
          background: 'white',
          width: '90%',
          maxWidth: '1200px',
          maxHeight: '90vh',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
        },
        onClick: e => e.stopPropagation()
      },
        // Header
        React.createElement('div', {
          style: {
            background: 'linear-gradient(135deg, #667eea, #764ba2)',
            color: 'white',
            padding: '20px 30px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }
        },
          React.createElement('h1', { style: { margin: 0, fontSize: '24px' } }, '🤖 MCP Management System'),
          React.createElement('button', {
            onClick: () => setIsOpen(false),
            style: {
              background: 'none',
              border: 'none',
              color: 'white',
              fontSize: '30px',
              cursor: 'pointer'
            }
          }, '×')
        ),

        // Tabs
        React.createElement('div', {
          style: {
            borderBottom: '1px solid #e2e8f0',
            padding: '0 30px',
            background: '#f8fafc'
          }
        },
          ['models', 'clients', 'health'].map(tab =>
            React.createElement('button', {
              key: tab,
              onClick: () => setActiveTab(tab),
              style: {
                background: 'none',
                border: 'none',
                padding: '15px 20px',
                fontSize: '16px',
                fontWeight: activeTab === tab ? '600' : '400',
                color: activeTab === tab ? '#667eea' : '#64748b',
                borderBottom: activeTab === tab ? '3px solid #667eea' : 'none',
                cursor: 'pointer',
                textTransform: 'capitalize'
              }
            }, tab)
          )
        ),

        // Content
        React.createElement('div', { 
          style: { 
            padding: '30px', 
            overflowY: 'auto', 
            maxHeight: 'calc(90vh - 180px)' 
          } 
        },
          loading ? 
            React.createElement('div', { 
              style: { textAlign: 'center', padding: '40px' } 
            },
              React.createElement('div', { 
                style: { fontSize: '18px', color: '#64748b' } 
              }, 'Loading...')
            ) :
          error ?
            React.createElement('div', {
              style: {
                background: '#fee2e2',
                border: '1px solid #fca5a5',
                borderRadius: '8px',
                padding: '15px',
                color: '#dc2626'
              }
            }, 'Error: ', error) :
          React.createElement('div', null,
            // Models Tab
            activeTab === 'models' && React.createElement('div', null,
              React.createElement('h2', { style: { marginTop: 0 } }, 
                `Available Models (${models.length})`
              ),
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
                    React.createElement('div', {
                      style: {
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: '10px'
                      }
                    },
                      React.createElement('strong', {
                        style: { fontSize: '18px', color: '#1e293b' }
                      }, model.display_name),
                      React.createElement('div', { style: { display: 'flex', gap: '10px' } },
                        React.createElement('button', {
                          onClick: () => testModel(model.id),
                          style: {
                            background: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            padding: '4px 12px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }
                        }, 'Test'),
                        React.createElement('button', {
                          onClick: () => toggleModel(model.id, model.is_active),
                          style: {
                            background: model.is_active ? '#10b981' : '#ef4444',
                            color: 'white',
                            padding: '4px 12px',
                            borderRadius: '12px',
                            fontSize: '12px',
                            border: 'none',
                            cursor: 'pointer'
                          }
                        }, model.is_active ? 'Active' : 'Inactive')
                      )
                    ),
                    React.createElement('div', { style: { color: '#64748b' } },
                      React.createElement('div', null, 'Provider: ', model.provider),
                      React.createElement('div', null, 'Model: ', model.model_name),
                      React.createElement('div', null, 'Max Tokens: ', model.max_tokens)
                    )
                  )
                )
              )
            ),

            // Clients Tab
            activeTab === 'clients' && React.createElement('div', null,
              React.createElement('h2', { style: { marginTop: 0 } }, 
                `MCP Clients (${clients.length})`
              ),
              React.createElement('div', { style: { display: 'grid', gap: '15px' } },
                clients.map(client =>
                  React.createElement('div', {
                    key: client.id,
                    style: {
                      padding: '20px',
                      background: '#f8fafc',
                      borderRadius: '8px',
                      border: '1px solid #e2e8f0'
                    }
                  },
                    React.createElement('div', { style: { marginBottom: '10px' } },
                      React.createElement('strong', {
                        style: { fontSize: '18px', color: '#1e293b' }
                      }, client.name)
                    ),
                    React.createElement('div', { style: { color: '#64748b' } },
                      React.createElement('div', null, 'Type: ', client.type),
                      React.createElement('div', null, 'Created: ', 
                        new Date(client.created_at).toLocaleDateString()
                      )
                    )
                  )
                )
              )
            ),

            // Health Tab
            activeTab === 'health' && React.createElement('div', null,
              React.createElement('h2', { style: { marginTop: 0 } }, 'System Health'),
              React.createElement('div', {
                style: {
                  padding: '20px',
                  background: health?.status === 'healthy' ? '#dcfce7' : '#fee2e2',
                  borderRadius: '8px',
                  border: `1px solid ${health?.status === 'healthy' ? '#86efac' : '#fca5a5'}`
                }
              },
                React.createElement('div', {
                  style: {
                    fontSize: '20px',
                    fontWeight: '600',
                    marginBottom: '15px'
                  }
                }, 'Status: ', health?.status || 'Unknown'),
                health?.details && React.createElement('div', { style: { color: '#64748b' } },
                  React.createElement('div', null, 'Models: ', health.details.models_count),
                  React.createElement('div', null, 'Active Models: ', health.details.active_models),
                  React.createElement('div', null, 'Clients: ', health.details.clients_count),
                  React.createElement('div', null, 'Last Check: ', 
                    new Date(health.timestamp).toLocaleString()
                  )
                )
              )
            )
          )
        )
      )
    )
  );
};

// Export for use in app
window.MCPManagement = MCPManagement;