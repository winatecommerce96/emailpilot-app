"""
Provider-agnostic usage tracer for token metering.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, date
from dataclasses import dataclass, asdict
import tiktoken
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from google.cloud import firestore
from google.cloud.firestore import SERVER_TIMESTAMP, Increment

from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage data."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = False
    
    @property
    def input_cost_usd(self) -> float:
        """Calculate input cost in USD."""
        # Simplified pricing - should be configurable
        return self.prompt_tokens * 0.000001
    
    @property
    def output_cost_usd(self) -> float:
        """Calculate output cost in USD."""
        # Simplified pricing - should be configurable
        return self.completion_tokens * 0.000002


class UsageTracer(BaseCallbackHandler):
    """
    Traces LLM usage across providers and emits events.
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        brand: Optional[str] = None,
        run_id: Optional[str] = None,
        agent: Optional[str] = None,
        node: Optional[str] = None,
        db: Optional[Any] = None
    ):
        """Initialize tracer."""
        self.user_id = user_id
        self.brand = brand
        self.run_id = run_id
        self.agent = agent
        self.node = node
        self.start_time = None
        self.config = get_config()
        
        self.db = db
        if not self.db and self.config.firestore_project:
            self.db = firestore.Client(project=self.config.firestore_project)
        
        # Track usage for this session
        self.session_usage = TokenUsage()
        self.events: List[Dict[str, Any]] = []
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts."""
        self.start_time = time.time()
        logger.debug(f"LLM start for run {self.run_id}, agent {self.agent}, node {self.node}")
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM ends."""
        latency_ms = int((time.time() - self.start_time) * 1000) if self.start_time else 0
        
        # Extract usage from response
        usage = self._extract_usage(response)
        
        # Update session totals
        self.session_usage.prompt_tokens += usage.prompt_tokens
        self.session_usage.completion_tokens += usage.completion_tokens
        self.session_usage.total_tokens += usage.total_tokens
        
        # Detect provider and model
        provider, model = self._detect_provider_model(response)
        
        # Create event
        event = {
            "ts": datetime.utcnow(),
            "user_id": self.user_id,
            "brand": self.brand,
            "run_id": self.run_id,
            "agent": self.agent,
            "node": self.node,
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "input_cost_usd": usage.input_cost_usd,
            "output_cost_usd": usage.output_cost_usd,
            "latency_ms": latency_ms,
            "tool_calls": 0,  # TODO: Track tool calls
            "request_id": kwargs.get("run_id"),
            "estimated": usage.estimated,
            "ttl_ts": datetime.utcnow()  # TTL for auto-cleanup
        }
        
        self.events.append(event)
        
        # Emit to Firestore
        if self.db:
            try:
                self.db.collection("token_usage_events").add(event)
                logger.debug(f"Emitted usage event: {usage.total_tokens} tokens")
            except Exception as e:
                logger.error(f"Failed to emit usage event: {e}")
    
    def _extract_usage(self, response: LLMResult) -> TokenUsage:
        """Extract usage from LLM response."""
        usage = TokenUsage()
        
        # Try to get usage from response
        if hasattr(response, "llm_output") and response.llm_output:
            llm_output = response.llm_output
            
            # OpenAI format
            if "token_usage" in llm_output:
                token_usage = llm_output["token_usage"]
                usage.prompt_tokens = token_usage.get("prompt_tokens", 0)
                usage.completion_tokens = token_usage.get("completion_tokens", 0)
                usage.total_tokens = token_usage.get("total_tokens", 0)
            
            # Anthropic format
            elif "usage" in llm_output:
                token_usage = llm_output["usage"]
                usage.prompt_tokens = token_usage.get("input_tokens", 0)
                usage.completion_tokens = token_usage.get("output_tokens", 0)
                usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        
        # If no usage data, estimate
        if usage.total_tokens == 0 and response.generations:
            usage = self._estimate_usage(response)
            usage.estimated = True
        
        return usage
    
    def _estimate_usage(self, response: LLMResult) -> TokenUsage:
        """Estimate token usage using tiktoken."""
        usage = TokenUsage(estimated=True)
        
        try:
            # Use cl100k_base encoding (GPT-4/3.5)
            encoding = tiktoken.get_encoding("cl100k_base")
            
            # Estimate from generations
            for generation_list in response.generations:
                for generation in generation_list:
                    text = generation.text if hasattr(generation, "text") else str(generation)
                    usage.completion_tokens += len(encoding.encode(text))
            
            # Rough estimate for prompt (assume 2:1 ratio)
            usage.prompt_tokens = usage.completion_tokens * 2
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
            
        except Exception as e:
            logger.warning(f"Failed to estimate tokens: {e}")
            # Fallback to character count / 4
            for generation_list in response.generations:
                for generation in generation_list:
                    text = generation.text if hasattr(generation, "text") else str(generation)
                    usage.completion_tokens += len(text) // 4
            usage.prompt_tokens = usage.completion_tokens * 2
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        
        return usage
    
    def _detect_provider_model(self, response: LLMResult) -> tuple[str, str]:
        """Detect provider and model from response."""
        provider = "unknown"
        model = "unknown"
        
        if hasattr(response, "llm_output") and response.llm_output:
            llm_output = response.llm_output
            
            # Try to detect from model name
            model_name = llm_output.get("model_name", "")
            
            if "gpt" in model_name.lower():
                provider = "openai"
                model = model_name
            elif "claude" in model_name.lower():
                provider = "anthropic"
                model = model_name
            elif "gemini" in model_name.lower():
                provider = "gemini"
                model = model_name
        
        return provider, model
    
    def flush(self) -> None:
        """Flush events and update daily aggregates."""
        if not self.db or not self.events:
            return
        
        try:
            # Group events by date/user/brand
            daily_groups: Dict[tuple, TokenUsage] = {}
            
            for event in self.events:
                key = (
                    event["ts"].date(),
                    event.get("user_id"),
                    event.get("brand")
                )
                
                if key not in daily_groups:
                    daily_groups[key] = TokenUsage()
                
                usage = daily_groups[key]
                usage.prompt_tokens += event["prompt_tokens"]
                usage.completion_tokens += event["completion_tokens"]
                usage.total_tokens += event["total_tokens"]
            
            # Update daily aggregates
            for (date_key, user_id, brand), usage in daily_groups.items():
                doc_id = f"{date_key}_{user_id or 'global'}_{brand or 'all'}"
                
                doc_ref = self.db.collection("token_usage_daily").document(doc_id)
                
                # Atomic increment
                doc_ref.set({
                    "date": date_key,
                    "user_id": user_id,
                    "brand": brand,
                    "totals": {
                        "prompt_tokens": Increment(usage.prompt_tokens),
                        "completion_tokens": Increment(usage.completion_tokens),
                        "total_tokens": Increment(usage.total_tokens),
                        "input_cost_usd": Increment(usage.input_cost_usd),
                        "output_cost_usd": Increment(usage.output_cost_usd)
                    },
                    "updated_at": SERVER_TIMESTAMP
                }, merge=True)
                
                logger.info(f"Updated daily usage for {doc_id}: +{usage.total_tokens} tokens")
        
        except Exception as e:
            logger.error(f"Failed to flush usage: {e}")
        
        finally:
            self.events.clear()


def create_usage_tracer(**kwargs) -> UsageTracer:
    """Factory function to create usage tracer."""
    return UsageTracer(**kwargs)