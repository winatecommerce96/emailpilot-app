# MCP Management System Package
**Version:** 1.0.0  
**Date:** 2025-08-11  
**Author:** EmailPilot Development Team

## 📦 Package Overview

The MCP (Model Context Protocol) Management System enables EmailPilot.ai to integrate with multiple AI model providers (Claude, OpenAI, Gemini) for enhanced Klaviyo data analysis and automation. This package provides secure API key management, multi-model support, usage tracking, and a comprehensive admin interface.

## 🎯 Features

### Core Capabilities
- **Multi-Model Support**: Seamlessly switch between Claude, OpenAI, and Gemini
- **Secure API Key Storage**: Google Secret Manager integration
- **Usage Analytics**: Track requests, tokens, costs, and performance
- **Rate Limiting**: Configurable limits per client
- **Admin Interface**: Full CRUD operations for MCP clients
- **Cost Management**: Real-time cost tracking and billing

### Supported Providers
- **Claude**: claude-3-opus, claude-3-sonnet
- **OpenAI**: gpt-4-turbo, gpt-4, gpt-3.5-turbo
- **Gemini**: gemini-pro, gemini-pro-vision

## 📋 Requirements

### Python Dependencies (for manual review)
```
openai>=1.0.0
anthropic>=0.18.0
google-generativeai>=0.3.0
httpx>=0.24.0
PyJWT>=2.8.0
```

**Note:** Dependencies are NOT automatically installed per EmailPilot safety guidelines. Add these to requirements.txt manually after review.

### System Requirements
- Python 3.11+
- Google Cloud Project with Secret Manager enabled
- Existing EmailPilot.ai deployment
- Admin access to EmailPilot Dashboard

## 🏗️ Package Structure

```
mcp-management-package/
├── deploy_to_emailpilot.sh      # Deployment script
├── frontend/
│   └── components/
│       └── MCPManagement.js     # React admin component
├── api/
│   └── mcp.py                   # FastAPI routes
├── services/
│   ├── mcp_service.py          # Multi-model orchestration
│   └── secret_manager.py       # Google Secret Manager
├── models/
│   └── mcp_client.py           # SQLAlchemy models
├── schemas/
│   └── mcp_client.py           # Pydantic schemas
├── core/
│   └── auth.py                 # Authentication utilities
├── migrate_mcp_only.py         # Database migration
├── test_compatibility.py       # Compatibility tests
└── README.md                   # This file
```

## 🚀 Installation

### Step 1: Upload Package
1. Create ZIP archive:
   ```bash
   zip -r mcp-management-v1.0.0.zip mcp-management-package/
   ```

2. Upload via Admin Dashboard:
   - Navigate to https://emailpilot.ai/admin
   - Go to "Package Management"
   - Click "Upload Package"
   - Select the ZIP file
   - Enter name: "MCP Management System"
   - Click "Upload"

### Step 2: Deploy Package
1. Find the uploaded package in the dashboard
2. Click "Deploy" button
3. Monitor deployment output
4. Note the integration directory path

### Step 3: Manual Backend Integration
1. Navigate to the integration directory shown in deployment output
2. Follow the INTEGRATION_INSTRUCTIONS.md file
3. Copy backend modules to appropriate directories:
   ```bash
   cp -r api/mcp.py ../../app/api/
   cp -r services/*.py ../../app/services/
   cp -r models/*.py ../../app/models/
   cp -r schemas/*.py ../../app/schemas/
   cp -r core/auth.py ../../app/core/
   ```

### Step 4: Database Migration
```bash
python migrate_mcp_only.py
```

### Step 5: Update Dependencies
Add to requirements.txt:
```
openai>=1.0.0
anthropic>=0.18.0
google-generativeai>=0.3.0
httpx>=0.24.0
PyJWT>=2.8.0
```

### Step 6: Restart Application
- Click "Restart Application" in admin dashboard
- Or use: `gcloud run services update emailpilot-api --region=us-central1`

## 🔧 Configuration

### Environment Variables
The following are managed through the EmailPilot config system:
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `SECRET_KEY`: JWT secret key
- `KLAVIYO_API_KEY`: Default Klaviyo API key (optional)

### Adding MCP Clients
1. Navigate to Admin > MCP Management
2. Click "Add New Client"
3. Enter:
   - Client name
   - Klaviyo Account ID
   - API keys (Klaviyo required, OpenAI/Gemini optional)
   - Rate limits
   - Default model provider
4. Save and test connection

## 📊 Usage

### API Endpoints
- `GET /api/mcp/clients` - List all clients
- `POST /api/mcp/clients` - Create new client
- `PUT /api/mcp/clients/{id}` - Update client
- `DELETE /api/mcp/clients/{id}` - Delete client
- `POST /api/mcp/execute` - Execute MCP tool
- `GET /api/mcp/usage/{id}` - Get usage history
- `GET /api/mcp/models` - List available models

### Testing Connections
```python
# Test via API
POST /api/mcp/clients/{client_id}/test
{
    "model_provider": "openai",
    "test_query": "List available tools"
}
```

### Executing Tools
```python
# Execute MCP tool
POST /api/mcp/execute
{
    "client_id": "uuid",
    "tool_name": "get_campaigns", 
    "parameters": {"limit": 10},
    "provider": "openai",
    "model": "gpt-4-turbo"
}
```

## 🧪 Testing

Run compatibility tests:
```bash
python test_compatibility.py
```

Expected output:
```
✅ Module Imports
✅ Dependencies
✅ Database Models
✅ API Compatibility
✅ MCP Service
✅ Authentication
```

## 🔒 Security

### API Key Storage
- All API keys encrypted in Google Secret Manager
- Never stored in plain text
- Access controlled via IAM roles

### Authentication
- JWT-based authentication required
- Admin role required for MCP management
- Demo users for development only

### Rate Limiting
- Per-client request limits
- Daily token quotas
- Automatic throttling

## 📈 Monitoring

### Usage Tracking
- Real-time request monitoring
- Token consumption tracking
- Cost estimation per model
- Performance metrics (latency, success rate)

### Analytics Dashboard
Access via Admin > MCP Management:
- Total requests and tokens
- Cost breakdown by model
- Top tools used
- Success/failure rates

## 🛠️ Troubleshooting

### Common Issues

**MCP routes not accessible:**
- Verify main.py includes MCP router
- Check authentication is working
- Ensure database tables created

**API keys not working:**
- Verify Secret Manager permissions
- Check key format (pk_, sk_, etc.)
- Test with direct API calls first

**High latency:**
- Check model selection (larger = slower)
- Review rate limits
- Monitor Google Cloud metrics

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Updates

### Version History
- **1.0.0** (2025-08-11): Initial release
  - Multi-model support (Claude, OpenAI, Gemini)
  - Secure API key management
  - Admin interface
  - Usage tracking and analytics

### Planned Features
- Streaming responses
- Model fine-tuning support
- Advanced caching
- Webhook notifications
- Batch processing

## 📝 Support

For issues or questions:
1. Check deployment logs in Google Cloud Console
2. Review INTEGRATION_INSTRUCTIONS.md
3. Test with test_compatibility.py
4. Contact EmailPilot development team

## 📄 License

Proprietary - EmailPilot.ai
All rights reserved.