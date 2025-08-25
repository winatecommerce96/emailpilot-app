# Multi-Agent Campaign Orchestration

A production-ready LangGraph-based multi-agent system for automated campaign creation workflows. This system interfaces with the existing EmailPilot platform without modifying its core functionality.

## 🎯 Overview

This multi-agent orchestration service implements a four-phase campaign creation workflow:

1. **Calendar Creation** → Performance analysis and strategic planning
2. **Brief Writing** → Campaign brief creation with brand compliance
3. **Copywriting** → Multi-variant copy generation with A/B testing
4. **Design & QA** → Design specifications and quality assurance

### Key Features

- **Deterministic & Observable**: Built with LangGraph for transparent state management
- **Human-in-the-Loop**: Approval interrupts and QA loopbacks
- **Idempotent**: Retry-safe operations with backoff strategies  
- **Testable**: Comprehensive test coverage with mocked dependencies
- **Production-Ready**: OpenTelemetry tracing, structured logging, Docker support

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Agent Orchestrator                     │
├─────────────────────────────────────────────────────────────────┤
│  Calendar Performance → Calendar Strategist → Brand Brain      │
│       ↓                      ↓                     ↓           │
│  [Approval Interrupt] → Copy Smith → Layout Lab → Gatekeeper   │
│                              ↓            ↓           ↓        │
│                     [QA Loop] ← ← ← ← ← ← ← ← ← ←     │        │
│                              ↓                        ↓        │
│                    [Final Approval] → Truth Teller    │        │
└─────────────────────────────────────────────────────────────────┘
           ↕️                    ↕️                    ↕️
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   EmailPilot    │  │   Klaviyo MCP   │  │  Analytics BQ   │
│   REST APIs     │  │   Revenue API   │  │   Firestore     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Agent Responsibilities

| Agent | Purpose | Implementation Status |
|-------|---------|----------------------|
| **Calendar Performance** | Fetch and normalize performance metrics | ✅ Complete |
| **Calendar Strategist** | Create strategic campaign calendar | ✅ Complete |
| **Brand Brain** | Generate brand-compliant creative briefs | ✅ Complete |
| **Copy Smith** | Multi-framework copy generation (AIDA, PAS, FOMO, Story) | ✅ Complete |
| **Layout Lab** | Mobile-first design specifications | ✅ Complete |
| **Gatekeeper** | QA, compliance, and deliverability review | ✅ Complete |
| **Truth Teller** | Analytics setup and KPI definition | ✅ Complete |
| **Audience Architect** | Segmentation and targeting optimization | 🚧 Stub |
| **Flowsmith** | Lifecycle automation flow design | 🚧 Stub |
| **Inbox Ranger** | Deliverability and warmup strategy | 🚧 Stub |
| **Meta Coach** | Cross-campaign optimization insights | 🚧 Stub |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- EmailPilot app running (read-only access)
- Google Cloud Project with Firestore and Secret Manager
- API keys for OpenAI, Claude, and/or Gemini

### Installation

```bash
# Navigate to multi-agent directory
cd /path/to/emailpilot-app/multi-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file:

```bash
# Core Configuration
ENVIRONMENT=development
GOOGLE_CLOUD_PROJECT=emailpilot-438321

# AI Model Configuration
PRIMARY_PROVIDER=openai
PRIMARY_MODEL=gpt-4-turbo-preview
SECONDARY_PROVIDER=anthropic
SECONDARY_MODEL=claude-3-sonnet-20240229
MARKETING_PROVIDER=gemini
MARKETING_MODEL=gemini-2.0-flash

# EmailPilot Integration
EMAILPILOT_BASE_URL=http://localhost:8000
KLAVIYO_MCP_URL=http://localhost:9090

# Orchestration Settings
AUTO_APPROVE_IN_DEV=true
MAX_REVISION_LOOPS=3
ENABLE_TRACING=true
```

### Demo Run

```bash
# Run complete workflow demo
python -m apps.orchestrator_service.main demo \
  --month 2024-11 \
  --brand acme \
  --auto-approve

# Interactive approval mode (disable auto-approve first)
python -m apps.orchestrator_service.main approve

# Start API server
python -m apps.orchestrator_service.main serve --port 8100
```

### Expected Output

```
Starting demo run for acme - 2024-11

✓ Demo completed successfully!
  Run ID: 550e8400-e29b-41d4-a716-446655440000
  Status: completed
  Artifacts saved to: multi-agent/.artifacts/acme/2024-11

Artifacts created:
  - performance_slice: perf_abc123
  - campaign_calendar: cal_def456
  - campaign_brief: brief_ghi789
  - copy_packet: copy_jkl012
  - design_spec: design_mno345
  - qa_report: qa_pqr678
```

## 📊 Artifacts Generated

### Performance Slice
```json
{
  "revenue_total": 125000.50,
  "conversion_rate": 3.2,
  "current_metrics": [...],
  "insights": [
    "Revenue increased 27.5% YoY",
    "VIP segment driving 60% of revenue"
  ]
}
```

### Campaign Calendar
```json
{
  "campaigns": [
    {
      "campaign_name": "November VIP Early Access Sale",
      "scheduled_date": "2024-11-05T10:00:00",
      "expected_revenue": 85000.00,
      "confidence_score": 0.85
    }
  ],
  "total_expected_revenue": 257000.00
}
```

### Copy Packet
```json
{
  "variants": [
    {
      "framework": "AIDA",
      "subject_line": "{{first_name}}, your VIP early access is here ✨",
      "body_copy": "Hi {{first_name}}, As one of our most valued customers...",
      "estimated_engagement": 0.42
    }
  ],
  "recommended_variant": "var_abc123"
}
```

## 🔧 API Reference

### Start Orchestration Run

```bash
POST /runs/start
Content-Type: application/json

{
  "tenant_id": "pilot-tenant",
  "brand_id": "acme",
  "selected_month": "2024-11",
  "prior_year_same_month": "2023-11",
  "metadata": {"source": "api"}
}
```

### Check Pending Approvals

```bash
GET /approvals/pending?approver_role=campaign_manager
```

### Submit Approval Decision

```bash
POST /approvals/submit
Content-Type: application/json

{
  "request_id": "approval_123",
  "decision": "approve",
  "approver": "john.doe",
  "notes": "Looks good, approved for launch"
}
```

## 🧪 Testing

### Run All Tests

```bash
# Run test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=apps --cov-report=html

# Run specific test
pytest tests/test_graph_happy_path.py::TestHappyPath::test_full_workflow_success -v
```

### Test Categories

- **Happy Path**: Full workflow with auto-approval
- **Revision Loops**: QA rejection and retry scenarios  
- **Schema Validation**: Input/output contract verification
- **Error Handling**: Network failures and timeouts
- **Approval Flows**: Human-in-the-loop interactions

## 🔍 Observability

### Structured Logging

All operations emit structured JSON logs:

```json
{
  "timestamp": "2024-11-01T10:30:00Z",
  "level": "INFO",
  "service": "multi-agent-orchestrator",
  "node": "copy_smith",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Generated 3 copy variants",
  "model_used": "gemini-2.0-flash",
  "tokens_consumed": 2847
}
```

### OpenTelemetry Tracing

Enable distributed tracing:

```bash
# Start Jaeger (optional)
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest

# Run with tracing enabled
ENABLE_TRACING=true python -m apps.orchestrator_service.main demo --month 2024-11 --brand acme
```

View traces at: http://localhost:16686

### Metrics Exported

- **Orchestration Runs**: Total runs, success rate, duration
- **Approval Latency**: Time to approval, timeout rate
- **Revision Loops**: QA reject rate, retry success
- **Model Usage**: Token consumption, provider fallbacks

## 🐳 Docker Deployment

### Build Container

```bash
cd multi-agent
docker build -f ops/dockerfile -t multi-agent-orchestrator .
```

### Run with Docker Compose

```bash
# Start full stack
docker-compose -f ops/compose.yaml up

# API available at: http://localhost:8100
# Jaeger UI at: http://localhost:16686
```

### Environment Variables

```yaml
environment:
  - ENVIRONMENT=production
  - GOOGLE_CLOUD_PROJECT=${GCP_PROJECT}
  - OPENAI_API_KEY=${OPENAI_KEY}
  - ANTHROPIC_API_KEY=${CLAUDE_KEY}
  - EMAILPILOT_BASE_URL=https://emailpilot.yourdomain.com
```

## 🔒 Security & Compliance

### API Key Management

- Production: Google Secret Manager integration
- Development: Environment variables (never commit)
- Rotation: Automatic key rotation support

### Data Handling

- **Firestore**: Artifact persistence with TTL
- **Approval History**: 90-day retention policy
- **PII Protection**: No customer data in logs
- **Encryption**: TLS 1.3 for all external calls

### Access Controls

- **Authentication**: JWT-based API access
- **Authorization**: Role-based approval workflows
- **Audit Trail**: All decisions logged with provenance

## 🚀 Production Deployment

### Checklist

- [ ] Configure Google Cloud IAM roles
- [ ] Set up Secret Manager for API keys  
- [ ] Configure Firestore security rules
- [ ] Set up monitoring and alerting
- [ ] Deploy with Cloud Run or Kubernetes
- [ ] Configure CI/CD pipeline
- [ ] Set up backup and disaster recovery

### Scaling Considerations

- **Concurrent Runs**: 10-50 simultaneous orchestrations
- **Memory Usage**: ~512MB per active run
- **Database**: Firestore scales automatically
- **Caching**: Redis cluster for high-volume operations

### Monitoring

- **Health Checks**: `/health` endpoint for load balancers
- **Metrics**: Prometheus exposition at `/metrics`
- **Logs**: JSON format for centralized logging
- **Alerts**: Critical failure notifications

## 📈 Performance

### Typical Run Times

- **Calendar Creation**: 30-60 seconds
- **Brief Writing**: 45-90 seconds  
- **Copywriting**: 60-120 seconds
- **Design & QA**: 30-60 seconds
- **Total (with approvals)**: 3-15 minutes

### Optimization

- **Caching**: Performance data and brand profiles
- **Parallelization**: Independent node operations
- **Model Selection**: Fast models for simple tasks
- **Batching**: Multiple campaigns per run

## 🔧 Configuration

### Model Provider Configuration

```python
# Fallback chain configuration
{
  "primary": {"provider": "openai", "model": "gpt-4-turbo"},
  "secondary": {"provider": "anthropic", "model": "claude-3-sonnet"},
  "marketing": {"provider": "gemini", "model": "gemini-2.0-flash"}
}
```

### Retry Strategy

```python
{
  "max_retries": 3,
  "initial_delay": 5,
  "backoff_factor": 2.0,
  "max_delay": 300
}
```

### Quality Gates

```python
{
  "brand_compliance_threshold": 0.8,
  "deliverability_threshold": 0.85,
  "accessibility_threshold": 0.9,
  "max_revision_loops": 3
}
```

## 🎓 Development Guide

### Adding New Agents

1. Create node file: `apps/orchestrator_service/nodes/new_agent.py`
2. Implement function with clear input/output types
3. Add to graph in `graph.py`
4. Create prompts in `prompts/new_agent/`
5. Add tests in `tests/`

### Custom Approval Workflows

```python
# Custom approver routing
async def custom_approval_routing(artifact_type, brand_id):
    if brand_id == "enterprise_client":
        return ["legal_team", "brand_manager", "c_suite"]
    else:
        return ["campaign_manager"]
```

### Integration Patterns

```python
# External service integration
class CustomMCPClient:
    async def call_tool(self, tool_name, parameters):
        # Implement with retries and circuit breaker
        pass
```

## 📚 Troubleshooting

### Common Issues

**Graph Compilation Fails**
```bash
# Check node imports
python -c "from apps.orchestrator_service.graph import CampaignOrchestrationGraph"
```

**Approval Timeouts**
```bash
# Check pending approvals
curl http://localhost:8100/approvals/pending
```

**Model API Failures**
```bash
# Validate configuration
python -m apps.orchestrator_service.main validate
```

**CORS Errors When Using Local HTML UI**
When running the orchestrator UI directly from `file://` (opening HTML files locally), the backend API server includes CORS middleware to allow cross-origin requests. The server is configured with:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows file:// (null origin) and all http origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

If you still encounter CORS issues:
1. Ensure the server is running with the latest code that includes CORS middleware
2. Access the API at `http://127.0.0.1:8100` (not `localhost` which may have different CORS behavior)
3. Check browser console for specific CORS error messages
4. For production, restrict `allow_origins` to specific domains instead of `"*"`

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG python -m apps.orchestrator_service.main demo --month 2024-11 --brand acme
```

### Recovery Procedures

1. **Failed Runs**: Resume from last checkpoint
2. **Stuck Approvals**: Manual override via CLI
3. **Data Corruption**: Restore from Firestore backup

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Core orchestration graph
- ✅ Basic agents implementation  
- ✅ Approval workflows
- ✅ Testing infrastructure

### Phase 2 (Q1 2025)
- 🚧 Complete Audience Architect implementation
- 🚧 Flowsmith lifecycle automation
- 🚧 Inbox Ranger deliverability optimization
- 🚧 Real-time collaboration features

### Phase 3 (Q2 2025)
- 📋 Multi-brand orchestration
- 📋 Advanced personalization engine
- 📋 Predictive performance modeling
- 📋 Integration with external creative tools

### Phase 4 (Q3 2025)
- 📋 Self-optimizing agent behaviors
- 📋 Natural language workflow creation
- 📋 Advanced A/B test orchestration
- 📋 Cross-channel campaign coordination

## 🤝 Contributing

### Development Setup

```bash
# Clone and setup
git clone <repository>
cd multi-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v
```

### Code Standards

- **Type Hints**: All functions must have complete type annotations
- **Documentation**: Docstrings for all public functions
- **Testing**: 90%+ coverage requirement
- **Security**: No secrets in code, all inputs validated

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Update documentation
4. Submit PR with detailed description
5. Address review feedback
6. Merge after approval

## 📄 License

MIT License - See LICENSE file for details.

## 🆘 Support

- **Documentation**: This README and inline docstrings
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Security**: security@yourdomain.com for vulnerabilities

## 💾 Firestore Checkpointing

The orchestration service uses **Google Cloud Firestore** for persisting LangGraph checkpoints, replacing the previous SQLite/Memory-based approach. This provides:

- **Serverless persistence**: No database server to manage
- **Automatic scaling**: Handles any workload automatically
- **Global distribution**: Multi-region replication available
- **Pay-per-use**: Only pay for what you use
- **Time-travel debugging**: Resume workflows from any checkpoint

### Configuration

The Firestore checkpointer is automatically configured using:

1. **Project ID**: From `GOOGLE_CLOUD_PROJECT` environment variable (defaults to `emailpilot-438321`)
2. **Collections**:
   - `langgraph_checkpoints`: Stores workflow checkpoints
   - `langgraph_writes`: Stores incremental writes

### Authentication

Firestore authentication works through:

1. **Google Application Default Credentials** (recommended for production):
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

2. **gcloud CLI** (for local development):
   ```bash
   gcloud auth application-default login
   gcloud config set project emailpilot-438321
   ```

3. **Google Secret Manager** (for API keys and sensitive data)

### IAM Requirements

The service account needs the following roles:
- `roles/datastore.user` - Read/write access to Firestore
- `roles/secretmanager.secretAccessor` - Access to secrets (if using Secret Manager)

### Fallback Behavior

If Firestore is unavailable, the system automatically falls back to in-memory checkpointing:

```python
try:
    self.checkpointer = FirestoreSaver(...)
    logger.info("Using Firestore checkpointer")
except Exception:
    logger.warning("Firestore unavailable, using in-memory")
    self.checkpointer = MemorySaver()
```

### Testing Checkpoints

```python
# Test checkpoint persistence
python tests/test_firestore_checkpoint.py

# Verify in Firestore Console
# Navigate to: https://console.cloud.google.com/firestore/data
# Collections: langgraph_checkpoints, langgraph_writes
```

### Migration from SQLite

**Note**: Existing SQLite checkpoints are not automatically migrated. To preserve workflow state:

1. Export SQLite data before upgrading
2. Run new workflows with Firestore
3. Old checkpoints remain in SQLite for reference

### Environment Variables

```bash
# Required
GOOGLE_CLOUD_PROJECT=emailpilot-438321

# Optional (for custom configuration)
FIRESTORE_EMULATOR_HOST=localhost:8080  # For local testing
FIRESTORE_COLLECTION_PREFIX=dev_         # For environment separation
```

### Monitoring

View checkpoint data in the Firestore console:
- URL: https://console.cloud.google.com/firestore
- Filter by collection: `langgraph_checkpoints`
- Sort by timestamp to see recent activity

## 🔧 LangGraph Compatibility

This project uses a compatibility shim to handle LangGraph version changes, particularly the `MemorySaver` import path which has changed across versions.

### Version Compatibility

- **LangGraph 0.6.x**: Uses `langgraph.checkpoint.memory.InMemorySaver`
- **LangGraph 0.2-0.5**: Uses `langgraph.checkpoint.memory.MemorySaver`
- **LangGraph <0.2**: Uses `langgraph.checkpoint.MemorySaver` (legacy)

### Import Resolution

The compatibility shim at `apps/orchestrator_service/compat/langgraph_checkpoint.py` automatically resolves the correct import path:

```python
from .compat.langgraph_checkpoint import resolve_memory_saver
MemorySaver = resolve_memory_saver()
```

### Supported Import Paths

1. `langgraph.checkpoint.memory.MemorySaver` (preferred)
2. `langgraph.checkpoint.memory.InMemorySaver` (LangGraph 0.6+)  
3. `langgraph.checkpoint.MemorySaver` (legacy)
4. `langgraph_checkpoint.memory.MemorySaver` (separate package)
5. Basic fallback implementation (last resort)

### Version Pinning

The `requirements.txt` pins LangGraph to a compatible range:

```
langgraph>=0.6.0,<1.0.0
```

### Upgrading LangGraph

When upgrading LangGraph:

1. Check compatibility with: `python -c "from apps.orchestrator_service.compat.langgraph_checkpoint import resolve_memory_saver; print(resolve_memory_saver())"`
2. Update version pin in `requirements.txt` if needed
3. Test import resolution: `python tests/test_checkpoint_import.py`

The compatibility shim provides forward and backward compatibility, so the application should work across LangGraph versions without code changes.

---

**Built with ❤️ for the EmailPilot ecosystem**