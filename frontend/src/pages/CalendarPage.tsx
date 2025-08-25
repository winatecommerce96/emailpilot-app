import React, { Suspense, lazy } from 'react';
import { useAuth } from '@auth/AuthProvider';

// Lazy load CalendarChat with proper error handling
const CalendarChat = lazy(() => 
  import('@features/calendar/CalendarChat').catch(() => {
    console.warn('CalendarChat component not available');
    // Return a valid React component that renders nothing
    return { default: () => React.createElement('div', null) };
  })
);

// Feature flag for CalendarChat
const ENABLE_CALENDAR_CHAT = localStorage.getItem('feature.calendarChat') === 'true';

export default function CalendarPage() {
  const { isAuthenticated } = useAuth();
  const [selectedDate, setSelectedDate] = React.useState(new Date());
  const [events, setEvents] = React.useState([]);
  
  if (!isAuthenticated) {
    return <div>Please log in to view the calendar</div>;
  }
  
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4">Campaign Calendar</h2>
          <div className="border rounded-lg p-4">
            <div className="text-center text-gray-500">
              Calendar component will be loaded here
            </div>
            <div className="mt-4 text-sm text-gray-400">
              Selected: {selectedDate.toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>
      
      <div className="lg:col-span-1">
        {ENABLE_CALENDAR_CHAT && (
          <Suspense fallback={
            <div className="bg-white shadow rounded-lg p-6">
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          }>
            <CalendarChat 
              selectedDate={selectedDate}
              events={events}
            />
          </Suspense>
        )}
        
        <div className="bg-white shadow rounded-lg p-6 mt-6">
          <h3 className="text-lg font-semibold mb-3">Quick Actions</h3>
          <div className="space-y-2">
            <button className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
              Create Campaign
            </button>
            <button className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
              Import Events
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}