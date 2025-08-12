/**
 * React hooks for Calendar State Management
 * Centralizes all calendar state and actions using modern React patterns
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  CalendarState,
  CalendarActions,
  Client,
  CalendarEvent,
  Goal,
  ChatMessage,
} from '../types';
import firebaseCalendarService from '../services/firebaseCalendar';
import goalsService from '../services/goals';
import aiService from '../services/ai';

/**
 * Main calendar state management hook
 */
export function useCalendarState(): CalendarState & CalendarActions {
  // Core state
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showEventModal, setShowEventModal] = useState<boolean>(false);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  // Refs for debouncing
  const saveTimeoutRef = useRef<NodeJS.Timeout>();

  /**
   * Load events for selected client with date range
   */
  const loadEvents = useCallback(async (
    clientId: string,
    startDate?: string,
    endDate?: string
  ): Promise<void> => {
    if (!clientId) return;

    try {
      setLoading(true);
      setError(null);
      
      const clientEvents = await firebaseCalendarService.getClientEvents(
        clientId,
        startDate,
        endDate
      );
      
      setEvents(clientEvents);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load events';
      setError(errorMessage);
      console.error('Failed to load events:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Load goals for selected client
   */
  const loadGoals = useCallback(async (clientId: string): Promise<void> => {
    if (!clientId) return;

    try {
      const clientGoals = await goalsService.getClientGoals(clientId);
      setGoals(clientGoals);
    } catch (err) {
      console.error('Failed to load goals:', err);
      setGoals([]);
    }
  }, []);

  /**
   * Create a new calendar event
   */
  const createEvent = useCallback(async (
    event: Omit<CalendarEvent, 'id'>
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      const newEvent = await firebaseCalendarService.createEvent(event);
      setEvents(prev => [...prev, newEvent]);
      
      setShowEventModal(false);
      setSelectedEvent(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create event';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Update an existing calendar event with debounced auto-save
   */
  const updateEvent = useCallback(async (
    event: CalendarEvent,
    autoSave = false
  ): Promise<void> => {
    try {
      // Update local state immediately
      setEvents(prev => prev.map(e => e.id === event.id ? event : e));
      
      if (autoSave) {
        // Debounced auto-save
        if (saveTimeoutRef.current) {
          clearTimeout(saveTimeoutRef.current);
        }
        
        saveTimeoutRef.current = setTimeout(async () => {
          try {
            await firebaseCalendarService.updateEvent(event);
          } catch (err) {
            console.error('Auto-save failed:', err);
            // Optionally show a subtle error indicator
          }
        }, 1000); // 1 second debounce
      } else {
        // Immediate save
        setLoading(true);
        setError(null);
        
        const updatedEvent = await firebaseCalendarService.updateEvent(event);
        setEvents(prev => prev.map(e => e.id === event.id ? updatedEvent : e));
        
        setShowEventModal(false);
        setSelectedEvent(null);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update event';
      setError(errorMessage);
      
      // Revert local state on error
      setEvents(prev => prev.map(e => 
        e.id === event.id ? (selectedEvent || e) : e
      ));
      
      if (!autoSave) {
        throw err;
      }
    } finally {
      if (!autoSave) {
        setLoading(false);
      }
    }
  }, [selectedEvent]);

  /**
   * Delete a calendar event
   */
  const deleteEvent = useCallback(async (eventId: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      await firebaseCalendarService.deleteEvent(eventId);
      setEvents(prev => prev.filter(e => e.id !== eventId));
      
      setShowEventModal(false);
      setSelectedEvent(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete event';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Open event modal for editing or creation
   */
  const openEventModal = useCallback((event?: CalendarEvent) => {
    setSelectedEvent(event || null);
    setShowEventModal(true);
  }, []);

  /**
   * Close event modal
   */
  const closeEventModal = useCallback(() => {
    setShowEventModal(false);
    setSelectedEvent(null);
  }, []);

  /**
   * Send chat message to AI
   */
  const sendChatMessage = useCallback(async (message: string): Promise<void> => {
    if (!message.trim()) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: message.trim(),
      timestamp: new Date().toISOString(),
      metadata: {
        client_id: selectedClient?.id,
        context_type: 'calendar'
      }
    };

    // Add user message immediately
    setChatMessages(prev => [...prev, userMessage]);

    try {
      const aiResponse = await aiService.sendMessage(message, {
        client: selectedClient || undefined,
        goals,
        events,
        chatHistory: chatMessages
      });

      setChatMessages(prev => [...prev, aiResponse]);

      // Save to fallback storage
      if (selectedClient?.id) {
        aiService.saveChatMessage(selectedClient.id, userMessage);
        aiService.saveChatMessage(selectedClient.id, aiResponse);
      }
    } catch (err) {
      console.error('Failed to send chat message:', err);
      
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        metadata: {
          client_id: selectedClient?.id,
          context_type: 'calendar'
        }
      };
      
      setChatMessages(prev => [...prev, errorMessage]);
    }
  }, [selectedClient, goals, events, chatMessages]);

  /**
   * Clear chat history
   */
  const clearChatHistory = useCallback(async (): Promise<void> => {
    if (!selectedClient?.id) return;

    try {
      await aiService.clearChatHistory(selectedClient.id);
      setChatMessages([]);
    } catch (err) {
      console.error('Failed to clear chat history:', err);
      // Clear locally anyway
      setChatMessages([]);
    }
  }, [selectedClient]);

  /**
   * Handle client selection change
   */
  const handleClientChange = useCallback(async (client: Client | null) => {
    setSelectedClient(client);
    setEvents([]);
    setGoals([]);
    setChatMessages([]);
    setError(null);

    if (client) {
      // Load data for new client
      const currentMonth = currentDate.getMonth() + 1;
      const currentYear = currentDate.getFullYear();
      const startDate = `${currentYear}-${currentMonth.toString().padStart(2, '0')}-01`;
      const endDate = new Date(currentYear, currentMonth, 0).toISOString().split('T')[0];

      await Promise.all([
        loadEvents(client.id, startDate, endDate),
        loadGoals(client.id),
        // Load chat history
        aiService.getChatHistory(client.id).then(setChatMessages)
      ]);
    }
  }, [currentDate, loadEvents, loadGoals]);

  /**
   * Handle date change (month navigation)
   */
  const handleDateChange = useCallback(async (newDate: Date) => {
    setCurrentDate(newDate);
    
    if (selectedClient) {
      const month = newDate.getMonth() + 1;
      const year = newDate.getFullYear();
      const startDate = `${year}-${month.toString().padStart(2, '0')}-01`;
      const endDate = new Date(year, month, 0).toISOString().split('T')[0];
      
      await loadEvents(selectedClient.id, startDate, endDate);
    }
  }, [selectedClient, loadEvents]);

  /**
   * Cleanup timeouts on unmount
   */
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // Return state and actions
  return {
    // State
    currentDate,
    selectedClient,
    events,
    goals,
    loading,
    error,
    showEventModal,
    selectedEvent,
    chatMessages,
    
    // Actions
    setCurrentDate: handleDateChange,
    setSelectedClient: handleClientChange,
    loadEvents,
    loadGoals,
    createEvent,
    updateEvent,
    deleteEvent,
    openEventModal,
    closeEventModal,
    sendChatMessage,
    clearChatHistory,
  };
}

/**
 * Hook for loading and managing clients
 */
export function useClients() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadClients = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const clientsData = await firebaseCalendarService.getClients();
      setClients(clientsData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load clients';
      setError(errorMessage);
      console.error('Failed to load clients:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createClient = useCallback(async (clientData: Omit<Client, 'id'>) => {
    try {
      const newClient = await firebaseCalendarService.saveClient(clientData);
      setClients(prev => [...prev, newClient]);
      return newClient;
    } catch (err) {
      console.error('Failed to create client:', err);
      throw err;
    }
  }, []);

  const updateClient = useCallback(async (client: Client) => {
    try {
      const updatedClient = await firebaseCalendarService.saveClient(client);
      setClients(prev => prev.map(c => c.id === client.id ? updatedClient : c));
      return updatedClient;
    } catch (err) {
      console.error('Failed to update client:', err);
      throw err;
    }
  }, []);

  const deleteClient = useCallback(async (clientId: string) => {
    try {
      await firebaseCalendarService.deleteClient(clientId);
      setClients(prev => prev.filter(c => c.id !== clientId));
    } catch (err) {
      console.error('Failed to delete client:', err);
      throw err;
    }
  }, []);

  useEffect(() => {
    loadClients();
  }, [loadClients]);

  return {
    clients,
    loading,
    error,
    loadClients,
    createClient,
    updateClient,
    deleteClient,
  };
}

/**
 * Hook for drag and drop functionality
 */
export function useDragAndDrop(
  onEventDrop: (eventId: string, newDate: Date) => Promise<void>
) {
  const [draggedEvent, setDraggedEvent] = useState<CalendarEvent | null>(null);
  const [dropTarget, setDropTarget] = useState<Date | null>(null);

  const handleDragStart = useCallback((event: CalendarEvent) => {
    setDraggedEvent(event);
  }, []);

  const handleDragOver = useCallback((date: Date) => {
    if (draggedEvent) {
      setDropTarget(date);
    }
  }, [draggedEvent]);

  const handleDragEnd = useCallback(async () => {
    if (draggedEvent && dropTarget) {
      try {
        await onEventDrop(draggedEvent.id!, dropTarget);
      } catch (error) {
        console.error('Failed to drop event:', error);
      }
    }
    
    setDraggedEvent(null);
    setDropTarget(null);
  }, [draggedEvent, dropTarget, onEventDrop]);

  const handleDragLeave = useCallback(() => {
    setDropTarget(null);
  }, []);

  return {
    draggedEvent,
    dropTarget,
    handleDragStart,
    handleDragOver,
    handleDragEnd,
    handleDragLeave,
  };
}

/**
 * Hook for debounced auto-save functionality
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}