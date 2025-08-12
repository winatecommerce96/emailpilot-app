/**
 * CalendarPage Component - Main Calendar Feature Page for EmailPilot
 * Integrates all calendar components and manages overall state
 */

import React, { useState, useCallback, useEffect } from 'react';
import CalendarBoard from './CalendarBoard';
import CalendarChat from './CalendarChat';
import EventModal from './modals/EventModal';
import { useCalendarState, useClients } from './hooks/useCalendarState';
import goalsService from './services/goals';

const CalendarPage = () => {
  // Main calendar state and actions
  const {
    currentDate,
    selectedClient,
    events,
    goals,
    loading,
    error,
    showEventModal,
    selectedEvent,
    chatMessages,
    setCurrentDate,
    setSelectedClient,
    createEvent,
    updateEvent,
    deleteEvent,
    openEventModal,
    closeEventModal,
    sendChatMessage,
    clearChatHistory
  } = useCalendarState();

  // Client management
  const { clients, loading: clientsLoading } = useClients();

  // Local state
  const [showGoalsPanel, setShowGoalsPanel] = useState(true);
  const [importDocUrl, setImportDocUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  // Handle event creation from calendar board
  const handleCreateEvent = useCallback((date) => {
    openEventModal(); // This will set initialDate internally
  }, [openEventModal]);

  // Handle event drag and drop
  const handleDragEvent = useCallback(async (eventId, newDate) => {
    const eventToUpdate = events.find(e => e.id === eventId);
    if (eventToUpdate) {
      const updatedEvent = {
        ...eventToUpdate,
        start_date: newDate.toISOString().split('T')[0]
      };
      await updateEvent(updatedEvent, true); // Use auto-save for drag operations
    }
  }, [events, updateEvent]);

  // Handle goal creation
  const handleCreateGoal = useCallback(async () => {
    if (!selectedClient) return;

    const goalData = {
      client_id: selectedClient.id,
      title: `Q${Math.ceil((currentDate.getMonth() + 1) / 3)} Revenue Goal`,
      description: 'Quarterly revenue target',
      target_revenue: 10000,
      current_revenue: 0,
      target_date: new Date(currentDate.getFullYear(), currentDate.getMonth() + 3, 0).toISOString().split('T')[0],
      status: 'active',
      category: 'revenue'
    };

    try {
      const newGoal = await goalsService.createGoal(goalData);
      // Goals will be refreshed automatically by the state hook
    } catch (error) {
      console.error('Failed to create goal:', error);
    }
  }, [selectedClient, currentDate]);

  // Handle campaign import
  const handleImportCampaigns = useCallback(async () => {
    if (!selectedClient || !importDocUrl.trim()) return;

    setImporting(true);
    try {
      const { firebaseCalendarService } = await import('./services/firebaseCalendar');
      const result = await firebaseCalendarService.importCampaigns(importDocUrl, selectedClient.id);
      
      if (result.imported > 0) {
        // Refresh events after import
        window.location.reload(); // Simple refresh, could be improved with state update
      }
      
      setShowImportModal(false);
      setImportDocUrl('');
    } catch (error) {
      console.error('Failed to import campaigns:', error);
    } finally {
      setImporting(false);
    }
  }, [selectedClient, importDocUrl]);

  // Calculate quick stats
  const quickStats = React.useMemo(() => {
    const thisMonth = events.filter(e => {
      const eventDate = new Date(e.start_date);
      return eventDate.getMonth() === currentDate.getMonth() && 
             eventDate.getFullYear() === currentDate.getFullYear();
    });

    const upcomingEvents = events.filter(e => {
      const eventDate = new Date(e.start_date);
      const today = new Date();
      return eventDate >= today && eventDate <= new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    });

    const activeGoals = goals.filter(g => g.status === 'active');
    const totalTargetRevenue = activeGoals.reduce((sum, g) => sum + g.target_revenue, 0);
    const totalCurrentRevenue = activeGoals.reduce((sum, g) => sum + g.current_revenue, 0);

    return {
      thisMonthEvents: thisMonth.length,
      upcomingEvents: upcomingEvents.length,
      activeGoals: activeGoals.length,
      revenueProgress: totalTargetRevenue > 0 ? (totalCurrentRevenue / totalTargetRevenue) * 100 : 0,
      totalTargetRevenue,
      totalCurrentRevenue
    };
  }, [events, goals, currentDate]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Page Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex justify-between items-center">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Campaign Calendar</h1>
                <p className="text-gray-600 mt-1">
                  Plan, track, and optimize your email marketing campaigns
                </p>
              </div>
              
              <div className="flex items-center space-x-4">
                {/* Client Selector */}
                <div className="min-w-[200px]">
                  <select
                    value={selectedClient?.id || ''}
                    onChange={(e) => {
                      const client = clients.find(c => c.id === e.target.value);
                      setSelectedClient(client || null);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={clientsLoading}
                  >
                    <option value="">Select a client</option>
                    {clients.map(client => (
                      <option key={client.id} value={client.id}>
                        {client.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Action Buttons */}
                <div className="flex space-x-2">
                  <button
                    onClick={() => setShowImportModal(true)}
                    disabled={!selectedClient}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    Import Campaigns
                  </button>
                  
                  <button
                    onClick={handleCreateGoal}
                    disabled={!selectedClient}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    Add Goal
                  </button>
                </div>
              </div>
            </div>
            
            {/* Quick Stats */}
            {selectedClient && (
              <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600">{quickStats.thisMonthEvents}</div>
                  <div className="text-sm text-blue-800">Events This Month</div>
                </div>
                
                <div className="bg-yellow-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-yellow-600">{quickStats.upcomingEvents}</div>
                  <div className="text-sm text-yellow-800">Upcoming (7 days)</div>
                </div>
                
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600">{quickStats.activeGoals}</div>
                  <div className="text-sm text-green-800">Active Goals</div>
                </div>
                
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-purple-600">
                    {quickStats.revenueProgress.toFixed(1)}%
                  </div>
                  <div className="text-sm text-purple-800">Revenue Progress</div>
                  <div className="text-xs text-purple-600 mt-1">
                    ${quickStats.totalCurrentRevenue.toLocaleString()} / ${quickStats.totalTargetRevenue.toLocaleString()}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading calendar...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex">
              <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {!selectedClient && !loading && (
          <div className="text-center py-12">
            <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a1 1 0 011-1h6a1 1 0 011 1v4h3a2 2 0 012 2v11a2 2 0 01-2 2H4a2 2 0 01-2-2V9a2 2 0 012-2h4z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-800 mb-2">Select a Client to Get Started</h3>
            <p className="text-gray-600">
              Choose a client from the dropdown above to view their campaign calendar and start planning.
            </p>
          </div>
        )}

        {selectedClient && !loading && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Calendar Board - Takes up 2/3 width on large screens */}
            <div className="lg:col-span-2">
              <CalendarBoard
                currentDate={currentDate}
                events={events}
                goals={goals}
                selectedClient={selectedClient}
                onDateChange={setCurrentDate}
                onEventClick={openEventModal}
                onCreateEvent={handleCreateEvent}
                onDragEvent={handleDragEvent}
              />
            </div>

            {/* Sidebar - Chat and Goals */}
            <div className="space-y-6">
              {/* Goals Panel */}
              {showGoalsPanel && goals.length > 0 && (
                <div className="bg-white rounded-lg shadow-lg p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold text-gray-800">Revenue Goals</h3>
                    <button
                      onClick={() => setShowGoalsPanel(false)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  
                  <div className="space-y-4">
                    {goals.filter(g => g.status === 'active').slice(0, 3).map(goal => (
                      <div key={goal.id} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex justify-between items-center mb-2">
                          <h4 className="font-medium text-gray-800">{goal.title}</h4>
                          <span className="text-sm text-gray-600">
                            {goal.metrics.progress_percentage}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${Math.min(100, goal.metrics.progress_percentage)}%` }}
                          />
                        </div>
                        <div className="text-sm text-gray-600">
                          ${goal.current_revenue.toLocaleString()} / ${goal.target_revenue.toLocaleString()}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {goal.metrics.days_remaining} days remaining
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Chat */}
              <CalendarChat
                messages={chatMessages}
                selectedClient={selectedClient}
                goals={goals}
                events={events}
                onSendMessage={sendChatMessage}
                onClearHistory={clearChatHistory}
                isLoading={loading}
              />
            </div>
          </div>
        )}
      </div>

      {/* Event Modal */}
      <EventModal
        isOpen={showEventModal}
        event={selectedEvent}
        clients={clients}
        selectedClient={selectedClient}
        onSave={selectedEvent ? updateEvent : createEvent}
        onDelete={selectedEvent ? deleteEvent : undefined}
        onClose={closeEventModal}
      />

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Import Campaigns</h3>
                <button
                  onClick={() => setShowImportModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Google Doc URL
                  </label>
                  <input
                    type="url"
                    value={importDocUrl}
                    onChange={(e) => setImportDocUrl(e.target.value)}
                    placeholder="https://docs.google.com/document/d/..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                
                <div className="text-sm text-gray-600">
                  Import campaigns from a Google Doc. The document should contain campaign information in a structured format.
                </div>
                
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={() => setShowImportModal(false)}
                    className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
                    disabled={importing}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleImportCampaigns}
                    disabled={importing || !importDocUrl.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {importing ? 'Importing...' : 'Import'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CalendarPage;