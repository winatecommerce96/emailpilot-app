# Multi-Agent Orchestrator Service

The orchestrator service coordinates multi-agent workflows for automated campaign creation using LangGraph.

## Overview

The orchestrator implements a sophisticated workflow that coordinates multiple AI agents to:
1. Analyze historical campaign performance
2. Generate new campaign strategies
3. Create campaign content and designs
4. Obtain approvals at key checkpoints
5. Deploy campaigns to production

## Workflow Stages

### 1. Data Collection
- Fetches campaign metrics from prior periods
- Analyzes performance trends
- Identifies successful patterns

### 2. Strategy Planning
- AI agents collaborate to create campaign strategy
- Considers brand guidelines and objectives
- Generates campaign calendar

### 3. Content Creation
- Subject line generation with A/B variants
- Email copy writing
- Design mockup creation
- Personalization rules

### 4. Approval Gates
- Strategy approval checkpoint
- Content approval checkpoint
- Final deployment approval
- Supports auto-approval in development

### 5. Deployment
- Campaign scheduling
- Audience segmentation
- Test sends
- Production deployment

## Configuration

### Environment Variables
- `APP_ENVIRONMENT` - development/staging/production
- `PRIMARY_MODEL` - LLM model selection
- `EMAILPILOT_BASE_URL` - EmailPilot API endpoint
- `AUTO_APPROVE_IN_DEV` - Skip approvals in development

### Models Configuration
```python
models:
  primary_provider: openai/anthropic/gemini
  primary_model: gpt-4/claude-3/gemini-pro
  temperature: 0.7
  max_tokens: 2000
```

## CLI Commands

### Run Demo Workflow
```bash
python -m apps.orchestrator_service.main demo \
  --month 2024-11 \
  --brand acme \
  --auto-approve
```

### Start API Server
```bash
python -m apps.orchestrator_service.main serve \
  --host 0.0.0.0 \
  --port 8100
```

### Interactive Approval
```bash
python -m apps.orchestrator_service.main approve
```

## API Endpoints

### Start Run
```
POST /runs/start
{
  "brand_id": "acme",
  "selected_month": "2024-11",
  "tenant_id": "pilot-tenant"
}
```

### Get Run Status
```
GET /runs/{run_id}
```

### Submit Approval
```
POST /approvals/submit
{
  "request_id": "xxx",
  "decision": "approve",
  "approver": "user@example.com",
  "notes": "Looks good"
}
```

## LangGraph Integration

The service uses LangGraph for:
- **State Management**: Tracking workflow progress
- **Checkpointing**: Resumable workflows
- **Graph Compilation**: Optimized execution
- **Error Recovery**: Automatic retries

## Agent Coordination

### Agent Types
- **Analyst Agent**: Data analysis and insights
- **Strategist Agent**: Campaign strategy
- **Creative Agent**: Content generation
- **QA Agent**: Quality assurance

### Communication
- Agents communicate through shared state
- Message passing for coordination
- Artifact storage for outputs

## Monitoring

### Metrics
- Workflow completion rate
- Average execution time
- Agent success rates
- Approval turnaround time

### Logging
- Structured logging with correlation IDs
- Agent conversation traces
- Performance profiling
- Error tracking

## Best Practices

1. **Incremental Development**: Test individual agents before orchestration
2. **Approval Gates**: Always include human checkpoints for critical decisions
3. **Error Handling**: Implement graceful degradation
4. **Observability**: Log all agent interactions
5. **Testing**: Use mock data for development