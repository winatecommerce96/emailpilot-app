// Admin OAuth Configuration Component
const AdminOAuthConfig = () => {
    const [config, setConfig] = React.useState({
        client_id: '',
        client_secret: '',
        redirect_uri: 'http://localhost:8000/api/auth/google/callback'
    });
    
    const [status, setStatus] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [oauthStatus, setOauthStatus] = React.useState(null);
    const [admins, setAdmins] = React.useState([]);
    const [newAdminEmail, setNewAdminEmail] = React.useState('');
    
    // Check OAuth configuration status
    React.useEffect(() => {
        checkOAuthStatus();
        loadAdmins();
    }, []);
    
    const checkOAuthStatus = async () => {
        try {
            const response = await fetch('/api/auth/google/status');
            const data = await response.json();
            setOauthStatus(data);
            if (data.client_id_set) {
                setConfig(prev => ({ ...prev, client_id: '***CONFIGURED***' }));
            }
        } catch (error) {
            console.error('Failed to check OAuth status:', error);
        }
    };
    
    const loadAdmins = async () => {
        try {
            const response = await fetch('/api/auth/google/admins', {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                setAdmins(data.admins || []);
            }
        } catch (error) {
            console.error('Failed to load admins:', error);
        }
    };
    
    const handleSaveConfig = async () => {
        setLoading(true);
        setStatus(null);
        
        try {
            const response = await fetch('/api/auth/google/oauth-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                setStatus({ type: 'success', message: 'OAuth configuration saved successfully!' });
                checkOAuthStatus();
                // Clear sensitive data
                setConfig(prev => ({ ...prev, client_secret: '' }));
            } else {
                setStatus({ type: 'error', message: result.detail || 'Failed to save configuration' });
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Error saving configuration: ' + error.message });
        } finally {
            setLoading(false);
        }
    };
    
    const handleAddAdmin = async () => {
        if (!newAdminEmail) return;
        
        try {
            const response = await fetch('/api/auth/google/admins', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ email: newAdminEmail })
            });
            
            if (response.ok) {
                setNewAdminEmail('');
                loadAdmins();
                setStatus({ type: 'success', message: 'Admin user added successfully!' });
            } else {
                const result = await response.json();
                setStatus({ type: 'error', message: result.detail || 'Failed to add admin' });
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Error adding admin: ' + error.message });
        }
    };
    
    const handleRemoveAdmin = async (email) => {
        if (!confirm(`Remove ${email} from admins?`)) return;
        
        try {
            const response = await fetch(`/api/auth/google/admins/${email}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            if (response.ok) {
                loadAdmins();
                setStatus({ type: 'success', message: 'Admin removed successfully!' });
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Error removing admin: ' + error.message });
        }
    };
    
    return React.createElement('div', { 
        style: {
            padding: '20px',
            background: 'white',
            borderRadius: '8px',
            border: '1px solid #e2e8f0'
        }
    },
        React.createElement('h2', { 
            style: { 
                margin: '0 0 20px 0', 
                fontSize: '24px', 
                color: '#1e293b' 
            } 
        }, '🔐 Google OAuth Configuration'),
        
        // OAuth Status
        oauthStatus && React.createElement('div', { 
            style: {
                marginBottom: '24px',
                padding: '16px',
                borderRadius: '8px',
                background: oauthStatus.configured ? '#f0fdf4' : '#fef3c7',
                border: '1px solid ' + (oauthStatus.configured ? '#86efac' : '#fbbf24')
            }
        },
            React.createElement('div', { 
                style: { 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center' 
                }
            },
                React.createElement('div', null,
                    React.createElement('p', { 
                        style: { 
                            margin: 0, 
                            fontWeight: '600',
                            color: oauthStatus.configured ? '#10b981' : '#d97706'
                        } 
                    }, 
                        oauthStatus.configured ? '✅ OAuth Configured' : '⚠️ OAuth Not Configured'
                    ),
                    React.createElement('p', { 
                        style: { 
                            margin: '4px 0 0 0', 
                            fontSize: '14px', 
                            color: '#64748b' 
                        }
                    },
                        `Redirect URI: ${oauthStatus.redirect_uri}`
                    )
                ),
                React.createElement('a', {
                    href: '/api/auth/google/login',
                    style: {
                        padding: '8px 16px',
                        background: '#3b82f6',
                        color: 'white',
                        textDecoration: 'none',
                        borderRadius: '6px',
                        fontSize: '14px',
                        fontWeight: '500'
                    }
                }, 'Test Login')
            )
        ),
        
        // Configuration Form
        React.createElement('div', { 
            style: { 
                marginBottom: '24px',
                padding: '20px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
            }
        },
            React.createElement('h3', {
                style: { 
                    margin: '0 0 16px 0', 
                    fontSize: '18px', 
                    color: '#1e293b' 
                }
            }, 'OAuth Credentials'),
            
            React.createElement('div', { style: { display: 'grid', gap: '16px' } },
                React.createElement('div', null,
                    React.createElement('label', { 
                        style: { 
                            display: 'block', 
                            fontSize: '14px', 
                            fontWeight: '500', 
                            marginBottom: '4px',
                            color: '#374151'
                        } 
                    }, 'Client ID'),
                    React.createElement('input', {
                        type: 'text',
                        value: config.client_id,
                        onChange: (e) => setConfig({ ...config, client_id: e.target.value }),
                        placeholder: 'Your Google OAuth Client ID',
                        style: {
                            width: '100%',
                            padding: '10px',
                            borderRadius: '6px',
                            border: '1px solid #d1d5db',
                            fontSize: '14px',
                            background: 'white'
                        }
                    })
                ),
                
                React.createElement('div', null,
                    React.createElement('label', { 
                        style: { 
                            display: 'block', 
                            fontSize: '14px', 
                            fontWeight: '500', 
                            marginBottom: '4px',
                            color: '#374151'
                        } 
                    }, 'Client Secret'),
                    React.createElement('input', {
                        type: 'password',
                        value: config.client_secret,
                        onChange: (e) => setConfig({ ...config, client_secret: e.target.value }),
                        placeholder: 'Your Google OAuth Client Secret',
                        style: {
                            width: '100%',
                            padding: '10px',
                            borderRadius: '6px',
                            border: '1px solid #d1d5db',
                            fontSize: '14px',
                            background: 'white'
                        }
                    })
                ),
                
                React.createElement('div', null,
                    React.createElement('label', { 
                        style: { 
                            display: 'block', 
                            fontSize: '14px', 
                            fontWeight: '500', 
                            marginBottom: '4px',
                            color: '#374151'
                        } 
                    }, 'Redirect URI (Add this to Google Console)'),
                    React.createElement('input', {
                        type: 'text',
                        value: config.redirect_uri,
                        readOnly: true,
                        onClick: (e) => e.target.select(),
                        style: {
                            width: '100%',
                            padding: '10px',
                            borderRadius: '6px',
                            border: '1px solid #d1d5db',
                            fontSize: '14px',
                            background: '#f9fafb',
                            color: '#6b7280'
                        }
                    })
                )
            ),
            
            // Save Button
            React.createElement('button', {
                onClick: handleSaveConfig,
                disabled: loading || !config.client_id || !config.client_secret,
                style: {
                    marginTop: '16px',
                    width: '100%',
                    padding: '12px',
                    background: (loading || !config.client_id || !config.client_secret) ? '#9ca3af' : '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '14px',
                    fontWeight: '500',
                    cursor: (loading || !config.client_id || !config.client_secret) ? 'not-allowed' : 'pointer'
                }
            }, loading ? 'Saving...' : 'Save OAuth Configuration')
        ),
        
        // Status Message
        status && React.createElement('div', {
            style: {
                marginBottom: '24px',
                padding: '12px',
                borderRadius: '6px',
                background: status.type === 'success' ? '#f0fdf4' : '#fef2f2',
                border: '1px solid ' + (status.type === 'success' ? '#86efac' : '#fca5a5'),
                color: status.type === 'success' ? '#166534' : '#dc2626'
            }
        }, status.message),
        
        // Admin Users Section
        React.createElement('div', { 
            style: {
                marginTop: '32px',
                padding: '20px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
            }
        },
            React.createElement('h3', { 
                style: { 
                    margin: '0 0 16px 0', 
                    fontSize: '18px', 
                    color: '#1e293b' 
                }
            }, '👥 Admin Users'),
            
            // Admin List
            React.createElement('div', { 
                style: { 
                    marginBottom: '16px' 
                }
            },
                admins.length === 0 ? 
                    React.createElement('p', {
                        style: { 
                            margin: 0, 
                            color: '#6b7280', 
                            fontStyle: 'italic' 
                        }
                    }, 'No admin users configured') :
                    admins.map(admin => 
                        React.createElement('div', { 
                            key: admin.email,
                            style: {
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '12px',
                                marginBottom: '8px',
                                background: 'white',
                                borderRadius: '6px',
                                border: '1px solid #e2e8f0'
                            }
                        },
                            React.createElement('span', {
                                style: { fontSize: '14px', color: '#374151' }
                            }, admin.email),
                            React.createElement('button', {
                                onClick: () => handleRemoveAdmin(admin.email),
                                style: {
                                    padding: '4px 8px',
                                    background: '#ef4444',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    fontSize: '12px',
                                    cursor: 'pointer'
                                }
                            }, 'Remove')
                        )
                    )
            ),
            
            // Add Admin Form
            React.createElement('div', { 
                style: { 
                    display: 'flex', 
                    gap: '8px' 
                }
            },
                React.createElement('input', {
                    type: 'email',
                    value: newAdminEmail,
                    onChange: (e) => setNewAdminEmail(e.target.value),
                    placeholder: 'admin@example.com',
                    style: {
                        flex: 1,
                        padding: '10px',
                        borderRadius: '6px',
                        border: '1px solid #d1d5db',
                        fontSize: '14px',
                        background: 'white'
                    }
                }),
                React.createElement('button', {
                    onClick: handleAddAdmin,
                    disabled: !newAdminEmail,
                    style: {
                        padding: '10px 16px',
                        background: !newAdminEmail ? '#9ca3af' : '#10b981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '14px',
                        fontWeight: '500',
                        cursor: !newAdminEmail ? 'not-allowed' : 'pointer'
                    }
                }, 'Add Admin')
            )
        ),
        
        // Instructions
        React.createElement('div', { 
            style: {
                marginTop: '32px',
                padding: '20px',
                background: '#eff6ff',
                borderRadius: '8px',
                border: '1px solid #bfdbfe'
            }
        },
            React.createElement('h4', { 
                style: { 
                    margin: '0 0 12px 0', 
                    fontSize: '16px', 
                    color: '#1e40af' 
                }
            }, '📋 Setup Instructions'),
            React.createElement('ol', { 
                style: { 
                    margin: 0,
                    paddingLeft: '20px',
                    fontSize: '14px',
                    color: '#374151',
                    lineHeight: '1.5'
                }
            },
                React.createElement('li', { style: { marginBottom: '4px' } }, 
                    'Go to Google Cloud Console > APIs & Services > Credentials'
                ),
                React.createElement('li', { style: { marginBottom: '4px' } }, 
                    'Create OAuth 2.0 Client ID (Web application)'
                ),
                React.createElement('li', { style: { marginBottom: '4px' } }, 
                    'Add the Redirect URI shown above to Authorized redirect URIs'
                ),
                React.createElement('li', { style: { marginBottom: '4px' } }, 
                    'Copy Client ID and Client Secret here'
                ),
                React.createElement('li', null, 
                    'Save configuration and test login'
                )
            )
        )
    );
};

// Export for global use
if (typeof window !== 'undefined') {
    window.AdminOAuthConfig = AdminOAuthConfig;
}