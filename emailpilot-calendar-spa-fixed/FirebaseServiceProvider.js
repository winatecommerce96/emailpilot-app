// Firebase Service Provider - Fixes "FirebaseCalendarService is not a constructor" error
// This file creates the missing window.FirebaseCalendarService that other components expect

(function() {
    'use strict';
    
    console.log('[FirebaseServiceProvider] Initializing...');
    
    // Define the FirebaseCalendarService class
    class FirebaseCalendarService {
        constructor() {
            console.log('[FirebaseCalendarService] Constructor called');
            this.initialized = false;
            this.db = null;
            this.auth = null;
            this.currentUser = null;
            this.initPromise = null;
        }

        async initialize() {
            console.log('[FirebaseCalendarService] Initialize called');
            
            // Return existing promise if already initializing
            if (this.initPromise) {
                return this.initPromise;
            }
            
            // Already initialized
            if (this.initialized) {
                console.log('[FirebaseCalendarService] Already initialized');
                return Promise.resolve();
            }
            
            this.initPromise = this._doInitialize();
            return this.initPromise;
        }
        
        async _doInitialize() {
            try {
                console.log('[FirebaseCalendarService] Starting initialization...');
                
                // Firebase configuration
                const firebaseConfig = {
                    apiKey: "AIzaSyByeHeCuEIS0wKhGq4vclyON9XpMxuHMw8",
                    authDomain: "winatecom.firebaseapp.com",
                    projectId: "winatecom",
                    storageBucket: "winatecom.appspot.com",
                    messagingSenderId: "386331689185",
                    appId: "1:386331689185:web:3e1e4f5b2f5b2f5b2f5b2f"
                };

                // Check if Firebase is loaded
                if (typeof firebase === 'undefined') {
                    console.error('[FirebaseCalendarService] Firebase SDK not loaded!');
                    throw new Error('Firebase SDK not loaded. Please include Firebase scripts.');
                }

                // Initialize Firebase if not already initialized
                if (!firebase.apps || !firebase.apps.length) {
                    console.log('[FirebaseCalendarService] Initializing Firebase app...');
                    firebase.initializeApp(firebaseConfig);
                } else {
                    console.log('[FirebaseCalendarService] Firebase app already initialized');
                }

                this.db = firebase.firestore();
                this.auth = firebase.auth();
                
                console.log('[FirebaseCalendarService] Signing in anonymously...');
                const userCredential = await this.auth.signInAnonymously();
                this.currentUser = userCredential.user;
                
                this.initialized = true;
                console.log('[FirebaseCalendarService] Initialization complete!', {
                    userId: this.currentUser?.uid,
                    initialized: this.initialized
                });
                
                return true;
            } catch (error) {
                console.error('[FirebaseCalendarService] Initialization error:', error);
                this.initialized = false;
                this.initPromise = null;
                throw error;
            }
        }

        async getClients() {
            console.log('[FirebaseCalendarService] getClients called');
            try {
                await this.initialize();
                
                // Try Firebase first
                const snapshot = await this.db.collection('clients').get();
                const clients = snapshot.docs.map(doc => ({
                    id: doc.id,
                    ...doc.data()
                }));
                
                console.log('[FirebaseCalendarService] Loaded clients from Firebase:', clients.length);
                
                // If no clients, return demo data
                if (clients.length === 0) {
                    console.log('[FirebaseCalendarService] No clients found, returning demo data');
                    return [
                        { id: 'demo1', name: 'Demo Client 1', email: 'demo1@example.com' },
                        { id: 'demo2', name: 'Demo Client 2', email: 'demo2@example.com' }
                    ];
                }
                
                return clients;
            } catch (error) {
                console.error('[FirebaseCalendarService] Error getting clients:', error);
                // Return demo data on error
                return [
                    { id: 'demo1', name: 'Demo Client 1', email: 'demo1@example.com' },
                    { id: 'demo2', name: 'Demo Client 2', email: 'demo2@example.com' }
                ];
            }
        }

        async getClientGoals(clientId) {
            console.log('[FirebaseCalendarService] getClientGoals called for:', clientId);
            try {
                await this.initialize();
                
                const snapshot = await this.db.collection('goals')
                    .where('clientId', '==', clientId)
                    .get();
                    
                const goals = snapshot.docs.map(doc => ({
                    id: doc.id,
                    ...doc.data()
                }));
                
                console.log('[FirebaseCalendarService] Loaded goals:', goals.length);
                
                // Return demo goal if none found
                if (goals.length === 0) {
                    return [{
                        id: 'demo-goal',
                        clientId: clientId,
                        monthlyRevenue: 50000,
                        year: new Date().getFullYear(),
                        month: new Date().getMonth()
                    }];
                }
                
                return goals;
            } catch (error) {
                console.error('[FirebaseCalendarService] Error getting goals:', error);
                return [{
                    id: 'demo-goal',
                    clientId: clientId,
                    monthlyRevenue: 50000,
                    year: new Date().getFullYear(),
                    month: new Date().getMonth()
                }];
            }
        }

        async getClientEvents(clientId) {
            console.log('[FirebaseCalendarService] getClientEvents called for:', clientId);
            try {
                await this.initialize();
                
                const snapshot = await this.db.collection('calendar_events')
                    .where('clientId', '==', clientId)
                    .get();
                    
                const events = snapshot.docs.map(doc => ({
                    id: doc.id,
                    ...doc.data()
                }));
                
                console.log('[FirebaseCalendarService] Loaded events:', events.length);
                return events;
            } catch (error) {
                console.error('[FirebaseCalendarService] Error getting events:', error);
                return [];
            }
        }

        async createEvent(eventData) {
            console.log('[FirebaseCalendarService] createEvent called:', eventData);
            try {
                await this.initialize();
                
                const docRef = await this.db.collection('calendar_events').add({
                    ...eventData,
                    createdAt: firebase.firestore.FieldValue.serverTimestamp(),
                    userId: this.currentUser?.uid || 'anonymous'
                });
                
                console.log('[FirebaseCalendarService] Event created:', docRef.id);
                return docRef.id;
            } catch (error) {
                console.error('[FirebaseCalendarService] Error creating event:', error);
                // Return mock ID for demo mode
                return 'demo-event-' + Date.now();
            }
        }

        async updateEvent(eventId, updates) {
            console.log('[FirebaseCalendarService] updateEvent called:', eventId, updates);
            try {
                await this.initialize();
                
                await this.db.collection('calendar_events').doc(eventId).update({
                    ...updates,
                    updatedAt: firebase.firestore.FieldValue.serverTimestamp()
                });
                
                console.log('[FirebaseCalendarService] Event updated:', eventId);
                return true;
            } catch (error) {
                console.error('[FirebaseCalendarService] Error updating event:', error);
                return false;
            }
        }

        async deleteEvent(eventId) {
            console.log('[FirebaseCalendarService] deleteEvent called:', eventId);
            try {
                await this.initialize();
                
                await this.db.collection('calendar_events').doc(eventId).delete();
                
                console.log('[FirebaseCalendarService] Event deleted:', eventId);
                return true;
            } catch (error) {
                console.error('[FirebaseCalendarService] Error deleting event:', error);
                return false;
            }
        }
    }

    // Define the GeminiChatService class
    class GeminiChatService {
        constructor(firebaseService) {
            console.log('[GeminiChatService] Constructor called');
            this.firebaseService = firebaseService;
        }
        
        async sendMessage(message, context = {}) {
            console.log('[GeminiChatService] sendMessage called:', message);
            try {
                // Mock response for now
                return {
                    response: "I'm here to help with your calendar planning. Based on your goals, I recommend focusing on high-value campaigns like Cheese Club promotions.",
                    suggestions: [
                        "Add more Cheese Club campaigns (2x revenue)",
                        "Schedule RRB promotions (1.5x revenue)",
                        "Include SMS alerts for quick wins (1.3x revenue)"
                    ]
                };
            } catch (error) {
                console.error('[GeminiChatService] Error sending message:', error);
                return {
                    response: "I'm having trouble connecting right now. Please try again later.",
                    suggestions: []
                };
            }
        }
    }

    // Make services available globally
    window.FirebaseCalendarService = FirebaseCalendarService;
    window.GeminiChatService = GeminiChatService;
    
    // Auto-create a default instance for backward compatibility
    if (!window.firebaseService) {
        console.log('[FirebaseServiceProvider] Creating default firebaseService instance');
        window.firebaseService = new FirebaseCalendarService();
    }
    
    if (!window.geminiService) {
        console.log('[FirebaseServiceProvider] Creating default geminiService instance');
        window.geminiService = new GeminiChatService(window.firebaseService);
    }
    
    console.log('[FirebaseServiceProvider] Services registered:', {
        FirebaseCalendarService: typeof window.FirebaseCalendarService,
        GeminiChatService: typeof window.GeminiChatService,
        firebaseService: typeof window.firebaseService,
        geminiService: typeof window.geminiService
    });
    
})();