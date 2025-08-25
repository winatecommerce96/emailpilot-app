"""
Direct AI Provider Integration for Copywriting Module
Handles OpenAI, Anthropic (Claude), and Google (Gemini) directly
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)

@dataclass
class AIProvider:
    """Configuration for an AI provider"""
    name: str
    api_key_env: str
    base_url: str
    is_available: bool = False
    error_message: Optional[str] = None

class DirectAIService:
    """Direct AI provider service - bypasses MCP when needed"""
    
    def __init__(self):
        self.providers = self._initialize_providers()
        self._probe_providers()
    
    def _initialize_providers(self) -> Dict[str, AIProvider]:
        """Initialize provider configurations"""
        return {
            "openai": AIProvider(
                name="OpenAI",
                api_key_env="OPENAI_API_KEY",
                base_url="https://api.openai.com/v1"
            ),
            "anthropic": AIProvider(
                name="Anthropic",
                api_key_env="ANTHROPIC_API_KEY", 
                base_url="https://api.anthropic.com/v1"
            ),
            "google": AIProvider(
                name="Google",
                api_key_env="GOOGLE_API_KEY",
                base_url="https://generativelanguage.googleapis.com/v1beta"
            )
        }
    
    def _probe_providers(self):
        """Probe each provider to check availability"""
        for provider_id, provider in self.providers.items():
            api_key = os.getenv(provider.api_key_env)
            if not api_key:
                provider.is_available = False
                provider.error_message = f"API key not found in {provider.api_key_env}"
                logger.warning(f"{provider.name}: {provider.error_message}")
            else:
                provider.is_available = True
                logger.info(f"{provider.name}: Available (API key found)")
    
    async def invoke_openai(
        self, 
        prompt: str, 
        model: str = "gpt-3.5-turbo",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Invoke OpenAI directly using the new client format
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found")
            return {"error": "OpenAI API key not configured", "content": ""}
        
        try:
            # Use the new OpenAI API format (>=1.0.0)
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Map model names to valid OpenAI models
            model_map = {
                "gpt-4-turbo": "gpt-4-turbo-preview",
                "gpt-4": "gpt-4",
                "gpt-3.5-turbo": "gpt-3.5-turbo",
                "gpt-3.5": "gpt-3.5-turbo"
            }
            
            actual_model = model_map.get(model, "gpt-3.5-turbo")
            
            payload = {
                "model": actual_model,
                "messages": [
                    {"role": "system", "content": "You are an expert email copywriter."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            logger.info(f"Calling OpenAI {actual_model} directly")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"OpenAI response received: {len(content)} chars")
                    return {
                        "content": content,
                        "model_used": actual_model,
                        "provider": "openai"
                    }
                else:
                    logger.error(f"OpenAI error: {response.status_code} - {response.text}")
                    return {
                        "error": f"OpenAI API error: {response.status_code}",
                        "content": ""
                    }
                    
        except Exception as e:
            logger.error(f"OpenAI invocation failed: {str(e)}")
            return {"error": str(e), "content": ""}
    
    async def invoke_anthropic(
        self,
        prompt: str,
        model: str = "claude-3-haiku-20240307",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Invoke Anthropic Claude directly with correct model IDs
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("Anthropic API key not found")
            return {"error": "Anthropic API key not configured", "content": ""}
        
        try:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Map model names to valid Anthropic model IDs
            model_map = {
                "claude-3-opus": "claude-3-opus-20240229",
                "claude-3-sonnet": "claude-3-5-sonnet-20241022",  # Latest Sonnet 3.5
                "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
                "claude-3-haiku": "claude-3-haiku-20240307",
                "claude-2.1": "claude-2.1",
                "claude-2": "claude-2.0",
                "claude-instant": "claude-instant-1.2"
            }
            
            actual_model = model_map.get(model, "claude-3-haiku-20240307")
            
            payload = {
                "model": actual_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            logger.info(f"Calling Anthropic {actual_model} directly")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["content"][0]["text"]
                    logger.info(f"Anthropic response received: {len(content)} chars")
                    return {
                        "content": content,
                        "model_used": actual_model,
                        "provider": "anthropic"
                    }
                else:
                    logger.error(f"Anthropic error: {response.status_code} - {response.text}")
                    return {
                        "error": f"Anthropic API error: {response.status_code}",
                        "content": ""
                    }
                    
        except Exception as e:
            logger.error(f"Anthropic invocation failed: {str(e)}")
            return {"error": str(e), "content": ""}
    
    async def invoke_gemini(
        self,
        prompt: str,
        model: str = "gemini-pro",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Invoke Google Gemini directly
        """
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("Google/Gemini API key not found")
            return {"error": "Gemini API key not configured", "content": ""}
        
        try:
            # Map model names
            model_map = {
                "gemini-pro": "gemini-pro",
                "gemini-1.5-pro": "gemini-1.5-pro-latest",
                "gemini-1.5-flash": "gemini-1.5-flash-latest"
            }
            
            actual_model = model_map.get(model, "gemini-pro")
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{actual_model}:generateContent"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2000
                }
            }
            
            logger.info(f"Calling Gemini {actual_model} directly")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{url}?key={api_key}",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    logger.info(f"Gemini response received: {len(content)} chars")
                    return {
                        "content": content,
                        "model_used": actual_model,
                        "provider": "google"
                    }
                else:
                    logger.error(f"Gemini error: {response.status_code} - {response.text}")
                    return {
                        "error": f"Gemini API error: {response.status_code}",
                        "content": ""
                    }
                    
        except Exception as e:
            logger.error(f"Gemini invocation failed: {str(e)}")
            return {"error": str(e), "content": ""}
    
    async def invoke_model(
        self,
        prompt: str,
        model: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Route to appropriate provider based on model name
        """
        # Ensure context is always included in prompt
        if context:
            brief = context.get("brief", "")
            client_name = context.get("brand_context", {}).get("name", "")
            if brief and brief not in prompt:
                logger.warning("Brief not in prompt, adding it")
                prompt = f"Campaign Brief: {brief}\n\n{prompt}"
            if client_name and client_name not in prompt:
                logger.warning("Client not in prompt, adding it") 
                prompt = f"Client: {client_name}\n\n{prompt}"
        
        # Route based on model name
        if "gpt" in model.lower():
            return await self.invoke_openai(prompt, model, context)
        elif "claude" in model.lower():
            return await self.invoke_anthropic(prompt, model, context)
        elif "gemini" in model.lower():
            return await self.invoke_gemini(prompt, model, context)
        else:
            # Default to trying OpenAI
            logger.warning(f"Unknown model {model}, defaulting to OpenAI")
            return await self.invoke_openai(prompt, "gpt-3.5-turbo", context)
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Return list of available models based on API key presence
        """
        models = []
        
        # OpenAI models
        if self.providers["openai"].is_available:
            models.extend([
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai", "description": "Most capable OpenAI model"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai", "description": "Fast and cost-effective", "default": True}
            ])
        
        # Anthropic models
        if self.providers["anthropic"].is_available:
            models.extend([
                {"id": "claude-3-opus", "name": "Claude 3 Opus", "provider": "anthropic", "description": "Most capable Claude model"},
                {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "description": "Latest Sonnet model"},
                {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "provider": "anthropic", "description": "Fast Claude model"}
            ])
        
        # Google models
        if self.providers["google"].is_available:
            models.extend([
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "google", "description": "Advanced Gemini model"},
                {"id": "gemini-pro", "name": "Gemini Pro", "provider": "google", "description": "Standard Gemini model"}
            ])
        
        # Always provide at least one fallback
        if not models:
            models.append({
                "id": "fallback",
                "name": "Fallback (No API keys configured)",
                "provider": "local",
                "description": "Template-based generation",
                "default": True
            })
        
        return models
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            provider_id: {
                "name": provider.name,
                "available": provider.is_available,
                "error": provider.error_message
            }
            for provider_id, provider in self.providers.items()
        }