# MCP Management System

## Overview

The MCP (Model Context Protocol) Management System provides a unified interface for managing multiple AI model providers (Claude, OpenAI, Gemini) within the EmailPilot application. It enables secure API key management, multi-model comparisons, usage tracking, and billing management.

## Features

### 🔐 Secure API Key Management
- All API keys stored in Google Secret Manager
- Encrypted at rest and in transit
- Role-based access control
- Automatic key rotation support

### 🤖 Multi-Model Support
- **Claude**: claude-3-opus, claude-3-sonnet
- **OpenAI**: gpt-4-turbo, gpt-4, gpt-3.5-turbo
- **Gemini**: gemini-pro, gemini-pro-vision
- Easy model switching and comparison
- Unified API interface across all providers

### 📊 Usage Analytics
- Real-time usage tracking
- Token consumption monitoring
- Cost estimation and billing
- Performance metrics (latency, success rate)
- Detailed usage reports by client and model

### 🎛️ Admin Interface
- Web-based MCP client management
- Add/edit/delete MCP clients
- Test connections to each provider
- Monitor usage and costs
- Rate limiting configuration

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                       │
│  ├── Admin Dashboard                                     │
│  └── MCP Management Component                           │
├─────────────────────────────────────────────────────────┤
│                  FastAPI Backend                         │
│  ├── /api/mcp/clients - Client CRUD                     │
│  ├── /api/mcp/execute - Tool execution                  │
│  ├── /api/mcp/usage - Analytics                         │
│  └── /api/mcp/models - Model configs                    │
├─────────────────────────────────────────────────────────┤
│               MCP Service Layer                          │
│  ├── Secret Manager Integration                          │
│  ├── Multi-provider orchestration                        │
│  ├── Rate limiting & billing                            │
│  └── Usage tracking                                      │
├─────────────────────────────────────────────────────────┤
│              External Services                           │
│  ├── Google Secret Manager                               │
│  ├── Claude API                                          │
│  ├── OpenAI API                                          │
│  ├── Gemini API                                          │
│  └── Klaviyo API                                         │
└─────────────────────────────────────────────────────────┘
```

## Setup Instructions

### Prerequisites
- Google Cloud Project with billing enabled
- Python 3.11+
- Node.js 16+
- API keys for providers you want to use

### Local Development

1. **Install dependencies:**
```bash
cd emailpilot-app
pip install -r requirements.txt
pip install google-cloud-secret-manager anthropic openai google-generativeai
```

2. **Set up environment variables:**
```bash
export GOOGLE_CLOUD_PROJECT="emailpilot-438321"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
```

3. **Create database tables:**
```bash
python migrate_mcp_tables.py
```

4. **Run the application:**
```bash
uvicorn main:app --reload --port 8000
```

5. **Access the admin panel:**
- Navigate to http://localhost:8000/app
- Login with admin credentials
- Go to Admin > MCP Management

### Cloud Deployment

Run the automated deployment script:

```bash
./deploy_mcp_system.sh
```

This script will:
1. Create database tables
2. Set up Google Secret Manager
3. Build and deploy Docker container
4. Configure Cloud Run service
5. Set up service accounts and permissions

## Usage Guide

### Adding a New MCP Client

1. Navigate to Admin > MCP Management
2. Click "Add New Client"
3. Enter:
   - Client name
   - Klaviyo Account ID
   - API keys (at minimum Klaviyo, optionally OpenAI/Gemini)
   - Rate limits and settings
4. Save the client
5. Test connections using the Test button

### Testing Connections

Each client can be tested against all configured providers:

1. Click "Test" on a client row
2. Select provider to test
3. View connection status and available tools
4. Execute test queries to verify functionality

### Monitoring Usage

View detailed usage statistics:
- Total requests and tokens
- Cost breakdown by model
- Success rates
- Performance metrics
- Top tools used

### API Usage

Execute MCP tools programmatically:

```python
import requests

# Execute a tool
response = requests.post(
    "https://your-domain.com/api/mcp/execute",
    json={
        "client_id": "client-uuid",
        "tool_name": "get_campaigns",
        "parameters": {"limit": 10},
        "provider": "openai",  # or "claude", "gemini"
        "model": "gpt-4-turbo"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

result = response.json()
```

## Security Considerations

### API Key Storage
- Never store API keys in code or environment variables
- All keys encrypted in Google Secret Manager
- Access controlled via IAM policies
- Audit logging enabled

### Rate Limiting
- Per-client request limits (default: 60/min)
- Daily token limits (default: 1M tokens)
- Automatic throttling when limits reached
- Customizable per client

### Access Control
- Admin-only access to MCP management
- JWT authentication required
- Session management
- Activity logging

## Cost Management

### Pricing Overview
Model costs per 1K tokens (approximate):

| Provider | Model | Input | Output |
|----------|-------|-------|--------|
| Claude | Opus | $0.015 | $0.075 |
| Claude | Sonnet | $0.003 | $0.015 |
| OpenAI | GPT-4 Turbo | $0.01 | $0.03 |
| OpenAI | GPT-4 | $0.03 | $0.06 |
| OpenAI | GPT-3.5 | $0.0005 | $0.0015 |
| Gemini | Pro | $0.00025 | $0.0005 |

### Cost Optimization
- Use appropriate models for tasks
- Implement caching for repeated queries
- Monitor usage regularly
- Set up billing alerts
- Use rate limiting to control costs

## Troubleshooting

### Common Issues

**MCP component not loading:**
- Check browser console for errors
- Verify all scripts are loaded
- Try refreshing the page
- Check network tab for failed requests

**API key errors:**
- Verify keys are correct format (pk_, sk_, etc.)
- Check Secret Manager permissions
- Ensure service account has access
- Review audit logs

**Connection failures:**
- Test with curl/postman first
- Check rate limits
- Verify API key validity
- Review provider status pages

**High latency:**
- Check model selection (larger = slower)
- Review request size
- Consider caching
- Check network connectivity

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View MCP service logs:
```bash
gcloud run logs read --service=emailpilot-mcp
```

## Support

For issues or questions:
1. Check this documentation
2. Review logs in Google Cloud Console
3. Contact the development team
4. File an issue in the repository

## License

This system is proprietary to EmailPilot. All rights reserved.