"""
Tests for RAG pipeline.

Minimal tests to verify RAG functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from ..config import LangChainConfig
from ..rag.ingest import DocumentIngester
from ..rag.chain import RAGChain, RAGResponse


def test_document_ingester_initialization():
    """Test DocumentIngester can be initialized."""
    config = LangChainConfig(
        lc_provider="openai",
        lc_model="gpt-4o-mini",
        openai_api_key="test-key"
    )
    
    ingester = DocumentIngester(config)
    
    assert ingester.config == config
    assert ingester.splitter.chunk_size == config.rag_chunk_size
    assert ingester.splitter.chunk_overlap == config.rag_chunk_overlap


def test_document_loading():
    """Test document loading from test files."""
    config = LangChainConfig()
    ingester = DocumentIngester(config)
    
    # Create test document
    test_dir = Path(__file__).parent / "test_docs"
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "test.md"
    test_file.write_text("""# Test Document

This is a test document for RAG.

It contains multiple paragraphs.

## Section 1
Some content here.

## Section 2
More content here.""")
    
    try:
        # Load documents
        docs = ingester.load_documents([test_file])
        
        assert len(docs) > 0
        assert docs[0].page_content in test_file.read_text()
        assert docs[0].metadata["source"] == str(test_file)
    
    finally:
        # Cleanup
        test_file.unlink()
        test_dir.rmdir()


def test_document_splitting():
    """Test document splitting into chunks."""
    from langchain_core.documents import Document
    
    config = LangChainConfig(
        rag_chunk_size=100,
        rag_chunk_overlap=20
    )
    ingester = DocumentIngester(config)
    
    # Create test document
    doc = Document(
        page_content="This is a test. " * 50,  # Long document
        metadata={"source": "test"}
    )
    
    # Split document
    chunks = ingester.split_documents([doc])
    
    assert len(chunks) > 1
    assert all(len(chunk.page_content) <= 100 * 1.5 for chunk in chunks)
    assert all(chunk.metadata.get("chunk_id") is not None for chunk in chunks)


@patch("langchain_openai.ChatOpenAI")
@patch("langchain_openai.OpenAIEmbeddings")
def test_rag_chain_initialization(mock_embeddings, mock_llm):
    """Test RAG chain can be initialized."""
    config = LangChainConfig(
        lc_provider="openai",
        openai_api_key="test-key"
    )
    
    # Mock dependencies
    mock_llm_instance = Mock()
    mock_embeddings_instance = Mock()
    mock_llm.return_value = mock_llm_instance
    mock_embeddings.return_value = mock_embeddings_instance
    
    # Mock vectorstore
    with patch("langchain_community.vectorstores.FAISS") as mock_faiss:
        mock_vectorstore = Mock()
        mock_retriever = Mock()
        mock_vectorstore.as_retriever.return_value = mock_retriever
        mock_faiss.from_texts.return_value = mock_vectorstore
        
        # Create chain
        chain = RAGChain(
            llm=mock_llm_instance,
            vectorstore=mock_vectorstore,
            config=config
        )
        
        assert chain.llm == mock_llm_instance
        assert chain.vectorstore == mock_vectorstore
        assert chain.retriever == mock_retriever


def test_rag_response_structure():
    """Test RAGResponse dataclass structure."""
    from ..rag.chain import Citation
    
    response = RAGResponse(
        question="Test question",
        answer="Test answer",
        citations=[
            Citation(
                source="test.md",
                text="Test citation",
                confidence=0.9
            )
        ],
        source_documents=[
            {"content": "Test doc", "metadata": {"source": "test.md"}}
        ],
        confidence=0.85,
        metadata={"duration_ms": 100}
    )
    
    # Test to_dict conversion
    result = response.to_dict()
    
    assert result["question"] == "Test question"
    assert result["answer"] == "Test answer"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["source"] == "test.md"
    assert result["confidence"] == 0.85


def test_citation_extraction():
    """Test citation extraction from answer."""
    config = LangChainConfig()
    
    with patch("langchain_openai.ChatOpenAI"), \
         patch("langchain_openai.OpenAIEmbeddings"), \
         patch("langchain_community.vectorstores.FAISS"):
        
        chain = RAGChain(config=config)
        
        # Test answer with citations
        answer = "According to the data [Source: report.md], the metrics show improvement."
        source_docs = [
            Mock(
                page_content="The metrics show improvement in Q3.",
                metadata={"source": "report.md"}
            )
        ]
        
        citations = chain._extract_citations(answer, source_docs)
        
        assert len(citations) > 0
        assert any("report.md" in c.source for c in citations)


@pytest.mark.integration
@pytest.mark.skipif(
    not Path(__file__).parent.parent.joinpath(".env").exists(),
    reason="No .env file with API keys"
)
def test_rag_end_to_end():
    """Integration test for complete RAG pipeline."""
    from ..rag import ingest_documents, create_rag_chain
    
    # Create test documents
    test_dir = Path(__file__).parent / "test_docs"
    test_dir.mkdir(exist_ok=True)
    
    doc1 = test_dir / "orchestrator.md"
    doc1.write_text("""# Orchestrator Service

The orchestrator service coordinates multi-agent workflows.
It uses LangGraph for state management and checkpointing.""")
    
    doc2 = test_dir / "emailpilot.md"
    doc2.write_text("""# EmailPilot Platform

EmailPilot is a Klaviyo automation platform.
It provides campaign management and performance monitoring.""")
    
    try:
        # Ingest documents
        result = ingest_documents(
            source_paths=[str(test_dir)],
            rebuild=True
        )
        
        assert result["status"] == "success"
        assert result["stats"]["total_files"] >= 2
        
        # Create RAG chain and ask question
        chain = create_rag_chain()
        response = chain.ask(
            "What does the orchestrator service do?",
            max_tokens=100
        )
        
        assert response.answer
        assert "orchestrator" in response.answer.lower()
        assert len(response.source_documents) > 0
    
    finally:
        # Cleanup
        doc1.unlink()
        doc2.unlink()
        test_dir.rmdir()