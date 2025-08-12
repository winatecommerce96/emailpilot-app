// Cloud Function: mcp-clients
// Deployed at: https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients

exports.mcpClients = (req, res) => {
  // Set CORS headers for all requests
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
  res.set('Access-Control-Max-Age', '3600');
  
  // Handle preflight OPTIONS request
  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }
  
  // In-memory storage for demo (would use Firestore in production)
  // This resets on each function cold start
  const clients = [];
  
  // Handle GET request - List all clients
  if (req.method === 'GET') {
    res.status(200).json(clients);
    return;
  }
  
  // Handle POST request - Create new client
  if (req.method === 'POST') {
    const { name, api_key, model_id, is_active } = req.body || {};
    
    if (!name) {
      res.status(400).json({ error: 'Client name is required' });
      return;
    }
    
    const newClient = {
      id: Date.now().toString(),
      name,
      api_key: api_key ? '***' + api_key.slice(-4) : null, // Mask API key
      model_id: model_id || 1,
      is_active: is_active !== false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    clients.push(newClient);
    res.status(201).json(newClient);
    return;
  }
  
  // Handle PUT request - Update client
  if (req.method === 'PUT') {
    const clientId = req.path.split('/').pop();
    const clientIndex = clients.findIndex(c => c.id === clientId);
    
    if (clientIndex === -1) {
      res.status(404).json({ error: 'Client not found' });
      return;
    }
    
    const updates = req.body || {};
    clients[clientIndex] = {
      ...clients[clientIndex],
      ...updates,
      updated_at: new Date().toISOString()
    };
    
    res.status(200).json(clients[clientIndex]);
    return;
  }
  
  // Handle DELETE request - Delete client
  if (req.method === 'DELETE') {
    const clientId = req.path.split('/').pop();
    const clientIndex = clients.findIndex(c => c.id === clientId);
    
    if (clientIndex === -1) {
      res.status(404).json({ error: 'Client not found' });
      return;
    }
    
    clients.splice(clientIndex, 1);
    res.status(204).send('');
    return;
  }
  
  // Method not allowed
  res.status(405).json({ error: 'Method not allowed' });
};