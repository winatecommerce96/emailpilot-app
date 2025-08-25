"""
Shim module to re-export multi-agent components safely.
"""

import sys
import os
from pathlib import Path
import importlib.util

# Get paths
REPO_ROOT = Path(__file__).parent.parent.absolute()
MULTIAGENT_PATH = REPO_ROOT / "multi-agent"

def import_from_multiagent(module_path: str):
    """
    Import a module from the multi-agent directory.
    
    Args:
        module_path: Dot-separated module path (e.g., "integrations.langchain_core.config")
    
    Returns:
        The imported module
    """
    parts = module_path.split(".")
    file_path = MULTIAGENT_PATH
    
    for part in parts[:-1]:
        file_path = file_path / part
    
    # Try __init__.py first, then module.py
    init_path = file_path / parts[-1] / "__init__.py"
    module_file = file_path / f"{parts[-1]}.py"
    
    if init_path.exists():
        target_path = init_path
    elif module_file.exists():
        target_path = module_file
    else:
        raise ImportError(f"Cannot find module {module_path}")
    
    spec = importlib.util.spec_from_file_location(module_path, target_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"emailpilot_multiagent.{module_path}"] = module
        spec.loader.exec_module(module)
        return module
    
    raise ImportError(f"Failed to import {module_path}")

# Re-export commonly used modules
def get_langchain_core():
    """Get the langchain_core module."""
    return import_from_multiagent("integrations.langchain_core")

def get_config():
    """Get the config module."""
    return import_from_multiagent("integrations.langchain_core.config")

def get_cli():
    """Get the CLI module."""
    return import_from_multiagent("integrations.langchain_core.cli")

__all__ = ["import_from_multiagent", "get_langchain_core", "get_config", "get_cli"]