"""
Dependency management and factory functions for LangChain Lab.

This module provides version guards, client factories, and dependency checking
to ensure all required packages are available and properly configured.
"""

import sys
import logging
from typing import Optional, Any, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


def check_dependencies() -> Dict[str, bool]:
    """
    Check if all required dependencies are installed.
    
    Returns:
        Dictionary mapping package names to availability status
    """
    deps = {}
    
    # Core LangChain
    try:
        import langchain
        deps["langchain"] = True
        version = getattr(langchain, "__version__", "unknown")
        logger.debug(f"langchain version: {version}")
    except ImportError:
        deps["langchain"] = False
    
    # LangChain OpenAI
    try:
        import langchain_openai
        deps["langchain_openai"] = True
    except ImportError:
        deps["langchain_openai"] = False
    
    # LangChain Community
    try:
        import langchain_community
        deps["langchain_community"] = True
    except ImportError:
        deps["langchain_community"] = False
    
    # Vector stores
    try:
        import faiss
        deps["faiss"] = True
    except ImportError:
        deps["faiss"] = False
    
    try:
        import chromadb
        deps["chromadb"] = True
    except ImportError:
        deps["chromadb"] = False
    
    # Other dependencies
    try:
        import tiktoken
        deps["tiktoken"] = True
    except ImportError:
        deps["tiktoken"] = False
    
    try:
        import httpx
        deps["httpx"] = True
    except ImportError:
        deps["httpx"] = False
    
    try:
        from google.cloud import firestore
        deps["firestore"] = True
    except ImportError:
        deps["firestore"] = False
    
    return deps


def get_llm(config: Optional[Any] = None) -> Any:
    """
    Factory function to create LLM instance based on configuration.
    
    Args:
        config: LangChainConfig instance (will create if not provided)
    
    Returns:
        LLM instance (ChatOpenAI, ChatAnthropic, or ChatGoogleGenerativeAI)
    
    Raises:
        ImportError: If required provider package is not installed
        ValueError: If provider is not supported
    """
    if config is None:
        from .config import get_config
        config = get_config()
    
    if config.lc_provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=config.lc_model,
                api_key=config.openai_api_key,
                temperature=0.7,
                streaming=True
            )
        except ImportError:
            raise ImportError("langchain-openai not installed. Run: pip install langchain-openai")
    
    elif config.lc_provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=config.lc_model,
                api_key=config.anthropic_api_key,
                temperature=0.7,
                streaming=True
            )
        except ImportError:
            raise ImportError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
    
    elif config.lc_provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=config.lc_model,
                google_api_key=config.google_api_key,
                temperature=0.7,
                streaming=True
            )
        except ImportError:
            raise ImportError("langchain-google-genai not installed. Run: pip install langchain-google-genai")
    
    else:
        raise ValueError(f"Unsupported LLM provider: {config.lc_provider}")


def get_embeddings(config: Optional[Any] = None) -> Any:
    """
    Factory function to create embeddings instance based on configuration.
    
    Args:
        config: LangChainConfig instance (will create if not provided)
    
    Returns:
        Embeddings instance
    
    Raises:
        ImportError: If required provider package is not installed
    """
    if config is None:
        from .config import get_config
        config = get_config()
    
    if config.embeddings_provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=config.embeddings_model,
                api_key=config.openai_api_key
            )
        except ImportError:
            raise ImportError("langchain-openai not installed. Run: pip install langchain-openai")
    
    elif config.embeddings_provider == "vertex":
        try:
            from langchain_google_vertexai import VertexAIEmbeddings
            return VertexAIEmbeddings(
                model_name=config.embeddings_model,
                project=config.vertex_project
            )
        except ImportError:
            raise ImportError("langchain-google-vertexai not installed. Run: pip install langchain-google-vertexai")
    
    elif config.embeddings_provider == "sentence-transformers":
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name=config.embeddings_model or "all-MiniLM-L6-v2"
            )
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    
    else:
        # Fallback to sentence-transformers if no API key
        logger.warning(f"Unknown embeddings provider {config.embeddings_provider}, falling back to sentence-transformers")
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError("No embeddings provider available. Install sentence-transformers or configure API keys")


def get_vectorstore(embeddings: Any, config: Optional[Any] = None, create_new: bool = False) -> Any:
    """
    Factory function to create or load vector store based on configuration.
    
    Args:
        embeddings: Embeddings instance to use
        config: LangChainConfig instance (will create if not provided)
        create_new: Whether to create a new vector store (vs loading existing)
    
    Returns:
        VectorStore instance (FAISS or Chroma)
    
    Raises:
        ImportError: If required vector store package is not installed
    """
    if config is None:
        from .config import get_config
        config = get_config()
    
    if config.vectorstore == "faiss":
        try:
            from langchain_community.vectorstores import FAISS
            
            store_path = config.vectorstore_path
            
            if not create_new and store_path.exists():
                logger.info(f"Loading existing FAISS index from {store_path}")
                return FAISS.load_local(
                    str(store_path),
                    embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                logger.info("Creating new FAISS index")
                # Return None - will be created during ingestion with documents
                return None
                
        except ImportError:
            raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu")
    
    elif config.vectorstore == "chroma":
        try:
            from langchain_community.vectorstores import Chroma
            
            persist_dir = str(config.vectorstore_path).replace(".faiss", ".chroma")
            
            logger.info(f"Using Chroma with persist_directory={persist_dir}")
            return Chroma(
                embedding_function=embeddings,
                persist_directory=persist_dir
            )
            
        except ImportError:
            raise ImportError("chromadb not installed. Run: pip install chromadb")
    
    else:
        raise ValueError(f"Unsupported vector store: {config.vectorstore}")


def get_firestore_client(config: Optional[Any] = None) -> Any:
    """
    Get a read-only Firestore client with REST transport fallback.
    
    Args:
        config: LangChainConfig instance (will create if not provided)
    
    Returns:
        Firestore Client instance configured for read-only access
    """
    if config is None:
        from .config import get_config
        config = get_config()
    
    try:
        # Try to use the robust client factory if available
        try:
            from ..apps.orchestrator_service.checkpoints.firestore_client_factory import get_firestore_client
            return get_firestore_client(project_id=config.firestore_project)
        except ImportError:
            pass
        
        # Fallback to standard Firestore client with REST transport
        import os
        from google.cloud import firestore
        
        # Force REST transport for reliability
        os.environ["FIRESTORE_TRANSPORT"] = "rest"
        
        client = firestore.Client(project=config.firestore_project)
        logger.info(f"Created Firestore client for project: {config.firestore_project}")
        return client
        
    except ImportError:
        logger.warning("google-cloud-firestore not installed. Firestore tools will be unavailable.")
        return None