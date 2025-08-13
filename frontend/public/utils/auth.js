// Authentication State Manager for EmailPilot
(function() {
    'use strict';
    
    // Authentication state
    let authState = {
        isAuthenticated: false,
        user: null,
        isAdmin: false,
        token: null,
        loading: true
    };
    
    // Event emitter for auth state changes
    const authEvents = new EventTarget();
    
    // Auth service
    const AuthService = {
        // Get current auth state
        getState: () => {
            return { ...authState };
        },
        
        // Check if user is authenticated
        isAuthenticated: () => {
            return authState.isAuthenticated;
        },
        
        // Check if user is admin
        isAdmin: () => {
            return authState.isAdmin;
        },
        
        // Get user info
        getUser: () => {
            return authState.user;
        },
        
        // Set auth state
        setState: (newState) => {
            const oldState = { ...authState };
            authState = { ...authState, ...newState };
            
            // Emit state change event
            authEvents.dispatchEvent(new CustomEvent('auth:statechange', {
                detail: { oldState, newState: authState }
            }));
        },
        
        // Subscribe to auth state changes
        subscribe: (callback) => {
            authEvents.addEventListener('auth:statechange', callback);
            
            // Return unsubscribe function
            return () => {
                authEvents.removeEventListener('auth:statechange', callback);
            };
        },
        
        // Initialize auth state from server
        init: async () => {
            try {
                authState.loading = true;
                
                // Check current session
                const response = await fetch('/api/auth/me', {
                    credentials: 'include'
                });
                
                if (response.ok) {
                    const userData = await response.json();
                    AuthService.setState({
                        isAuthenticated: true,
                        user: userData,
                        isAdmin: userData.is_admin || false,
                        loading: false
                    });
                } else {
                    AuthService.setState({
                        isAuthenticated: false,
                        user: null,
                        isAdmin: false,
                        loading: false
                    });
                }
            } catch (error) {
                console.error('Failed to initialize auth state:', error);
                AuthService.setState({
                    isAuthenticated: false,
                    user: null,
                    isAdmin: false,
                    loading: false
                });
            }
        },
        
        // Login with Google OAuth
        loginWithGoogle: () => {
            window.location.href = '/api/auth/google/login';
        },
        
        // Logout
        logout: async () => {
            try {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    credentials: 'include'
                });
            } catch (error) {
                console.error('Logout error:', error);
            } finally {
                AuthService.setState({
                    isAuthenticated: false,
                    user: null,
                    isAdmin: false,
                    token: null
                });
            }
        },
        
        // Check OAuth configuration status
        checkOAuthConfig: async () => {
            try {
                const response = await fetch('/api/auth/google/status');
                return await response.json();
            } catch (error) {
                console.error('Failed to check OAuth config:', error);
                return { configured: false };
            }
        }
    };
    
    // Navigation component for admin links
    const AdminNavigation = () => {
        const [authState, setAuthState] = React.useState(AuthService.getState());
        const [oauthConfig, setOauthConfig] = React.useState(null);
        
        // Subscribe to auth changes
        React.useEffect(() => {
            const unsubscribe = AuthService.subscribe((event) => {
                setAuthState(event.detail.newState);
            });
            
            return unsubscribe;
        }, []);
        
        // Load OAuth config status
        React.useEffect(() => {
            AuthService.checkOAuthConfig().then(setOauthConfig);
        }, []);
        
        // Don't show nav if still loading
        if (authState.loading) {
            return null;
        }
        
        return React.createElement('nav', {
            style: {
                position: 'fixed',
                top: 0,
                right: 0,
                zIndex: 1000,
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(10px)',
                border: '1px solid #e2e8f0',
                borderRadius: '0 0 0 8px',
                padding: '12px',
                display: 'flex',
                gap: '12px',
                alignItems: 'center',
                fontSize: '14px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }
        },
            // OAuth Config Status
            oauthConfig && React.createElement('div', {
                style: {
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    background: oauthConfig.configured ? '#f0fdf4' : '#fef3c7',
                    border: '1px solid ' + (oauthConfig.configured ? '#86efac' : '#fbbf24'),
                    color: oauthConfig.configured ? '#166534' : '#d97706'
                }
            },
                React.createElement('span', null, oauthConfig.configured ? '✅' : '⚠️'),
                React.createElement('span', null, oauthConfig.configured ? 'OAuth OK' : 'OAuth Setup')
            ),
            
            // Admin Link
            React.createElement('a', {
                href: '/admin',
                style: {
                    padding: '8px 16px',
                    background: '#3b82f6',
                    color: 'white',
                    textDecoration: 'none',
                    borderRadius: '6px',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                },
                title: 'Admin Panel'
            }, 
                React.createElement('span', null, '⚙️'),
                React.createElement('span', null, 'Admin Panel')
            ),
            
            // User Auth Status
            authState.isAuthenticated ? 
                React.createElement('div', {
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }
                },
                    React.createElement('span', {
                        style: {
                            color: '#374151',
                            fontSize: '12px'
                        }
                    }, `👤 ${authState.user?.email || 'User'}`),
                    React.createElement('button', {
                        onClick: AuthService.logout,
                        style: {
                            padding: '6px 10px',
                            background: '#ef4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            fontSize: '12px',
                            cursor: 'pointer'
                        }
                    }, 'Logout')
                ) :
                React.createElement('button', {
                    onClick: AuthService.loginWithGoogle,
                    style: {
                        padding: '8px 12px',
                        background: '#4285f4',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '14px',
                        fontWeight: '500',
                        cursor: 'pointer'
                    }
                }, '🔑 Login')
        );
    };
    
    // Initialize auth service when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            AuthService.init();
        });
    } else {
        AuthService.init();
    }
    
    // Export to global scope
    window.AuthService = AuthService;
    window.AdminNavigation = AdminNavigation;
    
    console.log('✅ Auth service initialized');
})();