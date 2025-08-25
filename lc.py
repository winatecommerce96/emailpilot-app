#!/usr/bin/env python
"""
LangChain CLI - Root entrypoint that doesn't rely on hyphenated imports.
"""

import sys
from pathlib import Path

# Add multi-agent to path for imports
REPO_ROOT = Path(__file__).parent.absolute()
MULTIAGENT_PATH = REPO_ROOT / "multi-agent"
sys.path.insert(0, str(MULTIAGENT_PATH))

# Now import and run the CLI
from integrations.langchain_core.cli import app
import typer

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)