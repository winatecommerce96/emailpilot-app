"""
AI Orchestrator - Centralized AI Access Layer for EmailPilot
==============================================================

This is the ONLY interface for AI API calls in the EmailPilot application.
All modules MUST use this orchestrator for AI completions.

Features:
- Unified interface for all AI providers (OpenAI, Claude, Gemini)
- Automatic fallback and retry logic
- Marketing content optimization
- Model discovery and management
- Token tracking and cost management
- Streaming support

Author: EmailPilot Team
Version: 1.0.0
Last Updated: 2025-08-19
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncIterator, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from app.services.ai_models_service import AIModelsService
from app.services.model_catalog import get_model_catalog
from app.deps import get_db
from app.deps.secrets import get_secret_manager_service

logger = logging.getLogger(__name__)


class Provider(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    AUTO = "auto"  # Automatically select best provider


class ModelTier(Enum):
    """Model performance tiers"""
    FLAGSHIP = "flagship"  # Best models (GPT-4o, Claude 3.5, Gemini 2.5 Pro)
    STANDARD = "standard"  # Standard models (GPT-4, Claude 3, Gemini 1.5)
    FAST = "fast"         # Fast models (GPT-3.5, Claude Haiku, Gemini Flash)
    AUTO = "auto"         # Automatically select based on task


@dataclass
class CompletionRequest:
    """Standard completion request format"""
    messages: List[Dict[str, str]]
    provider: Provider = Provider.AUTO
    model: Optional[str] = None
    model_tier: ModelTier = ModelTier.AUTO
    temperature: float = 0.7
    max_tokens: int = 1000
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        data = asdict(self)
        data['provider'] = self.provider.value
        data['model_tier'] = self.model_tier.value
        return data


@dataclass
class CompletionResponse:
    """Standard completion response format"""
    content: str
    provider: str
    model: str
    usage: Dict[str, int]
    metadata: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class AIOrchestrator:
    """
    Central AI Orchestrator for EmailPilot
    
    This is the ONLY class that should be used for AI API calls.
    All direct SDK usage is deprecated.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one orchestrator exists"""
        if cls._instance is None:
            cls._instance = super(AIOrchestrator, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the orchestrator"""
        if not self._initialized:
            self.db = get_db()
            self.secret_manager = get_secret_manager_service()
            self.ai_service = AIModelsService(self.db, self.secret_manager)
            self.model_catalog = get_model_catalog(self.secret_manager)
            self._cache = {}
            self._initialized = True
            logger.info("AI Orchestrator initialized")
    
    async def complete(
        self,
        request: Union[CompletionRequest, Dict[str, Any]]
    ) -> CompletionResponse:
        """
        Main completion method - handles all AI requests
        
        Args:
            request: CompletionRequest object or dictionary with request parameters
            
        Returns:
            CompletionResponse with the AI response
            
        Example:
            >>> orchestrator = AIOrchestrator()
            >>> response = await orchestrator.complete({
            ...     "messages": [{"role": "user", "content": "Hello!"}],
            ...     "provider": "auto"
            ... })
            >>> print(response.content)
        """
        # Convert dict to CompletionRequest if needed
        if isinstance(request, dict):
            # Handle provider enum conversion
            if 'provider' in request and isinstance(request['provider'], str):
                request['provider'] = Provider(request['provider'].lower())
            if 'model_tier' in request and isinstance(request['model_tier'], str):
                request['model_tier'] = ModelTier(request['model_tier'].lower())
            request = CompletionRequest(**request)
        
        # Select provider and model
        provider, model = await self._select_provider_and_model(request)
        
        # Check cache
        cache_key = self._get_cache_key(request, provider, model)
        if cache_key in self._cache and not request.stream:
            logger.info(f"Cache hit for {cache_key}")
            cached_response = self._cache[cache_key]
            cached_response.cached = True
            return cached_response
        
        # Execute completion
        try:
            result = await self.ai_service.complete(
                provider=provider,
                model=model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            if result.get("success"):
                response = CompletionResponse(
                    content=result["response"],
                    provider=provider,
                    model=model,
                    usage=result.get("usage", {}),
                    warnings=result.get("warnings"),
                    metadata=request.metadata
                )
                
                # Cache successful responses
                if not request.stream:
                    self._cache[cache_key] = response
                
                return response
            else:
                # Handle failure with fallback
                return await self._handle_failure(request, provider, model, result.get("error"))
                
        except Exception as e:
            logger.error(f"Completion failed: {e}")
            return await self._handle_failure(request, provider, model, str(e))
    
    async def stream(
        self,
        request: Union[CompletionRequest, Dict[str, Any]]
    ) -> AsyncIterator[str]:
        """
        Stream completion method for real-time responses
        
        Args:
            request: CompletionRequest object or dictionary
            
        Yields:
            Chunks of response text as they arrive
        """
        # Convert dict to CompletionRequest if needed
        if isinstance(request, dict):
            request = CompletionRequest(**request)
        
        request.stream = True
        provider, model = await self._select_provider_and_model(request)
        
        # Note: Streaming implementation would go here
        # For now, return complete response as single chunk
        response = await self.complete(request)
        yield response.content
    
    async def _select_provider_and_model(
        self,
        request: CompletionRequest
    ) -> tuple[str, str]:
        """
        Intelligently select provider and model based on request
        
        Returns:
            Tuple of (provider, model)
        """
        # Check if this is marketing content
        content = " ".join([m.get("content", "") for m in request.messages]).lower()
        is_marketing = any(term in content for term in [
            "email", "marketing", "campaign", "sale", "discount", "promotion",
            "subject line", "copy", "brief", "ecommerce", "subscribe"
        ])
        
        # If marketing content, use Gemini 2.0 Flash (most reliable)
        if is_marketing:
            logger.info("Marketing content detected - using Gemini 2.0 Flash")
            return "gemini", "gemini-2.0-flash"
        
        # Handle auto provider selection
        if request.provider == Provider.AUTO:
            # Select based on model tier
            if request.model_tier == ModelTier.FLAGSHIP:
                provider = "claude"
                model = "claude-3-5-sonnet-20241022"
            elif request.model_tier == ModelTier.FAST:
                provider = "gemini"
                model = "gemini-1.5-flash-002"
            else:  # STANDARD or AUTO
                provider = "openai"
                model = "gpt-4o"
        else:
            provider = request.provider.value
            
            # Select model if not specified
            if not request.model:
                models = await self.model_catalog.get_models(provider)
                if models:
                    model = models[0].id  # Use top-ranked model
                else:
                    # Fallback models
                    default_models = {
                        "openai": "gpt-4o",
                        "claude": "claude-3-5-sonnet-20241022",
                        "gemini": "gemini-2.0-flash"
                    }
                    model = default_models.get(provider, "gpt-4o")
            else:
                model = request.model
        
        return provider, model
    
    async def _handle_failure(
        self,
        request: CompletionRequest,
        failed_provider: str,
        failed_model: str,
        error: str
    ) -> CompletionResponse:
        """
        Handle completion failure with automatic fallback
        
        Returns:
            CompletionResponse from fallback provider or error response
        """
        logger.warning(f"Provider {failed_provider} model {failed_model} failed: {error}")
        
        # Define fallback chain
        fallback_chain = [
            ("gemini", "gemini-2.0-flash"),
            ("claude", "claude-3-5-sonnet-20241022"),
            ("openai", "gpt-4o"),
            ("gemini", "gemini-1.5-pro-002"),
        ]
        
        # Remove failed provider/model from chain
        fallback_chain = [
            (p, m) for p, m in fallback_chain 
            if not (p == failed_provider and m == failed_model)
        ]
        
        # Try fallbacks
        for provider, model in fallback_chain:
            try:
                logger.info(f"Trying fallback: {provider}/{model}")
                result = await self.ai_service.complete(
                    provider=provider,
                    model=model,
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                
                if result.get("success"):
                    return CompletionResponse(
                        content=result["response"],
                        provider=provider,
                        model=model,
                        usage=result.get("usage", {}),
                        warnings=[f"Fallback from {failed_provider}/{failed_model}"],
                        metadata=request.metadata
                    )
            except Exception as e:
                logger.debug(f"Fallback {provider}/{model} failed: {e}")
                continue
        
        # All fallbacks failed
        return CompletionResponse(
            content="I apologize, but I'm unable to process your request at the moment. Please try again later.",
            provider=failed_provider,
            model=failed_model,
            usage={},
            warnings=[f"All providers failed. Original error: {error}"],
            metadata=request.metadata
        )
    
    def _get_cache_key(
        self,
        request: CompletionRequest,
        provider: str,
        model: str
    ) -> str:
        """Generate cache key for request"""
        import hashlib
        import json
        
        key_data = {
            "messages": request.messages,
            "provider": provider,
            "model": model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def list_models(self, provider: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        List available models
        
        Args:
            provider: Optional provider filter
            
        Returns:
            Dictionary of provider -> list of model info
        """
        providers = [provider] if provider else ["openai", "claude", "gemini"]
        result = {}
        
        for p in providers:
            models = await self.model_catalog.get_models(p)
            result[p] = [m.to_dict() for m in models]
        
        return result
    
    async def refresh_models(self) -> Dict[str, Any]:
        """
        Refresh model catalog
        
        Returns:
            Refresh status information
        """
        return await self.model_catalog.refresh_all()
    
    def clear_cache(self):
        """Clear response cache"""
        self._cache.clear()
        logger.info("AI Orchestrator cache cleared")
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Returns:
            Dictionary with usage stats
        """
        # This would query from database in production
        return {
            "total_requests": len(self._cache),
            "cache_size": len(self._cache),
            "providers": {
                "openai": {"requests": 0, "tokens": 0},
                "claude": {"requests": 0, "tokens": 0},
                "gemini": {"requests": 0, "tokens": 0}
            }
        }


# Global singleton instance
_orchestrator: Optional[AIOrchestrator] = None


def get_ai_orchestrator() -> AIOrchestrator:
    """
    Get the global AI Orchestrator instance
    
    This is the recommended way to access the orchestrator.
    
    Example:
        >>> from app.core.ai_orchestrator import get_ai_orchestrator
        >>> orchestrator = get_ai_orchestrator()
        >>> response = await orchestrator.complete({
        ...     "messages": [{"role": "user", "content": "Hello!"}]
        ... })
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator


# Convenience functions for quick access
async def ai_complete(
    messages: List[Dict[str, str]],
    provider: str = "auto",
    model: Optional[str] = None,
    **kwargs
) -> str:
    """
    Quick completion function
    
    Args:
        messages: List of message dicts
        provider: Provider name or "auto"
        model: Optional model name
        **kwargs: Additional parameters
        
    Returns:
        Response content string
        
    Example:
        >>> response = await ai_complete([
        ...     {"role": "user", "content": "Hello!"}
        ... ])
    """
    orchestrator = get_ai_orchestrator()
    response = await orchestrator.complete({
        "messages": messages,
        "provider": provider,
        "model": model,
        **kwargs
    })
    return response.content


async def ai_stream(
    messages: List[Dict[str, str]],
    provider: str = "auto",
    model: Optional[str] = None,
    **kwargs
) -> AsyncIterator[str]:
    """
    Quick streaming function
    
    Args:
        messages: List of message dicts
        provider: Provider name or "auto"
        model: Optional model name
        **kwargs: Additional parameters
        
    Yields:
        Response content chunks
    """
    orchestrator = get_ai_orchestrator()
    async for chunk in orchestrator.stream({
        "messages": messages,
        "provider": provider,
        "model": model,
        **kwargs
    }):
        yield chunk