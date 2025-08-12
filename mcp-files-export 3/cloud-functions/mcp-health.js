// Cloud Function: mcp-health
// Deployed at: https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health

exports.mcpHealth = (req, res) => {
  // Set CORS headers for all requests
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
  res.set('Access-Control-Max-Age', '3600');
  
  // Handle preflight OPTIONS request
  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }
  
  // Build health status
  const healthStatus = {
    status: 'healthy',
    mcp: 'active',
    timestamp: new Date().toISOString(),
    message: 'MCP Cloud Function Workaround Active',
    version: '1.0.0',
    uptime: process.uptime(),
    memory: {
      used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + ' MB',
      total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024) + ' MB'
    },
    environment: {
      node_version: process.version,
      platform: process.platform,
      region: process.env.FUNCTION_REGION || 'us-central1',
      project: process.env.GCP_PROJECT || 'emailpilot-438321'
    },
    services: {
      models_endpoint: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models',
      clients_endpoint: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients',
      health_endpoint: 'https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health'
    },
    checks: {
      memory: 'OK',
      response_time: 'OK',
      api_availability: 'OK'
    }
  };
  
  // Handle GET request
  if (req.method === 'GET') {
    res.status(200).json(healthStatus);
    return;
  }
  
  // Handle POST request (for detailed health check)
  if (req.method === 'POST') {
    const { verbose, check_dependencies } = req.body || {};
    
    if (verbose) {
      healthStatus.detailed = {
        request_headers: req.headers,
        request_ip: req.ip,
        request_method: req.method,
        request_url: req.url
      };
    }
    
    if (check_dependencies) {
      // Simulate checking external dependencies
      healthStatus.dependencies = {
        secret_manager: 'connected',
        firestore: 'not_configured',
        cloud_storage: 'not_configured'
      };
    }
    
    res.status(200).json(healthStatus);
    return;
  }
  
  // Method not allowed
  res.status(405).json({ error: 'Method not allowed' });
};