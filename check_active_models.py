#!/usr/bin/env python3
"""
Check active MCP models directly from the database
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.mcp_client import MCPModelConfig
# Import other models to avoid circular dependency
from app.models.client import Client
from app.models.calendar import CalendarEvent
from app.models.goal import Goal
from app.models.report import Report

def check_models():
    """Check all MCP models in the database"""
    
    db = SessionLocal()
    try:
        # Get all models
        models = db.query(MCPModelConfig).filter(
            MCPModelConfig.enabled == True
        ).order_by(
            MCPModelConfig.provider,
            MCPModelConfig.display_name
        ).all()
        
        print("=" * 70)
        print("🤖 ACTIVE MCP MODELS IN DATABASE")
        print("=" * 70)
        
        # Group by provider
        providers = {}
        for model in models:
            if model.provider not in providers:
                providers[model.provider] = []
            providers[model.provider].append(model)
        
        # Display by provider
        for provider, provider_models in providers.items():
            print(f"\n{provider.upper()} ({len(provider_models)} models)")
            print("-" * 50)
            
            for model in provider_models:
                print(f"\n📌 {model.display_name}")
                print(f"   Model Name: {model.model_name}")
                print(f"   Max Tokens: {model.max_tokens:,}")
                print(f"   Context Window: {model.context_window:,} tokens")
                
                # Pricing
                if model.input_cost_per_1k or model.output_cost_per_1k:
                    print(f"   💰 Pricing:")
                    print(f"      Input: ${model.input_cost_per_1k:.5f} per 1k tokens")
                    print(f"      Output: ${model.output_cost_per_1k:.5f} per 1k tokens")
                else:
                    print(f"   💰 Pricing: FREE")
                
                # Features
                features = []
                if model.supports_functions:
                    features.append("Functions")
                if model.supports_vision:
                    features.append("Vision")
                if model.supports_streaming:
                    features.append("Streaming")
                if features:
                    print(f"   ✨ Features: {', '.join(features)}")
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✅ Total Active Models: {len(models)}")
        print(f"📦 Providers: {', '.join(providers.keys())}")
        
        # Highlight new models
        print("\n🆕 LATEST MODELS AVAILABLE:")
        print("-" * 50)
        
        # Check for specific new models
        new_models_to_check = [
            ("GPT-4o (Latest)", "openai", "Most capable OpenAI model, multimodal"),
            ("GPT-4o Mini", "openai", "Fast and cost-effective"),
            ("Gemini 2.0 Flash (Experimental)", "gemini", "Free experimental model"),
            ("Gemini 1.5 Pro (Latest)", "gemini", "2M token context window"),
            ("Gemini 1.5 Flash", "gemini", "1M token context, very fast")
        ]
        
        for display_name, provider, description in new_models_to_check:
            found = any(
                display_name == m.display_name 
                for m in models 
                if m.provider.lower() == provider.lower()
            )
            if found:
                print(f"✅ {display_name}")
                print(f"   {description}")
        
        print("\n" + "=" * 70)
        print("💡 To use these models:")
        print("   1. Go to the MCP Management section in the Admin Dashboard")
        print("   2. Create or edit an MCP client")
        print("   3. Add the required API keys:")
        print("      - OpenAI API Key for GPT models")
        print("      - Gemini API Key for Gemini models")
        print("   4. Select your preferred default model")
        print("=" * 70)
        
    finally:
        db.close()

if __name__ == "__main__":
    check_models()