#!/usr/bin/env python3
"""
Test script to verify MCP models are accessible via API
"""

import requests
import json

def test_models_api():
    """Test the MCP models API endpoint"""
    
    # API endpoint - note the double path due to router configuration
    url = "http://localhost:8000/api/mcp/api/mcp/models"
    
    try:
        # Make request without authentication (public endpoint)
        response = requests.get(url)
        
        if response.status_code == 200:
            models = response.json()
            
            print(f"✅ Successfully fetched {len(models)} models from API\n")
            
            # Group models by provider
            providers = {}
            for model in models:
                provider = model.get('provider', 'unknown')
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(model)
            
            # Display models by provider
            for provider, provider_models in providers.items():
                print(f"\n{provider.upper()} Models ({len(provider_models)}):")
                print("-" * 50)
                for model in provider_models:
                    print(f"  • {model['display_name']}")
                    print(f"    Model: {model['model_name']}")
                    print(f"    Max Tokens: {model['max_tokens']:,}")
                    print(f"    Context Window: {model['context_window']:,}")
                    print(f"    Cost: ${model.get('input_cost_per_1k', 0):.4f}/1k in, ${model.get('output_cost_per_1k', 0):.4f}/1k out")
                    print(f"    Status: {'✅ Active' if model.get('enabled', False) else '❌ Inactive'}")
                    print()
            
            # Summary
            print("\n" + "=" * 50)
            print("SUMMARY:")
            print(f"Total Models: {len(models)}")
            print(f"Providers: {', '.join(providers.keys())}")
            
            # Check for specific new models
            new_models = [
                ("GPT-4o", "openai"),
                ("GPT-4o Mini", "openai"),
                ("Gemini 2.0 Flash", "gemini"),
                ("Gemini 1.5 Pro", "gemini"),
                ("Gemini 1.5 Flash", "gemini")
            ]
            
            print("\nNew Models Status:")
            for model_name, provider in new_models:
                found = any(
                    model_name in m['display_name'] 
                    for m in models 
                    if m.get('provider', '').lower() == provider.lower()
                )
                status = "✅ Available" if found else "❌ Not Found"
                print(f"  {model_name}: {status}")
            
        else:
            print(f"❌ Failed to fetch models. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_models_api()