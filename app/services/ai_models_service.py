"""
AI Models Service
Integrates AI model management with prompt templates and AgentService
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
from google.cloud import firestore
import openai
import google.generativeai as genai
from anthropic import Anthropic
import os
import json

from app.deps import get_db
from app.deps.secrets import get_secret_manager_service

if TYPE_CHECKING:
    from app.services.secrets import SecretManagerService

logger = logging.getLogger(__name__)

class AIModelsService:
    def __init__(self, db: firestore.Client, secret_manager: "SecretManagerService"):
        self.db = db
        self.secret_manager = secret_manager
        self._api_clients = {}
        self._prompts_cache = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize API clients for each provider using new Secret Manager methods"""
        try:
            # Initialize OpenAI
            try:
                openai_key = self.secret_manager.get_ai_provider_key("OPENAI_API_KEY")
                if openai_key:
                    from openai import OpenAI
                    self._api_clients["openai"] = OpenAI(api_key=openai_key)
                    logger.info("OpenAI client initialized with v1.0+ API")
                else:
                    logger.info("No OpenAI API key found")
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI: {e}")
            
            # Initialize Gemini  
            try:
                gemini_key = self.secret_manager.get_ai_provider_key("GOOGLE_API_KEY")
                if gemini_key:
                    genai.configure(api_key=gemini_key)
                    self._api_clients["gemini"] = genai
                    logger.info("Gemini client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini: {e}")
            
            # Initialize Claude
            try:
                claude_key = self.secret_manager.get_ai_provider_key("ANTHROPIC_API_KEY")
                if claude_key:
                    self._api_clients["claude"] = Anthropic(api_key=claude_key)
                    logger.info("Claude client initialized")
                else:
                    logger.info("No Anthropic API key found")
            except Exception as e:
                logger.warning(f"Could not initialize Claude: {e}")
                
        except Exception as e:
            logger.error(f"Error initializing API clients: {e}")
    
    async def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get a prompt template from Firestore"""
        try:
            # Check cache first
            if prompt_id in self._prompts_cache:
                return self._prompts_cache[prompt_id]
            
            doc = self.db.collection("ai_prompts").document(prompt_id).get()
            if doc.exists:
                prompt_data = doc.to_dict()
                prompt_data["id"] = doc.id
                self._prompts_cache[prompt_id] = prompt_data
                return prompt_data
            return None
        except Exception as e:
            logger.error(f"Error fetching prompt {prompt_id}: {e}")
            return None
    
    async def get_prompts_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all prompts for a specific category"""
        try:
            prompts = []
            docs = self.db.collection("ai_prompts").where("category", "==", category).where("active", "==", True).stream()
            for doc in docs:
                prompt_data = doc.to_dict()
                prompt_data["id"] = doc.id
                prompts.append(prompt_data)
            return prompts
        except Exception as e:
            logger.error(f"Error fetching prompts for category {category}: {e}")
            return []
    
    def render_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """Render a prompt template with variables"""
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        return rendered
    
    async def execute_prompt(
        self, 
        prompt_id: str, 
        variables: Dict[str, Any], 
        override_provider: Optional[str] = None,
        override_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a prompt with the configured AI model"""
        try:
            # Get the prompt template
            prompt_data = await self.get_prompt(prompt_id)
            if not prompt_data:
                return {
                    "success": False,
                    "error": f"Prompt {prompt_id} not found"
                }
            
            # Render the prompt with variables
            rendered_prompt = self.render_prompt(prompt_data["prompt_template"], variables)
            
            # Determine provider and model
            provider = override_provider or prompt_data.get("model_provider", "gemini")
            model = override_model or prompt_data.get("model_name")
            
            # Check if provider is available
            if provider not in self._api_clients:
                return {
                    "success": False,
                    "error": f"Provider {provider} not configured or API key missing"
                }
            
            # Execute based on provider
            response = None
            if provider == "openai":
                response = await self._execute_openai(rendered_prompt, model or "gpt-4")
            elif provider == "gemini":
                response = await self._execute_gemini(rendered_prompt, model or "gemini-1.5-pro-latest")
            elif provider == "claude":
                response = await self._execute_claude(rendered_prompt, model or "claude-3-5-sonnet-20241022")
            else:
                return {
                    "success": False,
                    "error": f"Unknown provider: {provider}"
                }
            
            # Update usage statistics on prompt doc
            now = datetime.utcnow()
            self.db.collection("ai_prompts").document(prompt_id).update({
                "last_used": now,
                "usage_count": firestore.Increment(1)
            })

            # Log usage entry for richer stats (user/client breakdown)
            try:
                usage_entry = {
                    "timestamp": now,
                    "prompt_id": prompt_id,
                    "provider": provider,
                    "model": model,
                    "user_id": variables.get("user_id"),
                    "client_id": variables.get("client_id") or variables.get("account_id") or variables.get("metric_id"),
                }
                self.db.collection("ai_prompt_usage").add(usage_entry)
            except Exception as log_err:
                logger.warning(f"Failed to log prompt usage: {log_err}")
            
            return {
                "success": True,
                "response": response,
                "provider": provider,
                "model": model,
                "prompt_id": prompt_id,
                "rendered_prompt": rendered_prompt
            }
            
        except Exception as e:
            logger.error(f"Error executing prompt {prompt_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_openai(self, prompt: str, model: str) -> str:
        """Execute prompt with OpenAI"""
        try:
            client = self._api_clients["openai"]
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant for EmailPilot."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI execution error: {e}")
            raise
    
    async def _execute_gemini(self, prompt: str, model: str) -> str:
        """Execute prompt with Gemini"""
        try:
            genai_client = self._api_clients["gemini"]
            model_instance = genai_client.GenerativeModel(model)
            
            # Add instruction to ensure conversational response
            enhanced_prompt = "Please respond conversationally to the following request:\n\n" + prompt
            
            response = model_instance.generate_content(enhanced_prompt)
            
            # Extract text from response
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text')]
                    response_text = ''.join(text_parts)
            
            return response_text
        except Exception as e:
            logger.error(f"Gemini execution error: {e}")
            raise
    
    async def _execute_claude(self, prompt: str, model: str) -> str:
        """Execute prompt with Claude"""
        try:
            client = self._api_clients["claude"]
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude execution error: {e}")
            raise
    
    async def execute_agent_prompt(
        self,
        agent_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a prompt specifically for an agent"""
        try:
            # Find the appropriate prompt for this agent
            prompts = await self.get_prompts_by_category("agent")
            agent_prompt = None
            
            for prompt in prompts:
                # Check if this prompt matches the agent type
                metadata = prompt.get("metadata", {})
                if metadata.get("agent_type") == agent_type:
                    agent_prompt = prompt
                    break
            
            if not agent_prompt:
                # Fallback to default agent prompt
                logger.warning(f"No specific prompt found for agent {agent_type}, using default")
                return {
                    "success": False,
                    "error": f"No prompt configured for agent {agent_type}"
                }
            
            # Execute the prompt with context
            result = await self.execute_prompt(
                prompt_id=agent_prompt["id"],
                variables=context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing agent prompt for {agent_type}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def complete(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Unified method to complete a chat conversation using any provider.
        
        Args:
            provider: AI provider (openai, claude, gemini)
            model: Model name specific to provider
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0, clamped)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict with success, response, usage, warnings, and error fields
        """
        warnings = []
        
        try:
            # Check if provider is available
            if provider not in self._api_clients:
                return {
                    "success": False,
                    "error": f"Provider {provider} not configured or API key missing"
                }
            
            # Validate and clamp temperature (0.0-1.0 for all providers)
            if temperature is None:
                temperature = 0.7
            else:
                original_temp = temperature
                temperature = max(0.0, min(1.0, float(temperature)))
                if temperature != original_temp:
                    warnings.append(f"Temperature clamped from {original_temp} to {temperature}")
            
            # Set and validate max_tokens
            if max_tokens is None:
                max_tokens = 512
            else:
                original_tokens = max_tokens
                # Provider-specific limits
                if provider == "openai":
                    max_limit = 4096 if "gpt-4" not in model else 8192
                elif provider == "gemini":
                    max_limit = 8192
                elif provider == "claude":
                    max_limit = 8192 if "3-5" in model else 4096
                else:
                    max_limit = 4096
                
                max_tokens = max(1, min(max_limit, int(max_tokens)))
                if max_tokens != original_tokens:
                    warnings.append(f"Max tokens clamped from {original_tokens} to {max_tokens}")
            
            # Handle unsupported parameters
            unsupported_params = []
            if provider == "claude":
                # Claude doesn't support these
                for param in ["top_k", "frequency_penalty", "presence_penalty"]:
                    if param in kwargs:
                        unsupported_params.append(param)
                        del kwargs[param]
            elif provider == "gemini":
                # Gemini has different param names
                for param in ["frequency_penalty", "presence_penalty", "logprobs"]:
                    if param in kwargs:
                        unsupported_params.append(param)
                        del kwargs[param]
            
            if unsupported_params:
                warnings.append(f"Dropped unsupported params for {provider}: {', '.join(unsupported_params)}")
            
            response_text = ""
            usage = {}
            
            if provider == "openai":
                response_text, usage = await self._complete_openai(
                    messages, model, temperature, max_tokens
                )
            elif provider == "gemini":
                response_text, usage = await self._complete_gemini(
                    messages, model, temperature, max_tokens
                )
                # Add any Gemini-specific warnings from usage.meta
                if usage.get("meta"):
                    meta = usage.pop("meta")
                    if meta.get("warning"):
                        warnings.append(meta["warning"])
                    if meta.get("finish_reason"):
                        warnings.append(f"Finish reason: {meta['finish_reason']}")
            elif provider == "claude":
                response_text, usage = await self._complete_claude(
                    messages, model, temperature, max_tokens
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown provider: {provider}"
                }
            
            return {
                "success": True,
                "response": response_text,
                "provider": provider,
                "model": model,
                "usage": usage,
                "warnings": warnings if warnings else None
            }
            
        except Exception as e:
            logger.error(f"Complete error for {provider}/{model}: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": provider,
                "model": model
            }
    
    async def _complete_openai(
        self, messages: List[Dict], model: str, temperature: float, max_tokens: int
    ) -> tuple[str, Dict]:
        """Complete using OpenAI v1.0+ API"""
        try:
            client = self._api_clients.get("openai")
            if not client:
                raise ValueError("OpenAI client not initialized")
            
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            usage = {
                "input_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                "output_tokens": response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                "provider_raw": response.usage.model_dump() if hasattr(response.usage, 'model_dump') else {}
            }
            
            return response.choices[0].message.content, usage
            
        except Exception as e:
            logger.error(f"OpenAI complete error: {e}")
            raise
    
    def _gemini_extract_text(self, response) -> tuple[str, dict]:
        """Safely extract text from Gemini response without assuming response.text exists"""
        response_text = ""
        warnings = {}
        
        try:
            # Check if we have candidates
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Check finish_reason (2 = SAFETY, 3 = MAX_TOKENS, etc)
                finish_reason = getattr(candidate, 'finish_reason', None)
                if finish_reason and finish_reason != 1:  # 1 = STOP (normal completion)
                    finish_reason_map = {
                        2: "SAFETY",
                        3: "MAX_TOKENS", 
                        4: "RECITATION",
                        5: "OTHER"
                    }
                    warnings['finish_reason'] = finish_reason_map.get(finish_reason, f"UNKNOWN_{finish_reason}")
                    warnings['warning'] = f"Model ended early: {warnings['finish_reason']}"
                
                # Extract text from parts safely
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
                
            # Try the simple accessor as fallback (but don't fail if it doesn't work)
            if not response_text:
                try:
                    if hasattr(response, 'text'):
                        response_text = response.text
                except Exception:
                    pass  # Ignore if quick accessor fails
            
            # If still no text, return a message
            if not response_text:
                response_text = "[No text returned by model]"
                if not warnings:
                    warnings['warning'] = "Model returned no text content"
                    
        except Exception as e:
            logger.warning(f"Failed to extract text from Gemini response: {e}")
            response_text = "[Error extracting model response]"
            warnings['error'] = str(e)
            
        return response_text, warnings
    
    async def _complete_gemini(
        self, messages: List[Dict], model: str, temperature: float, max_tokens: int
    ) -> tuple[str, Dict]:
        """Complete using Gemini - intelligent fallback for marketing content"""
        try:
            # Check if this looks like marketing content
            content = " ".join([m.get("content", "") for m in messages]).lower()
            is_marketing = any(term in content for term in [
                "email", "marketing", "campaign", "sale", "discount", "promotion",
                "subject line", "copy", "brief", "ecommerce", "subscribe"
            ])
            
            # For marketing content, use the most reliable model order
            if is_marketing:
                fallback_models = [
                    "gemini-2.0-flash",      # Most reliable for marketing
                    "gemini-1.5-pro-002",    # Good alternative
                    "gemini-1.5-flash-002",  # Fast alternative
                    model                    # Original requested model
                ]
                # Remove duplicates while preserving order
                fallback_models = list(dict.fromkeys(fallback_models))
                
                # Ensure sufficient tokens for marketing content
                marketing_max_tokens = max(max_tokens, 2000)  # At least 2000 tokens for marketing
                
                last_error = None
                for try_model in fallback_models:
                    try:
                        logger.info(f"Trying model {try_model} for marketing content")
                        # Always try new SDK first for each model
                        try:
                            return await self._complete_gemini_new_sdk(messages, try_model, temperature, marketing_max_tokens)
                        except Exception as e:
                            # Try old SDK as backup
                            return await self._complete_gemini_old_sdk(messages, try_model, temperature, marketing_max_tokens)
                    except Exception as e:
                        last_error = e
                        logger.debug(f"Model {try_model} failed: {e}")
                        continue
                
                # If all models failed, raise the last error
                if last_error:
                    raise last_error
            
            # For non-marketing content, use standard flow
            try:
                return await self._complete_gemini_new_sdk(messages, model, temperature, max_tokens)
            except Exception as e:
                logger.info(f"New SDK failed, falling back to old SDK: {e}")
                return await self._complete_gemini_old_sdk(messages, model, temperature, max_tokens)
                
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise
    
    async def _complete_gemini_new_sdk(
        self, messages: List[Dict], model: str, temperature: float, max_tokens: int
    ) -> tuple[str, Dict]:
        """Complete using new google-genai SDK (no safety filters)"""
        try:
            from google import genai
            from google.genai import types
            
            # Get API key
            if self.secret_manager:
                api_key = self.secret_manager.get_secret("gemini-api-key")
            else:
                import os
                api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                raise ValueError("No Gemini API key available")
            
            # Create client
            client = genai.Client(api_key=api_key)
            
            # Convert messages to new SDK format
            contents = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Map roles: system -> user with prefix, assistant -> model
                if role == "system":
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=f"System instruction: {content}")]
                    ))
                elif role == "assistant":
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=content)]
                    ))
                else:
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=content)]
                    ))
            
            # Configure generation
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                # No safety settings - they're not needed in new SDK
            )
            
            # Generate response (non-streaming for simplicity)
            response_text = ""
            usage = {"input_tokens": 0, "output_tokens": 0}
            
            # Use non-streaming for complete response
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model.replace("models/", ""),
                contents=contents,
                config=config
            )
            
            # Extract text from response
            if response and response.candidates and response.candidates[0].content:
                if response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
            
            # Get usage metadata
            if hasattr(response, 'usage_metadata'):
                meta = response.usage_metadata
                if hasattr(meta, 'prompt_token_count'):
                    usage["input_tokens"] = meta.prompt_token_count
                if hasattr(meta, 'candidates_token_count'):
                    usage["output_tokens"] = meta.candidates_token_count
            
            # Estimate tokens if not provided
            if usage["input_tokens"] == 0:
                usage["input_tokens"] = sum(len(m.get("content", "").split()) for m in messages) * 1.3
            if usage["output_tokens"] == 0:
                usage["output_tokens"] = int(len(response_text.split()) * 1.3)
            
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
            usage["provider_raw"] = {"sdk": "google-genai"}
            
            return response_text, usage
            
        except Exception as e:
            logger.debug(f"New SDK error: {e}")
            raise
    
    async def _complete_gemini_old_sdk(
        self, messages: List[Dict], model: str, temperature: float, max_tokens: int
    ) -> tuple[str, Dict]:
        """Complete using original google-generativeai SDK"""
        try:
            # Initialize model with the official SDK
            import google.generativeai as genai
            
            # Ensure API key is configured
            if "gemini" not in self._api_clients:
                raise ValueError("Gemini API key not configured")
            
            # Create model instance with specific model ID
            # Remove "models/" prefix if present
            model_id = model.replace("models/", "")
            model_instance = genai.GenerativeModel(model_id)
            
            # Convert messages to proper conversation format
            # Gemini SDK expects a different format for multi-turn conversations
            contents = []
            system_instruction = None
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    # Gemini uses system instructions separately
                    if system_instruction:
                        system_instruction += "\n" + content
                    else:
                        system_instruction = content
                elif role == "assistant":
                    # Model responses in the conversation
                    contents.append({
                        "role": "model",
                        "parts": [{"text": content}]
                    })
                else:
                    # User messages
                    contents.append({
                        "role": "user", 
                        "parts": [{"text": content}]
                    })
            
            # If we have system instructions, prepend them to the first user message
            if system_instruction and contents:
                if contents[0]["role"] == "user":
                    original_content = contents[0]["parts"][0]["text"]
                    contents[0]["parts"][0]["text"] = f"{system_instruction}\n\n{original_content}"
                else:
                    # Insert system instruction as first user message
                    contents.insert(0, {
                        "role": "user",
                        "parts": [{"text": system_instruction}]
                    })
            
            # Create generation config with SDK types
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                candidate_count=1,  # Only generate one response
            )
            
            # REMOVE ALL SAFETY FILTERS - Set everything to BLOCK_NONE
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            # Disable ALL safety filters for ALL Gemini models
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Generate content using the SDK - NO SAFETY FILTERING
            if len(contents) == 1 and contents[0]["role"] == "user":
                # Single turn - use simple generate_content
                response = await asyncio.to_thread(
                    model_instance.generate_content,
                    contents[0]["parts"][0]["text"],
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            else:
                # Multi-turn - use chat session
                chat = model_instance.start_chat(history=contents[:-1] if contents else [])
                last_message = contents[-1]["parts"][0]["text"] if contents else "Hello"
                response = await asyncio.to_thread(
                    chat.send_message,
                    last_message,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            
            # Extract text safely
            response_text = ""
            warnings = {}
            
            try:
                # First try the simple text property
                if hasattr(response, 'text'):
                    response_text = response.text
            except Exception as e:
                # If text property fails, extract manually
                error_msg = str(e)
                if "response.text" in error_msg and "blocked" in error_msg.lower():
                    warnings['warning'] = "Response blocked by safety filters"
                    warnings['finish_reason'] = "SAFETY"
                
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    
                    # Check finish reason
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        # Map finish reason to readable string
                        finish_reason_str = str(finish_reason)
                        if "SAFETY" in finish_reason_str or finish_reason_str == "2":
                            # Safety block detected - this shouldn't happen with BLOCK_NONE
                            warnings['finish_reason'] = "SAFETY"
                            warnings['warning'] = "Model-level safety filter triggered (cannot be disabled). Try Gemini 2.5 Flash or 2.0 Flash instead."
                            # Try to get partial text if available
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        response_text += part.text
                            if not response_text:
                                # Provide helpful message about alternatives
                                response_text = "[Model blocked response. Gemini 2.5 Pro has built-in filters that cannot be disabled. Please use Gemini 2.5 Flash or 2.0 Flash instead, which work reliably.]"
                        elif finish_reason_str != "STOP" and finish_reason_str != "1":
                            warnings['finish_reason'] = finish_reason_str
                            warnings['warning'] = f"Generation ended: {finish_reason_str}"
                    
                    # Extract text from content parts if not already done
                    if not response_text and hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                response_text += part.text
            
            if not response_text:
                response_text = "[No response generated]"
                warnings['warning'] = "Model returned empty response"
            
            # Get token counts if available
            usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "provider_raw": {}
            }
            
            # Try to get usage metadata from response
            if hasattr(response, 'usage_metadata'):
                usage_meta = response.usage_metadata
                if hasattr(usage_meta, 'prompt_token_count'):
                    usage["input_tokens"] = usage_meta.prompt_token_count
                if hasattr(usage_meta, 'candidates_token_count'):
                    usage["output_tokens"] = usage_meta.candidates_token_count
            
            # Fallback: estimate tokens if not provided
            if usage["input_tokens"] == 0:
                prompt_text = " ".join([c["parts"][0]["text"] for c in contents if "parts" in c])
                usage["input_tokens"] = int(len(prompt_text.split()) * 1.3)
            if usage["output_tokens"] == 0:
                usage["output_tokens"] = int(len(response_text.split()) * 1.3)
            
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
            
            if warnings:
                usage["meta"] = warnings
            
            return response_text, usage
            
        except Exception as e:
            logger.error(f"Gemini SDK error: {e}")
            raise
    
    async def _complete_claude(
        self, messages: List[Dict], model: str, temperature: float, max_tokens: int
    ) -> tuple[str, Dict]:
        """Complete using Claude"""
        try:
            client = self._api_clients["claude"]
            
            # Claude expects messages without system role in messages array
            # System content goes in the system parameter
            system_content = ""
            claude_messages = []
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    system_content += content + "\n"
                else:
                    # Claude only accepts user and assistant roles
                    claude_messages.append({
                        "role": role if role in ["user", "assistant"] else "user",
                        "content": content
                    })
            
            # Make the API call
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": claude_messages
            }
            
            if system_content:
                kwargs["system"] = system_content.strip()
            
            response = await asyncio.to_thread(
                client.messages.create,
                **kwargs
            )
            
            # Extract usage info
            usage = {
                "input_tokens": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                "output_tokens": response.usage.output_tokens if hasattr(response, 'usage') else 0,
                "provider_raw": {}
            }
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
            
            return response.content[0].text, usage
            
        except Exception as e:
            logger.error(f"Claude complete error: {e}")
            raise
    
    def update_api_key(self, provider: str, api_key: str):
        """Update API key for a provider and reinitialize client"""
        try:
            # Map provider to secret name
            secret_map = {
                "openai": "openai-api-key",
                "gemini": "gemini-api-key",
                "claude": "emailpilot-claude"
            }
            
            if provider not in secret_map:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Update secret in Secret Manager
            secret_name = secret_map[provider]
            self.secret_manager.create_or_update_secret(secret_name, api_key)
            
            # Reinitialize the specific client
            if provider == "openai":
                from openai import OpenAI
                self._api_clients["openai"] = OpenAI(api_key=api_key)
            elif provider == "gemini":
                genai.configure(api_key=api_key)
                self._api_clients["gemini"] = genai
            elif provider == "claude":
                self._api_clients["claude"] = Anthropic(api_key=api_key)
            
            logger.info(f"Updated API key for {provider}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating API key for {provider}: {e}")
            raise

def get_ai_models_service(
    db: firestore.Client = None,
    secret_manager: SecretManagerService = None
) -> AIModelsService:
    """Factory function to get an instance of the AIModelsService"""
    if not db:
        db = get_db()
    if not secret_manager:
        secret_manager = get_secret_manager_service()
    return AIModelsService(db, secret_manager)
