# ✅ Directory Structure Resolved

## The Correct Structure

There should be **only ONE directory**: `multi-agent/` (with hyphen)

```
emailpilot-app/
└── multi-agent/                    # ✅ CORRECT - All agent systems here
    ├── apps/
    │   └── orchestrator_service/   # Existing LangGraph orchestrator
    ├── langchain_lab/             # New LangChain evaluation module
    │   ├── requirements.txt       # Separate optional dependencies
    │   ├── rag/                   # RAG implementation
    │   ├── agents/                # Agent implementation
    │   └── cli.py                 # CLI interface
    ├── prompts/                    # Shared prompts
    ├── ops/                        # Operations
    └── tests/                      # Tests
```

## What Was Fixed

1. **Removed `multi_agent/` directory** (with underscore) - This was created by mistake
2. **All code remains in `multi-agent/`** (with hyphen) - The original, correct location
3. **Import paths fixed** - Scripts now properly add `multi-agent` to Python path when needed

## Why This Structure?

### `multi-agent/` (with hyphen) ✅
- **Purpose**: Contains all agent-based systems for EmailPilot
- **Contents**:
  - Orchestrator service (existing LangGraph system)
  - LangChain Lab (new evaluation module)
  - Shared resources (prompts, ops, tests)
- **Status**: This is the ONLY directory that should exist

### `multi_agent/` (with underscore) ❌
- **Purpose**: Was mistakenly created for Python imports
- **Status**: DELETED - Not needed, caused confusion

## How Imports Work Now

Since Python doesn't allow hyphens in module names, we handle imports like this:

### In Scripts
```python
# Add the directory to path
import sys
sys.path.insert(0, 'path/to/multi-agent')

# Now import normally
from langchain_lab import something
```

### CLI Usage
```bash
# Run directly as script (no import issues)
python multi-agent/langchain_lab/cli.py rag.ingest

# Or with full path
cd emailpilot-app
python multi-agent/langchain_lab/cli.py rag.ask -q "question"
```

### Orchestrator Integration
The orchestrator service properly adds the path before importing:
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from langchain_lab.cli import rag_ask_entrypoint
```

## Dependencies Management

### Main Requirements
- `requirements.txt` - Core EmailPilot dependencies (LangChain commented out)

### LangChain Lab Requirements
- `multi-agent/langchain_lab/requirements.txt` - Optional LangChain dependencies
- Install separately only if using LangChain Lab:
  ```bash
  pip install -r multi-agent/langchain_lab/requirements.txt
  ```

## Key Takeaway

✅ **Use `multi-agent/` (with hyphen)** - This is the one and only correct directory
❌ **Never create `multi_agent/`** - Not needed, causes confusion

The hyphenated directory follows standard naming conventions and keeps all agent-related code organized in one place. Import issues are handled through proper path management, not by creating duplicate directories.