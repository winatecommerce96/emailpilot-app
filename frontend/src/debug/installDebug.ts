import { getDebugBus } from './debugBus';

export function installDebug() {
  // Check if debug mode is enabled
  const urlParams = new URLSearchParams(window.location.search);
  const enabled = urlParams.get('debug') === '1' || localStorage.getItem('debug') === '1';
  
  if (!enabled) {
    window.__EP_DEBUG_ENABLED__ = false;
    return;
  }
  
  window.__EP_DEBUG_ENABLED__ = true;
  console.log('🐛 Debug Mode Enabled');
  
  const bus = getDebugBus();
  
  // Intercept console.error
  const origError = console.error.bind(console);
  console.error = (...args: any[]) => {
    bus.emit({
      type: 'console.error',
      message: args.map(a => String(a)).join(' '),
      args,
      stack: new Error().stack
    });
    origError(...args);
  };
  
  // Intercept console.warn
  const origWarn = console.warn.bind(console);
  console.warn = (...args: any[]) => {
    bus.emit({
      type: 'console.warn',
      message: args.map(a => String(a)).join(' '),
      args
    });
    origWarn(...args);
  };
  
  // Global error handler
  window.addEventListener('error', (event) => {
    bus.emit({
      type: 'window.error',
      message: event.message,
      stack: event.error?.stack,
      url: event.filename
    });
  });
  
  // Unhandled promise rejection
  window.addEventListener('unhandledrejection', (event) => {
    bus.emit({
      type: 'unhandledrejection',
      message: String(event.reason),
      stack: event.reason?.stack
    });
  });
  
  // Intercept fetch for network errors
  const origFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : 
                input instanceof URL ? input.toString() : 
                input instanceof Request ? input.url : '';
    
    try {
      const response = await origFetch(input, init);
      
      // Log failures
      if (response.status >= 400) {
        bus.emit({
          type: 'network',
          message: `HTTP ${response.status}: ${url}`,
          status: response.status,
          url
        });
      }
      
      return response;
    } catch (error: any) {
      // Log network errors (CORS, timeouts, etc)
      bus.emit({
        type: 'network',
        message: `Network Error: ${error.message}`,
        url,
        stack: error.stack
      });
      throw error;
    }
  };
  
  // Intercept dynamic imports for missing modules
  const origImport = (window as any).__import || ((m: string) => import(m));
  (window as any).__import = async (module: string) => {
    try {
      return await origImport(module);
    } catch (error: any) {
      bus.emit({
        type: 'import.error',
        message: `Failed to import: ${module}`,
        stack: error.stack
      });
      throw error;
    }
  };
}