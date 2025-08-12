// Gemini Chat Service - Handles AI chat functionality for the calendar
class GeminiChatService {
    constructor(firebaseService) {
        this.firebaseService = firebaseService;
        this.apiBase = window.API_BASE_URL || '';
    }

    // Send a chat message
    async sendMessage(message, clientId = null) {
        try {
            const response = await fetch(`${this.apiBase}/api/calendar/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    message: message,
                    client_id: clientId
                })
            });

            if (!response.ok) {
                throw new Error('Chat API error');
            }

            const data = await response.json();
            return data.response || data.message || "No response from AI";
        } catch (error) {
            console.error('Failed to send chat message:', error);
            return "I'm having trouble connecting to the AI service. Please try again later.";
        }
    }

    // Get chat history
    async getChatHistory(clientId = null) {
        try {
            const response = await fetch(`${this.apiBase}/api/calendar/chat/history${clientId ? `?client_id=${clientId}` : ''}`, {
                credentials: 'include'
            });

            if (!response.ok) {
                return [];
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to fetch chat history:', error);
            return [];
        }
    }

    // Clear chat history
    async clearChatHistory(clientId = null) {
        try {
            const response = await fetch(`${this.apiBase}/api/calendar/chat/history`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ client_id: clientId })
            });

            return response.ok;
        } catch (error) {
            console.error('Failed to clear chat history:', error);
            return false;
        }
    }
}

// Make it available globally
window.GeminiChatService = GeminiChatService;