"""
LLM Model Configuration - Centralized model definitions
Updated with latest models from OpenAI, Anthropic, and Google (Dec 2024)
"""

from typing import Dict, Any, Optional
from enum import Enum

class ModelTier(Enum):
    """Model tier classification"""
    GOOD = "good"      # Fast and cost-effective
    BETTER = "better"  # Balanced performance
    BEST = "best"      # Maximum capability

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "gemini"

# Model configurations with Good/Better/Best tiers
LLM_MODELS = {
    # OpenAI Models
    "gpt-4o-mini": {
        "provider": LLMProvider.OPENAI,
        "name": "GPT-4o Mini",
        "tier": ModelTier.GOOD,
        "description": "Fast and cost-effective for simple tasks",
        "context_window": 128000,
        "max_output": 16384,
        "cost_tier": "$",
        "speed": "fast",
        "use_cases": ["simple queries", "quick responses", "basic analysis"]
    },
    "gpt-4o": {
        "provider": LLMProvider.OPENAI,
        "name": "GPT-4o",
        "tier": ModelTier.BETTER,
        "description": "Balanced performance for most tasks",
        "context_window": 128000,
        "max_output": 16384,
        "cost_tier": "$$",
        "speed": "medium",
        "use_cases": ["general tasks", "code generation", "content creation"]
    },
    "o1-preview": {
        "provider": LLMProvider.OPENAI,
        "name": "O1 Preview",
        "tier": ModelTier.BEST,
        "description": "Advanced reasoning and complex problem solving",
        "context_window": 128000,
        "max_output": 32768,
        "cost_tier": "$$$",
        "speed": "slow",
        "use_cases": ["complex reasoning", "advanced analysis", "mathematical problems"]
    },
    
    # Anthropic Models
    "claude-3-5-haiku-20241022": {
        "provider": LLMProvider.ANTHROPIC,
        "name": "Claude 3.5 Haiku",
        "tier": ModelTier.GOOD,
        "description": "Lightning-fast responses",
        "context_window": 200000,
        "max_output": 8192,
        "cost_tier": "$",
        "speed": "very fast",
        "use_cases": ["quick tasks", "high-volume processing", "simple queries"]
    },
    "claude-3-5-sonnet-20241022": {
        "provider": LLMProvider.ANTHROPIC,
        "name": "Claude 3.5 Sonnet",
        "tier": ModelTier.BETTER,
        "description": "Excellent balance of speed and intelligence",
        "context_window": 200000,
        "max_output": 8192,
        "cost_tier": "$$",
        "speed": "medium",
        "use_cases": ["coding", "creative writing", "detailed analysis"]
    },
    "claude-3-5-sonnet-best": {
        "provider": LLMProvider.ANTHROPIC,
        "name": "Claude 3.5 Sonnet (Best)",
        "tier": ModelTier.BEST,
        "description": "Most capable Claude model currently available",
        "context_window": 200000,
        "max_output": 8192,
        "cost_tier": "$$$",
        "speed": "medium",
        "use_cases": ["complex analysis", "nuanced reasoning", "expert tasks"],
        "model_id": "claude-3-5-sonnet-20241022"  # Uses same model ID as Better tier
    },
    
    # Google Models
    "gemini-1.5-flash-002": {
        "provider": LLMProvider.GOOGLE,
        "name": "Gemini 1.5 Flash",
        "tier": ModelTier.GOOD,
        "description": "Optimized for speed",
        "context_window": 1000000,  # 1M tokens
        "max_output": 8192,
        "cost_tier": "$",
        "speed": "very fast",
        "use_cases": ["large context tasks", "document processing", "quick analysis"]
    },
    "gemini-1.5-pro-002": {
        "provider": LLMProvider.GOOGLE,
        "name": "Gemini 1.5 Pro",
        "tier": ModelTier.BETTER,
        "description": "Advanced capabilities with huge context",
        "context_window": 2000000,  # 2M tokens
        "max_output": 8192,
        "cost_tier": "$$",
        "speed": "medium",
        "use_cases": ["very large documents", "complex reasoning", "multimodal tasks"]
    },
    "gemini-2.0-flash-exp": {
        "provider": LLMProvider.GOOGLE,
        "name": "Gemini 2.0 Flash (Experimental)",
        "tier": ModelTier.BEST,
        "description": "Latest experimental model with cutting-edge features",
        "context_window": 1000000,
        "max_output": 8192,
        "cost_tier": "$$",
        "speed": "fast",
        "use_cases": ["experimental features", "latest capabilities", "advanced multimodal"]
    }
}

def get_model_by_tier(provider: str, tier: str) -> Optional[str]:
    """Get model by provider and tier"""
    provider_enum = LLMProvider(provider.lower())
    tier_enum = ModelTier(tier.lower())
    
    for model_id, config in LLM_MODELS.items():
        if config["provider"] == provider_enum and config["tier"] == tier_enum:
            return model_id
    return None

def get_recommended_model(use_case: str) -> str:
    """Get recommended model based on use case"""
    recommendations = {
        # Task complexity
        "simple": "gpt-4o-mini",
        "balanced": "gpt-4o",
        "complex": "o1-preview",
        
        # Specific capabilities
        "creative": "claude-3-5-sonnet-20241022",
        "analytical": "claude-3-opus-20240229",
        "fast": "gemini-1.5-flash-002",
        "large_context": "gemini-1.5-pro-002",
        "experimental": "gemini-2.0-flash-exp",
        
        # Budget considerations
        "budget": "gpt-4o-mini",
        "premium": "o1-preview",
        
        # Default
        "default": "gpt-4o"
    }
    
    return recommendations.get(use_case, "gpt-4o")

def get_langchain_llm(model_id: str, temperature: float = 0.7, **kwargs):
    """Get LangChain LLM instance for the specified model"""
    if model_id not in LLM_MODELS:
        raise ValueError(f"Unknown model: {model_id}")
    
    config = LLM_MODELS[model_id]
    provider = config["provider"]
    
    # Use model_id override if present (for aliased models)
    actual_model_id = config.get("model_id", model_id)
    
    # Get API keys from Secret Manager if available
    api_key = None
    try:
        import sys
        import os
        from pathlib import Path
        
        # Add multi-agent path if needed
        multi_agent_path = Path(__file__).parent.parent.parent / "multi-agent"
        if str(multi_agent_path) not in sys.path:
            sys.path.insert(0, str(multi_agent_path))
        
        from integrations.langchain_core.secrets import get_api_key
        
        if provider == LLMProvider.OPENAI:
            api_key = get_api_key("openai")
        elif provider == LLMProvider.ANTHROPIC:
            api_key = get_api_key("anthropic")
        elif provider == LLMProvider.GOOGLE:
            api_key = get_api_key("gemini")
    except Exception as e:
        # Fall back to environment variables
        import os
        if provider == LLMProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider == LLMProvider.ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif provider == LLMProvider.GOOGLE:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    # Import the appropriate LangChain class
    if provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=actual_model_id,
            temperature=temperature,
            max_tokens=config.get("max_output", 4096),
            api_key=api_key,
            **kwargs
        )
    
    elif provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=actual_model_id,
            temperature=temperature,
            max_tokens=config.get("max_output", 4096),
            anthropic_api_key=api_key,
            **kwargs
        )
    
    elif provider == LLMProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Gemini uses a different model naming convention
        gemini_model = actual_model_id.replace("-002", "").replace("-exp", "")
        return ChatGoogleGenerativeAI(
            model=gemini_model,
            temperature=temperature,
            max_output_tokens=config.get("max_output", 4096),
            google_api_key=api_key,
            **kwargs
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")

# Model display information for UI
MODEL_DISPLAY_INFO = {
    # Icons for tiers
    "tier_icons": {
        ModelTier.GOOD: "💰",    # Budget-friendly
        ModelTier.BETTER: "⚖️",  # Balanced
        ModelTier.BEST: "🧠"     # Maximum capability
    },
    
    # Provider colors for UI
    "provider_colors": {
        LLMProvider.OPENAI: "#10A37F",     # OpenAI green
        LLMProvider.ANTHROPIC: "#D4A574",  # Anthropic gold
        LLMProvider.GOOGLE: "#4285F4"      # Google blue
    }
}

# Export default model selections
DEFAULT_MODELS = {
    "simple_task": "gpt-4o-mini",
    "general_task": "gpt-4o",
    "complex_task": "o1-preview",
    "creative_task": "claude-3-5-sonnet-20241022",
    "analytical_task": "claude-3-opus-20240229",
    "speed_priority": "gemini-1.5-flash-002",
    "context_priority": "gemini-1.5-pro-002"
}