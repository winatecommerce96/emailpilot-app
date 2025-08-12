// MCP Production Injector Script
// Run this in the browser console at https://emailpilot.ai/admin
// This will inject the MCP functionality directly into the page

(function() {
    console.log('🚀 Injecting MCP Management Interface...');
    
    // MCP Cloud Function endpoints
    const MCP_ENDPOINTS = {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    };

    // Create MCP Management UI
    function createMCPInterface() {
        // Remove any existing MCP interface
        const existingMCP = document.getElementById('mcp-injected-interface');
        if (existingMCP) {
            existingMCP.remove();
        }

        // Create container
        const mcpContainer = document.createElement('div');
        mcpContainer.id = 'mcp-injected-interface';
        mcpContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 400px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;

        mcpContainer.innerHTML = `
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0;">
                <h2 style="margin: 0; font-size: 20px; display: flex; align-items: center; justify-content: space-between;">
                    🤖 MCP Management
                    <button onclick="document.getElementById('mcp-injected-interface').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">×</button>
                </h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">Cloud Function Integration</p>
            </div>
            <div style="padding: 20px;">
                <div id="mcp-status" style="margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #f0f9ff; border-radius: 8px; border: 1px solid #0284c7;">
                        <div style="width: 12px; height: 12px; background: #22c55e; border-radius: 50%; animation: pulse 2s infinite;"></div>
                        <span style="color: #0284c7; font-weight: 500;">Connecting to Cloud Functions...</span>
                    </div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="font-size: 16px; margin-bottom: 10px; color: #4a5568;">Available Models</h3>
                    <div id="mcp-models-list" style="max-height: 200px; overflow-y: auto;">
                        <div style="padding: 10px; background: #f7fafc; border-radius: 6px;">Loading models...</div>
                    </div>
                </div>

                <div style="margin-bottom: 20px;">
                    <h3 style="font-size: 16px; margin-bottom: 10px; color: #4a5568;">Quick Actions</h3>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="window.testMCPModels()" style="flex: 1; padding: 10px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Test Models</button>
                        <button onclick="window.testMCPHealth()" style="flex: 1; padding: 10px; background: #48bb78; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Health Check</button>
                    </div>
                </div>

                <div style="margin-bottom: 20px;">
                    <h3 style="font-size: 16px; margin-bottom: 10px; color: #4a5568;">Add New Client</h3>
                    <input type="text" id="mcp-client-name" placeholder="Client Name" style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 10px;">
                    <input type="text" id="mcp-api-key" placeholder="API Key" style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 10px;">
                    <select id="mcp-model-select" style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 10px;">
                        <option value="">Select Model</option>
                    </select>
                    <button onclick="window.addMCPClient()" style="width: 100%; padding: 10px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Add Client</button>
                </div>

                <div id="mcp-results" style="margin-top: 20px; padding: 15px; background: #f7fafc; border-radius: 8px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; display: none;">
                </div>
            </div>
            <style>
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.5; }
                    100% { opacity: 1; }
                }
            </style>
        `;

        document.body.appendChild(mcpContainer);
    }

    // Test MCP Models endpoint
    window.testMCPModels = async function() {
        const resultsDiv = document.getElementById('mcp-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = 'Testing Models endpoint...';
        
        try {
            const response = await fetch(MCP_ENDPOINTS.models, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                mode: 'cors'
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            resultsDiv.innerHTML = `<strong>✅ Models Response:</strong>\n${JSON.stringify(data, null, 2)}`;
            
            // Update models list
            const modelsList = document.getElementById('mcp-models-list');
            const modelSelect = document.getElementById('mcp-model-select');
            
            modelsList.innerHTML = data.map(model => `
                <div style="padding: 10px; margin-bottom: 5px; background: white; border: 1px solid #e2e8f0; border-radius: 6px;">
                    <strong>${model.display_name}</strong><br>
                    <span style="color: #718096; font-size: 12px;">Provider: ${model.provider} | Model: ${model.model_name}</span>
                </div>
            `).join('');
            
            modelSelect.innerHTML = '<option value="">Select Model</option>' + 
                data.map(model => `<option value="${model.id}">${model.display_name}</option>`).join('');
            
            // Update status
            document.getElementById('mcp-status').innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #f0fdf4; border-radius: 8px; border: 1px solid #22c55e;">
                    <div style="width: 12px; height: 12px; background: #22c55e; border-radius: 50%;"></div>
                    <span style="color: #22c55e; font-weight: 500;">✅ Connected to Cloud Functions</span>
                </div>
            `;
            
        } catch (error) {
            resultsDiv.innerHTML = `<strong>❌ Error:</strong>\n${error.message}`;
            document.getElementById('mcp-status').innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #fef2f2; border-radius: 8px; border: 1px solid #ef4444;">
                    <div style="width: 12px; height: 12px; background: #ef4444; border-radius: 50%;"></div>
                    <span style="color: #ef4444; font-weight: 500;">❌ Connection Failed</span>
                </div>
            `;
        }
    };

    // Test MCP Health endpoint
    window.testMCPHealth = async function() {
        const resultsDiv = document.getElementById('mcp-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = 'Testing Health endpoint...';
        
        try {
            const response = await fetch(MCP_ENDPOINTS.health, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                mode: 'cors'
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            resultsDiv.innerHTML = `<strong>✅ Health Response:</strong>\n${JSON.stringify(data, null, 2)}`;
            
        } catch (error) {
            resultsDiv.innerHTML = `<strong>❌ Error:</strong>\n${error.message}`;
        }
    };

    // Add MCP Client
    window.addMCPClient = async function() {
        const name = document.getElementById('mcp-client-name').value;
        const apiKey = document.getElementById('mcp-api-key').value;
        const modelId = document.getElementById('mcp-model-select').value;
        
        if (!name || !apiKey || !modelId) {
            alert('Please fill in all fields');
            return;
        }
        
        const resultsDiv = document.getElementById('mcp-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = 'Adding client...';
        
        try {
            const response = await fetch(MCP_ENDPOINTS.clients, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                mode: 'cors',
                body: JSON.stringify({
                    name: name,
                    api_key: apiKey,
                    model_id: modelId,
                    is_active: true
                })
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            resultsDiv.innerHTML = `<strong>✅ Client Added:</strong>\n${JSON.stringify(data, null, 2)}`;
            
            // Clear form
            document.getElementById('mcp-client-name').value = '';
            document.getElementById('mcp-api-key').value = '';
            document.getElementById('mcp-model-select').value = '';
            
        } catch (error) {
            resultsDiv.innerHTML = `<strong>❌ Error:</strong>\n${error.message}\n\nNote: POST operations may not be supported by the simple Cloud Function yet.`;
        }
    };

    // Initialize
    createMCPInterface();
    
    // Auto-load models
    setTimeout(() => {
        window.testMCPModels();
    }, 500);

    console.log('✅ MCP Interface injected successfully!');
    console.log('📝 Available functions:');
    console.log('  - window.testMCPModels()');
    console.log('  - window.testMCPHealth()');
    console.log('  - window.addMCPClient()');
    
})();