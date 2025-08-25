#!/usr/bin/env python3
"""
RAG (Retrieval Augmented Generation) Setup Script for LangChain
This script initializes the vector store and ingests initial documents
"""

import os
import sys
from pathlib import Path

# Add multi-agent to path
sys.path.insert(0, "multi-agent")

def setup_rag():
    """Initialize RAG system with vector store and documents."""
    
    print("🔧 Setting up RAG for LangChain...")
    
    # Set environment variables
    os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"
    os.environ["USE_SECRET_MANAGER"] = "true"
    
    try:
        from integrations.langchain_core.rag.ingest import ingest_documents
        from integrations.langchain_core.config import get_config
        from integrations.langchain_core.deps import get_vectorstore
        
        config = get_config()
        
        # Create vector store directory if it doesn't exist
        vectorstore_path = Path(config.vectorstore_path)
        vectorstore_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Vector store directory created at: {vectorstore_path}")
        
        # Get initial documents to ingest
        docs_to_ingest = [
            "README.md",
            "CLAUDE.md",
            "docs/AI_ORCHESTRATOR_MIGRATION_GUIDE.md",
            "docs/UI_DEVELOPMENT_GUIDE.md",
            "multi-agent/integrations/langchain_core/README.md",
            "multi-agent/integrations/langchain_core/INTEGRATION_COMPLETE.md"
        ]
        
        # Ingest documents
        print("\n📚 Ingesting documents...")
        ingested_count = 0
        
        for doc_path in docs_to_ingest:
            if Path(doc_path).exists():
                print(f"  • Ingesting {doc_path}...")
                try:
                    result = ingest_documents([doc_path])
                    if result:
                        ingested_count += 1
                        print(f"    ✓ Success")
                except Exception as e:
                    print(f"    ✗ Failed: {e}")
            else:
                print(f"  • Skipping {doc_path} (not found)")
        
        print(f"\n✅ RAG setup complete! Ingested {ingested_count} documents.")
        
        # Test the vector store
        print("\n🧪 Testing vector store...")
        try:
            vectorstore = get_vectorstore(config)
            # Try a simple similarity search
            results = vectorstore.similarity_search("EmailPilot", k=2)
            if results:
                print(f"✓ Vector store is working! Found {len(results)} similar documents.")
            else:
                print("⚠️ Vector store is empty. You may need to ingest more documents.")
        except Exception as e:
            print(f"✗ Vector store test failed: {e}")
            
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\nMake sure you have installed all dependencies:")
        print("  pip install langchain langchain-community faiss-cpu sentence-transformers")
        return False
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False


def create_rag_query_script():
    """Create a simple script to query the RAG system."""
    
    script_content = '''#!/usr/bin/env python3
"""
Query the RAG system
Usage: python query_rag.py "Your question here"
"""

import sys
import os

# Add multi-agent to path
sys.path.insert(0, "multi-agent")

def query_rag(question):
    """Query the RAG system with a question."""
    
    # Set environment
    os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"
    os.environ["USE_SECRET_MANAGER"] = "true"
    
    from integrations.langchain_core.rag.chain import rag_query
    
    try:
        result = rag_query(question, k=5, max_tokens=1000)
        
        print(f"\\n📝 Question: {question}")
        print(f"\\n💡 Answer:\\n{result.answer}")
        
        if result.citations:
            print(f"\\n📚 Sources:")
            for citation in result.citations:
                print(f"  • {citation.source}")
                if citation.text:
                    print(f"    → {citation.text[:100]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query_rag.py \\"Your question here\\"")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    query_rag(question)
'''
    
    with open("query_rag.py", "w") as f:
        f.write(script_content)
    
    os.chmod("query_rag.py", 0o755)
    print("\n📝 Created query_rag.py script for testing RAG queries")


if __name__ == "__main__":
    success = setup_rag()
    if success:
        create_rag_query_script()
        print("\n🎯 Next steps:")
        print("  1. Start MCP servers: ./start_mcp_servers.sh")
        print("  2. Test RAG query: python query_rag.py 'What is EmailPilot?'")
        print("  3. Start main app: uvicorn main_firestore:app --reload --port 8000 --host localhost")
    else:
        sys.exit(1)