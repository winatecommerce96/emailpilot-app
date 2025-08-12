#!/usr/bin/env python3
"""
Script to populate MCP model configurations in the database
Adds the latest Google Gemini and OpenAI models
"""

import os
import sys
from pathlib import Path
import asyncio
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_models():
    """Populate the database with the latest AI models"""
    
    # Import after path is set
    from app.core.database import SessionLocal, engine, Base
    
    # Import all models to avoid circular dependencies
    from app.models.client import Client
    from app.models.calendar import CalendarEvent
    from app.models.goal import Goal
    from app.models.report import Report
    from app.models.mcp_client import MCPClient, MCPModelConfig, MCPUsage
    from app.services.mcp_service import MCPServiceManager
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Initialize MCP service to get model configs
        mcp_service = MCPServiceManager()
        model_configs = mcp_service.model_configs
        
        added_count = 0
        updated_count = 0
        
        # Iterate through all providers and models
        for provider_name, provider_config in model_configs.items():
            for model_key, model_info in provider_config.get("models", {}).items():
                # Check if model already exists
                existing_model = db.query(MCPModelConfig).filter(
                    MCPModelConfig.provider == provider_name,
                    MCPModelConfig.model_name == model_info["name"]
                ).first()
                
                if existing_model:
                    # Update existing model
                    existing_model.display_name = model_info["display_name"]
                    existing_model.max_tokens = model_info["max_tokens"]
                    existing_model.context_window = model_info["context_window"]
                    existing_model.input_cost_per_1k = model_info.get("input_cost_per_1k", 0)
                    existing_model.output_cost_per_1k = model_info.get("output_cost_per_1k", 0)
                    existing_model.enabled = True  # Ensure it's enabled
                    existing_model.deprecated = False
                    updated_count += 1
                    logger.info(f"Updated model: {model_info['display_name']} ({provider_name})")
                else:
                    # Create new model
                    new_model = MCPModelConfig(
                        provider=provider_name,
                        model_name=model_info["name"],
                        display_name=model_info["display_name"],
                        supports_functions=True,
                        supports_vision="vision" in model_key.lower() or "vision" in model_info["name"].lower(),
                        supports_streaming=True,
                        max_tokens=model_info["max_tokens"],
                        context_window=model_info["context_window"],
                        input_cost_per_1k=model_info.get("input_cost_per_1k", 0),
                        output_cost_per_1k=model_info.get("output_cost_per_1k", 0),
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True,
                        deprecated=False
                    )
                    db.add(new_model)
                    added_count += 1
                    logger.info(f"Added new model: {model_info['display_name']} ({provider_name})")
        
        # Commit changes
        db.commit()
        
        logger.info(f"\n✅ Model population completed!")
        logger.info(f"   Added: {added_count} new models")
        logger.info(f"   Updated: {updated_count} existing models")
        
        # List all active models
        logger.info("\n📋 Active Models in Database:")
        all_models = db.query(MCPModelConfig).filter(
            MCPModelConfig.enabled == True
        ).order_by(MCPModelConfig.provider, MCPModelConfig.display_name).all()
        
        current_provider = None
        for model in all_models:
            if model.provider != current_provider:
                current_provider = model.provider
                logger.info(f"\n{current_provider.upper()}:")
            logger.info(f"  - {model.display_name} ({model.model_name})")
            logger.info(f"    Context: {model.context_window:,} tokens, Max output: {model.max_tokens:,} tokens")
            logger.info(f"    Cost: ${model.input_cost_per_1k:.4f}/1k in, ${model.output_cost_per_1k:.4f}/1k out")
        
        # Special notice for new models
        logger.info("\n🆕 Latest Models Added:")
        logger.info("  OpenAI:")
        logger.info("    - GPT-4o (Latest) - Most capable, multimodal")
        logger.info("    - GPT-4o Mini - Cost-effective, fast")
        logger.info("  Google Gemini:")
        logger.info("    - Gemini 2.0 Flash (Experimental) - Free, cutting-edge")
        logger.info("    - Gemini 1.5 Pro - 2M token context window")
        logger.info("    - Gemini 1.5 Flash - Fast, 1M token context")
        
        # Check if API keys are needed
        logger.info("\n🔑 API Keys Required:")
        logger.info("  To use these models, ensure you have configured:")
        logger.info("  - OpenAI API Key: For GPT-4o, GPT-4o Mini, etc.")
        logger.info("  - Gemini API Key: For Gemini 1.5 Pro, Gemini 2.0 Flash, etc.")
        logger.info("  - These can be configured per MCP client in the Admin Dashboard")
        
    except Exception as e:
        logger.error(f"Error populating models: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    populate_models()