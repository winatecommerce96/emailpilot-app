"""
Create MCP tables in the database
"""
from app.core.database import engine, Base
from app.models.mcp_client import MCPClient, MCPUsage, MCPModelConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mcp_tables():
    """Create all MCP-related tables"""
    try:
        # Import all models to ensure they're registered with Base
        try:
            from app.models import client, report, goal  # Import existing models
        except ImportError as e:
            logger.warning(f"Some existing models couldn't be imported: {e}")
        
        # Import calendar models if they exist
        try:
            from app.models import calendar_event
        except ImportError:
            logger.warning("Calendar models not found - this is expected for new installations")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully created MCP tables")
        
        # Optionally, populate default model configurations
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            # Check if models already exist
            existing = db.query(MCPModelConfig).first()
            if not existing:
                logger.info("Adding default model configurations...")
                
                # Claude models
                claude_models = [
                    MCPModelConfig(
                        provider="claude",
                        model_name="claude-3-opus",
                        display_name="Claude 3 Opus",
                        supports_functions=True,
                        supports_vision=True,
                        supports_streaming=True,
                        max_tokens=4096,
                        context_window=200000,
                        input_cost_per_1k=0.015,
                        output_cost_per_1k=0.075,
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True
                    ),
                    MCPModelConfig(
                        provider="claude",
                        model_name="claude-3-sonnet",
                        display_name="Claude 3 Sonnet",
                        supports_functions=True,
                        supports_vision=True,
                        supports_streaming=True,
                        max_tokens=4096,
                        context_window=200000,
                        input_cost_per_1k=0.003,
                        output_cost_per_1k=0.015,
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True
                    )
                ]
                
                # OpenAI models
                openai_models = [
                    MCPModelConfig(
                        provider="openai",
                        model_name="gpt-4-turbo",
                        display_name="GPT-4 Turbo",
                        supports_functions=True,
                        supports_vision=True,
                        supports_streaming=True,
                        max_tokens=4096,
                        context_window=128000,
                        input_cost_per_1k=0.01,
                        output_cost_per_1k=0.03,
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True
                    ),
                    MCPModelConfig(
                        provider="openai",
                        model_name="gpt-4",
                        display_name="GPT-4",
                        supports_functions=True,
                        supports_vision=False,
                        supports_streaming=True,
                        max_tokens=8192,
                        context_window=8192,
                        input_cost_per_1k=0.03,
                        output_cost_per_1k=0.06,
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True
                    ),
                    MCPModelConfig(
                        provider="openai",
                        model_name="gpt-3.5-turbo",
                        display_name="GPT-3.5 Turbo",
                        supports_functions=True,
                        supports_vision=False,
                        supports_streaming=True,
                        max_tokens=4096,
                        context_window=16385,
                        input_cost_per_1k=0.0005,
                        output_cost_per_1k=0.0015,
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True
                    )
                ]
                
                # Gemini models
                gemini_models = [
                    MCPModelConfig(
                        provider="gemini",
                        model_name="gemini-pro",
                        display_name="Gemini Pro",
                        supports_functions=True,
                        supports_vision=False,
                        supports_streaming=True,
                        max_tokens=8192,
                        context_window=32760,
                        input_cost_per_1k=0.00025,
                        output_cost_per_1k=0.0005,
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True
                    ),
                    MCPModelConfig(
                        provider="gemini",
                        model_name="gemini-pro-vision",
                        display_name="Gemini Pro Vision",
                        supports_functions=True,
                        supports_vision=True,
                        supports_streaming=True,
                        max_tokens=4096,
                        context_window=16384,
                        input_cost_per_1k=0.00025,
                        output_cost_per_1k=0.0005,
                        default_temperature=0.7,
                        default_max_tokens=2048,
                        enabled=True
                    )
                ]
                
                # Add all models to database
                for model in claude_models + openai_models + gemini_models:
                    db.add(model)
                
                db.commit()
                logger.info(f"Added {len(claude_models + openai_models + gemini_models)} default model configurations")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating MCP tables: {e}")
        return False

if __name__ == "__main__":
    success = create_mcp_tables()
    if success:
        print("✅ MCP tables created successfully!")
    else:
        print("❌ Failed to create MCP tables")
        exit(1)