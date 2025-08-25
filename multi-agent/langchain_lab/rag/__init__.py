"""
RAG (Retrieval-Augmented Generation) module for LangChain Lab.

Provides document ingestion, vector store management, and retrieval chains
for grounded question-answering with citations.
"""

from .ingest import DocumentIngester, ingest_documents
from .chain import RAGChain, create_rag_chain
from .evaluators import RAGEvaluator, evaluate_response

__all__ = [
    "DocumentIngester",
    "ingest_documents",
    "RAGChain",
    "create_rag_chain",
    "RAGEvaluator",
    "evaluate_response",
]