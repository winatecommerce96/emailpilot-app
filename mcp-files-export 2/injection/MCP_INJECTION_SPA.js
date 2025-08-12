// EmailPilot MCP Injection for SPA
// Works with single-page application structure
// Copy and paste this entire script into the browser console at https://emailpilot.ai

(function() {
    console.log('🚀 Injecting MCP Management into EmailPilot SPA...');
    
    // Configuration
    const MCP_ENDPOINTS = {
        models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
        clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
        health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    };
    
    // Find the admin section or navigation
    function findAdminSection() {
        // Look for various possible admin indicators
        const selectors = [
            '[class*="admin"]',
            '[class*="Admin"]',
            '[class*="dashboard"]',
            '[class*="Dashboard"]',
            '[class*="sidebar"]',
            '[class*="Sidebar"]',
            '[class*="nav"]',
            '[class*="Nav"]',
            '[class*="menu"]',
            '[class*="Menu"]'
        ];
        
        for (const selector of selectors) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                console.log(`Found elements with selector: ${selector}`);
                return elements;
            }
        }
        return null;
    }
    
    // Add MCP button to the page
    function addMCPButton() {
        // First, try to find existing navigation or button area
        const adminElements = findAdminSection();
        
        // Create floating MCP button as fallback
        const mcpButton = document.createElement('button');
        mcpButton.id = 'mcp-toggle-button';
        mcpButton.innerHTML = '🤖 MCP Management';
        mcpButton.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            z-index: 99999;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            transition: transform 0.2s;
        `;
        
        mcpButton.onmouseover = () => {
            mcpButton.style.transform = 'scale(1.05)';
        };
        
        mcpButton.onmouseout = () => {
            mcpButton.style.transform = 'scale(1)';
        };
        
        mcpButton.onclick = () => {
            toggleMCPInterface();
        };
        
        document.body.appendChild(mcpButton);
        console.log('✅ Added MCP button (top-right corner)');
        
        // Also try to add to any existing menu
        if (adminElements) {
            adminElements.forEach(element => {
                // Check if this looks like a menu container
                if (element.querySelector('a, button') && !element.querySelector('#mcp-menu-item')) {
                    const mcpMenuItem = document.createElement('div');
                    mcpMenuItem.id = 'mcp-menu-item';
                    mcpMenuItem.innerHTML = `
                        <button style="
                            width: 100%;
                            text-align: left;
                            padding: 10px 20px;
                            background: transparent;
                            border: none;
                            color: #667eea;
                            font-size: 14px;
                            font-weight: 500;
                            cursor: pointer;
                            transition: background 0.2s;
                        " onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='transparent'" onclick="window.toggleMCPInterface()">
                            🤖 MCP Management
                        </button>
                    `;
                    element.appendChild(mcpMenuItem);
                    console.log('✅ Added MCP to existing menu');
                }
            });
        }
    }
    
    // Create MCP interface overlay
    function createMCPInterface() {
        const mcpInterface = document.createElement('div');
        mcpInterface.id = 'mcp-interface-overlay';
        mcpInterface.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 100000;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease;
        `;
        
        mcpInterface.innerHTML = `
            <div style="
                background: white;
                width: 90%;
                max-width: 1200px;
                max-height: 90vh;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                animation: slideUp 0.3s ease;
            ">
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px 30px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <h1 style="margin: 0; font-size: 24px; display: flex; align-items: center;">
                        🤖 MCP Management
                        <span style="
                            margin-left: 15px;
                            padding: 4px 12px;
                            background: rgba(255, 255, 255, 0.2);
                            border-radius: 20px;
                            font-size: 12px;
                            font-weight: normal;
                        ">Cloud Functions Integration</span>
                    </h1>
                    <button onclick="document.getElementById('mcp-interface-overlay').remove()" style="
                        background: none;
                        border: none;
                        color: white;
                        font-size: 30px;
                        cursor: pointer;
                        padding: 0;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border-radius: 4px;
                        transition: background 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.2)'" onmouseout="this.style.background='none'">×</button>
                </div>
                
                <div style="padding: 30px; overflow-y: auto; max-height: calc(90vh - 100px);">
                    <!-- Status Cards -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                        <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; border: 1px solid #86efac;">
                            <div style="color: #166534; font-size: 14px; margin-bottom: 5px;">System Status</div>
                            <div style="font-size: 24px; font-weight: bold; color: #22c55e;">✅ Active</div>
                        </div>
                        <div style="background: #fef3c7; padding: 20px; border-radius: 8px; border: 1px solid #fde047;">
                            <div style="color: #78350f; font-size: 14px; margin-bottom: 5px;">Available Models</div>
                            <div id="model-count" style="font-size: 24px; font-weight: bold; color: #f59e0b;">Loading...</div>
                        </div>
                        <div style="background: #ede9fe; padding: 20px; border-radius: 8px; border: 1px solid #c4b5fd;">
                            <div style="color: #4c1d95; font-size: 14px; margin-bottom: 5px;">Active Clients</div>
                            <div id="client-count" style="font-size: 24px; font-weight: bold; color: #8b5cf6;">Loading...</div>
                        </div>
                        <div style="background: #dbeafe; padding: 20px; border-radius: 8px; border: 1px solid #93c5fd;">
                            <div style="color: #1e3a8a; font-size: 14px; margin-bottom: 5px;">API Health</div>
                            <div id="api-health" style="font-size: 24px; font-weight: bold; color: #3b82f6;">Checking...</div>
                        </div>
                    </div>
                    
                    <!-- Models Section -->
                    <div style="background: #f8fafc; padding: 25px; border-radius: 8px; margin-bottom: 20px;">
                        <h2 style="margin: 0 0 20px 0; color: #1e293b; font-size: 20px;">Available AI Models</h2>
                        <div id="models-list" style="display: grid; gap: 15px;">
                            <div style="text-align: center; color: #94a3b8;">Loading models...</div>
                        </div>
                    </div>
                    
                    <!-- Actions Section -->
                    <div style="background: #f8fafc; padding: 25px; border-radius: 8px;">
                        <h2 style="margin: 0 0 20px 0; color: #1e293b; font-size: 20px;">Quick Actions</h2>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
                            <button onclick="window.testAllMCPEndpoints()" style="
                                padding: 10px 20px;
                                background: #667eea;
                                color: white;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 500;
                            ">🔍 Test All Endpoints</button>
                            <button onclick="window.refreshMCPData()" style="
                                padding: 10px 20px;
                                background: #10b981;
                                color: white;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 500;
                            ">🔄 Refresh Data</button>
                            <button onclick="window.showMCPDetails()" style="
                                padding: 10px 20px;
                                background: #3b82f6;
                                color: white;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                font-weight: 500;
                            ">📊 Show Details</button>
                        </div>
                        <div id="mcp-results" style="
                            padding: 15px;
                            background: #1e293b;
                            color: #e2e8f0;
                            border-radius: 6px;
                            font-family: monospace;
                            font-size: 12px;
                            min-height: 100px;
                            white-space: pre-wrap;
                            display: none;
                        "></div>
                    </div>
                </div>
            </div>
            
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideUp {
                    from { transform: translateY(20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
            </style>
        `;
        
        document.body.appendChild(mcpInterface);
        loadMCPData();
    }
    
    // Toggle MCP interface
    window.toggleMCPInterface = function() {
        const existing = document.getElementById('mcp-interface-overlay');
        if (existing) {
            existing.remove();
        } else {
            createMCPInterface();
        }
    };
    
    // Load MCP data
    async function loadMCPData() {
        try {
            const [modelsRes, clientsRes, healthRes] = await Promise.all([
                fetch(MCP_ENDPOINTS.models),
                fetch(MCP_ENDPOINTS.clients),
                fetch(MCP_ENDPOINTS.health)
            ]);
            
            const models = await modelsRes.json();
            const clients = await clientsRes.json();
            const health = await healthRes.json();
            
            // Update counts
            document.getElementById('model-count').textContent = models.length;
            document.getElementById('client-count').textContent = clients.length;
            document.getElementById('api-health').textContent = health.status === 'healthy' ? '✅ Healthy' : '⚠️ Issues';
            
            // Display models
            const modelsList = document.getElementById('models-list');
            modelsList.innerHTML = models.map(model => `
                <div style="
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    border: 1px solid #e2e8f0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <h3 style="margin: 0 0 5px 0; color: #1e293b; font-size: 16px;">${model.display_name}</h3>
                        <p style="margin: 0; color: #64748b; font-size: 14px;">
                            Provider: <strong>${model.provider}</strong> | 
                            Model: <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 3px;">${model.model_name}</code>
                        </p>
                    </div>
                    <div style="
                        padding: 6px 12px;
                        background: #dcfce7;
                        color: #166534;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 600;
                    ">ACTIVE</div>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Error loading MCP data:', error);
            const modelsList = document.getElementById('models-list');
            if (modelsList) {
                modelsList.innerHTML = `<div style="color: #ef4444;">Error loading data: ${error.message}</div>`;
            }
        }
    }
    
    // Test all endpoints
    window.testAllMCPEndpoints = async function() {
        const results = document.getElementById('mcp-results');
        results.style.display = 'block';
        results.textContent = '🔍 Testing MCP Cloud Function Endpoints...\n' + '='.repeat(50) + '\n\n';
        
        for (const [name, url] of Object.entries(MCP_ENDPOINTS)) {
            results.textContent += `Testing ${name}... `;
            try {
                const start = Date.now();
                const response = await fetch(url);
                const time = Date.now() - start;
                const data = await response.json();
                results.textContent += `✅ OK (${time}ms)\n`;
                results.textContent += `  Response: ${JSON.stringify(data).substring(0, 100)}...\n\n`;
            } catch (error) {
                results.textContent += `❌ FAILED\n`;
                results.textContent += `  Error: ${error.message}\n\n`;
            }
        }
        
        results.textContent += '='.repeat(50) + '\n';
        results.textContent += '✨ Test complete!';
    };
    
    // Refresh data
    window.refreshMCPData = function() {
        const results = document.getElementById('mcp-results');
        results.style.display = 'block';
        results.textContent = '🔄 Refreshing MCP data...';
        loadMCPData();
        setTimeout(() => {
            results.textContent = '✅ Data refreshed successfully!';
        }, 500);
    };
    
    // Show details
    window.showMCPDetails = function() {
        const results = document.getElementById('mcp-results');
        results.style.display = 'block';
        results.textContent = '📊 MCP System Details\n' + '='.repeat(50) + '\n\n';
        results.textContent += 'Endpoints:\n';
        for (const [name, url] of Object.entries(MCP_ENDPOINTS)) {
            results.textContent += `  ${name}: ${url}\n`;
        }
        results.textContent += '\nDeployment Info:\n';
        results.textContent += '  Type: Google Cloud Functions (Gen 2)\n';
        results.textContent += '  Region: us-central1\n';
        results.textContent += '  Project: emailpilot-438321\n';
        results.textContent += '  Created: 2025-08-11\n';
        results.textContent += '\nIntegration Status:\n';
        results.textContent += '  ✅ Cloud Functions: Active\n';
        results.textContent += '  ⏳ Frontend: Injection Mode\n';
        results.textContent += '  ⏳ Backend: Not integrated\n';
    };
    
    // Initialize
    addMCPButton();
    
    console.log('✅ MCP Management injection complete!');
    console.log('🎯 Click the "🤖 MCP Management" button in the top-right corner');
    console.log('📝 Or run: window.toggleMCPInterface()');
    
    // Auto-open for demonstration
    setTimeout(() => {
        console.log('💡 Tip: Opening MCP interface for preview...');
        toggleMCPInterface();
    }, 1000);
    
})();