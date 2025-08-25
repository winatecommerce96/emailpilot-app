# LangGraph Integration Troubleshooting Guide

## Quick Diagnostics

Run this command to check all integrations:
```bash
python -m workflow.diagnostics
```

---

## Common Issues and Solutions

### 1. Studio Not Syncing Schema

#### Symptoms
- Changes made in Studio don't appear in `workflow/workflow.json`
- Export button disabled or not working
- Schema reverts after save

#### Diagnosis
```bash
# Check file permissions
ls -la workflow/workflow.json

# Verify Studio configuration
echo $STUDIO_ALLOW_EDIT
echo $STUDIO_PROJECT_PATH

# Check Studio logs
tail -f logs/studio.log
```

#### Solutions

**Permission Issues:**
```bash
# Fix file permissions
chmod 755 workflow/
chmod 644 workflow/workflow.json

# Ensure user owns the files
chown -R $(whoami) workflow/
```

**Configuration Issues:**
```bash
# Verify environment variables
export STUDIO_ALLOW_EDIT=true
export STUDIO_PROJECT_PATH=./workflow

# Restart Studio
pkill langgraph-studio
langgraph-studio --project ./workflow --port 8123
```

**Schema Validation:**
```python
# Validate schema format
python -c "
import json
with open('workflow/workflow.json') as f:
    schema = json.load(f)
    print('✓ Valid JSON')
    assert 'nodes' in schema, 'Missing nodes'
    assert 'edges' in schema, 'Missing edges'
    print('✓ Valid schema structure')
"
```

---

### 2. LangSmith Traces Missing

#### Symptoms
- Workflow runs complete but no traces in LangSmith
- Empty project in LangSmith dashboard
- No cost/token metrics

#### Diagnosis
```bash
# Test API key
curl -H "X-API-Key: $LANGSMITH_API_KEY" \
     https://api.smith.langchain.com/info

# Check tracing is enabled
echo $ENABLE_TRACING
echo $LANGSMITH_PROJECT

# Test Python client
python -c "
from langsmith import Client
client = Client()
print('Projects:', list(client.list_projects()))
"
```

#### Solutions

**API Key Issues:**
```bash
# Verify API key format (should be ls_...)
echo $LANGSMITH_API_KEY | head -c 5

# Re-export if needed
export LANGSMITH_API_KEY="ls_your_actual_key_here"

# Test connection
python -m langsmith validate
```

**Tracing Disabled:**
```bash
# Enable tracing
export ENABLE_TRACING=true
export TRACE_SAMPLING_RATE=1.0

# Restart application
pkill -f uvicorn
uvicorn main_firestore:app --reload
```

**Project Configuration:**
```bash
# Create project if missing
python -c "
from langsmith import Client
client = Client()
client.create_project('emailpilot-calendar')
"

# Set project
export LANGSMITH_PROJECT=emailpilot-calendar
```

**Callback Issues:**
```python
# Debug callbacks in your code
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("langsmith").setLevel(logging.DEBUG)

# Add explicit callbacks
from langsmith.callbacks import LangSmithCallbackHandler
callbacks = [LangSmithCallbackHandler()]
```

---

### 3. Hub Dashboard Connection Issues

#### Symptoms
- Service status badges show red/offline
- "Failed to fetch" errors in console
- Deep links not working

#### Diagnosis
```bash
# Check each service endpoint
curl http://localhost:8000/api/hub/status
curl http://localhost:8123/health  # Studio
curl http://localhost:8000/api/workflow/schemas

# Check CORS configuration
curl -I http://localhost:8000/api/hub/status \
     -H "Origin: http://localhost:8000"
```

#### Solutions

**Service Unavailable:**
```bash
# Start missing services
langgraph-studio --project ./workflow --port 8123 &
uvicorn main_firestore:app --reload --port 8000 &

# Verify ports not in use
lsof -i :8123
lsof -i :8000
```

**CORS Issues:**
```python
# Update CORS in main_firestore.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:8123"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Network Issues:**
```bash
# Check firewall
sudo iptables -L | grep 8123

# Test localhost resolution
ping localhost
nslookup localhost
```

---

### 4. Workflow Execution Failures

#### Symptoms
- Workflows start but fail immediately
- "Module not found" errors
- State corruption errors

#### Diagnosis
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify imports
python -c "from workflow.nodes import *"
python -c "from workflow.agents import *"

# Check checkpointer
ls -la workflow/checkpoints/
```

#### Solutions

**Import Issues:**
```bash
# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or in code
import sys
sys.path.insert(0, '.')
```

**Checkpointer Issues:**
```bash
# Clear corrupted checkpoints
rm -rf workflow/checkpoints/*

# Recreate directory
mkdir -p workflow/checkpoints
chmod 755 workflow/checkpoints
```

**Dependency Issues:**
```bash
# Reinstall dependencies
pip install --upgrade langchain-core langgraph langsmith

# Check versions
pip list | grep lang
```

---

### 5. Performance Issues

#### Symptoms
- High memory usage
- Slow trace uploads
- UI lag in Studio

#### Diagnosis
```bash
# Monitor resources
htop  # or top

# Check trace volume
python -c "
from langsmith import Client
client = Client()
runs = list(client.list_runs(project_name='emailpilot-calendar'))
print(f'Total runs: {len(runs)}')
"

# Profile Python
python -m cProfile -o profile.stats your_script.py
```

#### Solutions

**Reduce Tracing Overhead:**
```bash
# Sample traces instead of all
export TRACE_SAMPLING_RATE=0.1  # 10% sampling

# Disable in production
export ENABLE_TRACING=false
```

**Memory Optimization:**
```python
# Use streaming for large outputs
from langchain.callbacks.streaming import StreamingStdOutCallbackHandler

# Clear caches periodically
import gc
gc.collect()
```

**Database Cleanup:**
```bash
# Archive old runs
python -c "
from datetime import datetime, timedelta
from langsmith import Client
client = Client()
cutoff = datetime.now() - timedelta(days=30)
# Archive runs older than 30 days
"
```

---

## Debug Commands Reference

### System Health Check
```bash
# Full system diagnostic
curl http://localhost:8000/api/hub/status | python -m json.tool

# Individual service checks
curl http://localhost:8123/health  # Studio
curl http://localhost:8000/health   # Main app
```

### Trace Debugging
```bash
# Enable verbose logging
export LANGSMITH_DEBUG=true
export LOG_LEVEL=DEBUG

# Test trace submission
python -c "
from langsmith import Client
from langsmith.run_helpers import traceable

@traceable
def test_function():
    return 'Hello, World!'

test_function()
print('Check LangSmith for trace')
"
```

### Configuration Export
```bash
# Export all configuration for support
cat > config_dump.json << EOF
{
  "env": {
    "LANGSMITH_API_KEY": "${LANGSMITH_API_KEY:0:10}...",
    "LANGSMITH_PROJECT": "$LANGSMITH_PROJECT",
    "ENABLE_TRACING": "$ENABLE_TRACING",
    "STUDIO_ROOT": "$STUDIO_ROOT",
    "APP_ENV": "$APP_ENV"
  },
  "versions": {
    "python": "$(python --version)",
    "langsmith": "$(pip show langsmith | grep Version)",
    "langgraph": "$(pip show langgraph | grep Version)",
    "langchain-core": "$(pip show langchain-core | grep Version)"
  }
}
EOF
```

### Emergency Recovery
```bash
# Full reset (preserves data)
./scripts/reset_integration.sh

# Backup current state
tar -czf backup_$(date +%Y%m%d).tar.gz \
    workflow/ \
    .env.langgraph \
    logs/

# Restore from backup
tar -xzf backup_20250822.tar.gz
```

---

## Getting Help

1. **Check logs first:**
   ```bash
   tail -f logs/app.log
   tail -f logs/studio.log
   ```

2. **Run diagnostics:**
   ```bash
   python -m workflow.diagnostics --verbose
   ```

3. **Collect debug info:**
   ```bash
   ./scripts/collect_debug_info.sh > debug_info.txt
   ```

4. **Contact support with:**
   - Debug info file
   - Screenshot of error
   - Steps to reproduce
   - Environment details

---

## Monitoring Checklist

Daily:
- [ ] Check service status badges in Hub
- [ ] Verify traces appearing in LangSmith
- [ ] Review error logs

Weekly:
- [ ] Clean up old checkpoints
- [ ] Archive completed runs
- [ ] Update dependencies

Monthly:
- [ ] Review trace costs
- [ ] Optimize sampling rates
- [ ] Backup configurations