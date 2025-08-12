// EmailPilot Frontend Update for MCP Cloud Functions
// Copy this configuration to your MCPManagement or MCPTestingInterface component

// Cloud Function endpoints (replace the old /api/mcp/* endpoints)
const MCP_CLOUD_FUNCTIONS = {
  models: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
  clients: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
  health: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
};

// Example: Update the fetchModels function
const fetchModels = async () => {
  try {
    const response = await fetch(MCP_CLOUD_FUNCTIONS.models, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      mode: 'cors'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Available models:', data);
    return data;
  } catch (error) {
    console.error('Error fetching models:', error);
    throw error;
  }
};

// Example: Update the fetchClients function
const fetchClients = async () => {
  try {
    const response = await fetch(MCP_CLOUD_FUNCTIONS.clients, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      mode: 'cors'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('MCP clients:', data);
    return data;
  } catch (error) {
    console.error('Error fetching clients:', error);
    throw error;
  }
};

// Example: Health check function
const checkMCPHealth = async () => {
  try {
    const response = await fetch(MCP_CLOUD_FUNCTIONS.health, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      },
      mode: 'cors'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('MCP Health:', data);
    return data;
  } catch (error) {
    console.error('Error checking MCP health:', error);
    return { status: 'error', message: error.message };
  }
};

// For React components, update your API calls like this:
/*
// In your MCPManagement.js or MCPTestingInterface.js component:

useEffect(() => {
  const loadMCPData = async () => {
    setLoading(true);
    try {
      // Replace the old API calls
      // OLD: const response = await fetch('/api/mcp/models');
      // NEW:
      const response = await fetch('https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models');
      const data = await response.json();
      setModels(data);
    } catch (error) {
      console.error('Failed to load MCP models:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };
  
  loadMCPData();
}, []);
*/

// Test all endpoints
const testAllMCPEndpoints = async () => {
  console.log('🚀 Testing MCP Cloud Functions...');
  
  try {
    console.log('\n1. Testing Models Endpoint...');
    const models = await fetchModels();
    console.log('✅ Models:', models);
    
    console.log('\n2. Testing Clients Endpoint...');
    const clients = await fetchClients();
    console.log('✅ Clients:', clients);
    
    console.log('\n3. Testing Health Endpoint...');
    const health = await checkMCPHealth();
    console.log('✅ Health:', health);
    
    console.log('\n✨ All MCP endpoints are working!');
    return { success: true, models, clients, health };
  } catch (error) {
    console.error('❌ MCP test failed:', error);
    return { success: false, error: error.message };
  }
};

// Export for use in your application
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MCP_CLOUD_FUNCTIONS,
    fetchModels,
    fetchClients,
    checkMCPHealth,
    testAllMCPEndpoints
  };
}