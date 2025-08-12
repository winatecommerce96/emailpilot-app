// Firebase Calendar Core - Direct Firebase Integration for React Components
const { useState, useEffect, useCallback, useRef } = React;

// Firebase configuration for EmailPilot
const FIREBASE_CONFIG = {
    apiKey: "AIzaSyB0RrH7hbER2R-SzXfNmFe0O32HhH7HBEM",
    authDomain: "emailpilot-438321.firebaseapp.com",
    projectId: "emailpilot-438321",
    storageBucket: "emailpilot-438321.appspot.com",
    messagingSenderId: "104067375141",
    appId: "1:104067375141:web:2b65c86eec8e8c8b4c9f3a"
};

const GEMINI_API_KEY = "AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs";
const GOOGLE_API_KEY = "AIzaSyAMeP8IjAfqmHAh7MeN5lpu2OpHhfRTTEg";
const GOOGLE_CLIENT_ID = "1058910766003-pqu4avth8ltclpbtpk81k0ln21dl8jue.apps.googleusercontent.com";

// Campaign type colors and revenue multipliers
const CAMPAIGN_COLORS = {
    'RRB Promotion': 'bg-red-300 text-red-800',
    'Cheese Club': 'bg-green-200 text-green-800',
    'Nurturing/Education': 'bg-blue-200 text-blue-800',
    'Community/Lifestyle': 'bg-purple-200 text-purple-800',
    'Re-engagement': 'bg-yellow-200 text-yellow-800',
    'SMS Alert': 'bg-orange-300 text-orange-800',
    'default': 'bg-gray-200 text-gray-800'
};

const REVENUE_MULTIPLIERS = {
    'RRB Promotion': 1.5,
    'Cheese Club': 2.0,
    'Nurturing/Education': 0.8,
    'Community/Lifestyle': 0.7,
    'Re-engagement': 1.2,
    'SMS Alert': 1.3,
    'default': 1.0
};

// Firebase service for calendar operations
class FirebaseCalendarService {
    constructor() {
        this.db = null;
        this.auth = null;
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return true;

        try {
            // Import Firebase dynamically
            const { initializeApp } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js");
            const { getAuth, signInAnonymously } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js");
            const { getFirestore, doc, getDoc, setDoc, deleteDoc, collection, getDocs, query, where, orderBy } = await import("https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js");

            // Initialize Firebase
            const app = initializeApp(FIREBASE_CONFIG);
            this.auth = getAuth(app);
            this.db = getFirestore(app);

            // Sign in anonymously
            await signInAnonymously(this.auth);
            
            // Store Firebase functions for later use
            this.firebaseUtils = {
                doc, getDoc, setDoc, deleteDoc, collection, getDocs, query, where, orderBy
            };

            this.initialized = true;
            console.log('Firebase Calendar Service initialized');
            return true;
        } catch (error) {
            console.error('Error initializing Firebase Calendar Service:', error);
            return false;
        }
    }

    async getClients() {
        if (!this.initialized) await this.initialize();
        
        try {
            const { collection, getDocs } = this.firebaseUtils;
            const clientsRef = collection(this.db, 'clients');
            const snapshot = await getDocs(clientsRef);
            
            const clients = [];
            snapshot.forEach(doc => {
                clients.push({ id: doc.id, ...doc.data() });
            });
            
            return clients;
        } catch (error) {
            console.error('Error fetching clients:', error);
            return [];
        }
    }

    async getClientData(clientId) {
        if (!this.initialized) await this.initialize();
        
        try {
            const { doc, getDoc } = this.firebaseUtils;
            const clientRef = doc(this.db, 'clients', clientId);
            const clientSnap = await getDoc(clientRef);
            
            if (clientSnap.exists()) {
                return clientSnap.data();
            }
            return null;
        } catch (error) {
            console.error('Error fetching client data:', error);
            return null;
        }
    }

    async saveClientData(clientId, data) {
        if (!this.initialized) await this.initialize();
        
        try {
            const { doc, setDoc } = this.firebaseUtils;
            const clientRef = doc(this.db, 'clients', clientId);
            await setDoc(clientRef, { ...data, lastModified: new Date().toISOString() }, { merge: true });
            return true;
        } catch (error) {
            console.error('Error saving client data:', error);
            return false;
        }
    }

    async createClient(clientData) {
        if (!this.initialized) await this.initialize();
        
        try {
            const { doc, setDoc } = this.firebaseUtils;
            const clientId = clientData.name.toLowerCase().replace(/\s+/g, '-') + '-' + Date.now();
            const clientRef = doc(this.db, 'clients', clientId);
            await setDoc(clientRef, { ...clientData, id: clientId });
            return clientId;
        } catch (error) {
            console.error('Error creating client:', error);
            return null;
        }
    }

    async deleteClient(clientId) {
        if (!this.initialized) await this.initialize();
        
        try {
            const { doc, deleteDoc } = this.firebaseUtils;
            const clientRef = doc(this.db, 'clients', clientId);
            await deleteDoc(clientRef);
            return true;
        } catch (error) {
            console.error('Error deleting client:', error);
            return false;
        }
    }

    async getClientGoals(clientId) {
        if (!this.initialized) await this.initialize();
        
        try {
            const { collection, query, where, orderBy, getDocs } = this.firebaseUtils;
            const goalsRef = collection(this.db, 'goals');
            const q = query(goalsRef, where('client_id', '==', clientId), orderBy('created_at', 'desc'));
            const snapshot = await getDocs(q);
            
            const goals = [];
            snapshot.forEach(doc => {
                goals.push({ id: doc.id, ...doc.data() });
            });
            
            return goals;
        } catch (error) {
            console.error('Error fetching goals:', error);
            return [];
        }
    }

    // Campaign type detection
    detectCampaignType(title, content) {
        const text = `${title} ${content}`.toLowerCase();
        
        if (text.includes('rrb') || text.includes('promotion')) return 'RRB Promotion';
        if (text.includes('cheese club')) return 'Cheese Club';
        if (text.includes('nurturing') || text.includes('education')) return 'Nurturing/Education';
        if (text.includes('community') || text.includes('lifestyle')) return 'Community/Lifestyle';
        if (text.includes('re-engagement')) return 'Re-engagement';
        if (text.includes('sms')) return 'SMS Alert';
        
        return 'default';
    }

    // Revenue calculation
    calculateEstimatedRevenue(campaigns) {
        let totalEstimated = 0;
        const baseRevenuePerCampaign = 500;
        
        Object.values(campaigns).forEach(campaign => {
            const campaignType = this.detectCampaignType(campaign.title || '', campaign.content || '');
            const multiplier = REVENUE_MULTIPLIERS[campaignType] || REVENUE_MULTIPLIERS.default;
            totalEstimated += baseRevenuePerCampaign * multiplier;
        });
        
        return totalEstimated;
    }

    // Get campaigns for a specific month
    getCampaignsForMonth(campaigns, year, month) {
        const monthCampaigns = {};
        const startDate = new Date(year, month, 1);
        const endDate = new Date(year, month + 1, 0);
        
        Object.entries(campaigns).forEach(([id, campaign]) => {
            const campaignDate = new Date(campaign.date);
            if (campaignDate >= startDate && campaignDate <= endDate) {
                monthCampaigns[id] = campaign;
            }
        });
        
        return monthCampaigns;
    }
}

// Gemini AI integration for goal-aware chat
class GeminiChatService {
    constructor(calendarService) {
        this.calendarService = calendarService;
    }

    async chatWithGemini(chatHistory, newMessage, clientName, campaigns, goals) {
        const today = new Date().toISOString().split('T')[0];
        const currentDate = new Date();
        const currentMonthCampaigns = this.calendarService.getCampaignsForMonth(campaigns, currentDate.getFullYear(), currentDate.getMonth());
        const estimatedRevenue = this.calendarService.calculateEstimatedRevenue(currentMonthCampaigns);
        
        // Find current month goal
        const currentMonthGoal = goals.find(g => 
            g.year === currentDate.getFullYear() && 
            g.month === currentDate.getMonth() + 1
        );
        
        let goalsContext = '';
        if (currentMonthGoal) {
            const targetRevenue = currentMonthGoal.revenue_goal || 0;
            const progress = targetRevenue > 0 ? (estimatedRevenue / targetRevenue) * 100 : 0;
            goalsContext = `
**REVENUE GOALS CONTEXT**
- Current Month Goal: $${targetRevenue.toLocaleString()}
- Estimated Revenue from Scheduled Campaigns: $${estimatedRevenue.toLocaleString()}
- Progress: ${Math.round(progress)}%
- Campaigns Scheduled: ${Object.keys(currentMonthCampaigns).length}
${progress < 75 ? '- WARNING: Revenue goal may not be met. Consider adding high-value campaigns.' : ''}
`;
        }

        const systemInstruction = `You are a Goal-Aware Calendar AI Assistant. Your capabilities are to answer questions about the calendar events, revenue goals, and to perform actions to modify the calendar.

**CONTEXT**
- Today's date is: ${today}.
- The current client is: ${clientName}.
${goalsContext}

**CAMPAIGN TYPE REVENUE MULTIPLIERS**
- RRB Promotion: 1.5x base revenue
- Cheese Club: 2.0x base revenue
- Nurturing/Education: 0.8x base revenue
- Community/Lifestyle: 0.7x base revenue
- Re-engagement: 1.2x base revenue
- SMS Alert: 1.3x base revenue

**INSTRUCTIONS**
1. **Analyze the User's Request:** Understand if the user is asking about campaigns, revenue goals, or requesting an action.
2. **For Questions:** Answer based on calendar data, goals, and revenue projections.
3. **For Actions:** Respond with a single JSON object describing the action.
4. **Goal Awareness:** When suggesting campaigns, prioritize high-revenue types if goal achievement is at risk.

**ACTION JSON FORMATS**
- **Delete:** \`{"action": "delete", "eventId": "EVENT_ID_TO_DELETE"}\`
- **Update:** \`{"action": "update", "eventId": "EVENT_ID_TO_UPDATE", "updates": {"field_to_change": "new_value"}}\`
- **Create:** \`{"action": "create", "event": {"date": "YYYY-MM-DD", "title": "New Event Title", "content": "Details..."}}\`

**Campaign Data:**
${JSON.stringify(campaigns, null, 2)}

**Goals Data:**
${JSON.stringify(goals, null, 2)}
`;

        try {
            const contents = [
                ...chatHistory,
                { role: "user", parts: [{ text: newMessage }] }
            ];

            const payload = {
                contents: contents,
                systemInstruction: { parts: [{ text: systemInstruction }] }
            };

            const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key=${GEMINI_API_KEY}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Gemini API error: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.candidates?.[0]?.content?.parts?.[0]?.text) {
                return result.candidates[0].content.parts[0].text;
            } else {
                throw new Error('Unexpected response structure from Gemini');
            }
        } catch (error) {
            console.error('Gemini chat error:', error);
            return "I'm sorry, I encountered an error trying to process your request.";
        }
    }
}

// Export services for use in React components
window.FirebaseCalendarService = FirebaseCalendarService;
window.GeminiChatService = GeminiChatService;
window.CAMPAIGN_COLORS = CAMPAIGN_COLORS;
window.REVENUE_MULTIPLIERS = REVENUE_MULTIPLIERS;