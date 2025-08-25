# Firestore Connectivity Auto-Fallback Guide

## Overview

This orchestrator service now includes **self-diagnosing Firestore connectivity** with automatic fallback from gRPC to REST transport when DNS or network issues are detected. This eliminates the dreaded 60-second timeout failures that occur when gRPC SRV records can't be resolved.

## Problem Solved

Previously, the service would fail with:
```
DNS resolution failed for firestore.googleapis.com:443 (60 second timeout)
```

Now, the service automatically:
1. Detects DNS/gRPC connectivity issues
2. Falls back to REST transport 
3. Continues operating without manual intervention

## How It Works

### 1. Automatic Detection (Default)

By default, the service runs connectivity diagnostics on startup:

```python
# Automatically happens when creating Firestore clients
from checkpoints.firestore_client_factory import get_firestore_client

client = get_firestore_client()  # Auto-detects best transport
```

### 2. Diagnostic Process

The system performs these checks:
1. **DNS Resolution** - Can we resolve firestore.googleapis.com?
2. **SRV Records** - Are gRPC SRV records available?
3. **gRPC Test** - Does a gRPC connection work within timeout?
4. **REST Test** - Does REST transport work as fallback?

Based on results, it selects the optimal transport.

### 3. Configuration Options

#### Environment Variables

```bash
# Transport mode (default: auto)
export FIRESTORE_TRANSPORT_MODE=auto  # Auto-detect (recommended)
export FIRESTORE_TRANSPORT_MODE=rest  # Force REST
export FIRESTORE_TRANSPORT_MODE=grpc  # Force gRPC

# Timeout for operations (default: 60 seconds)
export FIRESTORE_TIMEOUT_SECONDS=30

# Enable/disable diagnostics (default: true)
export FIRESTORE_ENABLE_DIAGNOSTICS=true

# Google Cloud Project
export GOOGLE_CLOUD_PROJECT=emailpilot-438321
```

#### In Code

```python
from checkpoints.firestore_client_factory import FirestoreClientFactory

# Auto mode (recommended)
client = FirestoreClientFactory.create_client(
    transport="auto",
    run_diagnostics=True
)

# Force specific transport
client_rest = FirestoreClientFactory.create_client(transport="rest")
client_grpc = FirestoreClientFactory.create_client(transport="grpc")
```

## Testing Connectivity

Run the diagnostic test script:

```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/multi-agent/apps/orchestrator_service
python test_firestore_connectivity.py
```

This will:
- Run full connectivity diagnostics
- Test both gRPC and REST transports
- Recommend the optimal configuration
- Test the RobustFirestoreSaver implementation

## Integration with LangGraph

The `RobustFirestoreSaver` class is a drop-in replacement for `langgraph_checkpoint_firestore.FirestoreSaver`:

```python
# Old way (fails with DNS issues)
from langgraph_checkpoint_firestore import FirestoreSaver
checkpointer = FirestoreSaver(project_id="...")

# New way (auto-fallback to REST)
from checkpoints.firestore_saver import get_robust_firestore_saver
checkpointer = get_robust_firestore_saver(project_id="...")
```

The graph.py already includes fallback logic:
1. Try original FirestoreSaver if available
2. Fall back to RobustFirestoreSaver if import fails
3. Fall back to in-memory if all else fails

## Troubleshooting

### Force REST Transport

If you consistently see gRPC failures:

```bash
# Force REST for this session
export FIRESTORE_TRANSPORT_MODE=rest
python main.py
```

### Check Current Transport

The service logs which transport is being used:

```
INFO - Creating Firestore client with REST transport for project: emailpilot-438321
```

### DNS Issues

If DNS resolution fails completely:
1. Check your network connection
2. Try using a different DNS server (8.8.8.8, 1.1.1.1)
3. Check if firewall is blocking DNS queries

### Monitoring

Enable debug logging to see detailed diagnostics:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

- **gRPC**: Lower latency, binary protocol, better for high-throughput
- **REST**: Higher latency, JSON protocol, more reliable in restricted networks

The auto-detection picks gRPC when it works well (<2s latency) and REST otherwise.

## Files Added/Modified

### New Files
- `checkpoints/firestore_client_factory.py` - Auto-detecting client factory
- `checkpoints/firestore_saver.py` - Robust checkpoint saver
- `checkpoints/__init__.py` - Module exports
- `test_firestore_connectivity.py` - Diagnostic test script
- `FIRESTORE_CONNECTIVITY_GUIDE.md` - This guide

### Modified Files
- `config.py` - Added Firestore transport settings
- `graph.py` - Updated to use RobustFirestoreSaver as fallback

## Summary

The orchestrator service now has bulletproof Firestore connectivity that:
- ✅ Auto-detects network conditions
- ✅ Falls back from gRPC to REST automatically
- ✅ Provides detailed diagnostics
- ✅ Works without manual configuration
- ✅ Logs transport selection for debugging
- ✅ Caches diagnostics for performance

No more 60-second timeouts! The service will automatically use the best available transport.