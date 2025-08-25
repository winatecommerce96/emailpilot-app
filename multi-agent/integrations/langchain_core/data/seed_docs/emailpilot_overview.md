# EmailPilot Platform Overview

EmailPilot is a comprehensive Klaviyo automation platform that streamlines email marketing campaigns, performance monitoring, and client management.

## Core Features

### Campaign Management
- Automated campaign creation and scheduling
- Multi-brand support with client isolation
- Campaign performance tracking and analytics
- A/B testing and optimization tools

### Calendar Integration
- Interactive campaign calendar for planning
- Drag-and-drop campaign scheduling
- Firebase real-time synchronization
- Campaign conflict detection

### Performance Monitoring
- Real-time metrics dashboard
- Revenue attribution tracking
- Engagement analytics (open rates, click rates, conversions)
- Custom reporting and insights

### Admin Dashboard
- User management and permissions
- System health monitoring
- Package deployment system
- Secret management integration

## Architecture

### Backend Stack
- **Framework**: FastAPI (Python 3.12)
- **Database**: Google Firestore
- **Authentication**: JWT with session management
- **Cloud Services**: Google Cloud Platform (Secret Manager, Cloud Run)

### Frontend Stack
- **Framework**: React (vanilla, CDN-loaded)
- **Styling**: TailwindCSS
- **Build System**: esbuild
- **Real-time**: Firebase/Firestore

### Integration Points
- **Klaviyo API**: Campaign and metrics data
- **Google APIs**: Calendar, authentication
- **MCP Services**: Model Context Protocol for AI features
- **LangChain**: RAG and agent capabilities (optional)

## Development Workflow

### Local Development
```bash
# Start development server
uvicorn main_firestore:app --port 8000 --host localhost --reload

# Or use make commands
make dev        # Start development server
make build      # Build frontend assets
make test       # Run tests
```

### Key Endpoints
- `/health` - Health check
- `/api/admin` - Admin operations
- `/api/calendar` - Calendar management
- `/api/goals` - Goals and targets
- `/api/performance` - Performance metrics

## Security Features
- Environment-based configuration
- Google Secret Manager integration
- Role-based access control
- API key rotation support
- Audit logging

## Deployment
- Google Cloud Run for containerized deployment
- GitHub Actions for CI/CD
- Docker support for consistent environments
- Automatic scaling based on traffic