import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { getDebugBus, type DebugEvent } from './debugBus';

export function DebugOverlay() {
  const [isOpen, setIsOpen] = useState(false);
  const [events, setEvents] = useState<DebugEvent[]>([]);
  const [selectedTab, setSelectedTab] = useState<'all' | 'errors' | 'network' | 'warnings'>('all');
  const [selectedEvent, setSelectedEvent] = useState<DebugEvent | null>(null);
  
  useEffect(() => {
    if (!window.__EP_DEBUG_ENABLED__) {
      return;
    }
    
    const bus = getDebugBus();
    setEvents(bus.events);
    
    const unsubscribe = bus.subscribe((event) => {
      setEvents(prev => [...prev.slice(-199), event]);
    });
    
    return unsubscribe;
  }, []);
  
  const filteredEvents = events.filter(event => {
    switch (selectedTab) {
      case 'errors':
        return event.type.includes('error') || event.type === 'unhandledrejection';
      case 'network':
        return event.type === 'network';
      case 'warnings':
        return event.type === 'console.warn';
      default:
        return true;
    }
  });
  
  const copyJson = useCallback((event: DebugEvent) => {
    navigator.clipboard.writeText(JSON.stringify(event, null, 2));
  }, []);
  
  const clearEvents = useCallback(() => {
    const bus = getDebugBus();
    bus.clear();
    setEvents([]);
  }, []);
  
  if (!window.__EP_DEBUG_ENABLED__) {
    return null;
  }
  
  return createPortal(
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      zIndex: 99999,
      fontFamily: 'monospace',
      fontSize: '12px'
    }}>
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '50%',
            width: '60px',
            height: '60px',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px'
          }}
        >
          🐛
        </button>
      ) : (
        <div style={{
          background: 'white',
          border: '2px solid #e5e7eb',
          borderRadius: '8px',
          width: '600px',
          height: '400px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Header */}
          <div style={{
            padding: '12px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: '#f9fafb'
          }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              {(['all', 'errors', 'network', 'warnings'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setSelectedTab(tab)}
                  style={{
                    padding: '4px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    background: selectedTab === tab ? '#6366f1' : 'white',
                    color: selectedTab === tab ? 'white' : '#374151',
                    cursor: 'pointer',
                    textTransform: 'capitalize'
                  }}
                >
                  {tab} ({events.filter(e => {
                    if (tab === 'all') return true;
                    if (tab === 'errors') return e.type.includes('error') || e.type === 'unhandledrejection';
                    if (tab === 'network') return e.type === 'network';
                    if (tab === 'warnings') return e.type === 'console.warn';
                    return false;
                  }).length})
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={clearEvents}
                style={{
                  padding: '4px 8px',
                  background: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Clear
              </button>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  padding: '4px 8px',
                  background: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                ✕
              </button>
            </div>
          </div>
          
          {/* Events list */}
          <div style={{
            flex: 1,
            overflow: 'auto',
            padding: '8px'
          }}>
            {filteredEvents.length === 0 ? (
              <div style={{ color: '#9ca3af', textAlign: 'center', marginTop: '20px' }}>
                No events captured
              </div>
            ) : (
              filteredEvents.map(event => (
                <div
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                  style={{
                    padding: '8px',
                    marginBottom: '4px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    background: event === selectedEvent ? '#f3f4f6' : 'white',
                    borderLeft: `4px solid ${
                      event.type.includes('error') ? '#ef4444' :
                      event.type === 'console.warn' ? '#f59e0b' :
                      event.type === 'network' ? '#3b82f6' : '#6b7280'
                    }`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 'bold' }}>{event.type}</span>
                    <span style={{ color: '#9ca3af' }}>
                      {new Date(event.ts).toLocaleTimeString()}
                    </span>
                  </div>
                  <div style={{
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    color: '#4b5563'
                  }}>
                    {event.message}
                  </div>
                  {event.url && (
                    <div style={{ color: '#9ca3af', fontSize: '10px' }}>{event.url}</div>
                  )}
                </div>
              ))
            )}
          </div>
          
          {/* Selected event details */}
          {selectedEvent && (
            <div style={{
              borderTop: '1px solid #e5e7eb',
              padding: '12px',
              background: '#f9fafb',
              maxHeight: '150px',
              overflow: 'auto'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <strong>Event Details</strong>
                <button
                  onClick={() => copyJson(selectedEvent)}
                  style={{
                    padding: '2px 8px',
                    background: '#6366f1',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '10px'
                  }}
                >
                  Copy JSON
                </button>
              </div>
              <pre style={{
                margin: 0,
                fontSize: '10px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all'
              }}>
                {JSON.stringify(selectedEvent, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>,
    document.body
  );
}