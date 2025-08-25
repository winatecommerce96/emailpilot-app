"""
Document ingestion for RAG pipeline.

Loads documents, splits them into chunks, and builds/updates vector store.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    DirectoryLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import LangChainConfig, get_config
from ..deps import get_embeddings, get_vectorstore

logger = logging.getLogger(__name__)


class DocumentIngester:
    """Handles document loading, splitting, and indexing."""
    
    def __init__(self, config: Optional[LangChainConfig] = None):
        """
        Initialize ingester.
        
        Args:
            config: Configuration instance
        """
        self.config = config or get_config()
        self.embeddings = None
        self.vectorstore = None
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.rag_chunk_size,
            chunk_overlap=self.config.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len
        )
    
    def load_documents(self, paths: Optional[List[Path]] = None) -> List[Document]:
        """
        Load documents from specified paths or default locations.
        
        Args:
            paths: Optional list of paths to load from
        
        Returns:
            List of loaded documents
        """
        if paths is None:
            # Default paths
            base_path = Path(__file__).parent.parent
            paths = [
                base_path / "data" / "seed_docs",  # Seed documents
                base_path.parent.parent.parent / "docs",  # Project docs
                base_path.parent.parent / "README.md",  # Multi-agent README
                base_path.parent.parent.parent / "README.md"  # Main README
            ]
        
        all_docs = []
        
        for path in paths:
            if not path.exists():
                logger.warning(f"Path does not exist: {path}")
                continue
            
            if path.is_file():
                # Load single file
                try:
                    if path.suffix == ".md":
                        loader = UnstructuredMarkdownLoader(str(path))
                    else:
                        loader = TextLoader(str(path))
                    
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["source"] = str(path)
                        doc.metadata["file_type"] = path.suffix
                        doc.metadata["ingested_at"] = datetime.utcnow().isoformat()
                    
                    all_docs.extend(docs)
                    logger.info(f"Loaded {len(docs)} documents from {path}")
                
                except Exception as e:
                    logger.error(f"Failed to load {path}: {e}")
            
            elif path.is_dir():
                # Load directory
                try:
                    # Load markdown files
                    md_loader = DirectoryLoader(
                        str(path),
                        glob="**/*.md",
                        loader_cls=UnstructuredMarkdownLoader,
                        show_progress=True
                    )
                    md_docs = md_loader.load()
                    
                    # Load text files
                    txt_loader = DirectoryLoader(
                        str(path),
                        glob="**/*.txt",
                        loader_cls=TextLoader,
                        show_progress=True
                    )
                    txt_docs = txt_loader.load()
                    
                    docs = md_docs + txt_docs
                    
                    for doc in docs:
                        doc.metadata["source_dir"] = str(path)
                        doc.metadata["ingested_at"] = datetime.utcnow().isoformat()
                    
                    all_docs.extend(docs)
                    logger.info(f"Loaded {len(docs)} documents from directory {path}")
                
                except Exception as e:
                    logger.error(f"Failed to load directory {path}: {e}")
        
        logger.info(f"Total documents loaded: {len(all_docs)}")
        return all_docs
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of documents to split
        
        Returns:
            List of document chunks
        """
        logger.info(f"Splitting {len(documents)} documents")
        
        chunks = self.splitter.split_documents(documents)
        
        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["chunk_size"] = len(chunk.page_content)
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    def build_vectorstore(
        self,
        chunks: List[Document],
        embeddings: Optional[Any] = None,
        rebuild: bool = False
    ) -> Any:
        """
        Build or update vector store with chunks.
        
        Args:
            chunks: Document chunks to index
            embeddings: Embeddings instance (creates if not provided)
            rebuild: Force rebuild of index
        
        Returns:
            VectorStore instance
        """
        if embeddings is None:
            embeddings = get_embeddings(self.config)
        
        self.embeddings = embeddings
        
        if rebuild or self.vectorstore is None:
            # Create new vector store
            logger.info("Building new vector store")
            self.vectorstore = get_vectorstore(
                embeddings=embeddings,
                config=self.config,
                rebuild=rebuild
            )
            
            if chunks:
                # Add chunks to store
                texts = [chunk.page_content for chunk in chunks]
                metadatas = [chunk.metadata for chunk in chunks]
                
                self.vectorstore.add_texts(
                    texts=texts,
                    metadatas=metadatas
                )
                
                # Persist if FAISS
                if self.config.vectorstore == "faiss":
                    index_path = self.config.vectorstore_path / "index"
                    self.vectorstore.save_local(str(index_path))
                    logger.info(f"Saved FAISS index to {index_path}")
        
        else:
            # Update existing store
            logger.info("Updating existing vector store")
            
            if chunks:
                texts = [chunk.page_content for chunk in chunks]
                metadatas = [chunk.metadata for chunk in chunks]
                
                self.vectorstore.add_texts(
                    texts=texts,
                    metadatas=metadatas
                )
                
                # Persist if FAISS
                if self.config.vectorstore == "faiss":
                    index_path = self.config.vectorstore_path / "index"
                    self.vectorstore.save_local(str(index_path))
                    logger.info(f"Updated FAISS index at {index_path}")
        
        return self.vectorstore
    
    def ingest(
        self,
        paths: Optional[List[Path]] = None,
        rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Complete ingestion pipeline.
        
        Args:
            paths: Optional paths to ingest from
            rebuild: Force rebuild of index
        
        Returns:
            Ingestion statistics
        """
        start_time = datetime.utcnow()
        
        # Load documents
        documents = self.load_documents(paths)
        
        if not documents:
            logger.warning("No documents loaded")
            return {
                "status": "no_documents",
                "message": "No documents found to ingest",
                "stats": {
                    "total_files": 0,
                    "total_chunks": 0,
                    "total_chars": 0
                }
            }
        
        # Split into chunks
        chunks = self.split_documents(documents)
        
        # Build vector store
        self.build_vectorstore(chunks, rebuild=rebuild)
        
        # Calculate statistics
        total_chars = sum(len(chunk.page_content) for chunk in chunks)
        file_types = set(doc.metadata.get("file_type", "unknown") for doc in documents)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        stats = {
            "total_files": len(documents),
            "total_chunks": len(chunks),
            "total_chars": total_chars,
            "file_types": list(file_types),
            "duration_seconds": duration,
            "chunks_per_file": len(chunks) / len(documents) if documents else 0,
            "avg_chunk_size": total_chars / len(chunks) if chunks else 0
        }
        
        logger.info(f"Ingestion complete: {stats}")
        
        return {
            "status": "success",
            "message": f"Ingested {len(documents)} documents into {len(chunks)} chunks",
            "stats": stats
        }


def ingest_documents(
    rebuild: bool = False,
    source_paths: Optional[List[str]] = None,
    config: Optional[LangChainConfig] = None
) -> Dict[str, Any]:
    """
    Convenience function for document ingestion.
    
    Args:
        rebuild: Force rebuild of index
        source_paths: Optional list of source paths
        config: Configuration instance
    
    Returns:
        Ingestion statistics
    """
    ingester = DocumentIngester(config)
    
    paths = None
    if source_paths:
        paths = [Path(p) for p in source_paths]
    
    return ingester.ingest(paths=paths, rebuild=rebuild)