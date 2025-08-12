/**
 * EventModal Component for EmailPilot Calendar
 * Modal dialog for creating and editing calendar events
 */

import React, { useState, useEffect } from 'react';
import { EventModalProps, CalendarEvent, EventType, EventStatus } from '../types';

const EventModal = ({
  isOpen,
  event,
  initialDate,
  clients,
  selectedClient,
  onSave,
  onDelete,
  onClose
}) => {
  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_date: '',
    end_date: '',
    type: 'campaign',
    status: 'planned',
    client_id: '',
    color: '#3B82F6',
    recurring: false,
    recurring_pattern: {
      frequency: 'weekly',
      interval: 1,
      end_date: '',
      count: null
    }
  });

  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  // Event types with descriptions
  const eventTypes = [
    { value: 'campaign', label: 'Campaign Launch', description: 'Email marketing campaign' },
    { value: 'flow', label: 'Automated Flow', description: 'Drip sequence or automation' },
    { value: 'audit', label: 'Account Audit', description: 'Klaviyo account review' },
    { value: 'meeting', label: 'Meeting', description: 'Client call or meeting' },
    { value: 'deadline', label: 'Deadline', description: 'Important due date' },
    { value: 'launch', label: 'Product Launch', description: 'New product or feature' },
    { value: 'review', label: 'Performance Review', description: 'Campaign analysis' },
    { value: 'planning', label: 'Strategy Planning', description: 'Planning session' },
    { value: 'other', label: 'Other', description: 'Other event type' }
  ];

  const eventStatuses = [
    { value: 'planned', label: 'Planned', color: 'bg-blue-100 text-blue-800' },
    { value: 'in_progress', label: 'In Progress', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'completed', label: 'Completed', color: 'bg-green-100 text-green-800' },
    { value: 'cancelled', label: 'Cancelled', color: 'bg-red-100 text-red-800' },
    { value: 'delayed', label: 'Delayed', color: 'bg-orange-100 text-orange-800' }
  ];

  const eventColors = [
    '#3B82F6', '#EF4444', '#10B981', '#F59E0B', 
    '#8B5CF6', '#EC4899', '#6B7280', '#059669'
  ];

  // Initialize form data when modal opens
  useEffect(() => {
    if (isOpen) {
      if (event) {
        // Editing existing event
        setFormData({
          title: event.title || '',
          description: event.description || '',
          start_date: event.start_date ? event.start_date.split('T')[0] : '',
          end_date: event.end_date ? event.end_date.split('T')[0] : '',
          type: event.type || 'campaign',
          status: event.status || 'planned',
          client_id: event.client_id || '',
          color: event.color || '#3B82F6',
          recurring: event.recurring || false,
          recurring_pattern: event.recurring_pattern || {
            frequency: 'weekly',
            interval: 1,
            end_date: '',
            count: null
          }
        });
      } else {
        // Creating new event
        const today = new Date();
        const defaultDate = initialDate || today;
        const dateStr = defaultDate.toISOString().split('T')[0];
        
        setFormData({
          title: '',
          description: '',
          start_date: dateStr,
          end_date: '',
          type: 'campaign',
          status: 'planned',
          client_id: selectedClient?.id || '',
          color: '#3B82F6',
          recurring: false,
          recurring_pattern: {
            frequency: 'weekly',
            interval: 1,
            end_date: '',
            count: null
          }
        });
      }
      setErrors({});
    }
  }, [isOpen, event, initialDate, selectedClient]);

  // Handle input changes
  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  // Handle recurring pattern changes
  const handleRecurringChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      recurring_pattern: {
        ...prev.recurring_pattern,
        [field]: value
      }
    }));
  };

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (!formData.start_date) {
      newErrors.start_date = 'Start date is required';
    }

    if (!formData.client_id && clients.length > 0) {
      newErrors.client_id = 'Please select a client';
    }

    if (formData.end_date && formData.start_date) {
      if (new Date(formData.end_date) < new Date(formData.start_date)) {
        newErrors.end_date = 'End date must be after start date';
      }
    }

    if (formData.recurring && formData.recurring_pattern.end_date) {
      if (new Date(formData.recurring_pattern.end_date) <= new Date(formData.start_date)) {
        newErrors.recurring_end_date = 'Recurring end date must be after start date';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setSaving(true);

    try {
      const eventData = {
        ...formData,
        id: event?.id,
        // Ensure dates are properly formatted
        start_date: formData.start_date,
        end_date: formData.end_date || null,
        recurring_pattern: formData.recurring ? formData.recurring_pattern : null
      };

      await onSave(eventData);
      onClose();
    } catch (error) {
      console.error('Failed to save event:', error);
      setErrors({ submit: 'Failed to save event. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!event?.id || !onDelete) return;

    if (window.confirm('Are you sure you want to delete this event?')) {
      setSaving(true);
      try {
        await onDelete(event.id);
        onClose();
      } catch (error) {
        console.error('Failed to delete event:', error);
        setErrors({ submit: 'Failed to delete event. Please try again.' });
      } finally {
        setSaving(false);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full m-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-800">
              {event ? 'Edit Event' : 'Create New Event'}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
              disabled={saving}
            >
              ×
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Event Title *
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleInputChange('title', e.target.value)}
                className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.title ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="Enter event title"
                disabled={saving}
              />
              {errors.title && (
                <p className="text-red-500 text-sm mt-1">{errors.title}</p>
              )}
            </div>

            {/* Client Selection */}
            {clients.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client *
                </label>
                <select
                  value={formData.client_id}
                  onChange={(e) => handleInputChange('client_id', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    errors.client_id ? 'border-red-500' : 'border-gray-300'
                  }`}
                  disabled={saving}
                >
                  <option value="">Select a client</option>
                  {clients.map(client => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
                {errors.client_id && (
                  <p className="text-red-500 text-sm mt-1">{errors.client_id}</p>
                )}
              </div>
            )}

            {/* Event Type and Status */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Event Type
                </label>
                <select
                  value={formData.type}
                  onChange={(e) => handleInputChange('type', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  disabled={saving}
                >
                  {eventTypes.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={formData.status}
                  onChange={(e) => handleInputChange('status', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  disabled={saving}
                >
                  {eventStatuses.map(status => (
                    <option key={status.value} value={status.value}>
                      {status.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Dates */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start Date *
                </label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => handleInputChange('start_date', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    errors.start_date ? 'border-red-500' : 'border-gray-300'
                  }`}
                  disabled={saving}
                />
                {errors.start_date && (
                  <p className="text-red-500 text-sm mt-1">{errors.start_date}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  End Date
                </label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => handleInputChange('end_date', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    errors.end_date ? 'border-red-500' : 'border-gray-300'
                  }`}
                  disabled={saving}
                />
                {errors.end_date && (
                  <p className="text-red-500 text-sm mt-1">{errors.end_date}</p>
                )}
              </div>
            </div>

            {/* Color Picker */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Color
              </label>
              <div className="flex space-x-2">
                {eventColors.map(color => (
                  <button
                    key={color}
                    type="button"
                    onClick={() => handleInputChange('color', color)}
                    className={`w-8 h-8 rounded-full border-2 ${
                      formData.color === color ? 'border-gray-800' : 'border-gray-300'
                    }`}
                    style={{ backgroundColor: color }}
                    disabled={saving}
                  />
                ))}
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={3}
                placeholder="Event description (optional)"
                disabled={saving}
              />
            </div>

            {/* Recurring Options */}
            <div>
              <div className="flex items-center mb-3">
                <input
                  type="checkbox"
                  id="recurring"
                  checked={formData.recurring}
                  onChange={(e) => handleInputChange('recurring', e.target.checked)}
                  className="mr-2"
                  disabled={saving}
                />
                <label htmlFor="recurring" className="text-sm font-medium text-gray-700">
                  Recurring Event
                </label>
              </div>

              {formData.recurring && (
                <div className="ml-6 space-y-3 p-3 bg-gray-50 rounded-md">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Frequency
                      </label>
                      <select
                        value={formData.recurring_pattern.frequency}
                        onChange={(e) => handleRecurringChange('frequency', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                        disabled={saving}
                      >
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                        <option value="yearly">Yearly</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Interval
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={formData.recurring_pattern.interval}
                        onChange={(e) => handleRecurringChange('interval', parseInt(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                        disabled={saving}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={formData.recurring_pattern.end_date}
                      onChange={(e) => handleRecurringChange('end_date', e.target.value)}
                      className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm ${
                        errors.recurring_end_date ? 'border-red-500' : 'border-gray-300'
                      }`}
                      disabled={saving}
                    />
                    {errors.recurring_end_date && (
                      <p className="text-red-500 text-sm mt-1">{errors.recurring_end_date}</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Error message */}
            {errors.submit && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-red-600 text-sm">{errors.submit}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-between pt-4">
              <div>
                {event && onDelete && (
                  <button
                    type="button"
                    onClick={handleDelete}
                    className="px-4 py-2 text-red-600 border border-red-600 rounded-md hover:bg-red-50 focus:ring-2 focus:ring-red-500 disabled:opacity-50"
                    disabled={saving}
                  >
                    Delete Event
                  </button>
                )}
              </div>

              <div className="space-x-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : (event ? 'Update Event' : 'Create Event')}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default EventModal;