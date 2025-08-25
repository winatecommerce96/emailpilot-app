"""
Document ingestion for RAG system.

Loads documents from seed_docs and optional external sources,
splits them into chunks, and builds/updates the vector store.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredMarkdownLoader,
    DirectoryLoader
)

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Statistics from document ingestion."""
    total_files: int = 0
    total_chunks: int = 0
    total_chars: int = 0
    file_types: Dict[str, int] = None
    
    def __post_init__(self):
        if self.file_types is None:
            self.file_types = {}


class DocumentIngester:
    """Handles document loading, splitting, and vector store creation."""
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the document ingester.
        
        Args:
            config: LangChainConfig instance (will create if not provided)
        """
        if config is None:
            from ..config import get_config
            config = get_config()
        
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.rag_chunk_size,
            chunk_overlap=config.rag_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
    def load_documents(self, paths: Optional[List[Path]] = None) -> List[Document]:
        """
        Load documents from specified paths.
        
        Args:
            paths: List of paths to load from (defaults to seed_docs)
        
        Returns:
            List of loaded documents
        """
        if paths is None:
            paths = [self.config.seed_docs_path]
            
            # Also load from ../docs if it exists
            docs_path = self.config.seed_docs_path.parent.parent.parent / "docs"
            if docs_path.exists():
                paths.append(docs_path)
                logger.info(f"Including documents from {docs_path}")
        
        all_docs = []
        stats = IngestionStats()
        
        for base_path in paths:
            if not base_path.exists():
                logger.warning(f"Path does not exist: {base_path}")
                continue
            
            # Load different file types
            for pattern, loader_cls in [
                ("*.txt", TextLoader),
                ("*.md", UnstructuredMarkdownLoader),
                ("*.mdx", UnstructuredMarkdownLoader),
            ]:
                try:
                    loader = DirectoryLoader(
                        str(base_path),
                        glob=pattern,
                        loader_cls=loader_cls,
                        recursive=True,
                        show_progress=True
                    )
                    docs = loader.load()
                    
                    # Add source metadata
                    for doc in docs:
                        # Make path relative for cleaner citations
                        source_path = Path(doc.metadata.get("source", ""))
                        if source_path.is_absolute():
                            try:
                                rel_path = source_path.relative_to(
                                    Path("/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app")
                                )
                                doc.metadata["source"] = str(rel_path)
                            except ValueError:
                                pass  # Keep absolute if not relative to project
                        
                        # Track file type
                        ext = source_path.suffix
                        stats.file_types[ext] = stats.file_types.get(ext, 0) + 1
                    
                    all_docs.extend(docs)
                    stats.total_files += len(docs)
                    
                except Exception as e:
                    logger.warning(f"Error loading {pattern} files from {base_path}: {e}")
        
        logger.info(f"Loaded {stats.total_files} documents from {len(paths)} paths")
        logger.info(f"File types: {stats.file_types}")
        
        return all_docs
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks for embedding.
        
        Args:
            documents: List of documents to split
        
        Returns:
            List of document chunks
        """
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["chunk_size"] = len(chunk.page_content)
        
        logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
        
        return chunks
    
    def build_vectorstore(
        self,
        chunks: List[Document],
        embeddings: Any,
        rebuild: bool = False
    ) -> Any:
        """
        Build or update the vector store.
        
        Args:
            chunks: Document chunks to embed
            embeddings: Embeddings instance
            rebuild: Whether to rebuild from scratch
        
        Returns:
            VectorStore instance
        """
        from ..deps import get_vectorstore
        
        if self.config.vectorstore == "faiss":
            from langchain_community.vectorstores import FAISS
            
            store_path = self.config.vectorstore_path
            
            if not rebuild and store_path.exists():
                logger.info(f"Loading existing FAISS index from {store_path}")
                vectorstore = FAISS.load_local(
                    str(store_path),
                    embeddings,
                    allow_dangerous_deserialization=True
                )
                
                # Add new chunks
                if chunks:
                    logger.info(f"Adding {len(chunks)} chunks to existing index")
                    vectorstore.add_documents(chunks)
            else:
                if rebuild and store_path.exists():
                    logger.info(f"Rebuilding index (removing {store_path})")
                    import shutil
                    shutil.rmtree(store_path, ignore_errors=True)
                
                logger.info(f"Creating new FAISS index with {len(chunks)} chunks")
                vectorstore = FAISS.from_documents(chunks, embeddings)
            
            # Save the index
            store_path.parent.mkdir(parents=True, exist_ok=True)
            vectorstore.save_local(str(store_path))
            logger.info(f"Saved FAISS index to {store_path}")
            
        elif self.config.vectorstore == "chroma":
            from langchain_community.vectorstores import Chroma
            
            persist_dir = str(self.config.vectorstore_path).replace(".faiss", ".chroma")
            
            if rebuild:
                logger.info(f"Rebuilding Chroma index at {persist_dir}")
                import shutil
                shutil.rmtree(persist_dir, ignore_errors=True)
            
            vectorstore = Chroma.from_documents(
                chunks,
                embeddings,
                persist_directory=persist_dir
            )
            logger.info(f"Created/updated Chroma index at {persist_dir}")
        
        else:
            raise ValueError(f"Unsupported vector store: {self.config.vectorstore}")
        
        return vectorstore


def ingest_documents(
    rebuild: bool = False,
    source_paths: Optional[List[str]] = None,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Main ingestion pipeline - loads, splits, and indexes documents.
    
    Args:
        rebuild: Whether to rebuild the index from scratch
        source_paths: Additional source paths to include
        config: LangChainConfig instance
    
    Returns:
        Dictionary with ingestion statistics and vectorstore
    """
    from ..deps import get_embeddings
    
    if config is None:
        from ..config import get_config
        config = get_config()
    
    ingester = DocumentIngester(config)
    
    # Parse source paths
    paths = None
    if source_paths:
        paths = [Path(p) for p in source_paths]
    
    # Load documents
    logger.info("Loading documents...")
    documents = ingester.load_documents(paths)
    
    if not documents:
        logger.warning("No documents found to ingest")
        return {
            "status": "error",
            "message": "No documents found",
            "stats": IngestionStats().__dict__
        }
    
    # Split documents
    logger.info("Splitting documents into chunks...")
    chunks = ingester.split_documents(documents)
    
    # Get embeddings
    logger.info("Initializing embeddings...")
    embeddings = get_embeddings(config)
    
    # Build vector store
    logger.info("Building vector store...")
    vectorstore = ingester.build_vectorstore(chunks, embeddings, rebuild=rebuild)
    
    # Compute statistics
    stats = IngestionStats(
        total_files=len(documents),
        total_chunks=len(chunks),
        total_chars=sum(len(c.page_content) for c in chunks)
    )
    
    # Count file types
    for doc in documents:
        ext = Path(doc.metadata.get("source", "")).suffix
        stats.file_types[ext] = stats.file_types.get(ext, 0) + 1
    
    logger.info(f"Ingestion complete: {stats}")
    
    return {
        "status": "success",
        "stats": stats.__dict__,
        "vectorstore": vectorstore
    }