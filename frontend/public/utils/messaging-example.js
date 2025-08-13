// Example usage of MessagingGuard utilities
// This file demonstrates how to safely use chrome.runtime and postMessage

// Example 1: Safe Chrome Extension Messaging
async function sendToExtension(data) {
    if (!window.MessagingGuard) {
        console.warn('MessagingGuard not loaded');
        return null;
    }
    
    try {
        const response = await window.MessagingGuard.sendExtensionMessage({
            action: 'SYNC_DATA',
            payload: data
        });
        
        if (response) {
            console.log('Extension response:', response);
            return response;
        } else {
            console.debug('Extension not available or no response');
            return null;
        }
    } catch (error) {
        console.error('Extension messaging failed:', error);
        return null;
    }
}

// Example 2: Safe iframe Communication
function setupIframeMessaging(iframeElement) {
    if (!window.MessagingGuard) {
        console.warn('MessagingGuard not loaded');
        return;
    }
    
    // Setup message receiver
    window.MessagingGuard.setupMessageReceiver((event) => {
        // Validate origin for security
        if (event.origin !== window.location.origin) {
            console.warn('Message from untrusted origin:', event.origin);
            return;
        }
        
        // Handle different message types
        switch (event.data?.type) {
            case 'CALENDAR_EVENT':
                handleCalendarEvent(event.data.payload);
                break;
            case 'USER_ACTION':
                handleUserAction(event.data.payload);
                break;
            default:
                console.debug('Unknown message type:', event.data?.type);
        }
    });
    
    // Setup iframe load handler
    iframeElement.onload = async () => {
        const isReady = await window.MessagingGuard.waitForMessageTarget(
            iframeElement.contentWindow,
            window.location.origin,
            3000 // 3 second timeout
        );
        
        if (isReady) {
            // Send initialization data
            window.MessagingGuard.safePostMessage(
                iframeElement.contentWindow,
                {
                    type: 'INIT',
                    config: {
                        apiBase: window.API_BASE_URL,
                        userId: getCurrentUserId(),
                        features: ['calendar', 'goals', 'reports']
                    }
                },
                window.location.origin
            );
        } else {
            console.warn('Iframe failed to respond to handshake');
        }
    };
}

// Example 3: Cross-window Communication (for popups/new windows)
function openWindowWithMessaging(url, windowName = 'popup') {
    const popup = window.open(url, windowName, 'width=800,height=600');
    
    if (!popup) {
        console.error('Popup blocked or failed to open');
        return null;
    }
    
    // Wait for popup to load and establish communication
    popup.onload = async () => {
        if (window.MessagingGuard) {
            const isReady = await window.MessagingGuard.waitForMessageTarget(
                popup,
                window.location.origin,
                5000
            );
            
            if (isReady) {
                console.log('Popup ready for communication');
                // Send initial data to popup
                window.MessagingGuard.safePostMessage(
                    popup,
                    { type: 'PARENT_READY', data: getInitialData() },
                    window.location.origin
                );
            }
        }
    };
    
    return popup;
}

// Helper functions for examples
function handleCalendarEvent(payload) {
    console.log('Calendar event received:', payload);
    // Handle calendar-specific events
}

function handleUserAction(payload) {
    console.log('User action received:', payload);
    // Handle user interactions
}

function getCurrentUserId() {
    // Return current user ID from your app state
    return 'demo-user-123';
}

function getInitialData() {
    // Return data to send to new windows/iframes
    return {
        timestamp: Date.now(),
        userPreferences: {},
        appState: {}
    };
}

// Example 4: Error-safe chrome.runtime check
function checkForExtension() {
    // Safe way to check if running in extension context
    const hasChrome = typeof window.chrome !== 'undefined';
    const hasRuntime = hasChrome && typeof window.chrome.runtime !== 'undefined';
    const hasExtensionId = hasRuntime && window.chrome.runtime.id;
    
    console.log('Extension environment check:', {
        hasChrome,
        hasRuntime,
        hasExtensionId,
        isExtension: hasExtensionId
    });
    
    return hasExtensionId;
}

// Export functions to global scope for easy testing
window.MessagingExamples = {
    sendToExtension,
    setupIframeMessaging,
    openWindowWithMessaging,
    checkForExtension
};

console.log('[MessagingExamples] Example functions loaded');