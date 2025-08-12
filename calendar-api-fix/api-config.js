// Shared API Configuration for EmailPilot
// This file provides consistent API configuration across all components

(function() {
    'use strict';
    
    // Determine API base URL based on environment
    const API_BASE = window.API_BASE || 
        (window.location.hostname === 'emailpilot.ai'
            ? 'https://emailpilot-api-935786836546.us-central1.run.app'
            : '');
    
    // Helper function to construct API URLs
    const api = (path) => `${API_BASE}${path}`;
    
    // Common API endpoints
    const API_ENDPOINTS = {
        // Client endpoints
        clients: [
            '/api/clients',
            '/api/firebase-calendar-test/clients',
            '/clients',
            '/api/calendar/clients'
        ],
        
        // Goals endpoints (use with clientId)
        goals: [
            '/api/goals/',
            '/api/goals-calendar-test/goals/',
            '/api/goals/clients/',
            '/goals/'
        ],
        
        // Events endpoints (use with client_id param)
        events: [
            '/api/calendar/events',
            '/api/firebase-calendar-test/events',
            '/api/events',
            '/calendar/events'
        ],
        
        // Dashboard endpoints
        dashboard: [
            '/api/dashboard',
            '/api/reports/dashboard',
            '/dashboard',
            '/api/analytics/dashboard'
        ],
        
        // Reports endpoints (use with clientId)
        reports: [
            '/api/reports/',
            '/api/analytics/reports/',
            '/reports/'
        ]
    };
    
    // Fetch wrapper with retry logic
    async function fetchWithFallback(endpoints, options = {}) {
        const errors = [];
        
        for (const endpoint of endpoints) {
            try {
                const url = api(endpoint);
                console.log(`[API] Trying: ${url}`);
                
                const response = await fetch(url, {
                    credentials: 'include',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });
                
                if (response.ok) {
                    const data = await response.json();
                    console.log(`[API] Success: ${endpoint}`);
                    return { success: true, data, endpoint };
                }
                
                errors.push(`${endpoint}: ${response.status} ${response.statusText}`);
            } catch (error) {
                errors.push(`${endpoint}: ${error.message}`);
            }
        }
        
        console.warn('[API] All endpoints failed:', errors);
        return { success: false, errors };
    }
    
    // API client object
    const APIClient = {
        // Get all clients
        async getClients() {
            const result = await fetchWithFallback(API_ENDPOINTS.clients);
            if (result.success) {
                return Array.isArray(result.data) ? result.data : (result.data.clients || []);
            }
            return [];
        },
        
        // Get client goals
        async getGoals(clientId) {
            const endpoints = API_ENDPOINTS.goals.map(e => `${e}${clientId}`);
            const result = await fetchWithFallback(endpoints);
            if (result.success) {
                return Array.isArray(result.data) ? result.data : (result.data.goals || []);
            }
            return [];
        },
        
        // Get client events
        async getEvents(clientId) {
            const endpoints = API_ENDPOINTS.events.map(e => `${e}?client_id=${clientId}`);
            const result = await fetchWithFallback(endpoints);
            if (result.success) {
                return Array.isArray(result.data) ? result.data : (result.data.events || []);
            }
            return [];
        },
        
        // Get dashboard data
        async getDashboard() {
            const result = await fetchWithFallback(API_ENDPOINTS.dashboard);
            return result.success ? result.data : null;
        },
        
        // Get client reports
        async getReports(clientId) {
            const endpoints = [
                ...API_ENDPOINTS.reports.map(e => `${e}${clientId}`),
                `/api/reports?client_id=${clientId}`
            ];
            const result = await fetchWithFallback(endpoints);
            if (result.success) {
                return Array.isArray(result.data) ? result.data : (result.data.reports || []);
            }
            return [];
        },
        
        // Create event
        async createEvent(eventData) {
            const result = await fetchWithFallback(
                API_ENDPOINTS.events,
                {
                    method: 'POST',
                    body: JSON.stringify(eventData)
                }
            );
            return result.success ? result.data : null;
        },
        
        // Update event
        async updateEvent(eventId, updates) {
            const endpoints = API_ENDPOINTS.events.map(e => `${e}/${eventId}`);
            const result = await fetchWithFallback(
                endpoints,
                {
                    method: 'PUT',
                    body: JSON.stringify(updates)
                }
            );
            return result.success;
        },
        
        // Delete event
        async deleteEvent(eventId) {
            const endpoints = API_ENDPOINTS.events.map(e => `${e}/${eventId}`);
            const result = await fetchWithFallback(
                endpoints,
                { method: 'DELETE' }
            );
            return result.success;
        }
    };
    
    // Make available globally
    window.EmailPilotAPI = {
        API_BASE,
        api,
        API_ENDPOINTS,
        fetchWithFallback,
        client: APIClient
    };
    
    console.log('[API Config] Initialized:', {
        hostname: window.location.hostname,
        API_BASE,
        isProduction: window.location.hostname === 'emailpilot.ai'
    });
    
})();