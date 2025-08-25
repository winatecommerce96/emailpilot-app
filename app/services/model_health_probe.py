"""
Model Health Probe Service
Performs lightweight health checks on AI models at startup and on-demand
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
from app.deps.secrets import get_secret_manager_service

logger = logging.getLogger(__name__)

class ModelHealthProbe:
    """Service to probe AI model health and availability"""
    
    def __init__(self):
        self.health_cache = {}
        self.cache_duration = timedelta(minutes=5)
        self.last_probe_time = None
        self.secret_manager = get_secret_manager_service()
        
    async def probe_openai(self) -> Dict[str, Any]:
        """Probe OpenAI models health"""
        try:
            api_key = self.secret_manager.get_secret("openai-api-key")
            if not api_key:
                return {"healthy": False, "error": "API key not configured"}
            
            # Make minimal API call to check health
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    return {
                        "healthy": False,
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"OpenAI probe failed: {e}")
            return {"healthy": False, "error": str(e)}
    
    async def probe_claude(self) -> Dict[str, Any]:
        """Probe Claude/Anthropic models health"""
        try:
            api_key = self.secret_manager.get_secret("emailpilot-claude")
            if not api_key:
                return {"healthy": False, "error": "API key not configured"}
            
            # Make minimal API call to check health
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-haiku-20240307"],
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    return {
                        "healthy": False,
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"Claude probe failed: {e}")
            return {"healthy": False, "error": str(e)}
    
    async def probe_gemini(self) -> Dict[str, Any]:
        """Probe Google Gemini models health"""
        try:
            api_key = self.secret_manager.get_secret("gemini-api-key")
            if not api_key:
                return {"healthy": False, "error": "API key not configured"}
            
            # Make minimal API call to check health
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                    json={
                        "contents": [{"parts": [{"text": "ping"}]}],
                        "generationConfig": {"maxOutputTokens": 1}
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    return {
                        "healthy": False,
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"Gemini probe failed: {e}")
            return {"healthy": False, "error": str(e)}
    
    async def probe_all(self, force: bool = False) -> Dict[str, Any]:
        """
        Probe all configured AI providers
        
        Args:
            force: Force refresh even if cache is valid
            
        Returns:
            Dict with health status for each provider
        """
        # Check cache
        if not force and self.last_probe_time:
            if datetime.now() - self.last_probe_time < self.cache_duration:
                logger.info("Using cached health probe results")
                return self.health_cache
        
        logger.info("Running health probes for all AI providers...")
        
        # Run probes in parallel
        results = await asyncio.gather(
            self.probe_openai(),
            self.probe_claude(),
            self.probe_gemini(),
            return_exceptions=True
        )
        
        # Process results
        health_status = {
            "openai": results[0] if not isinstance(results[0], Exception) else {"healthy": False, "error": str(results[0])},
            "claude": results[1] if not isinstance(results[1], Exception) else {"healthy": False, "error": str(results[1])},
            "gemini": results[2] if not isinstance(results[2], Exception) else {"healthy": False, "error": str(results[2])}
        }
        
        # Calculate overall health
        healthy_count = sum(1 for p in health_status.values() if p.get("healthy", False))
        total_count = len(health_status)
        
        health_status["summary"] = {
            "healthy_providers": healthy_count,
            "total_providers": total_count,
            "status": "healthy" if healthy_count == total_count else "degraded" if healthy_count > 0 else "unhealthy",
            "timestamp": datetime.now().isoformat()
        }
        
        # Log status
        status = health_status["summary"]["status"]
        providers_status = {k: "healthy" if v.get("healthy") else "down" for k, v in health_status.items() if k != "summary"}
        logger.info(f"models_fetch status={status} providers={providers_status}")
        
        # Update cache
        self.health_cache = health_status
        self.last_probe_time = datetime.now()
        
        return health_status
    
    async def get_healthy_models(self) -> List[Dict[str, Any]]:
        """
        Get list of all healthy models from all providers
        
        Returns:
            List of model dictionaries with provider, id, and health status
        """
        health_status = await self.probe_all()
        models = []
        
        for provider, status in health_status.items():
            if provider == "summary":
                continue
                
            if status.get("healthy", False):
                for model_id in status.get("models", []):
                    models.append({
                        "provider": provider,
                        "id": model_id,
                        "label": self._format_model_label(model_id),
                        "healthy": True,
                        "response_time": status.get("response_time")
                    })
            else:
                # Include unhealthy provider info
                models.append({
                    "provider": provider,
                    "id": None,
                    "label": f"{provider.title()} (Unavailable)",
                    "healthy": False,
                    "error": status.get("error", "Unknown error")
                })
        
        return models
    
    def _format_model_label(self, model_id: str) -> str:
        """Format model ID into human-readable label"""
        # Map of model IDs to friendly names
        labels = {
            "gpt-4o": "GPT-4o",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
            "claude-3-haiku-20240307": "Claude 3 Haiku",
            "gemini-2.5-pro": "Gemini 2.5 Pro",
            "gemini-2.5-flash": "Gemini 2.5 Flash",
            "gemini-2.0-flash": "Gemini 2.0 Flash"
        }
        return labels.get(model_id, model_id)

# Global instance
_health_probe = None

def get_health_probe() -> ModelHealthProbe:
    """Get singleton health probe instance"""
    global _health_probe
    if _health_probe is None:
        _health_probe = ModelHealthProbe()
    return _health_probe