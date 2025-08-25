"""
Model Catalog Service - Live discovery and caching of AI models
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import httpx
import json

logger = logging.getLogger(__name__)

@dataclass
class NormalizedModel:
    """Normalized model representation across all providers"""
    provider: str  # "openai" | "gemini" | "claude"
    id: str  # provider-native model id
    label: str  # human-friendly name
    rank: int = 99  # Priority rank (lower = better)
    chat: bool = True  # all models here support chat
    vision: Optional[bool] = False
    batch: Optional[bool] = False
    max_output_tokens: Optional[int] = None
    deprecated: bool = False
    last_seen: Optional[datetime] = None
    capabilities: Optional[Dict] = None  # {"chat": true, "vision": false}
    
    def to_dict(self):
        data = asdict(self)
        if data.get('last_seen'):
            data['last_seen'] = data['last_seen'].isoformat()
        # Ensure capabilities is set
        if not data.get('capabilities'):
            data['capabilities'] = {
                'chat': data.get('chat', True),
                'vision': data.get('vision', False)
            }
        return data


class ModelCatalog:
    """Manages live discovery and caching of AI models"""
    
    def __init__(self, secret_manager=None):
        self.secret_manager = secret_manager
        self._cache: Dict[str, List[NormalizedModel]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(hours=6)
        self._lock = asyncio.Lock()
        
    def _is_cache_valid(self, provider: str) -> bool:
        """Check if cache for provider is still valid"""
        if provider not in self._cache_timestamps:
            return False
        age = datetime.utcnow() - self._cache_timestamps[provider]
        return age < self._cache_ttl
    
    async def get_models(self, provider: str, force_refresh: bool = False) -> List[NormalizedModel]:
        """Get models for a provider, using cache if valid"""
        async with self._lock:
            if not force_refresh and self._is_cache_valid(provider):
                logger.info(f"Using cached models for {provider}")
                return self._cache.get(provider, [])
            
            logger.info(f"Discovering models for {provider}")
            models = await self._discover_models(provider)
            
            # Update cache
            self._cache[provider] = models
            self._cache_timestamps[provider] = datetime.utcnow()
            
            return models
    
    async def _discover_models(self, provider: str) -> List[NormalizedModel]:
        """Discover models from provider API"""
        try:
            if provider == "openai":
                return await self._discover_openai_models()
            elif provider == "gemini":
                return await self._discover_gemini_models()
            elif provider == "claude":
                return await self._discover_claude_models()
            else:
                logger.warning(f"Unknown provider: {provider}")
                return []
        except Exception as e:
            logger.error(f"Error discovering {provider} models: {e}")
            # Return cached if available on error
            return self._cache.get(provider, [])
    
    async def _discover_openai_models(self) -> List[NormalizedModel]:
        """Discover OpenAI models using v1 API"""
        models = []
        
        try:
            # Get API key
            if self.secret_manager:
                api_key = self.secret_manager.get_secret("openai-api-key")
            else:
                import os
                api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                logger.warning("No OpenAI API key available")
                # Return curated list as fallback
                return self._get_openai_fallback_models()
            
            # Use v1 client to list models
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # List models and filter for chat-capable ones
            response = client.models.list()
            
            # Define top 5 preferred models with rankings
            preferred_models = {
                "gpt-4o": 1,          # Latest omni model
                "gpt-4-turbo": 2,     # Latest turbo
                "gpt-4": 3,           # Standard GPT-4
                "gpt-3.5-turbo": 4,   # Fast and cheap
                "gpt-4o-mini": 5,     # Mini version
            }
            
            chat_capable_prefixes = ["gpt-4", "gpt-3.5", "gpt-4o"]
            
            for model in response.data:
                # Filter for chat models
                if any(model.id.startswith(prefix) for prefix in chat_capable_prefixes):
                    # Skip dated versions unless they're in our preferred list
                    base_model = model.id.split("-202")[0] if "-202" in model.id else model.id
                    
                    # Determine rank
                    rank = preferred_models.get(base_model, 99)
                    
                    # Skip if not in top 5 and is a dated version
                    if rank == 99 and "-202" in model.id:
                        continue
                    
                    # Determine capabilities
                    vision = "vision" in model.id or "4o" in model.id
                    
                    # Create normalized model
                    normalized = NormalizedModel(
                        provider="openai",
                        id=model.id,
                        label=self._format_model_label(model.id),
                        rank=rank,
                        chat=True,
                        vision=vision,
                        batch="batch" in model.id,
                        max_output_tokens=self._get_openai_max_tokens(model.id),
                        deprecated=self._is_openai_deprecated(model.id),
                        last_seen=datetime.utcnow(),
                        capabilities={"chat": True, "vision": vision}
                    )
                    models.append(normalized)
            
            # Sort by rank and take top 5
            models.sort(key=lambda m: (m.rank, m.deprecated, m.id))
            models = models[:5]
            
        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            return self._get_openai_fallback_models()
        
        return models if models else self._get_openai_fallback_models()
    
    def _get_openai_fallback_models(self) -> List[NormalizedModel]:
        """Fallback list of top 5 OpenAI models when API is unavailable"""
        return [
            NormalizedModel(
                provider="openai",
                id="gpt-4o",
                label="GPT-4o (Omni)",
                rank=1,
                chat=True,
                vision=True,
                max_output_tokens=4096,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="openai",
                id="gpt-4-turbo",
                label="GPT-4 Turbo",
                rank=2,
                chat=True,
                vision=True,
                max_output_tokens=4096,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="openai",
                id="gpt-4",
                label="GPT-4",
                rank=3,
                chat=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": False}
            ),
            NormalizedModel(
                provider="openai",
                id="gpt-3.5-turbo",
                label="GPT-3.5 Turbo",
                rank=4,
                chat=True,
                max_output_tokens=4096,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": False}
            ),
            NormalizedModel(
                provider="openai",
                id="gpt-4o-mini",
                label="GPT-4o Mini",
                rank=5,
                chat=True,
                vision=True,
                max_output_tokens=4096,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
        ]
    
    async def _discover_gemini_models(self) -> List[NormalizedModel]:
        """Discover Gemini models using official google-generativeai SDK"""
        models = []
        
        try:
            # Get API key
            if self.secret_manager:
                api_key = self.secret_manager.get_secret("gemini-api-key")
            else:
                import os
                api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                logger.warning("No Gemini API key available")
                return self._get_gemini_fallback_models()
            
            # Use the official SDK for model discovery
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # List all available models
            available_models = []
            for model in genai.list_models():
                # Only include models that support generateContent
                if 'generateContent' in model.supported_generation_methods:
                    model_id = model.name.replace("models/", "")
                    available_models.append({
                        'id': model_id,
                        'display_name': model.display_name,
                        'description': getattr(model, 'description', ''),
                        'input_token_limit': getattr(model, 'input_token_limit', 32768),
                        'output_token_limit': getattr(model, 'output_token_limit', 8192),
                    })
            
            # Define rankings for models - prioritize newest versions
            # Gemini 2.5 and 2.0 are now available!
            preferred_models = {
                # Gemini 2.5 models (newest)
                "gemini-2.5-pro": 1,           # Latest 2.5 Pro
                "gemini-2.5-flash": 2,         # Latest 2.5 Flash
                # Gemini 2.0 models
                "gemini-2.0-flash-exp": 3,     # 2.0 Flash Experimental
                "gemini-2.0-flash": 3,         # 2.0 Flash stable
                "gemini-2.0-flash-001": 3,     # 2.0 Flash versioned
                # Gemini 1.5 models (still good)
                "gemini-1.5-pro-002": 4,       # Latest stable 1.5 Pro
                "gemini-1.5-flash-002": 5,     # Latest stable 1.5 Flash
                # Generic fallbacks
                "gemini-1.5-pro": 4,
                "gemini-1.5-flash": 5,
            }
            
            seen_base_models = set()
            for model_info in available_models:
                model_id = model_info['id']
                
                # Skip embedding or AQA models
                if any(x in model_id.lower() for x in ['embedding', 'aqa']):
                    continue
                
                # Skip experimental UNLESS it's a 2.0 model we want
                if 'experimental' in model_id.lower() and '2.0' not in model_id:
                    continue
                
                # Skip preview/thinking models for now
                if any(x in model_id.lower() for x in ['thinking', 'image-generation', 'tts', 'lite']):
                    continue
                
                # Extract base model name
                base_model = model_id
                # Handle versioned models like gemini-2.0-flash-001
                if model_id[-3:].isdigit() and model_id[-4] == '-':
                    base_model = model_id[:-4]
                # Handle exp suffix
                if base_model.endswith('-exp'):
                    base_model = base_model[:-4]
                
                # Get rank
                rank = preferred_models.get(model_id, preferred_models.get(base_model, 99))
                
                # Skip if not in top 5
                if rank > 5:
                    continue
                
                seen_base_models.add(base_model)
                
                # Determine capabilities
                # 1.5, 2.0, and 2.5 models all support vision
                has_vision = any(ver in model_id for ver in ['1.5', '2.0', '2.5'])
                
                # Create normalized model
                normalized = NormalizedModel(
                    provider="gemini",
                    id=model_id,
                    label=self._format_model_label(model_info['display_name']),
                    rank=rank,
                    chat=True,
                    vision=has_vision,
                    max_output_tokens=model_info['output_token_limit'],
                    deprecated=False,
                    last_seen=datetime.utcnow(),
                    capabilities={"chat": True, "vision": has_vision}
                )
                models.append(normalized)
                logger.info(f"Discovered Gemini model: {model_id} (rank: {rank})")
            
            # If we didn't get enough models, add some fallbacks
            if len(models) < 5:
                fallback_models = self._get_gemini_fallback_models()
                for fallback in fallback_models:
                    if len(models) >= 5:
                        break
                    if not any(m.id == fallback.id for m in models):
                        models.append(fallback)
        
        except Exception as e:
            logger.error(f"Error discovering Gemini models with SDK: {e}")
            return self._get_gemini_fallback_models()
        
        # Sort by rank and take top 5
        models.sort(key=lambda m: (m.rank, m.id))
        models = models[:5]
        return models if models else self._get_gemini_fallback_models()
    
    def _get_gemini_fallback_models(self) -> List[NormalizedModel]:
        """Fallback list of top 5 Gemini models (includes 2.5 and 2.0)"""
        return [
            NormalizedModel(
                provider="gemini",
                id="gemini-2.5-pro",
                label="Gemini 2.5 Pro",
                rank=1,
                chat=True,
                vision=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="gemini",
                id="gemini-2.5-flash",
                label="Gemini 2.5 Flash",
                rank=2,
                chat=True,
                vision=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="gemini",
                id="gemini-2.0-flash",
                label="Gemini 2.0 Flash",
                rank=3,
                chat=True,
                vision=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="gemini",
                id="gemini-1.5-pro-002",
                label="Gemini 1.5 Pro",
                rank=4,
                chat=True,
                vision=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="gemini",
                id="gemini-1.5-flash-002",
                label="Gemini 1.5 Flash",
                rank=5,
                chat=True,
                vision=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
        ]
    
    async def _discover_claude_models(self) -> List[NormalizedModel]:
        """Discover Claude models - use curated list and validate with API"""
        models = []
        
        try:
            # Get API key
            if self.secret_manager:
                api_key = self.secret_manager.get_secret("emailpilot-claude")
            else:
                import os
                api_key = os.getenv("ANTHROPIC_API_KEY")
            
            if not api_key:
                logger.warning("No Claude API key available")
                return self._get_claude_fallback_models()
            
            # Claude doesn't have a list models endpoint, so we use a curated list
            # Top 5 Claude models with rankings
            candidate_models = [
                ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (Latest)", 1, 8192),
                ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku (Latest)", 2, 8192),
                ("claude-3-opus-20240229", "Claude 3 Opus", 3, 4096),
                ("claude-3-sonnet-20240229", "Claude 3 Sonnet", 4, 4096),
                ("claude-3-haiku-20240307", "Claude 3 Haiku", 5, 4096),
            ]
            
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            
            for model_id, label, rank, max_tokens in candidate_models:
                try:
                    # Validate model with a minimal dry run
                    # We'll use max_tokens=1 to minimize cost
                    response = client.messages.create(
                        model=model_id,
                        max_tokens=1,
                        messages=[{"role": "user", "content": "Hi"}],
                        temperature=0.5  # Use safe temperature (clamped to 0-1)
                    )
                    
                    # If we get here, model is valid
                    normalized = NormalizedModel(
                        provider="claude",
                        id=model_id,
                        label=label,
                        rank=rank,
                        chat=True,
                        vision="3-5" in model_id or "3.5" in model_id,  # 3.5 models support vision
                        max_output_tokens=max_tokens,
                        deprecated=False,
                        last_seen=datetime.utcnow(),
                        capabilities={"chat": True, "vision": "3-5" in model_id or "3.5" in model_id}
                    )
                    models.append(normalized)
                    logger.info(f"Validated Claude model: {model_id}")
                    
                except Exception as e:
                    error_str = str(e)
                    if "404" in error_str or "not_found" in error_str or "model_not_found" in error_str:
                        logger.warning(f"Claude model not found: {model_id}")
                        # Mark as deprecated/unavailable
                        normalized = NormalizedModel(
                            provider="claude",
                            id=model_id,
                            label=label + " (Unavailable)",
                            rank=rank,
                            chat=True,
                            max_output_tokens=max_tokens,
                            deprecated=True,
                            last_seen=datetime.utcnow(),
                            capabilities={"chat": True, "vision": False}
                        )
                        models.append(normalized)
                    else:
                        logger.warning(f"Error validating Claude model {model_id}: {e}")
            
            # Sort by rank and only keep top 5
            models.sort(key=lambda m: (m.deprecated, m.rank, m.id))
            models = models[:5]
        
        except Exception as e:
            logger.error(f"Error discovering Claude models: {e}")
            return self._get_claude_fallback_models()
        
        return models if models else self._get_claude_fallback_models()
    
    def _get_claude_fallback_models(self) -> List[NormalizedModel]:
        """Fallback list of top 5 Claude models"""
        return [
            NormalizedModel(
                provider="claude",
                id="claude-3-5-sonnet-20241022",
                label="Claude 3.5 Sonnet (Latest)",
                rank=1,
                chat=True,
                vision=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="claude",
                id="claude-3-5-haiku-20241022",
                label="Claude 3.5 Haiku (Latest)",
                rank=2,
                chat=True,
                vision=True,
                max_output_tokens=8192,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": True}
            ),
            NormalizedModel(
                provider="claude",
                id="claude-3-opus-20240229",
                label="Claude 3 Opus",
                rank=3,
                chat=True,
                max_output_tokens=4096,
                deprecated=True,  # Often unavailable
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": False}
            ),
            NormalizedModel(
                provider="claude",
                id="claude-3-sonnet-20240229",
                label="Claude 3 Sonnet",
                rank=4,
                chat=True,
                max_output_tokens=4096,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": False}
            ),
            NormalizedModel(
                provider="claude",
                id="claude-3-haiku-20240307",
                label="Claude 3 Haiku",
                rank=5,
                chat=True,
                max_output_tokens=4096,
                last_seen=datetime.utcnow(),
                capabilities={"chat": True, "vision": False}
            ),
        ]
    
    def _format_model_label(self, name: str) -> str:
        """Format model name for display"""
        # Clean up common patterns
        name = name.replace("models/", "").replace("-", " ")
        
        # Capitalize appropriately
        parts = name.split()
        formatted = []
        for part in parts:
            if part.lower() in ["gpt", "api", "pro", "turbo", "flash"]:
                formatted.append(part.upper())
            elif part.startswith("gemini") or part.startswith("claude"):
                formatted.append(part.capitalize())
            elif part.replace(".", "").isdigit():
                formatted.append(part)  # Keep version numbers as-is
            else:
                formatted.append(part.title())
        
        return " ".join(formatted)
    
    def _get_openai_max_tokens(self, model_id: str) -> int:
        """Get max tokens for OpenAI model"""
        if "gpt-4" in model_id:
            if "32k" in model_id:
                return 32768
            elif "turbo" in model_id or "4o" in model_id:
                return 4096
            else:
                return 8192
        elif "gpt-3.5" in model_id:
            if "16k" in model_id:
                return 16384
            else:
                return 4096
        return 4096  # default
    
    def _is_openai_deprecated(self, model_id: str) -> bool:
        """Check if OpenAI model is deprecated"""
        deprecated_patterns = [
            "0301", "0314", "0613",  # Old date-versioned models
            "davinci", "curie", "babbage", "ada",  # GPT-3 models
        ]
        return any(pattern in model_id for pattern in deprecated_patterns)
    
    async def refresh_all(self) -> Dict[str, List[NormalizedModel]]:
        """Force refresh all provider models"""
        results = {}
        for provider in ["openai", "gemini", "claude"]:
            models = await self.get_models(provider, force_refresh=True)
            results[provider] = models
        return results
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache state"""
        info = {
            "providers": {},
            "ttl_hours": self._cache_ttl.total_seconds() / 3600
        }
        
        for provider in ["openai", "gemini", "claude"]:
            if provider in self._cache_timestamps:
                age = datetime.utcnow() - self._cache_timestamps[provider]
                info["providers"][provider] = {
                    "cached_at": self._cache_timestamps[provider].isoformat(),
                    "age_minutes": int(age.total_seconds() / 60),
                    "model_count": len(self._cache.get(provider, [])),
                    "is_valid": self._is_cache_valid(provider)
                }
            else:
                info["providers"][provider] = {
                    "cached_at": None,
                    "model_count": 0,
                    "is_valid": False
                }
        
        return info


# Global singleton instance
_catalog_instance: Optional[ModelCatalog] = None

def get_model_catalog(secret_manager=None) -> ModelCatalog:
    """Get or create the global model catalog instance"""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = ModelCatalog(secret_manager)
    return _catalog_instance