import React from 'react';

interface CalendarChatProps {
  selectedDate: Date;
  events: any[];
}

export default function CalendarChat({ selectedDate, events }: CalendarChatProps) {
  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-3">AI Assistant</h3>
      <div className="space-y-3">
        <div className="bg-gray-50 rounded p-3">
          <p className="text-sm text-gray-600">
            How can I help you plan campaigns for {selectedDate.toLocaleDateString()}?
          </p>
        </div>
        <input
          type="text"
          placeholder="Ask about campaign planning..."
          className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>
  );
}