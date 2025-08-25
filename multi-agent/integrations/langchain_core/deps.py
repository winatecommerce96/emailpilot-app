"""
Dependency factories for LangChain Core components.

Provides factory functions for creating LLMs, embeddings, vector stores,
and other dependencies with proper fallback handling.
"""

import logging
from typing import Optional, Any, Dict, List
from pathlib import Path
from functools import lru_cache

from .config import LangChainConfig, get_config

logger = logging.getLogger(__name__)


class ModelPolicyResolver:
    """
    Resolves model configuration based on user/brand/global policies.
    Implements a cascade: user → brand → global with allowlist enforcement.
    """
    
    def __init__(self, config: Optional[LangChainConfig] = None):
        """Initialize resolver."""
        self.config = config or get_config()
        self._db = None
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_clear = 0
    
    @property
    def db(self):
        """Lazy load Firestore client."""
        if self._db is None:
            self._db = get_firestore_client(self.config)
        return self._db
    
    def resolve(
        self,
        user_id: Optional[str] = None,
        brand: Optional[str] = None,
        enforce_limits: bool = True
    ) -> Dict[str, Any]:
        """
        Resolve model configuration for user/brand with policy cascade.
        
        Args:
            user_id: User ID
            brand: Brand
            enforce_limits: Whether to enforce hard limits and allowlists
        
        Returns:
            Model configuration dictionary with resolved settings
        """
        import time
        
        # Clear cache periodically
        now = time.time()
        if now - self._last_cache_clear > self._cache_ttl:
            self._cache.clear()
            self._last_cache_clear = now
        
        # Check cache
        cache_key = f"{user_id}:{brand}:{enforce_limits}"
        if cache_key in self._cache:
            logger.debug(f"Using cached policy for {cache_key}")
            return self._cache[cache_key]
        
        # Start with global defaults
        result = {
            "provider": self.config.lc_provider,
            "model": self.config.lc_model,
            "temperature": self.config.lc_temperature,
            "max_tokens": self.config.lc_max_tokens,
            "tier": "default",
            "limits": {
                "daily_tokens": 1000000,  # 1M tokens default
                "max_context": 128000,
                "rate_limit_rpm": 60
            },
            "allowlist": [],  # Empty means all allowed
            "blocklist": [],
            "cascade_level": "global"
        }
        
        if not self.db:
            logger.warning("No Firestore client, using defaults")
            self._cache[cache_key] = result
            return result
        
        try:
            # 1. Load global policy
            global_policy = self._load_policy("global", "default")
            if global_policy:
                result = self._merge_policy(result, global_policy)
                result["cascade_level"] = "global"
            
            # 2. Load brand policy if specified
            if brand:
                brand_policy = self._load_policy("brand", brand)
                if brand_policy:
                    result = self._merge_policy(result, brand_policy)
                    result["cascade_level"] = "brand"
            
            # 3. Load user policy if specified
            if user_id:
                user_policy = self._load_policy("user", user_id)
                if user_policy:
                    result = self._merge_policy(result, user_policy)
                    result["cascade_level"] = "user"
            
            # 4. Apply enforcement if enabled
            if enforce_limits:
                result = self._enforce_limits(result, user_id, brand)
            
            # Cache the result
            self._cache[cache_key] = result
            
            logger.info(
                f"Resolved policy: level={result['cascade_level']}, "
                f"provider={result['provider']}, model={result['model']}, "
                f"tier={result['tier']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error resolving model policy: {e}")
            return result
    
    def _load_policy(self, level: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Load policy from Firestore."""
        try:
            if level == "global":
                doc_ref = self.db.collection("model_policies").document("global")
            elif level == "brand":
                doc_ref = self.db.collection("model_policies").document(f"brand_{identifier}")
            elif level == "user":
                doc_ref = self.db.collection("model_policies").document(f"user_{identifier}")
            else:
                return None
            
            doc = doc_ref.get()
            if doc.exists:
                logger.debug(f"Loaded {level} policy for {identifier}")
                return doc.to_dict()
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to load {level} policy for {identifier}: {e}")
            return None
    
    def _merge_policy(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge policy override into base, respecting allowlists."""
        result = base.copy()
        
        # Simple fields override
        for field in ["provider", "model", "temperature", "max_tokens", "tier"]:
            if field in override:
                result[field] = override[field]
        
        # Merge limits (more restrictive wins)
        if "limits" in override:
            base_limits = result.get("limits", {})
            override_limits = override["limits"]
            
            for limit_key in ["daily_tokens", "max_context", "rate_limit_rpm"]:
                if limit_key in override_limits:
                    base_val = base_limits.get(limit_key, float('inf'))
                    override_val = override_limits[limit_key]
                    # Take the more restrictive limit
                    result["limits"][limit_key] = min(base_val, override_val)
        
        # Allowlist/blocklist handling
        if "allowlist" in override:
            # If override has allowlist, it replaces (more specific)
            result["allowlist"] = override["allowlist"]
        
        if "blocklist" in override:
            # Blocklists accumulate
            existing = set(result.get("blocklist", []))
            new = set(override["blocklist"])
            result["blocklist"] = list(existing | new)
        
        return result
    
    def _enforce_limits(
        self, 
        policy: Dict[str, Any], 
        user_id: Optional[str], 
        brand: Optional[str]
    ) -> Dict[str, Any]:
        """
        Enforce hard limits and check usage.
        May downgrade to a lower tier if limits exceeded.
        """
        result = policy.copy()
        
        # Check allowlist
        if policy.get("allowlist"):
            current_model = f"{policy['provider']}:{policy['model']}"
            if current_model not in policy["allowlist"]:
                # Downgrade to first allowed model
                if policy["allowlist"]:
                    allowed = policy["allowlist"][0]
                    provider, model = allowed.split(":", 1)
                    result["provider"] = provider
                    result["model"] = model
                    result["tier"] = "downgraded"
                    logger.warning(
                        f"Model {current_model} not in allowlist, "
                        f"downgraded to {allowed}"
                    )
        
        # Check blocklist
        if policy.get("blocklist"):
            current_model = f"{policy['provider']}:{policy['model']}"
            if current_model in policy["blocklist"]:
                # Fallback to cheapest model
                result["provider"] = "gemini"
                result["model"] = "gemini-1.5-flash"
                result["tier"] = "blocked_fallback"
                logger.warning(
                    f"Model {current_model} is blocked, "
                    f"falling back to gemini-1.5-flash"
                )
        
        # Check daily usage against limits
        if user_id and self.db:
            try:
                from datetime import datetime, date
                today = date.today()
                doc_id = f"{today}_{user_id}_{brand or 'all'}"
                
                usage_doc = self.db.collection("token_usage_daily").document(doc_id).get()
                if usage_doc.exists:
                    usage_data = usage_doc.to_dict()
                    totals = usage_data.get("totals", {})
                    daily_used = totals.get("total_tokens", 0)
                    daily_limit = policy["limits"].get("daily_tokens", float('inf'))
                    
                    if daily_used >= daily_limit:
                        # Exceeded limit, downgrade to cheaper model
                        result["provider"] = "gemini"
                        result["model"] = "gemini-1.5-flash"
                        result["tier"] = "limit_exceeded"
                        logger.warning(
                            f"User {user_id} exceeded daily limit "
                            f"({daily_used}/{daily_limit}), downgrading"
                        )
            except Exception as e:
                logger.error(f"Failed to check usage limits: {e}")
        
        return result
    
    def check_violation(
        self, 
        provider: str, 
        model: str,
        user_id: Optional[str] = None,
        brand: Optional[str] = None
    ) -> Optional[str]:
        """
        Check if a model selection violates policy.
        
        Returns:
            Violation reason or None if allowed
        """
        policy = self.resolve(user_id, brand, enforce_limits=True)
        
        model_key = f"{provider}:{model}"
        
        # Check blocklist
        if model_key in policy.get("blocklist", []):
            return f"Model {model_key} is blocked by policy"
        
        # Check allowlist
        allowlist = policy.get("allowlist", [])
        if allowlist and model_key not in allowlist:
            return f"Model {model_key} not in allowlist: {allowlist}"
        
        return None
    
    def get_available_models(
        self,
        user_id: Optional[str] = None,
        brand: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get list of available models for user/brand.
        
        Returns:
            List of model dictionaries with provider, model, tier info
        """
        policy = self.resolve(user_id, brand, enforce_limits=False)
        
        # Default available models
        all_models = [
            {"provider": "openai", "model": "gpt-4", "tier": "premium"},
            {"provider": "openai", "model": "gpt-3.5-turbo", "tier": "standard"},
            {"provider": "anthropic", "model": "claude-3-opus-20240229", "tier": "premium"},
            {"provider": "anthropic", "model": "claude-3-sonnet-20240229", "tier": "standard"},
            {"provider": "anthropic", "model": "claude-3-haiku-20240307", "tier": "economy"},
            {"provider": "gemini", "model": "gemini-1.5-pro", "tier": "premium"},
            {"provider": "gemini", "model": "gemini-1.5-flash", "tier": "economy"}
        ]
        
        # Filter by allowlist
        allowlist = policy.get("allowlist", [])
        if allowlist:
            allowed_keys = set(allowlist)
            all_models = [
                m for m in all_models 
                if f"{m['provider']}:{m['model']}" in allowed_keys
            ]
        
        # Filter by blocklist
        blocklist = set(policy.get("blocklist", []))
        if blocklist:
            all_models = [
                m for m in all_models
                if f"{m['provider']}:{m['model']}" not in blocklist
            ]
        
        # Mark current selection
        current_key = f"{policy['provider']}:{policy['model']}"
        for model in all_models:
            model_key = f"{model['provider']}:{model['model']}"
            model["selected"] = (model_key == current_key)
        
        return all_models


def get_llm(
    config: Optional[LangChainConfig] = None,
    user_id: Optional[str] = None,
    brand: Optional[str] = None,
    use_policy: bool = True
) -> Any:
    """
    Create LLM instance based on configuration and policies.
    
    Args:
        config: Configuration instance (uses singleton if not provided)
        user_id: User ID for policy resolution
        brand: Brand for policy resolution
        use_policy: Whether to use ModelPolicyResolver
    
    Returns:
        LLM instance
    
    Raises:
        ImportError: If provider libraries not installed
        ValueError: If API key missing
    """
    if config is None:
        config = get_config()
    
    # Resolve model configuration based on policies
    if use_policy:
        resolver = ModelPolicyResolver(config)
        model_config = resolver.resolve(user_id, brand)
        provider = model_config["provider"]
        model = model_config["model"]
        temperature = model_config.get("temperature", config.lc_temperature)
        max_tokens = model_config.get("max_tokens", config.lc_max_tokens)
        logger.info(
            f"Policy-resolved LLM: provider={provider}, model={model}, "
            f"tier={model_config.get('tier')}, level={model_config.get('cascade_level')}"
        )
    else:
        provider = config.lc_provider
        model = config.lc_model
        temperature = config.lc_temperature
        max_tokens = config.lc_max_tokens
        logger.info(f"Creating LLM: provider={provider}, model={model}")
    
    try:
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            
            if not config.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=config.openai_api_key,
                timeout=30,
                max_retries=3
            )
        
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            
            if not config.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                anthropic_api_key=config.anthropic_api_key,
                timeout=30,
                max_retries=3
            )
        
        elif provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            if not config.google_api_key:
                raise ValueError("Google API key not configured")
            
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                max_output_tokens=max_tokens,
                google_api_key=config.google_api_key,
                timeout=30,
                max_retries=3
            )
        
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    except ImportError as e:
        logger.error(f"Failed to import {provider} provider: {e}")
        raise ImportError(
            f"Provider '{provider}' not installed. "
            f"Install with: pip install langchain-{provider}"
        )


def get_embeddings(config: Optional[LangChainConfig] = None) -> Any:
    """
    Create embeddings instance based on configuration.
    
    Args:
        config: Configuration instance
    
    Returns:
        Embeddings instance
    """
    if config is None:
        config = get_config()
    
    provider = config.embeddings_provider
    model = config.embeddings_model
    
    logger.info(f"Creating embeddings: provider={provider}, model={model}")
    
    try:
        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            
            if not config.openai_api_key:
                logger.warning("OpenAI API key missing, falling back to local embeddings")
                provider = "local"
            else:
                return OpenAIEmbeddings(
                    model=model,
                    openai_api_key=config.openai_api_key,
                    timeout=30,
                    max_retries=3
                )
        
        if provider == "vertex":
            try:
                from langchain_google_vertexai import VertexAIEmbeddings
                
                return VertexAIEmbeddings(
                    model_name=model,
                    project=config.firestore_project
                )
            except Exception as e:
                logger.warning(f"Vertex AI embeddings failed: {e}, falling back to local")
                provider = "local"
        
        if provider == "local":
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            # Use sentence-transformers for local embeddings
            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )
        
        raise ValueError(f"Unknown embeddings provider: {provider}")
    
    except ImportError as e:
        logger.error(f"Failed to import embeddings: {e}")
        # Final fallback to local embeddings
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        logger.info("Using fallback local embeddings")
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )


def get_vectorstore(
    embeddings: Any,
    config: Optional[LangChainConfig] = None,
    rebuild: bool = False
) -> Any:
    """
    Create or load vector store instance.
    
    Args:
        embeddings: Embeddings instance
        config: Configuration instance
        rebuild: Force rebuild of index
    
    Returns:
        VectorStore instance
    """
    if config is None:
        config = get_config()
    
    store_type = config.vectorstore
    store_path = config.vectorstore_path
    
    logger.info(f"Getting vector store: type={store_type}, path={store_path}")
    
    if store_type == "faiss":
        from langchain_community.vectorstores import FAISS
        
        # Ensure directory exists
        store_path.mkdir(parents=True, exist_ok=True)
        index_path = store_path / "index"
        
        if not rebuild and index_path.exists():
            logger.info(f"Loading existing FAISS index from {index_path}")
            try:
                return FAISS.load_local(
                    str(index_path),
                    embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                logger.warning(f"Failed to load index: {e}, will create new")
        
        # Create new index
        logger.info("Creating new FAISS index")
        return FAISS.from_texts(
            texts=["Initial document for index creation"],
            embedding=embeddings,
            metadatas=[{"source": "initialization"}]
        )
    
    elif store_type == "chroma":
        from langchain_community.vectorstores import Chroma
        
        persist_dir = str(store_path / "chroma")
        
        if rebuild and Path(persist_dir).exists():
            import shutil
            logger.info(f"Removing existing Chroma database at {persist_dir}")
            shutil.rmtree(persist_dir)
        
        return Chroma(
            embedding_function=embeddings,
            persist_directory=persist_dir
        )
    
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")


def get_firestore_client(config: Optional[LangChainConfig] = None) -> Any:
    """
    Get Firestore client for read-only operations.
    
    Args:
        config: Configuration instance
    
    Returns:
        Firestore client instance
    """
    if config is None:
        config = get_config()
    
    try:
        from google.cloud import firestore
        
        if config.firestore_emulator:
            # Use emulator if configured
            import os
            os.environ["FIRESTORE_EMULATOR_HOST"] = config.firestore_emulator
            logger.info(f"Using Firestore emulator at {config.firestore_emulator}")
        
        client = firestore.Client(project=config.firestore_project)
        
        # Test connection
        try:
            list(client.collections(limit=1))
            logger.info("Firestore client connected successfully")
        except Exception as e:
            logger.warning(f"Firestore connection test failed: {e}")
        
        return client
    
    except ImportError:
        logger.error("google-cloud-firestore not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to create Firestore client: {e}")
        return None


def get_cache() -> Dict[str, Any]:
    """
    Get in-process cache for agent tools.
    
    Returns:
        Cache dictionary
    """
    if not hasattr(get_cache, "_cache"):
        get_cache._cache = {}
        logger.info("Initialized in-process cache")
    
    return get_cache._cache


def check_dependencies() -> Dict[str, bool]:
    """
    Check availability of all dependencies.
    
    Returns:
        Dictionary of package -> availability
    """
    deps = {
        "langchain": False,
        "langgraph": False,
        "langchain-openai": False,
        "langchain-anthropic": False,
        "langchain-google-genai": False,
        "langchain-community": False,
        "faiss-cpu": False,
        "chromadb": False,
        "sentence-transformers": False,
        "tiktoken": False,
        "google-cloud-firestore": False
    }
    
    for package in deps:
        try:
            if package == "faiss-cpu":
                import faiss
                deps[package] = True
            elif package == "chromadb":
                import chromadb
                deps[package] = True
            elif package == "sentence-transformers":
                import sentence_transformers
                deps[package] = True
            elif package == "tiktoken":
                import tiktoken
                deps[package] = True
            elif package == "google-cloud-firestore":
                from google.cloud import firestore
                deps[package] = True
            else:
                __import__(package.replace("-", "_"))
                deps[package] = True
        except ImportError:
            pass
    
    return deps


def initialize_tracing(config: Optional[LangChainConfig] = None) -> None:
    """
    Initialize tracing if enabled.
    
    Args:
        config: Configuration instance
    """
    if config is None:
        config = get_config()
    
    if not config.enable_tracing:
        return
    
    logger.info("Initializing tracing")
    
    try:
        import os
        
        if config.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = config.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = config.langsmith_project
            logger.info(f"LangSmith tracing enabled for project: {config.langsmith_project}")
        else:
            logger.warning("Tracing enabled but no LangSmith API key configured")
    
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")