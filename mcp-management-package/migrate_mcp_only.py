"""
Create only MCP tables without importing conflicting models
"""
from sqlalchemy import create_engine, MetaData
from app.models.mcp_client import MCPClient, MCPUsage, MCPModelConfig
from app.core.database import Base, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mcp_tables_only():
    """Create only MCP-related tables"""
    try:
        # Create just MCP tables by directly using their metadata
        mcp_tables = [
            MCPClient.__table__,
            MCPUsage.__table__,
            MCPModelConfig.__table__
        ]
        
        for table in mcp_tables:
            table.create(engine, checkfirst=True)
            logger.info(f"Created table: {table.name}")
        
        # Add default model configurations
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            # Check if models already exist
            existing = db.query(MCPModelConfig).first()
            if not existing:
                logger.info("Adding default model configurations...")
                
                # Default models
                default_models = [
                    # Claude models
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
                    ),
                    # OpenAI models
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
                    ),
                    # Gemini models
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
                    )
                ]
                
                for model in default_models:
                    db.add(model)
                
                db.commit()
                logger.info(f"Added {len(default_models)} default model configurations")
            else:
                logger.info("Default model configurations already exist")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating MCP tables: {e}")
        return False

if __name__ == "__main__":
    success = create_mcp_tables_only()
    if success:
        print("✅ MCP tables created successfully!")
    else:
        print("❌ Failed to create MCP tables")
        exit(1)