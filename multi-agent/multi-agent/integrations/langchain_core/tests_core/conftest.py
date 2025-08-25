"""
Test configuration for LangChain Core tests.
Sets up path for emailpilot_multiagent alias imports.
"""
import sys
import pathlib

# Get the root directory (4 levels up from tests_core)
root = pathlib.Path(__file__).resolve().parents[4]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Also add multi-agent directory for direct imports
multi_agent = root / "multi-agent"
if str(multi_agent) not in sys.path:
    sys.path.insert(0, str(multi_agent))
