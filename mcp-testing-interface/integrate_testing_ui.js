// Integration Script for MCP Testing Interface
// This script updates the existing MCP Management component to include testing features

(function() {
    console.log('🚀 Starting MCP Testing Interface integration...');

    // Check if we're on the admin page
    if (!window.location.pathname.includes('admin')) {
        console.log('Not on admin page, skipping integration');
        return;
    }

    // Function to inject testing button into existing MCP Management
    function injectTestingButton() {
        // Wait for MCP Management to be loaded
        const checkInterval = setInterval(() => {
            // Look for the MCP Management header
            const headers = document.querySelectorAll('h2');
            let mcpHeader = null;
            
            headers.forEach(h => {
                if (h.textContent.includes('MCP Client Management') || h.textContent.includes('MCP Management')) {
                    mcpHeader = h;
                }
            });

            if (mcpHeader) {
                clearInterval(checkInterval);
                console.log('✅ Found MCP Management section');

                // Check if testing button already exists
                if (document.querySelector('.mcp-testing-button')) {
                    console.log('Testing button already exists');
                    return;
                }

                // Find the button container (usually next to the header)
                const headerParent = mcpHeader.parentElement;
                let buttonContainer = headerParent.querySelector('div');
                
                // If there's already a button container with "Add New Client" button
                const addButton = headerParent.querySelector('button');
                if (addButton && addButton.textContent.includes('Add New Client')) {
                    // Create testing button
                    const testingButton = document.createElement('button');
                    testingButton.className = 'mcp-testing-button bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 flex items-center mr-3';
                    testingButton.innerHTML = '🧪 Production Testing';
                    testingButton.style.marginRight = '12px';
                    
                    // Insert before the Add New Client button
                    addButton.parentElement.insertBefore(testingButton, addButton);

                    // Add click handler
                    testingButton.addEventListener('click', () => {
                        console.log('Loading MCP Testing Interface...');
                        loadTestingInterface();
                    });

                    // Also add a quick health check button
                    const healthButton = document.createElement('button');
                    healthButton.className = 'bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 flex items-center mr-3';
                    healthButton.innerHTML = '🏥 Quick Health Check';
                    healthButton.style.marginRight = '12px';
                    
                    addButton.parentElement.insertBefore(healthButton, testingButton);

                    healthButton.addEventListener('click', async () => {
                        try {
                            const response = await fetch('/api/mcp/health', {
                                headers: {
                                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                                }
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                alert(`✅ MCP System Health Check\n\nStatus: ${data.status}\nClients: ${data.clients || 'N/A'}\nModels: ${data.models || 'N/A'}\n\nSystem is operational!`);
                            } else {
                                // Try basic models endpoint as fallback
                                const modelsResponse = await fetch('/api/mcp/models', {
                                    headers: {
                                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                                    }
                                });
                                
                                if (modelsResponse.ok) {
                                    const models = await modelsResponse.json();
                                    alert(`✅ MCP System is operational!\n\nModels available: ${models.length}\n\nUse Production Testing for detailed analysis.`);
                                } else {
                                    alert('⚠️ MCP System health check failed.\n\nPlease run Production Testing for detailed diagnostics.');
                                }
                            }
                        } catch (error) {
                            alert(`❌ Health check error: ${error.message}\n\nPlease check console for details.`);
                            console.error('Health check error:', error);
                        }
                    });

                    console.log('✅ Testing buttons injected successfully');
                } else {
                    // Create a new button container if needed
                    const buttonDiv = document.createElement('div');
                    buttonDiv.className = 'flex space-x-3';
                    
                    const testingButton = document.createElement('button');
                    testingButton.className = 'mcp-testing-button bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700';
                    testingButton.innerHTML = '🧪 Production Testing';
                    
                    buttonDiv.appendChild(testingButton);
                    headerParent.appendChild(buttonDiv);

                    testingButton.addEventListener('click', () => {
                        loadTestingInterface();
                    });

                    console.log('✅ Testing button added to new container');
                }

                // Add status banner
                injectStatusBanner();
            }
        }, 500);

        // Stop checking after 10 seconds
        setTimeout(() => clearInterval(checkInterval), 10000);
    }

    // Function to inject status banner
    function injectStatusBanner() {
        // Check if banner already exists
        if (document.querySelector('.mcp-status-banner')) {
            return;
        }

        // Find the main content area
        const contentArea = document.querySelector('.p-6') || document.querySelector('[class*="p-"]');
        if (!contentArea) return;

        // Create status banner
        const banner = document.createElement('div');
        banner.className = 'mcp-status-banner bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4 mb-6';
        banner.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="font-semibold text-gray-900">🧪 MCP Testing Suite Available</h3>
                    <p class="text-sm text-gray-600 mt-1">
                        Click "Production Testing" to run comprehensive tests on your MCP configuration
                    </p>
                </div>
                <div class="flex space-x-2">
                    <button onclick="window.runQuickMCPTest()" class="px-3 py-1 bg-white border border-purple-300 text-purple-700 rounded hover:bg-purple-50 text-sm">
                        ⚡ Quick Test
                    </button>
                    <button onclick="window.showMCPTestDocs()" class="px-3 py-1 bg-white border border-blue-300 text-blue-700 rounded hover:bg-blue-50 text-sm">
                        📚 Test Docs
                    </button>
                </div>
            </div>
        `;

        // Insert after the header
        const header = document.querySelector('h2');
        if (header && header.parentElement) {
            header.parentElement.insertBefore(banner, header.nextSibling);
        }

        console.log('✅ Status banner added');
    }

    // Function to load the testing interface
    function loadTestingInterface() {
        // Check if MCPTestingInterface is already loaded
        if (window.MCPTestingInterface) {
            showTestingInterface();
            return;
        }

        // Load the testing interface component
        const script = document.createElement('script');
        script.src = 'components/MCPTestingInterface.js';
        script.onload = () => {
            console.log('✅ MCPTestingInterface component loaded');
            showTestingInterface();
        };
        script.onerror = (error) => {
            console.error('Failed to load MCPTestingInterface:', error);
            alert('Failed to load testing interface. Please ensure MCPTestingInterface.js is deployed to components folder.');
        };
        document.head.appendChild(script);
    }

    // Function to show the testing interface
    function showTestingInterface() {
        if (!window.MCPTestingInterface) {
            alert('Testing interface component not found. Please deploy MCPTestingInterface.js to the components folder.');
            return;
        }

        // Find the main content area
        const contentArea = document.querySelector('.p-6') || document.querySelector('[class*="p-"]');
        if (!contentArea) {
            alert('Could not find content area to display testing interface');
            return;
        }

        // Store original content
        const originalContent = contentArea.innerHTML;

        // Create back button and container
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="mb-4">
                <button id="backToMCP" class="text-blue-600 hover:text-blue-800 flex items-center">
                    ← Back to MCP Management
                </button>
            </div>
            <div id="testingInterfaceRoot"></div>
        `;

        // Replace content
        contentArea.innerHTML = '';
        contentArea.appendChild(container);

        // Render testing interface
        const TestingInterface = window.MCPTestingInterface;
        ReactDOM.render(React.createElement(TestingInterface), document.getElementById('testingInterfaceRoot'));

        // Add back button handler
        document.getElementById('backToMCP').addEventListener('click', () => {
            contentArea.innerHTML = originalContent;
            // Re-inject buttons since we restored original content
            setTimeout(() => injectTestingButton(), 100);
        });

        console.log('✅ Testing interface displayed');
    }

    // Global helper functions
    window.runQuickMCPTest = async function() {
        console.log('Running quick MCP test...');
        
        try {
            const token = localStorage.getItem('token');
            
            // Test 1: Check models endpoint
            const modelsResponse = await fetch('/api/mcp/models', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            // Test 2: Check clients endpoint
            const clientsResponse = await fetch('/api/mcp/clients', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const modelsOk = modelsResponse.ok;
            const clientsOk = clientsResponse.ok;
            
            let message = '🧪 Quick MCP Test Results:\n\n';
            message += `Models API: ${modelsOk ? '✅ OK' : '❌ Failed'}\n`;
            message += `Clients API: ${clientsOk ? '✅ OK' : '❌ Failed'}\n`;
            
            if (modelsOk && clientsOk) {
                const models = await modelsResponse.json();
                const clients = await clientsResponse.json();
                message += `\nModels available: ${models.length}\n`;
                message += `Clients configured: ${clients.length}\n`;
                message += '\n✅ MCP system is operational!';
            } else {
                message += '\n⚠️ Some MCP endpoints are not responding correctly.';
            }
            
            alert(message);
        } catch (error) {
            alert(`❌ Quick test failed: ${error.message}`);
        }
    };

    window.showMCPTestDocs = function() {
        const docs = `
📚 MCP Testing Documentation

🧪 TESTING OPTIONS:
1. Quick Test (⚡) - 30 second basic check
2. Production Testing - Full 5-phase test suite
3. Health Check (🏥) - Instant system status

📊 TEST PHASES:
• Phase 1: Deployment verification
• Phase 2: Functional testing
• Phase 3: Integration testing
• Phase 4: Security & performance
• Phase 5: Monitoring & logs

🔧 MANUAL TESTING:
Use CURL commands from the testing interface
to manually test specific endpoints.

💡 TIP: Run Quick Test first, then full suite
if issues are detected.
        `;
        alert(docs);
    };

    // Start the integration
    injectTestingButton();

    console.log('✅ MCP Testing Interface integration script loaded');
})();