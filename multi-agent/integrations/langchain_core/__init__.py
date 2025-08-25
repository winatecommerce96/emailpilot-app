"""
LangChain Core Integration Module.

Production-quality LangChain/LangGraph integration for EmailPilot,
providing RAG and Agent capabilities with MCP service interoperability.
"""

from .config import LangChainConfig, get_config
from .deps import (
    get_llm,
    get_embeddings,
    get_vectorstore,
    get_firestore_client,
    get_cache,
    check_dependencies,
    initialize_tracing
)

__version__ = "1.0.0"

__all__ = [
    "LangChainConfig",
    "get_config",
    "get_llm",
    "get_embeddings",
    "get_vectorstore",
    "get_firestore_client",
    "get_cache",
    "check_dependencies",
    "initialize_tracing"
]