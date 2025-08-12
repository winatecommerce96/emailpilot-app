// Quick Console Test for MCP Cloud Functions
// Copy and paste this into the browser console at https://emailpilot.ai/admin

console.log('🔍 Testing MCP Cloud Functions...');

// Test Models endpoint
fetch('https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models')
    .then(res => res.json())
    .then(data => {
        console.log('✅ Models endpoint working:');
        console.table(data);
    })
    .catch(err => console.error('❌ Models endpoint failed:', err));

// Test Health endpoint  
fetch('https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health')
    .then(res => res.json())
    .then(data => {
        console.log('✅ Health endpoint working:', data);
    })
    .catch(err => console.error('❌ Health endpoint failed:', err));

// Test Clients endpoint
fetch('https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients')
    .then(res => res.json())
    .then(data => {
        console.log('✅ Clients endpoint working:', data);
    })
    .catch(err => console.error('❌ Clients endpoint failed:', err));