#!/usr/bin/env python3
"""
Quick validation script for LangChain Lab setup.
Run this to verify the module is properly installed and configured.
"""

import sys
import os
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    # Add multi-agent directory to path for imports
    import sys
    sys.path.insert(0, str(project_root / "multi-agent"))
    
    try:
        import langchain_lab
        from langchain_lab import check_dependencies, get_config
        print("✓ Core module imports successful")
    except ImportError as e:
        print(f"✗ Core module import failed: {e}")
        return False
    
    try:
        from langchain_lab.rag import ingest_documents, create_rag_chain
        print("✓ RAG module imports successful")
    except ImportError as e:
        print(f"✗ RAG module import failed: {e}")
        return False
    
    try:
        from langchain_lab.agents import get_agent_tools, create_agent
        print("✓ Agents module imports successful")
    except ImportError as e:
        print(f"✗ Agents module import failed: {e}")
        return False
    
    return True

def test_dependencies():
    """Test dependency availability."""
    print("\nTesting dependencies...")
    
    import sys
    sys.path.insert(0, str(project_root / "multi-agent"))
    from langchain_lab import check_dependencies
    deps = check_dependencies()
    
    required_deps = ["langchain", "httpx", "tiktoken"]
    optional_deps = ["faiss", "langchain_openai", "firestore"]
    
    all_ok = True
    for dep in required_deps:
        if deps.get(dep, False):
            print(f"✓ {dep}: available")
        else:
            print(f"✗ {dep}: MISSING (required)")
            all_ok = False
    
    for dep in optional_deps:
        if deps.get(dep, False):
            print(f"✓ {dep}: available")
        else:
            print(f"⚠ {dep}: missing (optional)")
    
    return all_ok

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        import sys
        sys.path.insert(0, str(project_root / "multi-agent"))
        from langchain_lab import get_config
        config = get_config()
        
        print(f"✓ Configuration loaded")
        print(f"  LLM Provider: {config.lc_provider}")
        print(f"  LLM Model: {config.lc_model}")
        print(f"  Embeddings Provider: {config.embeddings_provider}")
        print(f"  Vector Store: {config.vectorstore}")
        
        # Check for API keys
        missing_keys = config.validate_api_keys()
        if missing_keys:
            print(f"⚠ Missing API keys: {', '.join(missing_keys)}")
        else:
            print("✓ All required API keys present")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False

def test_cli():
    """Test CLI functionality."""
    print("\nTesting CLI...")
    
    try:
        import sys
        sys.path.insert(0, str(project_root / "multi-agent"))
        from langchain_lab.cli import main
        print("✓ CLI module can be imported")
        return True
    except ImportError as e:
        print(f"✗ CLI import failed: {e}")
        return False

def test_directories():
    """Test directory structure."""
    print("\nTesting directory structure...")
    
    base_dir = project_root / "multi-agent" / "langchain_lab"
    
    required_dirs = [
        "rag",
        "agents", 
        "data/seed_docs",
        "tests"
    ]
    
    all_ok = True
    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        if full_path.exists():
            print(f"✓ {dir_path}: exists")
        else:
            print(f"✗ {dir_path}: missing")
            all_ok = False
    
    # Check for seed documents
    seed_docs = base_dir / "data" / "seed_docs"
    if seed_docs.exists():
        doc_count = len(list(seed_docs.glob("*.md")))
        print(f"✓ Found {doc_count} seed documents")
    
    return all_ok

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("LANGCHAIN LAB VALIDATION")
    print("=" * 60)
    
    tests = [
        ("Directory Structure", test_directories),
        ("Module Imports", test_imports),
        ("Dependencies", test_dependencies), 
        ("Configuration", test_config),
        ("CLI Interface", test_cli),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All validation tests passed! LangChain Lab is ready to use.")
        print("\nNext steps:")
        print("1. Set up API keys in .env file")
        print("2. Run: python -m multi_agent.langchain_lab.cli rag.ingest --rebuild")
        print("3. Test: python -m multi_agent.langchain_lab.cli rag.ask -q 'What is EmailPilot?'")
        return 0
    else:
        print(f"\n❌ {total - passed} validation tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())