// Cloud Function: mcp-models
// Deployed at: https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models

exports.mcpModels = (req, res) => {
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
  
  // Return available AI models
  const models = [
    {
      id: 1,
      provider: 'claude',
      model_name: 'claude-3-opus',
      display_name: 'Claude 3 Opus',
      description: 'Most capable Claude model for complex tasks',
      max_tokens: 200000,
      supports_vision: true,
      supports_tools: true
    },
    {
      id: 2,
      provider: 'openai',
      model_name: 'gpt-4-turbo',
      display_name: 'GPT-4 Turbo',
      description: 'Latest GPT-4 with vision capabilities',
      max_tokens: 128000,
      supports_vision: true,
      supports_tools: true
    },
    {
      id: 3,
      provider: 'gemini',
      model_name: 'gemini-pro',
      display_name: 'Gemini Pro',
      description: 'Google\'s advanced multimodal model',
      max_tokens: 32000,
      supports_vision: true,
      supports_tools: true
    }
  ];
  
  // Handle GET request
  if (req.method === 'GET') {
    res.status(200).json(models);
    return;
  }
  
  // Handle POST request (for filtering/querying)
  if (req.method === 'POST') {
    const { provider, feature } = req.body || {};
    
    let filteredModels = models;
    
    if (provider) {
      filteredModels = filteredModels.filter(m => m.provider === provider);
    }
    
    if (feature === 'vision') {
      filteredModels = filteredModels.filter(m => m.supports_vision);
    }
    
    if (feature === 'tools') {
      filteredModels = filteredModels.filter(m => m.supports_tools);
    }
    
    res.status(200).json(filteredModels);
    return;
  }
  
  // Method not allowed
  res.status(405).json({ error: 'Method not allowed' });
};