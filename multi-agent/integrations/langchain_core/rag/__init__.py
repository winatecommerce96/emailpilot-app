"""
RAG (Retrieval-Augmented Generation) module.

Provides document ingestion, retrieval, and grounded Q&A with citations.
"""

from .ingest import DocumentIngester, ingest_documents
from .chain import RAGChain, create_rag_chain, RAGResponse
from .evaluators import evaluate_response, RAGEvaluator

__all__ = [
    "DocumentIngester",
    "ingest_documents",
    "RAGChain",
    "create_rag_chain",
    "RAGResponse",
    "evaluate_response",
    "RAGEvaluator"
]