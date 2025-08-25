"""
Main entry point for running as module: python -m multi-agent.integrations.langchain_core
"""

from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())