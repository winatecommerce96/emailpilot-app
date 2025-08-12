/**
 * Firebase Calendar Service for EmailPilot
 * Provides API integration with Firebase backend endpoints
 */

import { Client, CalendarEvent, APIResponse } from '../types';

class FirebaseCalendarService {
  private baseUrl: string;
  private initialized: boolean = false;

  constructor() {
    // Use environment variables or fallback to current origin
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
  }

  /**
   * Initialize the service
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;
    
    try {
      // Test connection to the API
      const response = await this.makeRequest('/api/health', 'GET');
      if (!response.ok) {
        throw new Error('Failed to connect to API');
      }
      this.initialized = true;
    } catch (error) {
      console.warn('API connection failed, using fallback mode:', error);
      this.initialized = true; // Continue in offline mode
    }
  }

  /**
   * Generic HTTP request helper
   */
  private async makeRequest(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    data?: any
  ): Promise<Response> {
    const url = `${this.baseUrl}${endpoint}`;
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      credentials: 'include', // Include cookies for authentication
    };

    if (data && method !== 'GET') {
      options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  }

  /**
   * Get all clients
   */
  async getClients(): Promise<Client[]> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/firebase_calendar/clients', 'GET');
      const data: APIResponse<Client[]> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch clients');
      }
      
      return data.data || [];
    } catch (error) {
      console.error('Failed to fetch clients:', error);
      // Return fallback data if available
      return this.getFallbackClients();
    }
  }

  /**
   * Get client by ID
   */
  async getClient(clientId: string): Promise<Client | null> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/firebase_calendar/clients/${clientId}`, 'GET');
      const data: APIResponse<Client> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch client');
      }
      
      return data.data || null;
    } catch (error) {
      console.error('Failed to fetch client:', error);
      return null;
    }
  }

  /**
   * Create or update a client
   */
  async saveClient(client: Omit<Client, 'id'> | Client): Promise<Client> {
    await this.initialize();
    
    const isUpdate = 'id' in client && client.id;
    const endpoint = isUpdate 
      ? `/api/firebase_calendar/clients/${client.id}`
      : '/api/firebase_calendar/clients';
    const method = isUpdate ? 'PUT' : 'POST';

    try {
      const response = await this.makeRequest(endpoint, method, client);
      const data: APIResponse<Client> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to save client');
      }
      
      return data.data!;
    } catch (error) {
      console.error('Failed to save client:', error);
      throw error;
    }
  }

  /**
   * Delete a client
   */
  async deleteClient(clientId: string): Promise<void> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/firebase_calendar/clients/${clientId}`, 'DELETE');
      const data: APIResponse<void> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to delete client');
      }
    } catch (error) {
      console.error('Failed to delete client:', error);
      throw error;
    }
  }

  /**
   * Get calendar events for a client
   */
  async getClientEvents(
    clientId: string,
    startDate?: string,
    endDate?: string
  ): Promise<CalendarEvent[]> {
    await this.initialize();
    
    try {
      const params = new URLSearchParams({ client_id: clientId });
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const response = await this.makeRequest(`/api/firebase_calendar/events?${params}`, 'GET');
      const data: APIResponse<CalendarEvent[]> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch events');
      }
      
      return data.data || [];
    } catch (error) {
      console.error('Failed to fetch events:', error);
      return [];
    }
  }

  /**
   * Create a new calendar event
   */
  async createEvent(event: Omit<CalendarEvent, 'id'>): Promise<CalendarEvent> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/firebase_calendar/events', 'POST', event);
      const data: APIResponse<CalendarEvent> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to create event');
      }
      
      return data.data!;
    } catch (error) {
      console.error('Failed to create event:', error);
      throw error;
    }
  }

  /**
   * Update an existing calendar event
   */
  async updateEvent(event: CalendarEvent): Promise<CalendarEvent> {
    await this.initialize();
    
    if (!event.id) {
      throw new Error('Event ID is required for updates');
    }

    try {
      const response = await this.makeRequest(`/api/firebase_calendar/events/${event.id}`, 'PUT', event);
      const data: APIResponse<CalendarEvent> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to update event');
      }
      
      return data.data!;
    } catch (error) {
      console.error('Failed to update event:', error);
      throw error;
    }
  }

  /**
   * Delete a calendar event
   */
  async deleteEvent(eventId: string): Promise<void> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/firebase_calendar/events/${eventId}`, 'DELETE');
      const data: APIResponse<void> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to delete event');
      }
    } catch (error) {
      console.error('Failed to delete event:', error);
      throw error;
    }
  }

  /**
   * Import campaigns from Google Docs
   */
  async importCampaigns(
    docUrl: string,
    clientId: string
  ): Promise<{ imported: number; errors: string[] }> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/firebase_calendar/import-campaigns', 'POST', {
        doc_url: docUrl,
        client_id: clientId
      });
      
      const data: APIResponse<{ imported: number; errors: string[] }> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to import campaigns');
      }
      
      return data.data!;
    } catch (error) {
      console.error('Failed to import campaigns:', error);
      throw error;
    }
  }

  /**
   * Get events for multiple clients (dashboard view)
   */
  async getAllEvents(
    clientIds?: string[],
    startDate?: string,
    endDate?: string
  ): Promise<CalendarEvent[]> {
    await this.initialize();
    
    try {
      const params = new URLSearchParams();
      if (clientIds?.length) {
        params.append('client_ids', clientIds.join(','));
      }
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const response = await this.makeRequest(`/api/firebase_calendar/events/all?${params}`, 'GET');
      const data: APIResponse<CalendarEvent[]> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch all events');
      }
      
      return data.data || [];
    } catch (error) {
      console.error('Failed to fetch all events:', error);
      return [];
    }
  }

  /**
   * Fallback clients for offline mode
   */
  private getFallbackClients(): Client[] {
    const fallbackData = localStorage.getItem('emailpilot_calendar_clients');
    if (fallbackData) {
      try {
        return JSON.parse(fallbackData);
      } catch (error) {
        console.warn('Failed to parse fallback client data');
      }
    }
    return [];
  }

  /**
   * Save data to local storage as fallback
   */
  private saveFallbackData(key: string, data: any): void {
    try {
      localStorage.setItem(`emailpilot_calendar_${key}`, JSON.stringify(data));
    } catch (error) {
      console.warn('Failed to save fallback data:', error);
    }
  }

  /**
   * Check if service is online/connected
   */
  isOnline(): boolean {
    return this.initialized && navigator.onLine;
  }

  /**
   * Get service status
   */
  getStatus(): { initialized: boolean; online: boolean } {
    return {
      initialized: this.initialized,
      online: this.isOnline()
    };
  }
}

// Export singleton instance
export const firebaseCalendarService = new FirebaseCalendarService();
export default firebaseCalendarService;