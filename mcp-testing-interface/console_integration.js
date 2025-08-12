// Simple Console Integration Script for MCP Testing
// Copy and paste this entire script into the browser console

(function() {
    console.log('Starting MCP Testing UI integration...');
    
    // Find the MCP header
    const headers = document.querySelectorAll('h2');
    let mcpHeader = null;
    
    for (let h of headers) {
        if (h.textContent.includes('MCP') || h.textContent.includes('Client Management')) {
            mcpHeader = h;
            break;
        }
    }
    
    if (!mcpHeader) {
        console.error('Could not find MCP Management section');
        alert('Please navigate to the MCP Management section first');
        return;
    }
    
    console.log('Found MCP header:', mcpHeader.textContent);
    
    // Find the button container
    const headerParent = mcpHeader.parentElement;
    let buttonContainer = null;
    
    // Look for existing buttons
    const existingButtons = headerParent.querySelectorAll('button');
    console.log('Found', existingButtons.length, 'existing buttons');
    
    if (existingButtons.length > 0) {
        buttonContainer = existingButtons[0].parentElement;
    } else {
        // Create new button container
        buttonContainer = document.createElement('div');
        buttonContainer.className = 'flex space-x-3';
        headerParent.appendChild(buttonContainer);
    }
    
    // Check if testing buttons already exist
    if (document.getElementById('mcp-quick-test-btn')) {
        console.log('Testing buttons already exist');
        return;
    }
    
    // Create Quick Test button
    const quickTestBtn = document.createElement('button');
    quickTestBtn.id = 'mcp-quick-test-btn';
    quickTestBtn.className = 'bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700';
    quickTestBtn.innerHTML = '⚡ Quick Test';
    quickTestBtn.style.marginRight = '12px';
    
    // Quick Test functionality
    quickTestBtn.onclick = async function() {
        console.log('Running quick test...');
        const token = localStorage.getItem('token');
        
        if (!token) {
            alert('No authentication token found. Please log in again.');
            return;
        }
        
        try {
            // Test models endpoint
            const modelsResponse = await fetch('/api/mcp/models', {
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                }
            });
            
            // Test clients endpoint
            const clientsResponse = await fetch('/api/mcp/clients', {
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                }
            });
            
            let resultMessage = '⚡ Quick MCP Test Results\n\n';
            
            if (modelsResponse.ok) {
                const models = await modelsResponse.json();
                resultMessage += '✅ Models API: Working\n';
                resultMessage += '   Available models: ' + models.length + '\n\n';
            } else {
                resultMessage += '❌ Models API: Failed (Status: ' + modelsResponse.status + ')\n\n';
            }
            
            if (clientsResponse.ok) {
                const clients = await clientsResponse.json();
                resultMessage += '✅ Clients API: Working\n';
                resultMessage += '   Configured clients: ' + clients.length + '\n\n';
            } else {
                resultMessage += '❌ Clients API: Failed (Status: ' + clientsResponse.status + ')\n\n';
            }
            
            if (modelsResponse.ok && clientsResponse.ok) {
                resultMessage += '🎉 MCP System is fully operational!';
            } else {
                resultMessage += '⚠️ Some issues detected. Check the console for details.';
                console.error('API Response Details:', {
                    models: modelsResponse.status,
                    clients: clientsResponse.status
                });
            }
            
            alert(resultMessage);
            
        } catch (error) {
            console.error('Quick test error:', error);
            alert('❌ Quick test failed:\n\n' + error.message + '\n\nCheck console for details.');
        }
    };
    
    // Create Production Testing button
    const prodTestBtn = document.createElement('button');
    prodTestBtn.id = 'mcp-prod-test-btn';
    prodTestBtn.className = 'bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700';
    prodTestBtn.innerHTML = '🧪 Production Testing';
    prodTestBtn.style.marginRight = '12px';
    
    // Production Testing functionality
    prodTestBtn.onclick = function() {
        console.log('Loading production testing interface...');
        
        // Create testing interface inline
        const contentArea = document.querySelector('.p-6') || document.querySelector('main') || document.body;
        
        // Store original content
        const originalContent = contentArea.innerHTML;
        
        // Create testing UI
        contentArea.innerHTML = `
            <div style="padding: 20px;">
                <button onclick="location.reload()" style="color: #2563eb; margin-bottom: 20px; cursor: pointer;">
                    ← Back to MCP Management
                </button>
                
                <div style="background: white; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <h2 style="font-size: 24px; font-weight: bold; margin-bottom: 16px;">
                        🧪 MCP Production Testing Suite
                    </h2>
                    
                    <p style="color: #6b7280; margin-bottom: 24px;">
                        Run comprehensive tests on your MCP configuration
                    </p>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px;">
                        <button onclick="window.runPhase1Test()" style="padding: 12px; background: #3b82f6; color: white; border-radius: 6px; cursor: pointer;">
                            Phase 1: Deployment Verification
                        </button>
                        <button onclick="window.runPhase2Test()" style="padding: 12px; background: #8b5cf6; color: white; border-radius: 6px; cursor: pointer;">
                            Phase 2: Functional Testing
                        </button>
                        <button onclick="window.runPhase3Test()" style="padding: 12px; background: #10b981; color: white; border-radius: 6px; cursor: pointer;">
                            Phase 3: Integration Testing
                        </button>
                        <button onclick="window.runPhase4Test()" style="padding: 12px; background: #f59e0b; color: white; border-radius: 6px; cursor: pointer;">
                            Phase 4: Performance Testing
                        </button>
                    </div>
                    
                    <div id="test-results" style="background: #f9fafb; border-radius: 6px; padding: 16px; min-height: 200px;">
                        <h3 style="font-weight: 600; margin-bottom: 12px;">Test Results</h3>
                        <div id="results-content" style="font-family: monospace; font-size: 14px;">
                            Click a test phase to begin...
                        </div>
                    </div>
                    
                    <div style="margin-top: 24px;">
                        <button onclick="window.runAllTests()" style="padding: 12px 24px; background: #059669; color: white; border-radius: 6px; cursor: pointer; margin-right: 12px;">
                            🚀 Run All Tests
                        </button>
                        <button onclick="window.exportTestResults()" style="padding: 12px 24px; background: #6b7280; color: white; border-radius: 6px; cursor: pointer;">
                            📥 Export Results
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Define test functions
        window.testResults = [];
        
        window.addTestResult = function(phase, test, status, message) {
            const result = {
                phase: phase,
                test: test,
                status: status,
                message: message,
                timestamp: new Date().toISOString()
            };
            window.testResults.push(result);
            
            const resultsDiv = document.getElementById('results-content');
            const statusIcon = status === 'success' ? '✅' : status === 'error' ? '❌' : '⚠️';
            resultsDiv.innerHTML += `<div>${statusIcon} ${phase} - ${test}: ${message}</div>`;
        };
        
        window.runPhase1Test = async function() {
            document.getElementById('results-content').innerHTML = 'Running Phase 1: Deployment Verification...<br>';
            const token = localStorage.getItem('token');
            
            // Test 1: Check API health
            try {
                const response = await fetch('/api/mcp/models', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (response.ok) {
                    window.addTestResult('Phase 1', 'API Health', 'success', 'MCP API is accessible');
                } else {
                    window.addTestResult('Phase 1', 'API Health', 'error', 'API returned status ' + response.status);
                }
            } catch (error) {
                window.addTestResult('Phase 1', 'API Health', 'error', error.message);
            }
            
            // Test 2: Check authentication
            if (token) {
                window.addTestResult('Phase 1', 'Authentication', 'success', 'Token is present');
            } else {
                window.addTestResult('Phase 1', 'Authentication', 'error', 'No authentication token');
            }
        };
        
        window.runPhase2Test = async function() {
            document.getElementById('results-content').innerHTML += '<br>Running Phase 2: Functional Testing...<br>';
            const token = localStorage.getItem('token');
            
            // Test clients endpoint
            try {
                const response = await fetch('/api/mcp/clients', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                const clients = await response.json();
                window.addTestResult('Phase 2', 'List Clients', 'success', 'Found ' + clients.length + ' clients');
            } catch (error) {
                window.addTestResult('Phase 2', 'List Clients', 'error', error.message);
            }
        };
        
        window.runPhase3Test = function() {
            document.getElementById('results-content').innerHTML += '<br>Running Phase 3: Integration Testing...<br>';
            window.addTestResult('Phase 3', 'Klaviyo Integration', 'warning', 'Requires valid Klaviyo API key');
        };
        
        window.runPhase4Test = async function() {
            document.getElementById('results-content').innerHTML += '<br>Running Phase 4: Performance Testing...<br>';
            const token = localStorage.getItem('token');
            
            // Measure response time
            const start = Date.now();
            try {
                await fetch('/api/mcp/models', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                const elapsed = Date.now() - start;
                if (elapsed < 1000) {
                    window.addTestResult('Phase 4', 'Response Time', 'success', elapsed + 'ms (Good)');
                } else {
                    window.addTestResult('Phase 4', 'Response Time', 'warning', elapsed + 'ms (Slow)');
                }
            } catch (error) {
                window.addTestResult('Phase 4', 'Response Time', 'error', error.message);
            }
        };
        
        window.runAllTests = async function() {
            document.getElementById('results-content').innerHTML = 'Running all tests...<br>';
            await window.runPhase1Test();
            await window.runPhase2Test();
            window.runPhase3Test();
            await window.runPhase4Test();
            document.getElementById('results-content').innerHTML += '<br><strong>All tests complete!</strong>';
        };
        
        window.exportTestResults = function() {
            const blob = new Blob([JSON.stringify(window.testResults, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mcp-test-results-' + Date.now() + '.json';
            a.click();
        };
    };
    
    // Insert buttons at the beginning of button container
    if (existingButtons.length > 0) {
        buttonContainer.insertBefore(quickTestBtn, existingButtons[0]);
        buttonContainer.insertBefore(prodTestBtn, existingButtons[0]);
    } else {
        buttonContainer.appendChild(quickTestBtn);
        buttonContainer.appendChild(prodTestBtn);
    }
    
    console.log('✅ MCP Testing buttons added successfully!');
    
    // Show success message
    const banner = document.createElement('div');
    banner.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #10b981; color: white; padding: 16px; border-radius: 8px; z-index: 9999; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
    banner.innerHTML = '✅ MCP Testing UI has been added!<br>Look for the new buttons: ⚡ Quick Test and 🧪 Production Testing';
    document.body.appendChild(banner);
    
    setTimeout(() => {
        banner.remove();
    }, 5000);
    
})();