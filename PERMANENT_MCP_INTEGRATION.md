# Permanent MCP Frontend Integration for EmailPilot SPA

## Implementation Strategy

Since EmailPilot is a single-page application that stays on the base URL, we need to:

1. **Add MCP as a modal/overlay component** (not a route)
2. **Integrate into the existing React app structure**
3. **Add the MCP button to the existing UI**
4. **Rebuild the Docker container with these changes**

## Step 1: Create React Component

### MCPManagement.jsx
```jsx
import React, { useState, useEffect } from 'react';
import './MCPManagement.css';

const MCP_ENDPOINTS = {
    models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
    clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
    health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
};

const MCPManagement = ({ isOpen, onClose }) => {
    const [models, setModels] = useState([]);
    const [clients, setClients] = useState([]);
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [testResults, setTestResults] = useState('');

    useEffect(() => {
        if (isOpen) {
            loadMCPData();
        }
    }, [isOpen]);

    const loadMCPData = async () => {
        setLoading(true);
        try {
            const [modelsRes, clientsRes, healthRes] = await Promise.all([
                fetch(MCP_ENDPOINTS.models),
                fetch(MCP_ENDPOINTS.clients),
                fetch(MCP_ENDPOINTS.health)
            ]);
            
            setModels(await modelsRes.json());
            setClients(await clientsRes.json());
            setHealth(await healthRes.json());
        } catch (error) {
            console.error('Error loading MCP data:', error);
        } finally {
            setLoading(false);
        }
    };

    const testEndpoints = async () => {
        let results = '🔍 Testing MCP Endpoints...\\n\\n';
        
        for (const [name, url] of Object.entries(MCP_ENDPOINTS)) {
            try {
                const start = Date.now();
                const response = await fetch(url);
                const time = Date.now() - start;
                await response.json();
                results += `✅ ${name}: OK (${time}ms)\\n`;
            } catch (error) {
                results += `❌ ${name}: Failed - ${error.message}\\n`;
            }
        }
        
        setTestResults(results);
    };

    if (!isOpen) return null;

    return (
        <div className="mcp-overlay" onClick={onClose}>
            <div className="mcp-modal" onClick={(e) => e.stopPropagation()}>
                <div className="mcp-header">
                    <h1>🤖 MCP Management</h1>
                    <span className="mcp-badge">Cloud Functions Integration</span>
                    <button className="mcp-close" onClick={onClose}>×</button>
                </div>
                
                <div className="mcp-content">
                    {loading ? (
                        <div className="mcp-loading">Loading MCP data...</div>
                    ) : (
                        <>
                            <div className="mcp-stats">
                                <div className="stat-card success">
                                    <div className="stat-label">System Status</div>
                                    <div className="stat-value">✅ Active</div>
                                </div>
                                <div className="stat-card info">
                                    <div className="stat-label">Available Models</div>
                                    <div className="stat-value">{models.length}</div>
                                </div>
                                <div className="stat-card warning">
                                    <div className="stat-label">Active Clients</div>
                                    <div className="stat-value">{clients.length}</div>
                                </div>
                                <div className="stat-card primary">
                                    <div className="stat-label">API Health</div>
                                    <div className="stat-value">
                                        {health?.status === 'healthy' ? '✅ Healthy' : '⚠️ Issues'}
                                    </div>
                                </div>
                            </div>

                            <div className="mcp-section">
                                <h2>Available AI Models</h2>
                                <div className="models-grid">
                                    {models.map(model => (
                                        <div key={model.id} className="model-card">
                                            <div className="model-info">
                                                <h3>{model.display_name}</h3>
                                                <p>Provider: <strong>{model.provider}</strong></p>
                                                <p>Model: <code>{model.model_name}</code></p>
                                            </div>
                                            <div className="model-status">ACTIVE</div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="mcp-section">
                                <h2>Quick Actions</h2>
                                <div className="action-buttons">
                                    <button onClick={testEndpoints} className="btn btn-primary">
                                        🔍 Test All Endpoints
                                    </button>
                                    <button onClick={loadMCPData} className="btn btn-success">
                                        🔄 Refresh Data
                                    </button>
                                </div>
                                {testResults && (
                                    <pre className="test-results">{testResults}</pre>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MCPManagement;
```

## Step 2: Add MCP Button to Main App

### In App.jsx or Main Component:
```jsx
import React, { useState } from 'react';
import MCPManagement from './components/MCPManagement';

function App() {
    const [showMCP, setShowMCP] = useState(false);
    
    // ... existing app code ...
    
    return (
        <div className="app">
            {/* Existing app content */}
            
            {/* MCP Button - Always visible */}
            <button 
                className="mcp-trigger-button"
                onClick={() => setShowMCP(true)}
                style={{
                    position: 'fixed',
                    top: '20px',
                    right: '20px',
                    zIndex: 1000
                }}
            >
                🤖 MCP Management
            </button>
            
            {/* MCP Modal */}
            <MCPManagement 
                isOpen={showMCP} 
                onClose={() => setShowMCP(false)} 
            />
        </div>
    );
}
```

## Step 3: CSS Styling

### MCPManagement.css
```css
.mcp-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s ease;
}

.mcp-modal {
    background: white;
    width: 90%;
    max-width: 1200px;
    max-height: 90vh;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    animation: slideUp 0.3s ease;
}

.mcp-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px 30px;
    display: flex;
    align-items: center;
    position: relative;
}

.mcp-header h1 {
    margin: 0;
    font-size: 24px;
}

.mcp-badge {
    margin-left: 15px;
    padding: 4px 12px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 20px;
    font-size: 12px;
}

.mcp-close {
    position: absolute;
    right: 20px;
    background: none;
    border: none;
    color: white;
    font-size: 30px;
    cursor: pointer;
    width: 40px;
    height: 40px;
}

.mcp-content {
    padding: 30px;
    overflow-y: auto;
    max-height: calc(90vh - 80px);
}

.mcp-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    padding: 20px;
    border-radius: 8px;
    border: 1px solid;
}

.stat-card.success {
    background: #f0fdf4;
    border-color: #86efac;
    color: #166534;
}

.stat-card.info {
    background: #dbeafe;
    border-color: #93c5fd;
    color: #1e3a8a;
}

.models-grid {
    display: grid;
    gap: 15px;
}

.model-card {
    padding: 20px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.model-status {
    padding: 6px 12px;
    background: #dcfce7;
    color: #166534;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

.mcp-trigger-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    transition: transform 0.2s;
}

.mcp-trigger-button:hover {
    transform: scale(1.05);
}
```

## Implementation Notes

1. **No Routing Required**: MCP opens as a modal overlay, not a separate page
2. **Always Accessible**: The MCP button is fixed in the top-right corner
3. **React Integration**: Works within existing React app structure
4. **Cloud Functions**: Uses the deployed Cloud Functions directly
5. **Responsive**: Works on all screen sizes