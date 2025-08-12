// Enhanced Admin Client Management Component
const AdminClientManagement = () => {
  const [clients, setClients] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [editingClient, setEditingClient] = React.useState(null);
  const [showCreateForm, setShowCreateForm] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState('basic'); // basic, brand, segments, growth
  const [stats, setStats] = React.useState({ total_clients: 0, active_clients: 0, clients_with_keys: 0 });
  const [formData, setFormData] = React.useState({
    // Basic Info
    name: '',
    metric_id: '',
    klaviyo_private_key: '',
    description: '',
    contact_email: '',
    contact_name: '',
    website: '',
    is_active: true,
    // Brand Manager
    client_voice: '',
    client_background: '',
    // Project Management
    asana_project_link: '',
    // Affinity Segments
    affinity_segment_1_name: '',
    affinity_segment_1_definition: '',
    affinity_segment_2_name: '',
    affinity_segment_2_definition: '',
    affinity_segment_3_name: '',
    affinity_segment_3_definition: '',
    // Growth
    key_growth_objective: 'subscriptions'
  });

  const loadClients = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/admin/clients', {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch clients');
      }
      
      const data = await response.json();
      setClients(data.clients || []);
      setStats({
        total_clients: data.total_clients || 0,
        active_clients: data.active_clients || 0,
        clients_with_keys: data.clients_with_keys || 0
      });
    } catch (err) {
      setError(err.message);
      console.error('Failed to load clients:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClient = async () => {
    try {
      const response = await fetch('/api/admin/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        alert('Client created successfully!');
        setShowCreateForm(false);
        resetForm();
        await loadClients();
      } else {
        const error = await response.json();
        alert(`Failed to create client: ${error.detail}`);
      }
    } catch (err) {
      alert(`Error creating client: ${err.message}`);
    }
  };

  const handleUpdateClient = async (clientId) => {
    try {
      const response = await fetch(`/api/admin/clients/${clientId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        alert('Client updated successfully!');
        setEditingClient(null);
        resetForm();
        await loadClients();
      } else {
        const error = await response.json();
        alert(`Failed to update client: ${error.detail}`);
      }
    } catch (err) {
      alert(`Error updating client: ${err.message}`);
    }
  };

  const handleDeleteClient = async (clientId, clientName) => {
    if (!confirm(`Are you sure you want to deactivate ${clientName}?`)) {
      return;
    }
    
    try {
      const response = await fetch(`/api/admin/clients/${clientId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        alert('Client deactivated successfully!');
        await loadClients();
      } else {
        const error = await response.json();
        alert(`Failed to deactivate client: ${error.detail}`);
      }
    } catch (err) {
      alert(`Error deactivating client: ${err.message}`);
    }
  };

  const testKlaviyoConnection = async (clientId, clientName) => {
    try {
      const response = await fetch(`/api/admin/clients/${clientId}/test-klaviyo`, {
        method: 'POST',
        credentials: 'include'
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        alert(`✅ ${clientName}\nKlaviyo connection successful!\nResponse time: ${result.response_time_ms}ms`);
      } else {
        alert(`❌ ${clientName}\n${result.message}\n${result.error || ''}`);
      }
    } catch (err) {
      alert(`Error testing connection: ${err.message}`);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      metric_id: '',
      klaviyo_private_key: '',
      description: '',
      contact_email: '',
      contact_name: '',
      website: '',
      is_active: true,
      client_voice: '',
      client_background: '',
      asana_project_link: '',
      affinity_segment_1_name: '',
      affinity_segment_1_definition: '',
      affinity_segment_2_name: '',
      affinity_segment_2_definition: '',
      affinity_segment_3_name: '',
      affinity_segment_3_definition: '',
      key_growth_objective: 'subscriptions'
    });
    setActiveTab('basic');
  };

  const startEdit = (client) => {
    setFormData({
      name: client.name,
      metric_id: client.metric_id || '',
      klaviyo_private_key: '', // Don't pre-fill for security
      description: client.description || '',
      contact_email: client.contact_email || '',
      contact_name: client.contact_name || '',
      website: client.website || '',
      is_active: client.is_active,
      client_voice: client.client_voice || '',
      client_background: client.client_background || '',
      asana_project_link: client.asana_project_link || '',
      affinity_segment_1_name: client.affinity_segment_1_name || '',
      affinity_segment_1_definition: client.affinity_segment_1_definition || '',
      affinity_segment_2_name: client.affinity_segment_2_name || '',
      affinity_segment_2_definition: client.affinity_segment_2_definition || '',
      affinity_segment_3_name: client.affinity_segment_3_name || '',
      affinity_segment_3_definition: client.affinity_segment_3_definition || '',
      key_growth_objective: client.key_growth_objective || 'subscriptions'
    });
    setEditingClient(client.id);
    setActiveTab('basic');
  };

  React.useEffect(() => {
    loadClients();
  }, []);

  // Tab buttons style
  const tabButtonStyle = (isActive) => ({
    padding: '10px 20px',
    background: isActive ? '#3b82f6' : 'transparent',
    color: isActive ? 'white' : '#64748b',
    border: 'none',
    borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: isActive ? '600' : '400',
    transition: 'all 0.2s'
  });

  // Render form fields based on active tab
  const renderFormTab = () => {
    switch(activeTab) {
      case 'basic':
        return React.createElement('div', {
          style: {
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '15px'
          }
        },
          // Name
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, 'Client Name *'),
            React.createElement('input', {
              type: 'text',
              value: formData.name,
              onChange: (e) => setFormData({...formData, name: e.target.value}),
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Metric ID
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, 'Metric ID'),
            React.createElement('input', {
              type: 'text',
              value: formData.metric_id,
              onChange: (e) => setFormData({...formData, metric_id: e.target.value}),
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Klaviyo Key
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, 'Klaviyo Private Key'),
            React.createElement('input', {
              type: 'password',
              value: formData.klaviyo_private_key,
              onChange: (e) => setFormData({...formData, klaviyo_private_key: e.target.value}),
              placeholder: editingClient ? 'Enter new key to update' : 'pk_...',
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Contact Name
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, 'Contact Name'),
            React.createElement('input', {
              type: 'text',
              value: formData.contact_name,
              onChange: (e) => setFormData({...formData, contact_name: e.target.value}),
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Contact Email
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, 'Contact Email'),
            React.createElement('input', {
              type: 'email',
              value: formData.contact_email,
              onChange: (e) => setFormData({...formData, contact_email: e.target.value}),
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Website
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, 'Website'),
            React.createElement('input', {
              type: 'url',
              value: formData.website,
              onChange: (e) => setFormData({...formData, website: e.target.value}),
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Description (full width)
          React.createElement('div', { style: { gridColumn: '1 / -1' } },
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, 'Description'),
            React.createElement('textarea', {
              value: formData.description,
              onChange: (e) => setFormData({...formData, description: e.target.value}),
              rows: 3,
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Asana Project Link (full width)
          React.createElement('div', { style: { gridColumn: '1 / -1' } },
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, '🔗 Asana Project Link'),
            React.createElement('input', {
              type: 'url',
              value: formData.asana_project_link,
              onChange: (e) => setFormData({...formData, asana_project_link: e.target.value}),
              placeholder: 'https://app.asana.com/...',
              style: {
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Active checkbox
          React.createElement('div', { style: { gridColumn: '1 / -1' } },
            React.createElement('label', {
              style: { display: 'flex', alignItems: 'center', fontSize: '14px' }
            },
              React.createElement('input', {
                type: 'checkbox',
                checked: formData.is_active,
                onChange: (e) => setFormData({...formData, is_active: e.target.checked}),
                style: { marginRight: '8px' }
              }),
              'Active'
            )
          )
        );

      case 'brand':
        return React.createElement('div', { style: { display: 'grid', gap: '20px' } },
          // Client Voice
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, '🎯 Client Voice & Tone'),
            React.createElement('textarea', {
              value: formData.client_voice,
              onChange: (e) => setFormData({...formData, client_voice: e.target.value}),
              rows: 4,
              placeholder: 'Describe the brand voice, tone, and communication style...',
              style: {
                width: '100%',
                padding: '10px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          ),
          
          // Client Background
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '5px' }
            }, '📚 Brand Background & Story'),
            React.createElement('textarea', {
              value: formData.client_background,
              onChange: (e) => setFormData({...formData, client_background: e.target.value}),
              rows: 6,
              placeholder: 'Brand history, mission, values, unique selling propositions...',
              style: {
                width: '100%',
                padding: '10px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }
            })
          )
        );

      case 'segments':
        return React.createElement('div', { style: { display: 'grid', gap: '25px' } },
          // Segment 1
          React.createElement('div', {
            style: {
              padding: '20px',
              background: '#f0f9ff',
              borderRadius: '8px',
              border: '1px solid #bae6fd'
            }
          },
            React.createElement('h4', { 
              style: { margin: '0 0 15px 0', color: '#0284c7', fontSize: '16px' } 
            }, '🎯 Affinity Segment 1'),
            React.createElement('div', { style: { display: 'grid', gap: '10px' } },
              React.createElement('input', {
                type: 'text',
                value: formData.affinity_segment_1_name,
                onChange: (e) => setFormData({...formData, affinity_segment_1_name: e.target.value}),
                placeholder: 'Segment Name (e.g., Premium Shoppers)',
                style: {
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '14px'
                }
              }),
              React.createElement('textarea', {
                value: formData.affinity_segment_1_definition,
                onChange: (e) => setFormData({...formData, affinity_segment_1_definition: e.target.value}),
                rows: 3,
                placeholder: 'Segment Definition (demographics, behaviors, preferences...)',
                style: {
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '14px'
                }
              })
            )
          ),
          
          // Segment 2
          React.createElement('div', {
            style: {
              padding: '20px',
              background: '#f0fdf4',
              borderRadius: '8px',
              border: '1px solid #86efac'
            }
          },
            React.createElement('h4', { 
              style: { margin: '0 0 15px 0', color: '#10b981', fontSize: '16px' } 
            }, '🎯 Affinity Segment 2'),
            React.createElement('div', { style: { display: 'grid', gap: '10px' } },
              React.createElement('input', {
                type: 'text',
                value: formData.affinity_segment_2_name,
                onChange: (e) => setFormData({...formData, affinity_segment_2_name: e.target.value}),
                placeholder: 'Segment Name (e.g., Bargain Hunters)',
                style: {
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '14px'
                }
              }),
              React.createElement('textarea', {
                value: formData.affinity_segment_2_definition,
                onChange: (e) => setFormData({...formData, affinity_segment_2_definition: e.target.value}),
                rows: 3,
                placeholder: 'Segment Definition (demographics, behaviors, preferences...)',
                style: {
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '14px'
                }
              })
            )
          ),
          
          // Segment 3
          React.createElement('div', {
            style: {
              padding: '20px',
              background: '#fef3c7',
              borderRadius: '8px',
              border: '1px solid #fbbf24'
            }
          },
            React.createElement('h4', { 
              style: { margin: '0 0 15px 0', color: '#d97706', fontSize: '16px' } 
            }, '🎯 Affinity Segment 3'),
            React.createElement('div', { style: { display: 'grid', gap: '10px' } },
              React.createElement('input', {
                type: 'text',
                value: formData.affinity_segment_3_name,
                onChange: (e) => setFormData({...formData, affinity_segment_3_name: e.target.value}),
                placeholder: 'Segment Name (e.g., Loyal Subscribers)',
                style: {
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '14px'
                }
              }),
              React.createElement('textarea', {
                value: formData.affinity_segment_3_definition,
                onChange: (e) => setFormData({...formData, affinity_segment_3_definition: e.target.value}),
                rows: 3,
                placeholder: 'Segment Definition (demographics, behaviors, preferences...)',
                style: {
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '14px'
                }
              })
            )
          )
        );

      case 'growth':
        return React.createElement('div', { style: { display: 'grid', gap: '20px' } },
          React.createElement('div', null,
            React.createElement('label', {
              style: { display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '10px' }
            }, '📈 Key Growth Objective'),
            React.createElement('select', {
              value: formData.key_growth_objective,
              onChange: (e) => setFormData({...formData, key_growth_objective: e.target.value}),
              style: {
                width: '100%',
                padding: '10px',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                fontSize: '14px',
                background: 'white'
              }
            },
              React.createElement('option', { value: 'subscriptions' }, 'Subscriptions'),
              React.createElement('option', { value: 'revenue' }, 'Revenue Growth'),
              React.createElement('option', { value: 'customer_acquisition' }, 'Customer Acquisition'),
              React.createElement('option', { value: 'retention' }, 'Customer Retention'),
              React.createElement('option', { value: 'engagement' }, 'Engagement & Loyalty'),
              React.createElement('option', { value: 'market_expansion' }, 'Market Expansion'),
              React.createElement('option', { value: 'brand_awareness' }, 'Brand Awareness'),
              React.createElement('option', { value: 'conversion_rate' }, 'Conversion Rate'),
              React.createElement('option', { value: 'average_order_value' }, 'Average Order Value'),
              React.createElement('option', { value: 'lifetime_value' }, 'Customer Lifetime Value')
            )
          ),
          
          React.createElement('div', {
            style: {
              padding: '20px',
              background: '#f3e8ff',
              borderRadius: '8px',
              border: '1px solid #c084fc'
            }
          },
            React.createElement('p', {
              style: { margin: 0, fontSize: '14px', color: '#7c3aed' }
            }, 
              `Current Focus: ${formData.key_growth_objective.replace(/_/g, ' ').toUpperCase()}`
            ),
            React.createElement('p', {
              style: { margin: '10px 0 0 0', fontSize: '13px', color: '#6b7280' }
            }, 
              'This objective will guide campaign strategies and performance metrics tracking.'
            )
          )
        );

      default:
        return null;
    }
  };

  if (loading) {
    return React.createElement('div', { 
      style: { textAlign: 'center', padding: '40px' } 
    }, 'Loading clients...');
  }

  if (error) {
    return React.createElement('div', {
      style: {
        background: '#fee2e2',
        border: '1px solid #fca5a5',
        borderRadius: '8px',
        padding: '15px',
        color: '#dc2626'
      }
    }, 'Error: ', error);
  }

  return React.createElement('div', { style: { padding: '20px' } },
    // Header with stats
    React.createElement('div', {
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px'
      }
    },
      React.createElement('div', null,
        React.createElement('h2', { 
          style: { margin: 0, fontSize: '24px', color: '#1e293b' } 
        }, '👥 Enhanced Client Management'),
        React.createElement('p', {
          style: { margin: '5px 0 0 0', color: '#64748b' }
        }, `${stats.active_clients} active of ${stats.total_clients} total clients`)
      ),
      React.createElement('button', {
        onClick: () => setShowCreateForm(true),
        style: {
          background: '#10b981',
          color: 'white',
          border: 'none',
          padding: '10px 20px',
          borderRadius: '6px',
          fontSize: '14px',
          cursor: 'pointer'
        }
      }, '➕ Add Client')
    ),

    // Stats cards
    React.createElement('div', {
      style: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '30px'
      }
    },
      React.createElement('div', {
        style: {
          background: '#f0f9ff',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #bae6fd'
        }
      },
        React.createElement('div', {
          style: { fontSize: '24px', fontWeight: 'bold', color: '#0284c7' }
        }, stats.total_clients),
        React.createElement('div', {
          style: { fontSize: '14px', color: '#64748b' }
        }, 'Total Clients')
      ),
      React.createElement('div', {
        style: {
          background: '#f0fdf4',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #86efac'
        }
      },
        React.createElement('div', {
          style: { fontSize: '24px', fontWeight: 'bold', color: '#10b981' }
        }, stats.active_clients),
        React.createElement('div', {
          style: { fontSize: '14px', color: '#64748b' }
        }, 'Active Clients')
      ),
      React.createElement('div', {
        style: {
          background: '#fef3c7',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #fbbf24'
        }
      },
        React.createElement('div', {
          style: { fontSize: '24px', fontWeight: 'bold', color: '#d97706' }
        }, stats.clients_with_keys),
        React.createElement('div', {
          style: { fontSize: '14px', color: '#64748b' }
        }, 'With Klaviyo Keys')
      ),
      React.createElement('div', {
        style: {
          background: '#f3e8ff',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #c084fc'
        }
      },
        React.createElement('div', {
          style: { fontSize: '24px', fontWeight: 'bold', color: '#8b5cf6' }
        }, 
        stats.total_clients > 0 ? 
          Math.round((stats.clients_with_keys / stats.total_clients) * 100) + '%' : 
          '0%'
        ),
        React.createElement('div', {
          style: { fontSize: '14px', color: '#64748b' }
        }, 'API Coverage')
      )
    ),

    // Create/Edit form with tabs
    (showCreateForm || editingClient) && React.createElement('div', {
      style: {
        background: 'white',
        borderRadius: '8px',
        border: '1px solid #e2e8f0',
        marginBottom: '20px',
        overflow: 'hidden'
      }
    },
      // Form header
      React.createElement('div', {
        style: {
          background: '#f8fafc',
          padding: '15px 20px',
          borderBottom: '1px solid #e2e8f0'
        }
      },
        React.createElement('h3', {
          style: { margin: 0, fontSize: '18px' }
        }, editingClient ? 'Edit Client' : 'Create New Client')
      ),
      
      // Tab navigation
      React.createElement('div', {
        style: {
          display: 'flex',
          borderBottom: '1px solid #e2e8f0',
          background: '#f8fafc'
        }
      },
        React.createElement('button', {
          onClick: () => setActiveTab('basic'),
          style: tabButtonStyle(activeTab === 'basic')
        }, '📋 Basic Info'),
        React.createElement('button', {
          onClick: () => setActiveTab('brand'),
          style: tabButtonStyle(activeTab === 'brand')
        }, '🎨 Brand Manager'),
        React.createElement('button', {
          onClick: () => setActiveTab('segments'),
          style: tabButtonStyle(activeTab === 'segments')
        }, '👥 Affinity Segments'),
        React.createElement('button', {
          onClick: () => setActiveTab('growth'),
          style: tabButtonStyle(activeTab === 'growth')
        }, '📈 Growth Objectives')
      ),
      
      // Tab content
      React.createElement('div', {
        style: { padding: '20px' }
      }, renderFormTab()),
      
      // Form buttons
      React.createElement('div', {
        style: { 
          display: 'flex', 
          gap: '10px', 
          padding: '20px',
          borderTop: '1px solid #e2e8f0',
          background: '#f8fafc'
        }
      },
        React.createElement('button', {
          onClick: editingClient ? 
            () => handleUpdateClient(editingClient) : 
            handleCreateClient,
          style: {
            background: '#10b981',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '6px',
            fontSize: '14px',
            cursor: 'pointer'
          }
        }, editingClient ? 'Update Client' : 'Create Client'),
        
        React.createElement('button', {
          onClick: () => {
            setShowCreateForm(false);
            setEditingClient(null);
            resetForm();
          },
          style: {
            background: '#6b7280',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '6px',
            fontSize: '14px',
            cursor: 'pointer'
          }
        }, 'Cancel')
      )
    ),

    // Enhanced Clients list
    React.createElement('div', {
      style: {
        background: 'white',
        borderRadius: '8px',
        border: '1px solid #e2e8f0',
        overflow: 'hidden'
      }
    },
      React.createElement('div', {
        style: {
          background: '#f8fafc',
          padding: '15px 20px',
          borderBottom: '1px solid #e2e8f0',
          fontSize: '16px',
          fontWeight: '600'
        }
      }, 'Clients'),
      
      React.createElement('div', { style: { display: 'grid', gap: '1px' } },
        clients.map(client =>
          React.createElement('div', {
            key: client.id,
            style: {
              padding: '20px',
              borderBottom: '1px solid #f1f5f9',
              background: client.is_active ? 'white' : '#f9fafb'
            }
          },
            // Client header
            React.createElement('div', {
              style: {
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'start',
                marginBottom: '15px'
              }
            },
              React.createElement('div', null,
                React.createElement('h3', {
                  style: { 
                    margin: 0, 
                    fontSize: '18px', 
                    color: client.is_active ? '#1e293b' : '#64748b' 
                  }
                }, client.name),
                React.createElement('div', {
                  style: { 
                    fontSize: '12px', 
                    color: '#64748b',
                    marginTop: '4px'
                  }
                }, `ID: ${client.id} | Metric: ${client.metric_id || 'Not set'}`),
                client.key_growth_objective && React.createElement('div', {
                  style: {
                    display: 'inline-block',
                    background: '#f3e8ff',
                    color: '#8b5cf6',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    fontSize: '11px',
                    marginTop: '5px'
                  }
                }, `📈 ${client.key_growth_objective.replace(/_/g, ' ')}`)
              ),
              React.createElement('div', { 
                style: { 
                  display: 'flex', 
                  gap: '8px',
                  alignItems: 'center'
                } 
              },
                client.has_klaviyo_key && React.createElement('button', {
                  onClick: () => testKlaviyoConnection(client.id, client.name),
                  style: {
                    background: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }
                }, '🧪 Test'),
                
                React.createElement('button', {
                  onClick: () => startEdit(client),
                  style: {
                    background: '#10b981',
                    color: 'white',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }
                }, '✏️ Edit'),
                
                client.is_active && React.createElement('button', {
                  onClick: () => handleDeleteClient(client.id, client.name),
                  style: {
                    background: '#ef4444',
                    color: 'white',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }
                }, '🗑️'),
                
                React.createElement('span', {
                  style: {
                    background: client.is_active ? '#10b981' : '#ef4444',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    fontSize: '11px'
                  }
                }, client.is_active ? 'Active' : 'Inactive')
              )
            ),
            
            // Client details grid
            React.createElement('div', {
              style: {
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: '15px',
                fontSize: '14px',
                color: '#64748b'
              }
            },
              // Contact info
              React.createElement('div', null,
                React.createElement('strong', null, '👤 Contact: '),
                client.contact_name || 'Not set',
                client.contact_email && React.createElement('div', {
                  style: { fontSize: '12px' }
                }, client.contact_email)
              ),
              
              // Klaviyo status
              React.createElement('div', null,
                React.createElement('strong', null, '🔑 Klaviyo: '),
                client.has_klaviyo_key ? 
                  React.createElement('span', { style: { color: '#10b981' } }, 
                    `✓ ${client.klaviyo_key_preview}`) :
                  React.createElement('span', { style: { color: '#ef4444' } }, '✗ No key')
              ),
              
              // Website
              client.website && React.createElement('div', null,
                React.createElement('strong', null, '🌐 Website: '),
                React.createElement('a', {
                  href: client.website,
                  target: '_blank',
                  style: { color: '#3b82f6' }
                }, client.website.replace(/^https?:\/\//, ''))
              ),
              
              // Asana link
              client.asana_project_link && React.createElement('div', null,
                React.createElement('strong', null, '📋 Asana: '),
                React.createElement('a', {
                  href: client.asana_project_link,
                  target: '_blank',
                  style: { color: '#3b82f6' }
                }, 'View Project')
              )
            ),
            
            // Brand voice preview
            client.client_voice && React.createElement('div', {
              style: {
                marginTop: '10px',
                padding: '10px',
                background: '#f0f9ff',
                borderRadius: '4px',
                fontSize: '13px'
              }
            },
              React.createElement('strong', null, '🎯 Voice: '),
              client.client_voice.substring(0, 100),
              client.client_voice.length > 100 && '...'
            ),
            
            // Affinity segments summary
            (client.affinity_segment_1_name || client.affinity_segment_2_name || client.affinity_segment_3_name) &&
            React.createElement('div', {
              style: {
                marginTop: '10px',
                display: 'flex',
                gap: '10px',
                flexWrap: 'wrap'
              }
            },
              client.affinity_segment_1_name && React.createElement('span', {
                style: {
                  background: '#f0f9ff',
                  color: '#0284c7',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '12px'
                }
              }, client.affinity_segment_1_name),
              client.affinity_segment_2_name && React.createElement('span', {
                style: {
                  background: '#f0fdf4',
                  color: '#10b981',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '12px'
                }
              }, client.affinity_segment_2_name),
              client.affinity_segment_3_name && React.createElement('span', {
                style: {
                  background: '#fef3c7',
                  color: '#d97706',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '12px'
                }
              }, client.affinity_segment_3_name)
            )
          )
        )
      )
    )
  );
};

// Export for use in admin
window.AdminClientManagement = AdminClientManagement;