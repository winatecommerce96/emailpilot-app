/**
 * Modern Authentication Provider with Clerk Integration
 * Supports multi-tenant, refresh tokens, and API keys
 */

// Auth Context
const AuthV2Context = React.createContext(null);

// Auth Provider Component
function AuthV2Provider({ children }) {
    const [user, setUser] = React.useState(null);
    const [tenant, setTenant] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);
    const [tokens, setTokens] = React.useState({
        accessToken: null,
        refreshToken: null
    });

    // Load tokens from localStorage on mount
    React.useEffect(() => {
        const storedAccessToken = localStorage.getItem('access_token_v2');
        const storedRefreshToken = localStorage.getItem('refresh_token_v2');
        
        if (storedAccessToken && storedRefreshToken) {
            setTokens({
                accessToken: storedAccessToken,
                refreshToken: storedRefreshToken
            });
            fetchCurrentUser(storedAccessToken);
        } else {
            setLoading(false);
        }
    }, []);

    // Refresh token when access token expires
    const refreshAccessToken = React.useCallback(async () => {
        const refreshToken = tokens.refreshToken || localStorage.getItem('refresh_token_v2');
        
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        try {
            const response = await fetch('/api/auth/v2/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });

            if (!response.ok) {
                throw new Error('Failed to refresh token');
            }

            const data = await response.json();
            
            // Update tokens
            setTokens({
                accessToken: data.access_token,
                refreshToken: data.refresh_token
            });
            
            // Store in localStorage
            localStorage.setItem('access_token_v2', data.access_token);
            localStorage.setItem('refresh_token_v2', data.refresh_token);
            
            // Update user and tenant
            setUser(data.user);
            setTenant(data.tenant);
            
            return data.access_token;
        } catch (error) {
            console.error('Token refresh failed:', error);
            logout();
            throw error;
        }
    }, [tokens.refreshToken]);

    // Fetch with automatic token refresh
    const authenticatedFetch = React.useCallback(async (url, options = {}) => {
        let accessToken = tokens.accessToken || localStorage.getItem('access_token_v2');
        
        if (!accessToken) {
            throw new Error('Not authenticated');
        }

        // First attempt
        let response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${accessToken}`
            }
        });

        // If unauthorized, try refreshing token
        if (response.status === 401) {
            try {
                accessToken = await refreshAccessToken();
                
                // Retry with new token
                response = await fetch(url, {
                    ...options,
                    headers: {
                        ...options.headers,
                        'Authorization': `Bearer ${accessToken}`
                    }
                });
            } catch (error) {
                throw new Error('Authentication failed');
            }
        }

        return response;
    }, [tokens.accessToken, refreshAccessToken]);

    // Fetch current user
    const fetchCurrentUser = async (accessToken) => {
        try {
            const response = await fetch('/api/auth/v2/auth/me', {
                headers: {
                    'Authorization': `Bearer ${accessToken}`
                }
            });

            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
                setTenant(userData.tenant);
            } else {
                // Try to refresh token
                await refreshAccessToken();
            }
        } catch (error) {
            console.error('Failed to fetch current user:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    // Login function
    const login = async (email, password, tenantId = null) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/auth/v2/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    password,
                    tenant_id: tenantId
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }

            const data = await response.json();
            
            // Store tokens
            setTokens({
                accessToken: data.access_token,
                refreshToken: data.refresh_token
            });
            
            localStorage.setItem('access_token_v2', data.access_token);
            localStorage.setItem('refresh_token_v2', data.refresh_token);
            
            // Set user and tenant
            setUser(data.user);
            setTenant(data.tenant);
            
            return data;
        } catch (error) {
            setError(error.message);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    // Register function
    const register = async (email, password, name, company = null, tenantId = null) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/auth/v2/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    password,
                    name,
                    company,
                    tenant_id: tenantId
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Registration failed');
            }

            const data = await response.json();
            
            // Store tokens
            setTokens({
                accessToken: data.access_token,
                refreshToken: data.refresh_token
            });
            
            localStorage.setItem('access_token_v2', data.access_token);
            localStorage.setItem('refresh_token_v2', data.refresh_token);
            
            // Set user and tenant
            setUser(data.user);
            setTenant(data.tenant);
            
            return data;
        } catch (error) {
            setError(error.message);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    // Logout function
    const logout = async () => {
        try {
            // Call logout endpoint if we have a token
            if (tokens.accessToken) {
                await fetch('/api/auth/v2/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${tokens.accessToken}`
                    }
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear local state
            setUser(null);
            setTenant(null);
            setTokens({
                accessToken: null,
                refreshToken: null
            });
            
            // Clear localStorage
            localStorage.removeItem('access_token_v2');
            localStorage.removeItem('refresh_token_v2');
        }
    };

    // Switch tenant
    const switchTenant = async (tenantId) => {
        setLoading(true);
        setError(null);

        try {
            const response = await authenticatedFetch(`/api/auth/v2/tenants/${tenantId}/switch`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to switch tenant');
            }

            const data = await response.json();
            
            // Update tokens
            setTokens({
                accessToken: data.access_token,
                refreshToken: data.refresh_token
            });
            
            localStorage.setItem('access_token_v2', data.access_token);
            localStorage.setItem('refresh_token_v2', data.refresh_token);
            
            // Update tenant
            setTenant(data.tenant);
            
            return data;
        } catch (error) {
            setError(error.message);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    // SSO Login with Clerk
    const loginWithClerk = () => {
        const tenantId = tenant?.id;
        const url = tenantId 
            ? `/api/auth/v2/auth/sso/clerk?tenant_id=${tenantId}`
            : '/api/auth/v2/auth/sso/clerk';
        
        window.location.href = url;
    };

    // SSO Login with Google (legacy support)
    const loginWithGoogle = () => {
        const tenantId = tenant?.id;
        const url = tenantId 
            ? `/api/auth/v2/auth/sso/google?tenant_id=${tenantId}`
            : '/api/auth/v2/auth/sso/google';
        
        window.location.href = url;
    };

    // API Key Management
    const createApiKey = async (name, scopes = ['read'], expiresInDays = 90) => {
        try {
            const response = await authenticatedFetch('/api/auth/v2/auth/api-keys', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    scopes,
                    expires_in_days: expiresInDays
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create API key');
            }

            return await response.json();
        } catch (error) {
            setError(error.message);
            throw error;
        }
    };

    const listApiKeys = async () => {
        try {
            const response = await authenticatedFetch('/api/auth/v2/auth/api-keys');

            if (!response.ok) {
                throw new Error('Failed to fetch API keys');
            }

            return await response.json();
        } catch (error) {
            setError(error.message);
            throw error;
        }
    };

    const revokeApiKey = async (keyId) => {
        try {
            const response = await authenticatedFetch(`/api/auth/v2/auth/api-keys/${keyId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to revoke API key');
            }

            return await response.json();
        } catch (error) {
            setError(error.message);
            throw error;
        }
    };

    // Context value
    const value = {
        user,
        tenant,
        loading,
        error,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
        login,
        register,
        logout,
        switchTenant,
        loginWithClerk,
        loginWithGoogle,
        authenticatedFetch,
        createApiKey,
        listApiKeys,
        revokeApiKey
    };

    return React.createElement(
        AuthV2Context.Provider,
        { value },
        children
    );
}

// Hook to use auth context
function useAuthV2() {
    const context = React.useContext(AuthV2Context);
    
    if (!context) {
        throw new Error('useAuthV2 must be used within AuthV2Provider');
    }
    
    return context;
}

// Export for use in other components
window.AuthV2Provider = AuthV2Provider;
window.useAuthV2 = useAuthV2;