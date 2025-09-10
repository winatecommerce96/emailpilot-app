#!/usr/bin/env python3
"""Test script to verify new LLM models are working"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up paths
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def test_models():
    """Test each model provider with the new models"""
    
    # Import the centralized LLM config
    from core.llm_models import LLM_MODELS, get_langchain_llm
    
    print("=" * 60)
    print("TESTING NEW LLM MODELS")
    print("=" * 60)
    
    # Test models to verify
    test_models = [
        ("gpt-4o-mini", "What is 2+2?"),
        ("gpt-4o", "What is the capital of France?"),
        ("claude-3-5-haiku-20241022", "Tell me a one-line joke"),
        ("claude-3-5-sonnet-20241022", "Write a haiku about coding"),
        ("gemini-1.5-flash-002", "What color is the sky?"),
        ("gemini-1.5-pro-002", "Explain quantum computing in one sentence")
    ]
    
    results = []
    
    for model_id, test_prompt in test_models:
        if model_id not in LLM_MODELS:
            print(f"❌ Model {model_id} not found in configuration")
            continue
            
        config = LLM_MODELS[model_id]
        print(f"\n Testing {config['name']} ({config['tier'].value})...")
        print(f"  Provider: {config['provider'].value}")
        print(f"  Test prompt: {test_prompt}")
        
        try:
            # Get the LangChain LLM instance
            llm = get_langchain_llm(model_id, temperature=0.5)
            
            # Test the model
            response = await llm.ainvoke(test_prompt)
            
            # Extract the response text
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            print(f"  ✅ Response: {response_text[:100]}...")
            results.append((model_id, True, response_text[:100]))
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append((model_id, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    working = sum(1 for _, success, _ in results if success)
    failed = sum(1 for _, success, _ in results if not success)
    
    print(f"✅ Working: {working}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    
    if failed > 0:
        print("\nFailed models:")
        for model_id, success, error in results:
            if not success:
                print(f"  - {model_id}: {error}")
    
    return results

if __name__ == "__main__":
    # Run the test
    results = asyncio.run(test_models())
    
    # Exit with error code if any tests failed
    if any(not success for _, success, _ in results):
        sys.exit(1)