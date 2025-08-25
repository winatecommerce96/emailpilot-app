"""
Tests for RAG chain functionality.

Tests document ingestion, retrieval, and answer generation with citations.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import json


class TestRAGChain(unittest.TestCase):
    """Test RAG chain operations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Create temporary directory for test data
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_docs_dir = Path(cls.temp_dir) / "test_docs"
        cls.test_docs_dir.mkdir(parents=True)
        
        # Create test documents
        doc1 = cls.test_docs_dir / "doc1.txt"
        doc1.write_text("EmailPilot is an automation platform for Klaviyo campaigns.")
        
        doc2 = cls.test_docs_dir / "doc2.md"
        doc2.write_text("# Features\n\nThe orchestrator manages multi-agent workflows.")
    
    def test_document_ingestion(self):
        """Test document loading and splitting."""
        from ..rag.ingest import DocumentIngester
        
        # Mock config
        config = MagicMock()
        config.seed_docs_path = self.test_docs_dir
        config.rag_chunk_size = 100
        config.rag_chunk_overlap = 20
        
        ingester = DocumentIngester(config)
        
        # Load documents
        docs = ingester.load_documents([self.test_docs_dir])
        
        self.assertGreater(len(docs), 0)
        self.assertEqual(len(docs), 2)  # We created 2 test documents
        
        # Split documents
        chunks = ingester.split_documents(docs)
        self.assertGreaterEqual(len(chunks), len(docs))
    
    @patch('langchain_openai.OpenAIEmbeddings')
    @patch('langchain_community.vectorstores.FAISS')
    def test_rag_chain_ask(self, mock_faiss, mock_embeddings):
        """Test RAG chain question answering."""
        from ..rag.chain import RAGChain
        
        # Mock vectorstore
        mock_vectorstore = MagicMock()
        mock_retriever = MagicMock()
        mock_vectorstore.as_retriever.return_value = mock_retriever
        
        # Mock retriever response
        mock_doc = MagicMock()
        mock_doc.page_content = "EmailPilot is an automation platform."
        mock_doc.metadata = {"source": "doc1.txt", "chunk_id": 0}
        mock_retriever.get_relevant_documents.return_value = [mock_doc]
        
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="EmailPilot is an automation platform for campaigns."
        )
        
        # Mock config
        config = MagicMock()
        config.rag_k_documents = 5
        
        # Create chain
        chain = RAGChain(mock_vectorstore, mock_llm, config)
        
        # Mock the chain's invoke method
        with patch.object(chain.chain, 'invoke') as mock_invoke:
            mock_invoke.return_value = {
                "result": "EmailPilot is an automation platform.",
                "source_documents": [mock_doc]
            }
            
            # Ask question
            response = chain.ask("What is EmailPilot?")
        
        # Assertions
        self.assertIsNotNone(response.answer)
        self.assertIn("EmailPilot", response.answer)
        self.assertGreater(len(response.source_documents), 0)
        self.assertGreater(len(response.citations), 0)
        self.assertIn("doc1.txt", response.citations[0])
    
    def test_citation_extraction(self):
        """Test citation extraction from source documents."""
        from ..rag.chain import RAGChain
        
        # Mock components
        mock_vectorstore = MagicMock()
        mock_llm = MagicMock()
        config = MagicMock()
        
        chain = RAGChain(mock_vectorstore, mock_llm, config)
        
        # Create mock documents
        mock_docs = [
            MagicMock(metadata={"source": "file1.md", "chunk_id": 0}),
            MagicMock(metadata={"source": "file2.txt", "line_start": 10, "line_end": 20})
        ]
        
        # Extract citations
        citations = chain._extract_citations("Test answer", mock_docs)
        
        self.assertEqual(len(citations), 2)
        self.assertIn("file1.md", citations[0])
        self.assertIn("file2.txt:10-20", citations[1])
    
    def test_evaluator(self):
        """Test RAG response evaluation."""
        from ..rag.evaluators import RAGEvaluator
        
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"score": 0.8, "reasoning": "Good faithfulness"}'
        )
        
        evaluator = RAGEvaluator(mock_llm)
        
        # Evaluate
        score = evaluator.evaluate(
            question="What is EmailPilot?",
            answer="EmailPilot is an automation platform.",
            source_documents=[{"content": "EmailPilot automation", "metadata": {}}]
        )
        
        self.assertIsNotNone(score.faithfulness)
        self.assertIsNotNone(score.relevance)
        self.assertIsNotNone(score.overall)
        self.assertGreater(score.overall, 0)


if __name__ == "__main__":
    unittest.main()