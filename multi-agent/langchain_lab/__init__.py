"""
LangChain Lab - Sandboxed module for evaluating RAG and Agent flows.

This module provides experimental LangChain-based capabilities that can be
evaluated alongside the existing EmailPilot orchestration system. All features
are opt-in and designed for zero impact on the core application.

Version: 1.0.0
"""

__version__ = "1.0.0"

# Export key components for external integration
from .config import LangChainConfig, get_config
from .deps import check_dependencies, get_llm, get_embeddings, get_vectorstore

__all__ = [
    "LangChainConfig",
    "get_config",
    "check_dependencies",
    "get_llm",
    "get_embeddings",
    "get_vectorstore",
]