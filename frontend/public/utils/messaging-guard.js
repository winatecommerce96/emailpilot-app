// Safe messaging utilities for extension and iframe communication
// Global namespace for browser compatibility
window.MessagingGuard = window.MessagingGuard || {};

// Chrome extension messaging guard
window.MessagingGuard.sendExtensionMessage = function sendExtensionMessage(payload) {
    if (window?.chrome?.runtime?.id && typeof window.chrome.runtime.sendMessage === 'function') {
        return new Promise((resolve) => {
            try {
                window.chrome.runtime.sendMessage(payload, (response) => {
                    // Check for runtime errors
                    if (chrome.runtime.lastError) {
                        console.debug('Extension messaging not available:', chrome.runtime.lastError.message);
                        resolve(null);
                    } else {
                        resolve(response);
                    }
                });
            } catch (e) {
                console.debug('Extension messaging error:', e.message);
                resolve(null);
            }
        });
    }
    return Promise.resolve(null);
};

// PostMessage with handshake
window.MessagingGuard.setupMessageReceiver = function setupMessageReceiver(messageHandler) {
    window.addEventListener('message', (event) => {
        // Validate origin if needed
        if (event.data?.type === 'PING') {
            event.source?.postMessage({ type: 'PONG', ready: true }, event.origin);
        } else if (messageHandler) {
            messageHandler(event);
        }
    });
};

window.MessagingGuard.waitForMessageTarget = async function waitForMessageTarget(targetWindow, origin = '*', timeout = 1000) {
    return new Promise((resolve) => {
        let responded = false;
        
        function onMessage(event) {
            if (event.data?.type === 'PONG') {
                responded = true;
                window.removeEventListener('message', onMessage);
                resolve(true);
            }
        }
        
        window.addEventListener('message', onMessage);
        
        // Try to ping the target
        try {
            targetWindow.postMessage({ type: 'PING' }, origin);
        } catch (e) {
            window.removeEventListener('message', onMessage);
            resolve(false);
        }
        
        // Timeout fallback
        setTimeout(() => {
            window.removeEventListener('message', onMessage);
            resolve(responded);
        }, timeout);
    });
};

// Safe postMessage wrapper
window.MessagingGuard.safePostMessage = function safePostMessage(targetWindow, message, origin = '*') {
    try {
        if (targetWindow && typeof targetWindow.postMessage === 'function') {
            targetWindow.postMessage(message, origin);
            return true;
        }
    } catch (e) {
        console.debug('PostMessage failed:', e.message);
    }
    return false;
};

console.log('[MessagingGuard] Utilities loaded:', Object.keys(window.MessagingGuard));