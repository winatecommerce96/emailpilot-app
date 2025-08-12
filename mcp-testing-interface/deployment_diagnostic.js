// Deployment Diagnostic Script
// Run this in browser console to check current deployment status

(function() {
    console.log('🔍 MCP Auto-Integration Deployment Diagnostic');
    console.log('=' * 50);
    
    const results = {
        timestamp: new Date().toISOString(),
        checks: []
    };
    
    function addResult(check, status, message, details = null) {
        const result = { check, status, message, details };
        results.checks.push(result);
        
        const icon = status === 'success' ? '✅' : status === 'error' ? '❌' : '⚠️';
        console.log(`${icon} ${check}: ${message}`);
        if (details) console.log(`   Details:`, details);
    }
    
    // Check 1: Verify package files were staged
    async function checkStagedFiles() {
        console.log('\n📦 Checking staged package files...');
        
        try {
            // Try to fetch integration config to see if files were staged
            const response = await fetch('/staged_packages/mcp_auto_20250811/integration_config.json');
            if (response.ok) {
                const config = await response.json();
                addResult('Staged Files', 'success', 'Package files found in staging directory', config);
                return config;
            } else {
                addResult('Staged Files', 'warning', 'Package files not found at expected staging location');
                return null;
            }
        } catch (error) {
            addResult('Staged Files', 'error', 'Could not check staged files', error.message);
            return null;
        }
    }
    
    // Check 2: Test MCP API endpoints
    async function checkMCPEndpoints() {
        console.log('\n🧪 Testing MCP API endpoints...');
        
        const token = localStorage.getItem('token');
        const endpoints = [
            '/api/mcp/models',
            '/api/mcp/clients',
            '/api/mcp/health'
        ];
        
        for (const endpoint of endpoints) {
            try {
                const response = await fetch(endpoint, {
                    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
                });
                
                if (response.status === 404) {
                    addResult(`Endpoint ${endpoint}`, 'error', 'Returns 404 - Not integrated');
                } else if (response.status === 401) {
                    addResult(`Endpoint ${endpoint}`, 'success', 'Returns 401 - Integrated (auth required)');
                } else if (response.status === 200) {
                    addResult(`Endpoint ${endpoint}`, 'success', 'Returns 200 - Working');
                } else {
                    addResult(`Endpoint ${endpoint}`, 'warning', `Returns ${response.status}`);
                }
            } catch (error) {
                addResult(`Endpoint ${endpoint}`, 'error', 'Request failed', error.message);
            }
        }
    }
    
    // Check 3: Verify main_firestore.py integration
    async function checkMainFileIntegration() {
        console.log('\n🔧 Checking main_firestore.py integration...');
        
        // This check would need server-side support to actually read the file
        // For now, we'll infer from API endpoint responses
        const modelsResponse = await fetch('/api/mcp/models', {
            headers: localStorage.getItem('token') ? 
                { 'Authorization': `Bearer ${localStorage.getItem('token')}` } : {}
        });
        
        if (modelsResponse.status === 404) {
            addResult('Main File Integration', 'error', 'MCP routes not registered in main_firestore.py');
        } else {
            addResult('Main File Integration', 'success', 'MCP routes appear to be registered');
        }
    }
    
    // Check 4: Look for UI components
    function checkUIComponents() {
        console.log('\n🖥️ Checking UI components...');
        
        // Check if MCPTestingInterface is loaded
        if (window.MCPTestingInterface) {
            addResult('Testing Interface', 'success', 'MCPTestingInterface component loaded');
        } else {
            addResult('Testing Interface', 'warning', 'MCPTestingInterface component not loaded');
        }
        
        // Check if AutoIntegrationDialog is loaded
        if (window.AutoIntegrationDialog) {
            addResult('Auto Integration Dialog', 'success', 'AutoIntegrationDialog component loaded');
        } else {
            addResult('Auto Integration Dialog', 'error', 'AutoIntegrationDialog component not loaded');
        }
        
        // Check current page for MCP Management
        const headers = document.querySelectorAll('h2');
        let hasMCPSection = false;
        headers.forEach(h => {
            if (h.textContent.includes('MCP')) {
                hasMCPSection = true;
            }
        });
        
        if (hasMCPSection) {
            addResult('MCP Management UI', 'success', 'MCP Management section found on page');
        } else {
            addResult('MCP Management UI', 'warning', 'MCP Management section not found - may not be on correct page');
        }
    }
    
    // Check 5: Package deployment history
    async function checkDeploymentHistory() {
        console.log('\n📝 Checking deployment history...');
        
        try {
            // Try to get deployment info from admin API
            const response = await fetch('/api/admin/packages/deployments', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (response.ok) {
                const deployments = await response.json();
                const mcpDeployments = deployments.filter(d => 
                    d.name && d.name.toLowerCase().includes('mcp')
                );
                
                addResult('Deployment History', 'success', 
                    `Found ${mcpDeployments.length} MCP-related deployments`, 
                    mcpDeployments);
            } else {
                addResult('Deployment History', 'warning', 'Could not access deployment history');
            }
        } catch (error) {
            addResult('Deployment History', 'error', 'Error accessing deployment history', error.message);
        }
    }
    
    // Check 6: Auto-integration trigger
    function checkAutoIntegrationTrigger() {
        console.log('\n🚀 Checking auto-integration trigger...');
        
        // Check if the package upload system has auto-integration support
        if (window.AutoIntegrationPackageManager) {
            addResult('Auto Integration Support', 'success', 'Package manager supports auto-integration');
        } else {
            addResult('Auto Integration Support', 'error', 'Package manager does not support auto-integration');
        }
        
        // Check if enhanced package upload endpoints exist
        fetch('/api/packages/deploy-with-integration', {
            method: 'OPTIONS',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        }).then(response => {
            if (response.ok) {
                addResult('Auto Integration Endpoint', 'success', 'Deploy-with-integration endpoint exists');
            } else {
                addResult('Auto Integration Endpoint', 'error', 'Deploy-with-integration endpoint missing');
            }
        }).catch(() => {
            addResult('Auto Integration Endpoint', 'error', 'Could not check auto-integration endpoint');
        });
    }
    
    // Main diagnostic function
    async function runDiagnostic() {
        console.log('\n🔍 Running comprehensive deployment diagnostic...\n');
        
        // Run all checks
        const config = await checkStagedFiles();
        await checkMCPEndpoints();
        await checkMainFileIntegration();
        checkUIComponents();
        await checkDeploymentHistory();
        checkAutoIntegrationTrigger();
        
        console.log('\n📊 DIAGNOSTIC SUMMARY');
        console.log('=' * 30);
        
        const successCount = results.checks.filter(c => c.status === 'success').length;
        const errorCount = results.checks.filter(c => c.status === 'error').length;
        const warningCount = results.checks.filter(c => c.status === 'warning').length;
        
        console.log(`✅ Passed: ${successCount}`);
        console.log(`❌ Failed: ${errorCount}`);
        console.log(`⚠️ Warnings: ${warningCount}`);
        
        // Determine overall status
        if (errorCount === 0) {
            console.log('\n🎉 Overall Status: AUTO-INTEGRATION SUCCESSFUL');
        } else if (successCount > errorCount) {
            console.log('\n⚠️ Overall Status: PARTIAL INTEGRATION - Manual steps may be needed');
        } else {
            console.log('\n❌ Overall Status: INTEGRATION FAILED - Manual integration required');
        }
        
        // Provide recommendations
        console.log('\n💡 RECOMMENDATIONS:');
        
        const failedEndpoints = results.checks.filter(c => 
            c.check.includes('Endpoint') && c.status === 'error'
        ).length;
        
        if (failedEndpoints > 0) {
            console.log('1. MCP API routes need to be manually added to main_firestore.py');
            console.log('2. Service needs to be restarted after route integration');
        }
        
        const hasAutoIntegrationSupport = results.checks.find(c => 
            c.check === 'Auto Integration Support' && c.status === 'success'
        );
        
        if (!hasAutoIntegrationSupport) {
            console.log('3. Package upload system needs auto-integration enhancement');
            console.log('4. Use manual integration instructions from staged files');
        }
        
        // Export results for detailed analysis
        window.mcpDiagnosticResults = results;
        console.log('\n📄 Full results saved to: window.mcpDiagnosticResults');
        console.log('📥 To export: copy(JSON.stringify(window.mcpDiagnosticResults, null, 2))');
        
        return results;
    }
    
    // Run the diagnostic
    return runDiagnostic();
})();