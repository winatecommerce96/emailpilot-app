/**
 * CalendarBoard Component for EmailPilot
 * Displays monthly calendar grid with drag-and-drop events
 */

import React, { useState, useCallback, useMemo } from 'react';
import { CalendarViewProps } from './types';
import { useDragAndDrop } from './hooks/useCalendarState';

const CalendarBoard = ({ 
  currentDate, 
  events, 
  goals, 
  selectedClient, 
  onDateChange, 
  onEventClick, 
  onCreateEvent, 
  onDragEvent 
}) => {
  const [hoveredDate, setHoveredDate] = useState(null);
  
  // Drag and drop functionality
  const {
    draggedEvent,
    dropTarget,
    handleDragStart,
    handleDragOver,
    handleDragEnd,
    handleDragLeave
  } = useDragAndDrop(onDragEvent || (() => Promise.resolve()));

  // Calendar calculations
  const { calendarDays, monthName, year } = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const monthName = currentDate.toLocaleString('default', { month: 'long' });
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const days = [];
    const current = new Date(startDate);
    
    // Generate 6 weeks (42 days) to fill calendar grid
    for (let i = 0; i < 42; i++) {
      days.push({
        date: new Date(current),
        dateString: current.toISOString().split('T')[0],
        day: current.getDate(),
        isCurrentMonth: current.getMonth() === month,
        isToday: current.toDateString() === new Date().toDateString(),
        isPast: current < new Date().setHours(0, 0, 0, 0)
      });
      current.setDate(current.getDate() + 1);
    }
    
    return { calendarDays: days, monthName, year };
  }, [currentDate]);

  // Group events by date
  const eventsByDate = useMemo(() => {
    const grouped = {};
    events.forEach(event => {
      const dateKey = event.start_date.split('T')[0];
      if (!grouped[dateKey]) {
        grouped[dateKey] = [];
      }
      grouped[dateKey].push(event);
    });
    return grouped;
  }, [events]);

  // Get goal progress for current month
  const monthlyGoalProgress = useMemo(() => {
    if (!goals.length) return null;
    
    const totalTarget = goals.reduce((sum, goal) => sum + goal.target_revenue, 0);
    const totalCurrent = goals.reduce((sum, goal) => sum + goal.current_revenue, 0);
    const progress = totalTarget > 0 ? (totalCurrent / totalTarget) * 100 : 0;
    
    return {
      progress: Math.round(progress),
      current: totalCurrent,
      target: totalTarget
    };
  }, [goals]);

  // Navigation handlers
  const handlePrevMonth = useCallback(() => {
    const newDate = new Date(currentDate);
    newDate.setMonth(newDate.getMonth() - 1);
    onDateChange(newDate);
  }, [currentDate, onDateChange]);

  const handleNextMonth = useCallback(() => {
    const newDate = new Date(currentDate);
    newDate.setMonth(newDate.getMonth() + 1);
    onDateChange(newDate);
  }, [currentDate, onDateChange]);

  const handleToday = useCallback(() => {
    onDateChange(new Date());
  }, [onDateChange]);

  // Event handlers
  const handleCellClick = useCallback((day) => {
    if (day.isCurrentMonth) {
      onCreateEvent(day.date);
    }
  }, [onCreateEvent]);

  const handleEventClick = useCallback((e, event) => {
    e.stopPropagation();
    onEventClick(event);
  }, [onEventClick]);

  // Drag and drop handlers
  const handleDragStartEvent = useCallback((e, event) => {
    e.stopPropagation();
    handleDragStart(event);
  }, [handleDragStart]);

  const handleDragOverCell = useCallback((e, day) => {
    e.preventDefault();
    if (day.isCurrentMonth && draggedEvent) {
      handleDragOver(day.date);
    }
  }, [draggedEvent, handleDragOver]);

  const handleDropCell = useCallback((e, day) => {
    e.preventDefault();
    if (day.isCurrentMonth) {
      handleDragEnd();
    }
  }, [handleDragEnd]);

  const handleDragLeaveCell = useCallback(() => {
    handleDragLeave();
  }, [handleDragLeave]);

  // Helper to get event color based on type and status
  const getEventColor = (event) => {
    if (event.color) return event.color;
    
    const typeColors = {
      campaign: '#3B82F6',
      flow: '#10B981',
      audit: '#F59E0B',
      meeting: '#8B5CF6',
      deadline: '#EF4444',
      launch: '#EC4899',
      review: '#6B7280',
      planning: '#059669',
      other: '#6B7280'
    };
    
    return typeColors[event.type] || '#6B7280';
  };

  // Helper to get status indicator
  const getStatusBadge = (status) => {
    const badges = {
      planned: 'bg-blue-100 text-blue-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      delayed: 'bg-orange-100 text-orange-800'
    };
    
    return badges[status] || 'bg-gray-100 text-gray-800';
  };

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Calendar Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center space-x-4">
            <h2 className="text-2xl font-bold text-gray-800">
              {monthName} {year}
            </h2>
            {selectedClient && (
              <span className="text-lg text-gray-600">
                - {selectedClient.name}
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={handlePrevMonth}
              className="p-2 rounded-md hover:bg-gray-100 focus:ring-2 focus:ring-blue-500"
              title="Previous Month"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            
            <button
              onClick={handleToday}
              className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:ring-2 focus:ring-blue-500"
            >
              Today
            </button>
            
            <button
              onClick={handleNextMonth}
              className="p-2 rounded-md hover:bg-gray-100 focus:ring-2 focus:ring-blue-500"
              title="Next Month"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Goal Progress Bar */}
        {monthlyGoalProgress && (
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">Monthly Goal Progress</span>
              <span className="text-sm text-gray-600">
                ${monthlyGoalProgress.current.toLocaleString()} / ${monthlyGoalProgress.target.toLocaleString()}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, monthlyGoalProgress.progress)}%` }}
              />
            </div>
            <div className="text-right text-sm text-gray-600 mt-1">
              {monthlyGoalProgress.progress}% complete
            </div>
          </div>
        )}
      </div>

      {/* Calendar Grid */}
      <div className="p-6">
        {/* Week Day Headers */}
        <div className="grid grid-cols-7 gap-px mb-2">
          {weekDays.map(day => (
            <div key={day} className="p-3 text-center text-sm font-medium text-gray-500">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Days Grid */}
        <div className="grid grid-cols-7 gap-px bg-gray-200 rounded-lg overflow-hidden">
          {calendarDays.map((day, index) => {
            const dayEvents = eventsByDate[day.dateString] || [];
            const isDropTarget = dropTarget && dropTarget.toDateString() === day.date.toDateString();
            
            return (
              <div
                key={index}
                className={`
                  min-h-[120px] bg-white p-2 cursor-pointer transition-colors duration-200
                  ${day.isCurrentMonth ? 'hover:bg-gray-50' : 'bg-gray-50 text-gray-400'}
                  ${day.isToday ? 'ring-2 ring-blue-500' : ''}
                  ${isDropTarget ? 'bg-blue-100 ring-2 ring-blue-400' : ''}
                  ${hoveredDate === day.dateString ? 'bg-blue-50' : ''}
                `}
                onClick={() => handleCellClick(day)}
                onMouseEnter={() => setHoveredDate(day.dateString)}
                onMouseLeave={() => setHoveredDate(null)}
                onDragOver={(e) => handleDragOverCell(e, day)}
                onDrop={(e) => handleDropCell(e, day)}
                onDragLeave={handleDragLeaveCell}
              >
                {/* Day Number */}
                <div className={`
                  text-sm font-medium mb-1 flex justify-between items-center
                  ${day.isToday ? 'text-blue-600' : ''}
                `}>
                  <span>{day.day}</span>
                  {day.isCurrentMonth && dayEvents.length > 3 && (
                    <span className="text-xs text-gray-500 bg-gray-200 rounded-full px-1">
                      +{dayEvents.length - 3}
                    </span>
                  )}
                </div>

                {/* Events */}
                <div className="space-y-1">
                  {dayEvents.slice(0, 3).map((event, eventIndex) => (
                    <div
                      key={event.id || eventIndex}
                      className={`
                        text-xs p-1 rounded cursor-pointer text-white font-medium
                        hover:opacity-80 transition-opacity duration-200
                        ${draggedEvent?.id === event.id ? 'opacity-50' : ''}
                      `}
                      style={{ backgroundColor: getEventColor(event) }}
                      onClick={(e) => handleEventClick(e, event)}
                      onDragStart={(e) => handleDragStartEvent(e, event)}
                      draggable={onDragEvent ? true : false}
                      title={`${event.title} - ${event.type}`}
                    >
                      <div className="flex items-center space-x-1">
                        <div 
                          className={`w-2 h-2 rounded-full ${getStatusBadge(event.status).replace('bg-', 'bg-').replace('text-', '')}`}
                        />
                        <span className="truncate">{event.title}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Create Event Hint */}
                {day.isCurrentMonth && dayEvents.length === 0 && hoveredDate === day.dateString && (
                  <div className="text-xs text-gray-400 text-center mt-2">
                    Click to create event
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="p-6 border-t border-gray-200 bg-gray-50">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Event Types</h4>
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-xs text-gray-600">Campaign</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-xs text-gray-600">Flow</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <span className="text-xs text-gray-600">Audit</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Status</h4>
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-blue-200"></div>
                <span className="text-xs text-gray-600">Planned</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-yellow-200"></div>
                <span className="text-xs text-gray-600">In Progress</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-green-200"></div>
                <span className="text-xs text-gray-600">Completed</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Quick Actions</h4>
            <div className="space-y-1 text-xs text-gray-600">
              <div>Click empty day to create event</div>
              <div>Drag events to reschedule</div>
              <div>Click event to edit details</div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Navigation</h4>
            <div className="space-y-1 text-xs text-gray-600">
              <div>Use arrows to change months</div>
              <div>Click "Today" to return to current</div>
              <div>Current date highlighted in blue</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarBoard;