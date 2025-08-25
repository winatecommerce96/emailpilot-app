"""
RAG chain implementation for question-answering with citations.

Provides retrieval-augmented generation chains that return answers
grounded in source documents with proper citations.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Structured response from RAG chain."""
    answer: str
    source_documents: List[Dict[str, Any]]
    citations: List[str]
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "answer": self.answer,
            "source_documents": self.source_documents,
            "citations": self.citations,
            "confidence": self.confidence
        }


class RAGChain:
    """Retrieval-augmented generation chain with citations."""
    
    SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context.

IMPORTANT RULES:
1. Answer ONLY based on the information in the context documents
2. ALWAYS cite your sources using [filename:line_range] format
3. If the context doesn't contain enough information, say "I don't have enough information to answer this question"
4. Be specific and accurate in your citations
5. If multiple documents support a claim, cite all relevant sources

Context documents:
{context}

Question: {question}

Answer with citations:"""
    
    def __init__(
        self,
        vectorstore: Any,
        llm: Any,
        config: Optional[Any] = None
    ):
        """
        Initialize RAG chain.
        
        Args:
            vectorstore: Vector store for retrieval
            llm: Language model for generation
            config: LangChainConfig instance
        """
        if config is None:
            from ..config import get_config
            config = get_config()
        
        self.config = config
        self.vectorstore = vectorstore
        self.llm = llm
        
        # Create retriever
        self.retriever = vectorstore.as_retriever(
            search_kwargs={"k": config.rag_k_documents}
        )
        
        # Create prompt
        self.prompt = PromptTemplate(
            template=self.SYSTEM_PROMPT,
            input_variables=["context", "question"]
        )
        
        # Build the chain
        self.chain = self._build_chain()
    
    def _build_chain(self) -> Any:
        """Build the retrieval QA chain."""
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs={
                "prompt": self.prompt,
                "verbose": False
            }
        )
    
    def _extract_citations(
        self,
        answer: str,
        source_docs: List[Any]
    ) -> List[str]:
        """
        Extract citations from answer and source documents.
        
        Args:
            answer: Generated answer
            source_docs: Retrieved source documents
        
        Returns:
            List of citation strings
        """
        citations = []
        
        for i, doc in enumerate(source_docs):
            source = doc.metadata.get("source", f"doc_{i}")
            
            # Try to extract line numbers if available
            if "line_start" in doc.metadata and "line_end" in doc.metadata:
                line_range = f"{doc.metadata['line_start']}-{doc.metadata['line_end']}"
            else:
                # Estimate based on chunk position
                chunk_id = doc.metadata.get("chunk_id", i)
                line_range = f"chunk_{chunk_id}"
            
            citation = f"[{source}:{line_range}]"
            citations.append(citation)
        
        return citations
    
    def ask(
        self,
        question: str,
        max_tokens: Optional[int] = None,
        chat_history: Optional[List[tuple]] = None
    ) -> RAGResponse:
        """
        Ask a question and get an answer with citations.
        
        Args:
            question: Question to answer
            max_tokens: Maximum tokens in response
            chat_history: Optional conversation history
        
        Returns:
            RAGResponse with answer and citations
        """
        try:
            # Run the chain
            result = self.chain.invoke({"query": question})
            
            # Extract components
            answer = result.get("result", "")
            source_docs = result.get("source_documents", [])
            
            # Extract citations
            citations = self._extract_citations(answer, source_docs)
            
            # Add citations to answer if not already present
            if citations and not any(c in answer for c in citations):
                answer += "\n\nSources: " + ", ".join(citations)
            
            # Convert source documents to serializable format
            source_documents = []
            for doc in source_docs:
                source_documents.append({
                    "content": doc.page_content[:500],  # Truncate for readability
                    "metadata": doc.metadata
                })
            
            # Calculate confidence (simple heuristic based on number of sources)
            confidence = min(1.0, len(source_docs) * 0.2) if source_docs else 0.0
            
            return RAGResponse(
                answer=answer,
                source_documents=source_documents,
                citations=citations,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error in RAG chain: {e}")
            return RAGResponse(
                answer=f"Error processing question: {str(e)}",
                source_documents=[],
                citations=[],
                confidence=0.0
            )


def create_rag_chain(
    vectorstore: Optional[Any] = None,
    llm: Optional[Any] = None,
    config: Optional[Any] = None
) -> RAGChain:
    """
    Factory function to create a RAG chain.
    
    Args:
        vectorstore: Vector store (will load if not provided)
        llm: Language model (will create if not provided)
        config: Configuration instance
    
    Returns:
        Configured RAGChain instance
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    # Get or create LLM
    if llm is None:
        from ..deps import get_llm
        llm = get_llm(config)
    
    # Get or load vector store
    if vectorstore is None:
        from ..deps import get_embeddings, get_vectorstore
        embeddings = get_embeddings(config)
        vectorstore = get_vectorstore(embeddings, config)
        
        if vectorstore is None:
            raise ValueError(
                "No vector store found. Run 'rag.ingest' first to build the index."
            )
    
    return RAGChain(vectorstore, llm, config)