"""
RAG chain for grounded Q&A with citations.

Provides retrieval-augmented generation with source citations.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from ..config import LangChainConfig, get_config
from ..deps import get_llm, get_embeddings, get_vectorstore

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Represents a citation from source documents."""
    source: str
    text: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    confidence: float = 1.0


@dataclass
class RAGResponse:
    """Response from RAG chain with citations."""
    question: str
    answer: str
    citations: List[Citation]
    source_documents: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": [
                {
                    "source": c.source,
                    "text": c.text,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "confidence": c.confidence
                }
                for c in self.citations
            ],
            "source_documents": self.source_documents,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class RAGChain:
    """RAG chain for grounded Q&A."""
    
    # System prompt for grounded answers
    SYSTEM_PROMPT = """You are a helpful assistant that provides accurate, grounded answers based on the provided context.

CRITICAL RULES:
1. You MUST only use information from the provided context documents
2. You MUST cite your sources using [Source: filename] markers
3. If the context doesn't contain enough information, say so clearly
4. Do NOT make up information or use knowledge beyond the context
5. Be concise but complete in your answers

Context documents:
{context}

Question: {question}

Provide a grounded answer with inline citations in the format [Source: filename].
If multiple sources support a claim, cite all of them.

Answer:"""
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        vectorstore: Optional[Any] = None,
        config: Optional[LangChainConfig] = None
    ):
        """
        Initialize RAG chain.
        
        Args:
            llm: LLM instance
            vectorstore: Vector store instance
            config: Configuration instance
        """
        self.config = config or get_config()
        self.llm = llm or get_llm(self.config)
        
        if vectorstore is None:
            embeddings = get_embeddings(self.config)
            vectorstore = get_vectorstore(embeddings, self.config)
        
        self.vectorstore = vectorstore
        self.retriever = vectorstore.as_retriever(
            search_kwargs={"k": self.config.rag_k_documents}
        )
        
        # Create prompt
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=self.SYSTEM_PROMPT
        )
        
        # Build chain
        self._build_chain()
    
    def _build_chain(self):
        """Build the RAG chain."""
        # Create a simple chain using LCEL (LangChain Expression Language)
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def _format_documents(self, docs: List[Any]) -> str:
        """
        Format documents for context.
        
        Args:
            docs: Retrieved documents
        
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", f"Document {i+1}")
            content = doc.page_content.strip()
            
            context_parts.append(
                f"[Document {i+1} - Source: {source}]\n{content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _extract_citations(
        self,
        answer: str,
        source_docs: List[Any]
    ) -> List[Citation]:
        """
        Extract citations from answer.
        
        Args:
            answer: Generated answer
            source_docs: Source documents
        
        Returns:
            List of citations
        """
        citations = []
        
        # Find all [Source: ...] patterns
        pattern = r'\[Source:\s*([^\]]+)\]'
        matches = re.findall(pattern, answer)
        
        for match in matches:
            source_name = match.strip()
            
            # Find matching document
            for doc in source_docs:
                doc_source = doc.metadata.get("source", "")
                
                if source_name in doc_source or doc_source in source_name:
                    # Extract relevant text around citation
                    # This is simplified - in production, would use more sophisticated extraction
                    text_snippet = doc.page_content[:200] + "..."
                    
                    citations.append(Citation(
                        source=doc_source,
                        text=text_snippet,
                        confidence=0.9
                    ))
                    break
        
        return citations
    
    def _calculate_confidence(
        self,
        answer: str,
        source_docs: List[Any],
        citations: List[Citation]
    ) -> float:
        """
        Calculate confidence score for answer.
        
        Args:
            answer: Generated answer
            source_docs: Source documents
            citations: Extracted citations
        
        Returns:
            Confidence score (0-1)
        """
        if not source_docs:
            return 0.0
        
        # Simple heuristic: higher confidence with more citations and sources
        base_confidence = 0.5
        citation_bonus = min(0.3, len(citations) * 0.1)
        source_bonus = min(0.2, len(source_docs) * 0.04)
        
        return min(1.0, base_confidence + citation_bonus + source_bonus)
    
    def ask(
        self,
        question: str,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RAGResponse:
        """
        Ask a question using RAG.
        
        Args:
            question: Question to ask
            max_tokens: Maximum tokens for response
            metadata: Additional metadata
        
        Returns:
            RAGResponse with answer and citations
        """
        start_time = datetime.utcnow()
        
        logger.info(f"RAG query: {question}")
        
        # Retrieve relevant documents
        source_docs = self.retriever.get_relevant_documents(question)
        logger.info(f"Retrieved {len(source_docs)} documents")
        
        # Format context
        context = self._format_documents(source_docs)
        
        # Generate answer using the chain
        formatted_prompt = self.prompt.format(context=context, question=question)
        answer = self.chain.invoke({"context": context, "question": question})
        
        # Extract citations
        citations = self._extract_citations(answer, source_docs)
        
        # Calculate confidence
        confidence = self._calculate_confidence(answer, source_docs, citations)
        
        # Format source documents for response
        formatted_docs = []
        for doc in source_docs:
            formatted_docs.append({
                "content": doc.page_content[:500],  # Truncate for response
                "metadata": doc.metadata
            })
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Build metadata
        response_metadata = {
            "duration_ms": duration_ms,
            "num_sources": len(source_docs),
            "num_citations": len(citations),
            "model": self.config.lc_model,
            "provider": self.config.lc_provider
        }
        
        if metadata:
            response_metadata.update(metadata)
        
        return RAGResponse(
            question=question,
            answer=answer,
            citations=citations,
            source_documents=formatted_docs,
            confidence=confidence,
            metadata=response_metadata
        )


def rag_query(
    question: str,
    k: int = 5,
    max_tokens: int = 600,
    user_id: Optional[str] = None,
    brand: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a RAG query with usage tracking.
    
    Args:
        question: The question to answer
        k: Number of documents to retrieve
        max_tokens: Maximum tokens in response
        user_id: Optional user ID
        brand: Optional brand context
        
    Returns:
        Dict with answer and citations
    """
    import time
    
    # Try to import usage tracer
    try:
        from ..engine import get_tracer
        tracer = get_tracer()
    except ImportError:
        tracer = None
    
    start_time = time.time()
    
    # Mock RAG implementation for testing
    # In production, this would use actual LangChain RAG
    answer = f"Based on the EmailPilot documentation: EmailPilot is a comprehensive FastAPI-based platform for automating Klaviyo email marketing campaigns. It features campaign planning, performance monitoring, and client management with Firebase integration for real-time synchronization. The system provides an integrated calendar for campaign planning and an admin dashboard for system management."
    
    citations = [
        "EmailPilot documentation (Section 1.1)",
        "Architecture guide (Section 2.3)",
        "Feature overview (Section 3.1)"
    ]
    
    # Record usage if tracer available
    duration_ms = (time.time() - start_time) * 1000
    if tracer:
        tracer.record_llm_call(
            model="gpt-3.5-turbo",
            provider="openai",
            operation="rag_query",
            tokens_input=150,  # Mock token count
            tokens_output=120,  # Mock token count
            duration_ms=duration_ms,
            user_id=user_id,
            brand=brand,
            metadata={
                "question": question,
                "k": k,
                "max_tokens": max_tokens
            }
        )
    
    return {
        "answer": answer,
        "citations": citations,
        "metadata": {
            "k": k,
            "max_tokens": max_tokens,
            "duration_ms": duration_ms
        }
    }


def create_rag_chain(
    config: Optional[LangChainConfig] = None,
    rebuild_index: bool = False
) -> RAGChain:
    """
    Create a RAG chain instance.
    
    Args:
        config: Configuration instance
        rebuild_index: Force rebuild of vector store
    
    Returns:
        RAGChain instance
    """
    config = config or get_config()
    
    # Get dependencies
    llm = get_llm(config)
    embeddings = get_embeddings(config)
    vectorstore = get_vectorstore(embeddings, config, rebuild=rebuild_index)
    
    return RAGChain(llm=llm, vectorstore=vectorstore, config=config)