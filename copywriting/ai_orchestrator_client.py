"""
AI Orchestrator Client for Copywriting Module
Connects to the main EmailPilot AI Orchestrator service
"""

import httpx
import logging
from typing import Dict, Any, List, Optional
import os
import json

logger = logging.getLogger(__name__)

class AIOrchestratorClient:
    """Client for connecting to EmailPilot's AI Orchestrator"""
    
    def __init__(self, base_url: str = None):
        """
        Initialize the AI Orchestrator client
        
        Args:
            base_url: Base URL of the main EmailPilot app (default: http://localhost:8000)
        """
        self.base_url = base_url or os.getenv("EMAILPILOT_BASE_URL", "http://localhost:8000")
        self.timeout = 120.0  # Extended timeout for AI operations
        logger.info(f"AI Orchestrator client initialized with base URL: {self.base_url}")
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        provider: str = "auto",
        model: Optional[str] = None,
        model_tier: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send completion request to AI Orchestrator
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            provider: Provider to use (auto, openai, claude, gemini)
            model: Specific model to use (optional)
            model_tier: Tier preference (flagship, standard, fast)
            temperature: Creativity level (0.0-1.0)
            max_tokens: Maximum tokens in response
            context: Additional context for the request
            
        Returns:
            Dict containing response content and metadata
        """
        try:
            # Build request payload
            payload = {
                "messages": messages,
                "provider": provider,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if model:
                payload["model"] = model
            if model_tier:
                payload["model_tier"] = model_tier
            if context:
                payload["context"] = context
            
            # Log the request
            logger.info(f"Sending AI Orchestrator request: provider={provider}, model={model or 'auto'}")
            
            # Send request to orchestrator
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/complete",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        logger.info(f"AI Orchestrator response: provider={data.get('provider')}, model={data.get('model')}")
                        return {
                            "content": data.get("content", ""),
                            "provider": data.get("provider"),
                            "model": data.get("model"),
                            "usage": data.get("usage", {}),
                            "cached": data.get("cached", False),
                            "warnings": data.get("warnings", [])
                        }
                    else:
                        error_msg = data.get("error", "Unknown error from orchestrator")
                        logger.error(f"AI Orchestrator error: {error_msg}")
                        return {
                            "content": "",
                            "error": error_msg,
                            "provider": "none",
                            "model": "none"
                        }
                else:
                    logger.error(f"AI Orchestrator HTTP error: {response.status_code}")
                    return {
                        "content": "",
                        "error": f"HTTP {response.status_code}: {response.text[:200]}",
                        "provider": "none",
                        "model": "none"
                    }
                    
        except httpx.ConnectError:
            logger.warning("Could not connect to AI Orchestrator, using fallback")
            return {
                "content": "",
                "error": "Could not connect to EmailPilot AI Orchestrator",
                "provider": "none",
                "model": "none"
            }
        except httpx.TimeoutException:
            logger.warning("AI Orchestrator request timed out")
            return {
                "content": "",
                "error": "Request timed out",
                "provider": "none",
                "model": "none"
            }
        except Exception as e:
            logger.error(f"Unexpected error calling AI Orchestrator: {str(e)}")
            return {
                "content": "",
                "error": str(e),
                "provider": "none",
                "model": "none"
            }
    
    async def complete_marketing(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.8,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Specialized method for marketing content generation
        Automatically routes to providers without safety filters
        
        Args:
            prompt: The marketing prompt
            context: Additional context (brand, client, etc.)
            temperature: Creativity level (default higher for marketing)
            max_tokens: Maximum response length
            
        Returns:
            Dict containing response content and metadata
        """
        messages = [
            {"role": "system", "content": "You are an expert marketing copywriter."},
            {"role": "user", "content": prompt}
        ]
        
        # Marketing content automatically routes to Gemini 2.0 Flash
        # to avoid safety filter issues
        return await self.complete(
            messages=messages,
            provider="auto",  # Orchestrator detects marketing content
            temperature=temperature,
            max_tokens=max_tokens,
            context=context
        )
    
    async def get_models(self) -> Dict[str, Any]:
        """
        Get available models from the AI Orchestrator
        
        Returns:
            Dict containing available models by provider
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/ai/models"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get models: HTTP {response.status_code}")
                    return {"models": {}}
                    
        except Exception as e:
            logger.error(f"Error fetching models: {str(e)}")
            return {"models": {}}
    
    async def refresh_models(self) -> bool:
        """
        Refresh the model catalog in the orchestrator
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/models/refresh"
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error refreshing models: {str(e)}")
            return False
    
    async def get_health(self) -> Dict[str, Any]:
        """
        Check health of the AI Orchestrator
        
        Returns:
            Dict containing health status
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/ai/health"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error checking orchestrator health: {str(e)}")
            return {"status": "unavailable", "error": str(e)}


# Singleton instance
_orchestrator_client = None

def get_orchestrator_client() -> AIOrchestratorClient:
    """Get or create the singleton orchestrator client"""
    global _orchestrator_client
    if _orchestrator_client is None:
        _orchestrator_client = AIOrchestratorClient()
    return _orchestrator_client


# Convenience function for direct completion
async def ai_complete(
    messages: List[Dict[str, str]],
    provider: str = "auto",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function for simple AI completions
    
    Returns just the content string, not the full response
    """
    client = get_orchestrator_client()
    response = await client.complete(
        messages=messages,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        context=context
    )
    
    if response.get("error"):
        logger.error(f"AI completion error: {response['error']}")
        return ""
    
    return response.get("content", "")