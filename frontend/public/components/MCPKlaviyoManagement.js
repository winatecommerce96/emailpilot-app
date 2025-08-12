// MCP Klaviyo Management Component
const MCPManagement = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [klaviyoKeys, setKlaviyoKeys] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState('klaviyo');
  const [editingClient, setEditingClient] = React.useState(null);
  const [newKey, setNewKey] = React.useState('');
  const [stats, setStats] = React.useState({ total_clients: 0, clients_with_keys: 0 });

  const loadKlaviyoKeys = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/mcp/klaviyo/keys');
      
      if (!response.ok) {
        throw new Error('Failed to fetch Klaviyo keys');
      }
      
      const data = await response.json();
      setKlaviyoKeys(data.clients || []);
      setStats({
        total_clients: data.total_clients || 0,
        clients_with_keys: data.clients_with_keys || 0
      });
    } catch (err) {
      setError(err.message);
      console.error('Failed to load Klaviyo keys:', err);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (clientId, clientName) => {
    try {
      const response = await fetch(`/api/mcp/klaviyo/keys/test/${clientId}`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        alert(`✅ ${clientName}\nConnection successful!\nResponse time: ${result.response_time_ms}ms`);
      } else {
        alert(`❌ ${clientName}\n${result.message}\n${result.error || ''}`);
      }
    } catch (err) {
      alert(`Error testing connection: ${err.message}`);
    }
  };

  const updateKey = async (clientId) => {
    if (!newKey.trim()) {
      alert('Please enter a valid API key');
      return;
    }
    
    try {
      const response = await fetch('/api/mcp/klaviyo/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          klaviyo_private_key: newKey
        })
      });
      
      if (response.ok) {
        alert('Key updated successfully!');
        setEditingClient(null);
        setNewKey('');
        await loadKlaviyoKeys();
      } else {
        const error = await response.json();
        alert(`Failed to update key: ${error.detail}`);
      }
    } catch (err) {
      alert(`Error updating key: ${err.message}`);
    }
  };

  const deleteKey = async (clientId, clientName) => {
    if (!confirm(`Are you sure you want to remove the Klaviyo key for ${clientName}?`)) {
      return;
    }
    
    try {
      const response = await fetch(`/api/mcp/klaviyo/keys/${clientId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        alert('Key removed successfully!');
        await loadKlaviyoKeys();
      } else {
        const error = await response.json();
        alert(`Failed to remove key: ${error.detail}`);
      }
    } catch (err) {
      alert(`Error removing key: ${err.message}`);
    }
  };

  React.useEffect(() => {
    if (isOpen) {
      loadKlaviyoKeys();
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
    }, '🔑 MCP Klaviyo Keys'),

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
          React.createElement('div', null,
            React.createElement('h1', { style: { margin: 0, fontSize: '24px' } }, 
              '🔑 MCP Klaviyo API Keys Management'
            ),
            React.createElement('p', { 
              style: { 
                margin: '5px 0 0 0', 
                fontSize: '14px', 
                opacity: 0.9 
              } 
            }, 
              `${stats.clients_with_keys} of ${stats.total_clients} clients have API keys configured`
            )
          ),
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

        // Content
        React.createElement('div', { 
          style: { 
            padding: '30px', 
            overflowY: 'auto', 
            maxHeight: 'calc(90vh - 100px)' 
          } 
        },
          loading ? 
            React.createElement('div', { 
              style: { textAlign: 'center', padding: '40px' } 
            },
              React.createElement('div', { 
                style: { fontSize: '18px', color: '#64748b' } 
              }, 'Loading Klaviyo keys...')
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
            // Klaviyo Keys List
            React.createElement('div', { style: { display: 'grid', gap: '15px' } },
              klaviyoKeys.map(client =>
                React.createElement('div', {
                  key: client.id,
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
                      alignItems: 'start',
                      marginBottom: '10px'
                    }
                  },
                    React.createElement('div', null,
                      React.createElement('strong', {
                        style: { fontSize: '18px', color: '#1e293b' }
                      }, client.name),
                      React.createElement('div', {
                        style: { 
                          fontSize: '12px', 
                          color: '#64748b',
                          marginTop: '4px'
                        }
                      }, `Metric ID: ${client.metric_id || 'Not set'}`)
                    ),
                    React.createElement('div', { 
                      style: { 
                        display: 'flex', 
                        gap: '10px',
                        alignItems: 'center'
                      } 
                    },
                      client.has_key && React.createElement('button', {
                        onClick: () => testConnection(client.id, client.name),
                        style: {
                          background: '#3b82f6',
                          color: 'white',
                          border: 'none',
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }
                      }, '🧪 Test'),
                      
                      editingClient === client.id ? 
                        React.createElement('button', {
                          onClick: () => {
                            setEditingClient(null);
                            setNewKey('');
                          },
                          style: {
                            background: '#6b7280',
                            color: 'white',
                            border: 'none',
                            padding: '6px 12px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }
                        }, 'Cancel') :
                        React.createElement('button', {
                          onClick: () => {
                            setEditingClient(client.id);
                            setNewKey('');
                          },
                          style: {
                            background: '#10b981',
                            color: 'white',
                            border: 'none',
                            padding: '6px 12px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }
                        }, client.has_key ? '✏️ Edit' : '➕ Add'),
                      
                      client.has_key && React.createElement('button', {
                        onClick: () => deleteKey(client.id, client.name),
                        style: {
                          background: '#ef4444',
                          color: 'white',
                          border: 'none',
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }
                      }, '🗑️ Remove'),
                      
                      React.createElement('span', {
                        style: {
                          background: client.has_key ? '#10b981' : '#ef4444',
                          color: 'white',
                          padding: '4px 12px',
                          borderRadius: '12px',
                          fontSize: '12px'
                        }
                      }, client.has_key ? '✓ Configured' : '✗ Missing')
                    )
                  ),
                  
                  // Key display or edit form
                  editingClient === client.id ?
                    React.createElement('div', {
                      style: {
                        marginTop: '15px',
                        padding: '15px',
                        background: 'white',
                        borderRadius: '6px',
                        border: '1px solid #e2e8f0'
                      }
                    },
                      React.createElement('label', {
                        style: {
                          display: 'block',
                          fontSize: '14px',
                          fontWeight: '500',
                          color: '#374151',
                          marginBottom: '5px'
                        }
                      }, 'Klaviyo Private API Key:'),
                      React.createElement('div', {
                        style: { display: 'flex', gap: '10px' }
                      },
                        React.createElement('input', {
                          type: 'password',
                          value: newKey,
                          onChange: (e) => setNewKey(e.target.value),
                          placeholder: 'pk_...',
                          style: {
                            flex: 1,
                            padding: '8px',
                            borderRadius: '4px',
                            border: '1px solid #d1d5db',
                            fontSize: '14px'
                          }
                        }),
                        React.createElement('button', {
                          onClick: () => updateKey(client.id),
                          style: {
                            background: '#10b981',
                            color: 'white',
                            border: 'none',
                            padding: '8px 16px',
                            borderRadius: '4px',
                            fontSize: '14px',
                            cursor: 'pointer'
                          }
                        }, 'Save')
                      )
                    ) :
                    client.has_key && React.createElement('div', {
                      style: { 
                        color: '#64748b',
                        fontSize: '14px',
                        marginTop: '10px'
                      }
                    },
                      React.createElement('div', null, 
                        'API Key: ',
                        React.createElement('code', {
                          style: {
                            background: '#f1f5f9',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '12px'
                          }
                        }, client.key_preview || '***')
                      ),
                      React.createElement('div', {
                        style: { 
                          display: 'flex',
                          gap: '15px',
                          marginTop: '5px'
                        }
                      },
                        React.createElement('span', null, 
                          `Status: ${client.is_active ? '✅ Active' : '❌ Inactive'}`
                        )
                      )
                    )
                )
              )
            ),
            
            // Summary
            React.createElement('div', {
              style: {
                marginTop: '30px',
                padding: '20px',
                background: '#f0f9ff',
                borderRadius: '8px',
                border: '1px solid #bae6fd'
              }
            },
              React.createElement('h3', {
                style: { 
                  margin: '0 0 10px 0',
                  fontSize: '16px',
                  color: '#0369a1'
                }
              }, '📊 Klaviyo API Keys Summary'),
              React.createElement('div', {
                style: { 
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '15px',
                  marginTop: '15px'
                }
              },
                React.createElement('div', null,
                  React.createElement('div', {
                    style: { fontSize: '24px', fontWeight: 'bold', color: '#0284c7' }
                  }, stats.total_clients),
                  React.createElement('div', {
                    style: { fontSize: '12px', color: '#64748b' }
                  }, 'Total Clients')
                ),
                React.createElement('div', null,
                  React.createElement('div', {
                    style: { fontSize: '24px', fontWeight: 'bold', color: '#10b981' }
                  }, stats.clients_with_keys),
                  React.createElement('div', {
                    style: { fontSize: '12px', color: '#64748b' }
                  }, 'Configured')
                ),
                React.createElement('div', null,
                  React.createElement('div', {
                    style: { fontSize: '24px', fontWeight: 'bold', color: '#ef4444' }
                  }, stats.total_clients - stats.clients_with_keys),
                  React.createElement('div', {
                    style: { fontSize: '12px', color: '#64748b' }
                  }, 'Missing Keys')
                ),
                React.createElement('div', null,
                  React.createElement('div', {
                    style: { fontSize: '24px', fontWeight: 'bold', color: '#8b5cf6' }
                  }, 
                  stats.total_clients > 0 ? 
                    Math.round((stats.clients_with_keys / stats.total_clients) * 100) + '%' : 
                    '0%'
                  ),
                  React.createElement('div', {
                    style: { fontSize: '12px', color: '#64748b' }
                  }, 'Coverage')
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