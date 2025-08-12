// MCP Cloud Function Configuration
// Centralized configuration for MCP endpoints

window.MCPConfig = {
    // Cloud Function Base URLs
    endpoints: {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health',
        execute: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-execute',
        usage: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-usage'
    },
    
    // Request configuration
    requestConfig: {
        timeout: 30000, // 30 seconds
        retries: 3,
        retryDelay: 1000 // 1 second
    },
    
    // CORS configuration
    corsConfig: {
        mode: 'cors',
        credentials: 'omit',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    },
    
    // Helper function to build URLs
    buildUrl: function(endpoint, path = '') {
        const baseUrl = this.endpoints[endpoint];
        if (!baseUrl) {
            throw new Error(`Unknown endpoint: ${endpoint}`);
        }
        return path ? `${baseUrl}${path}` : baseUrl;
    },
    
    // Helper function to make requests with retry logic
    makeRequest: async function(url, options = {}) {
        const config = {
            ...this.corsConfig,
            ...options,
            headers: {
                ...this.corsConfig.headers,
                ...options.headers
            }
        };
        
        // Add authorization header if token is available
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        
        let lastError;
        for (let attempt = 0; attempt < this.requestConfig.retries; attempt++) {
            try {
                const response = await fetch(url, config);
                
                // Handle non-OK responses
                if (!response.ok) {
                    const errorText = await response.text();
                    let errorMessage;
                    try {
                        const errorJson = JSON.parse(errorText);
                        errorMessage = errorJson.detail || errorJson.message || errorText;
                    } catch {
                        errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`;
                    }
                    throw new Error(errorMessage);
                }
                
                // Handle empty responses
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                } else {
                    const text = await response.text();
                    return text ? JSON.parse(text) : {};
                }
            } catch (error) {
                lastError = error;
                console.warn(`Request attempt ${attempt + 1} failed:`, error.message);
                
                if (attempt < this.requestConfig.retries - 1) {
                    await new Promise(resolve => setTimeout(resolve, this.requestConfig.retryDelay));
                }
            }
        }
        
        throw lastError;
    },
    
    // API helper functions
    api: {
        // Models API
        getModels: function() {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('models'));
        },
        
        // Clients API
        getClients: function() {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('clients'));
        },
        
        getClient: function(clientId) {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('clients', `/${clientId}`));
        },
        
        createClient: function(clientData) {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('clients'), {
                method: 'POST',
                body: JSON.stringify(clientData)
            });
        },
        
        updateClient: function(clientId, clientData) {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('clients', `/${clientId}`), {
                method: 'PUT',
                body: JSON.stringify(clientData)
            });
        },
        
        deleteClient: function(clientId) {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('clients', `/${clientId}`), {
                method: 'DELETE'
            });
        },
        
        testClient: function(clientId, testData) {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('clients', `/${clientId}/test`), {
                method: 'POST',
                body: JSON.stringify(testData)
            });
        },
        
        // Health check
        checkHealth: function() {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('health'));
        },
        
        // Execute API
        executeTool: function(executeData) {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('execute'), {
                method: 'POST',
                body: JSON.stringify(executeData)
            });
        },
        
        // Usage API
        getUsageStats: function(clientId, period = 'weekly') {
            return window.MCPConfig.makeRequest(window.MCPConfig.buildUrl('usage', `/${clientId}/stats?period=${period}`));
        }
    }
};

console.log('MCP Config loaded with endpoints:', window.MCPConfig.endpoints);