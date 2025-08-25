"""
EmailPilot Multi-Agent - Import alias for multi-agent directory.

This package provides a clean import path for the multi-agent directory
which contains hyphens and cannot be imported directly.
"""

import sys
import os
from pathlib import Path

# Get the repo root
REPO_ROOT = Path(__file__).parent.parent.absolute()
MULTIAGENT_PATH = REPO_ROOT / "multi-agent"

# Add multi-agent to path only for this package's imports
if str(MULTIAGENT_PATH) not in sys.path:
    sys.path.insert(0, str(MULTIAGENT_PATH))

# Now we can import from integrations
try:
    from integrations import langchain_core
except ImportError:
    # Fallback if direct import fails
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "integrations.langchain_core",
        MULTIAGENT_PATH / "integrations" / "langchain_core" / "__init__.py"
    )
    if spec and spec.loader:
        langchain_core = importlib.util.module_from_spec(spec)
        sys.modules["emailpilot_multiagent.integrations.langchain_core"] = langchain_core
        spec.loader.exec_module(langchain_core)

__version__ = "1.0.0"
__all__ = ["langchain_core"]