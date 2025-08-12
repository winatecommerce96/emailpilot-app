// Firebase Calendar Service - Handles calendar data operations
class FirebaseCalendarService {
    constructor() {
        this.apiBase = window.API_BASE_URL || '';
        this.events = {};
        this.clients = [];
        this.initialized = false;
    }

    // Initialize the service
    async initialize() {
        if (this.initialized) {
            return true;
        }
        
        try {
            // Check if the API is available
            const response = await fetch(`${this.apiBase}/api/calendar/health`);
            if (response.ok) {
                this.initialized = true;
                console.log('FirebaseCalendarService initialized successfully');
                return true;
            }
            throw new Error('Calendar API not available');
        } catch (error) {
            console.error('Failed to initialize FirebaseCalendarService:', error);
            throw error;
        }
    }

    // Get all events
    async getEvents() {
        try {
            const response = await axios.get(`${this.apiBase}/api/calendar/events`, {
                withCredentials: true
            });
            this.events = response.data || {};
            return this.events;
        } catch (error) {
            console.warn('Failed to fetch events, using empty data:', error);
            return {};
        }
    }

    // Get events for a specific client
    async getClientEvents(clientId) {
        try {
            const response = await axios.get(`${this.apiBase}/api/calendar/events/${clientId}`, {
                withCredentials: true
            });
            return response.data || {};
        } catch (error) {
            console.warn('Failed to fetch client events:', error);
            return {};
        }
    }

    // Save an event
    async saveEvent(eventId, eventData) {
        try {
            const response = await axios.post(`${this.apiBase}/api/calendar/events`, {
                id: eventId,
                ...eventData
            }, {
                withCredentials: true
            });
            return response.data;
        } catch (error) {
            console.error('Failed to save event:', error);
            throw error;
        }
    }

    // Delete an event
    async deleteEvent(eventId) {
        try {
            await axios.delete(`${this.apiBase}/api/calendar/events/${eventId}`, {
                withCredentials: true
            });
            return true;
        } catch (error) {
            console.error('Failed to delete event:', error);
            return false;
        }
    }

    // Get clients list
    async getClients() {
        try {
            const response = await axios.get(`${this.apiBase}/api/clients/`, {
                withCredentials: true
            });
            this.clients = response.data || [];
            return this.clients;
        } catch (error) {
            console.warn('Failed to fetch clients:', error);
            return [];
        }
    }

    // Get goals for evaluation
    async getGoals(clientId) {
        try {
            const response = await axios.get(`${this.apiBase}/api/goals/${clientId}`, {
                withCredentials: true
            });
            return response.data || [];
        } catch (error) {
            console.warn('Failed to fetch goals:', error);
            return [];
        }
    }

    // Get client goals (alias for getGoals)
    async getClientGoals(clientId) {
        return this.getGoals(clientId);
    }

    // Import from Google Docs (mock implementation)
    async importFromGoogleDocs(docUrl) {
        console.log('Google Docs import not yet implemented');
        return {
            success: false,
            message: 'Google Docs import is coming soon'
        };
    }

    // Chat with AI (mock implementation)
    async sendChatMessage(message) {
        return {
            response: "AI chat integration coming soon. For now, you can manually add and edit calendar events."
        };
    }
}

// Make it available globally
window.FirebaseCalendarService = FirebaseCalendarService;