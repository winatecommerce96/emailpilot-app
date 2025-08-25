export interface DebugEvent {
  type: 'console.error' | 'console.warn' | 'window.error' | 'unhandledrejection' | 
        'network' | 'react.error' | 'import.error' | 'auth.error';
  message: string;
  stack?: string;
  status?: number;
  url?: string;
  route?: string;
  args?: any[];
  ts: number;
  id: string;
}

export interface DebugBus {
  events: DebugEvent[];
  listeners: Set<(event: DebugEvent) => void>;
  emit: (event: Omit<DebugEvent, 'ts' | 'id'>) => void;
  subscribe: (listener: (event: DebugEvent) => void) => () => void;
  clear: () => void;
}

declare global {
  interface Window {
    __EP_DEBUG_BUS__: DebugBus;
    __EP_DEBUG_ENABLED__: boolean;
  }
}

export function getDebugBus(): DebugBus {
  if (!window.__EP_DEBUG_BUS__) {
    const bus: DebugBus = {
      events: [],
      listeners: new Set(),
      
      emit(event) {
        const fullEvent: DebugEvent = {
          ...event,
          ts: Date.now(),
          id: Math.random().toString(36).substr(2, 9),
          route: window.location.pathname
        };
        
        // Keep last 200 events
        bus.events.push(fullEvent);
        if (bus.events.length > 200) {
          bus.events.shift();
        }
        
        // Notify listeners
        bus.listeners.forEach(listener => {
          try {
            listener(fullEvent);
          } catch (e) {
            console.log('Debug listener error:', e);
          }
        });
        
        // Send telemetry (with backoff)
        sendTelemetry(fullEvent);
      },
      
      subscribe(listener) {
        bus.listeners.add(listener);
        return () => bus.listeners.delete(listener);
      },
      
      clear() {
        bus.events = [];
      }
    };
    
    window.__EP_DEBUG_BUS__ = bus;
  }
  
  return window.__EP_DEBUG_BUS__;
}

let telemetryFailures = 0;
const MAX_TELEMETRY_FAILURES = 5;

async function sendTelemetry(event: DebugEvent) {
  if (telemetryFailures >= MAX_TELEMETRY_FAILURES) {
    return; // Stop sending after too many failures
  }
  
  try {
    await fetch('/api/dev/telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event)
    });
    telemetryFailures = 0; // Reset on success
  } catch (e) {
    telemetryFailures++;
    // Swallow error to avoid loops
  }
}