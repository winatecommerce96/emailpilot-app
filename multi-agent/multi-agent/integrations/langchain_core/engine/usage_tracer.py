"""
Usage tracking for LangChain operations.
Records LLM calls, tokens, and costs to Firestore.
"""
import time
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import firestore

class UsageTracer:
    """Tracks LLM usage and saves to Firestore."""
    
    def __init__(self):
        """Initialize the usage tracer."""
        try:
            self.db = firestore.Client()
            self.collection = self.db.collection('langchain_usage')
        except Exception:
            # Fallback if Firestore not available
            self.db = None
            self.collection = None
            self.in_memory = []
    
    def record_llm_call(
        self,
        model: str,
        provider: str,
        operation: str,
        tokens_input: int,
        tokens_output: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        brand: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an LLM call.
        
        Args:
            model: Model name (e.g., "gpt-4")
            provider: Provider name (e.g., "openai")
            operation: Operation type (e.g., "rag_query", "agent_run")
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            duration_ms: Duration in milliseconds
            user_id: Optional user ID
            brand: Optional brand context
            metadata: Additional metadata
            
        Returns:
            Document ID of the recorded usage
        """
        doc = {
            "timestamp": datetime.utcnow(),
            "model": model,
            "provider": provider,
            "operation": operation,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "tokens_total": tokens_input + tokens_output,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "brand": brand,
            "metadata": metadata or {},
            "cost_estimate": self._estimate_cost(
                provider, model, tokens_input, tokens_output
            )
        }
        
        if self.collection:
            # Save to Firestore
            ref = self.collection.add(doc)[1]
            return ref.id
        else:
            # Save to memory
            doc["id"] = f"mock_{int(time.time() * 1000)}"
            self.in_memory.append(doc)
            return doc["id"]
    
    def _estimate_cost(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """Estimate cost based on provider pricing."""
        # Simplified pricing (per 1K tokens)
        pricing = {
            "openai": {
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
            },
            "anthropic": {
                "claude-3-opus": {"input": 0.015, "output": 0.075},
                "claude-3-sonnet": {"input": 0.003, "output": 0.015},
                "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
            }
        }
        
        if provider in pricing:
            for model_key in pricing[provider]:
                if model_key in model.lower():
                    rates = pricing[provider][model_key]
                    cost_input = (tokens_input / 1000) * rates["input"]
                    cost_output = (tokens_output / 1000) * rates["output"]
                    return round(cost_input + cost_output, 6)
        
        return 0.0
    
    def get_usage_summary(
        self,
        user_id: Optional[str] = None,
        brand: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage summary for a user or brand.
        
        Args:
            user_id: Optional user ID filter
            brand: Optional brand filter
            days: Number of days to look back
            
        Returns:
            Usage summary with totals and breakdown
        """
        if self.collection:
            # Query Firestore
            query = self.collection
            
            if user_id:
                query = query.where("user_id", "==", user_id)
            if brand:
                query = query.where("brand", "==", brand)
            
            # Time filter
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where("timestamp", ">=", cutoff)
            
            docs = query.stream()
            usage = list(docs)
        else:
            # Use in-memory data
            usage = self.in_memory
            if user_id:
                usage = [u for u in usage if u.get("user_id") == user_id]
            if brand:
                usage = [u for u in usage if u.get("brand") == brand]
        
        # Calculate summary
        total_tokens = sum(u.get("tokens_total", 0) for u in usage)
        total_cost = sum(u.get("cost_estimate", 0) for u in usage)
        total_calls = len(usage)
        
        # Group by model
        by_model = {}
        for u in usage:
            model = u.get("model", "unknown")
            if model not in by_model:
                by_model[model] = {"calls": 0, "tokens": 0, "cost": 0}
            by_model[model]["calls"] += 1
            by_model[model]["tokens"] += u.get("tokens_total", 0)
            by_model[model]["cost"] += u.get("cost_estimate", 0)
        
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 2),
            "by_model": by_model,
            "period_days": days,
            "user_id": user_id,
            "brand": brand
        }


# Global tracer instance
_tracer = None

def get_tracer() -> UsageTracer:
    """Get the global usage tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = UsageTracer()
    return _tracer