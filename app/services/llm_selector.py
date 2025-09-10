"""
LLM Selector Service

Intelligent LLM selection based on task requirements, cost, and performance.
"""
from typing import Dict, Any, Optional
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks for LLM selection"""
    QUERY_ANALYSIS = "query_analysis"
    DISCOVERY = "discovery"
    WRAPPER_GENERATION = "wrapper_generation"
    REAL_TIME = "real_time_processing"
    COMPLEX_REASONING = "complex_reasoning"
    CODE_GENERATION = "code_generation"
    SUMMARIZATION = "summarization"


class OptimizationMode(Enum):
    """Optimization modes for LLM selection"""
    SPEED = "speed"
    QUALITY = "quality"
    COST = "cost"
    BALANCED = "balanced"


class LLMSelector:
    """
    Intelligent LLM selection based on task requirements
    """
    
    def __init__(self):
        # Model capabilities (speed, quality, cost on scale of 1-10)
        self.available_models = {
            'gpt-4-turbo': {
                'speed': 7,
                'quality': 9,
                'cost': 8,  # Higher = more expensive
                'capabilities': ['code', 'reasoning', 'analysis'],
                'provider': 'openai'
            },
            'gpt-4o': {
                'speed': 8,
                'quality': 9,
                'cost': 7,
                'capabilities': ['code', 'reasoning', 'vision', 'analysis'],
                'provider': 'openai'
            },
            'gpt-4o-mini': {
                'speed': 9,
                'quality': 7,
                'cost': 3,
                'capabilities': ['code', 'reasoning', 'analysis'],
                'provider': 'openai'
            },
            'gpt-3.5-turbo': {
                'speed': 9,
                'quality': 7,
                'cost': 2,
                'capabilities': ['general', 'chat'],
                'provider': 'openai'
            },
            'claude-3-opus': {
                'speed': 6,
                'quality': 10,
                'cost': 9,
                'capabilities': ['code', 'reasoning', 'analysis', 'creative'],
                'provider': 'anthropic'
            },
            'claude-3-sonnet': {
                'speed': 8,
                'quality': 8,
                'cost': 5,
                'capabilities': ['code', 'reasoning', 'analysis'],
                'provider': 'anthropic'
            },
            'claude-3-haiku': {
                'speed': 10,
                'quality': 6,
                'cost': 1,
                'capabilities': ['general', 'chat', 'fast'],
                'provider': 'anthropic'
            },
            'gemini-1.5-pro': {
                'speed': 7,
                'quality': 8,
                'cost': 4,
                'capabilities': ['multimodal', 'long-context', 'reasoning'],
                'provider': 'google'
            },
            'gemini-1.5-flash': {
                'speed': 9,
                'quality': 6,
                'cost': 1,
                'capabilities': ['fast', 'general'],
                'provider': 'google'
            }
        }
        
        # Task-specific model preferences
        self.task_preferences = {
            TaskType.QUERY_ANALYSIS: ['claude-3-haiku', 'gpt-4o-mini', 'gemini-1.5-flash'],
            TaskType.DISCOVERY: ['claude-3-opus', 'gpt-4-turbo', 'gemini-1.5-pro'],
            TaskType.WRAPPER_GENERATION: ['gpt-4-turbo', 'claude-3-opus', 'gpt-4o'],
            TaskType.REAL_TIME: ['gemini-1.5-flash', 'claude-3-haiku', 'gpt-3.5-turbo'],
            TaskType.COMPLEX_REASONING: ['claude-3-opus', 'gpt-4o', 'gemini-1.5-pro'],
            TaskType.CODE_GENERATION: ['gpt-4-turbo', 'claude-3-opus', 'gpt-4o'],
            TaskType.SUMMARIZATION: ['claude-3-sonnet', 'gpt-4o-mini', 'gemini-1.5-pro']
        }
        
        # MCP-specific preferences
        self.mcp_preferences = {
            'klaviyo': 'claude-3-sonnet',  # Good for marketing/email data
            'stripe': 'gpt-4-turbo',  # Good for financial data
            'shopify': 'gemini-1.5-pro',  # Good for e-commerce
            'salesforce': 'gpt-4o',  # Good for CRM data
            'hubspot': 'claude-3-sonnet',  # Good for marketing
            'twilio': 'gpt-4o-mini',  # Good for communication APIs
            'sendgrid': 'claude-3-haiku',  # Fast for email operations
            'braze': 'claude-3-sonnet'  # Good for customer engagement
        }
    
    def select_for_task(self, task_type: str, 
                       optimization: OptimizationMode = OptimizationMode.BALANCED,
                       requirements: Dict[str, Any] = None) -> str:
        """
        Select best LLM for specific task
        
        Args:
            task_type: Type of task to perform
            optimization: Optimization mode (speed, quality, cost, balanced)
            requirements: Additional requirements
            
        Returns:
            Model name to use
        """
        try:
            task = TaskType(task_type) if isinstance(task_type, str) else task_type
        except ValueError:
            task = TaskType.QUERY_ANALYSIS  # Default
        
        # Get task-specific preferences
        preferred_models = self.task_preferences.get(task, [])
        
        if optimization == OptimizationMode.SPEED:
            return self._select_fastest(preferred_models)
        elif optimization == OptimizationMode.QUALITY:
            return self._select_highest_quality(preferred_models)
        elif optimization == OptimizationMode.COST:
            return self._select_cheapest(preferred_models)
        else:  # BALANCED
            return self._select_balanced(preferred_models)
    
    def select_for_mcp(self, mcp_id: str, 
                      fallback_optimization: OptimizationMode = OptimizationMode.BALANCED) -> str:
        """
        Select best LLM for specific MCP type
        
        Args:
            mcp_id: MCP identifier
            fallback_optimization: Optimization if no specific preference
            
        Returns:
            Model name to use
        """
        # Check for specific MCP preference
        if mcp_id.lower() in self.mcp_preferences:
            model = self.mcp_preferences[mcp_id.lower()]
            logger.info(f"Selected {model} for MCP {mcp_id}")
            return model
        
        # Fallback to balanced selection
        return self.select_balanced()
    
    def select_balanced(self, candidates: Optional[list] = None) -> str:
        """
        Select a balanced model (good speed, quality, and cost)
        
        Args:
            candidates: Optional list of candidate models
            
        Returns:
            Model name
        """
        if not candidates:
            candidates = list(self.available_models.keys())
        
        # Calculate balanced score
        best_model = None
        best_score = -1
        
        for model in candidates:
            if model in self.available_models:
                specs = self.available_models[model]
                # Balanced formula: quality is most important, then speed, then inverse cost
                score = (specs['quality'] * 0.5 + 
                        specs['speed'] * 0.3 + 
                        (10 - specs['cost']) * 0.2)
                
                if score > best_score:
                    best_score = score
                    best_model = model
        
        return best_model or 'claude-3-haiku'  # Default fallback
    
    def _select_fastest(self, candidates: list) -> str:
        """Select fastest model from candidates"""
        if not candidates:
            candidates = list(self.available_models.keys())
        
        fastest = max(candidates, 
                     key=lambda m: self.available_models.get(m, {}).get('speed', 0))
        return fastest
    
    def _select_highest_quality(self, candidates: list) -> str:
        """Select highest quality model from candidates"""
        if not candidates:
            candidates = list(self.available_models.keys())
        
        best = max(candidates,
                  key=lambda m: self.available_models.get(m, {}).get('quality', 0))
        return best
    
    def _select_cheapest(self, candidates: list) -> str:
        """Select cheapest model from candidates"""
        if not candidates:
            candidates = list(self.available_models.keys())
        
        cheapest = min(candidates,
                      key=lambda m: self.available_models.get(m, {}).get('cost', 10))
        return cheapest
    
    def _select_balanced(self, candidates: list) -> str:
        """Select balanced model from candidates"""
        return self.select_balanced(candidates)
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model"""
        return self.available_models.get(model_name, {})
    
    def list_models(self, provider: Optional[str] = None) -> list:
        """List available models, optionally filtered by provider"""
        if provider:
            return [name for name, info in self.available_models.items()
                   if info.get('provider') == provider]
        return list(self.available_models.keys())
    
    def recommend_for_budget(self, max_cost: int) -> list:
        """Recommend models within budget (cost <= max_cost)"""
        return [name for name, info in self.available_models.items()
               if info.get('cost', 10) <= max_cost]