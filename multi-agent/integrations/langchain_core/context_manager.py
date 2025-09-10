"""
Context Passing and Memory Management for Enhanced MCP + LangChain Integration

This module implements a comprehensive context passing mechanism that:
- Maintains state across agent executions using LangChain memory
- Passes context between Enhanced MCP tools and agents  
- Provides persistent storage using Firestore
- Implements smart context resolution and variable interpolation
- Supports both synchronous and asynchronous execution patterns

Features:
- Multi-level context hierarchy (system, client, session, task)
- Automatic variable resolution from multiple sources
- Context inheritance and scoping
- Memory consolidation and cleanup
- Performance optimization with caching
- Error handling and recovery
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict
import threading
from functools import lru_cache

# LangChain imports
from langchain_core.memory import (
    ConversationBufferMemory, 
    ConversationBufferWindowMemory,
    ConversationSummaryBufferMemory
)
from langchain_core.callbacks import CallbackManager, BaseCallbackHandler
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage

# Project imports
from .config import LangChainConfig, get_config
from .adapters.enhanced_mcp_adapter import ToolContext
from ..deps import get_firestore_client, get_cache

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ContextScope:
    """Defines the scope and priority of context data."""
    level: int  # Higher = higher priority (0=system, 1=client, 2=session, 3=task)
    name: str
    ttl_seconds: Optional[int] = None
    persistent: bool = True
    
    
@dataclass 
class ContextEntry:
    """A single context entry with metadata."""
    key: str
    value: Any
    scope: ContextScope
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if not self.scope.ttl_seconds:
            return False
        
        expiry = self.timestamp + timedelta(seconds=self.scope.ttl_seconds)
        return datetime.utcnow() > expiry
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "key": self.key,
            "value": self.value,
            "scope": {
                "level": self.scope.level,
                "name": self.scope.name,
                "ttl_seconds": self.scope.ttl_seconds,
                "persistent": self.scope.persistent
            },
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextEntry':
        """Create from dictionary."""
        scope_data = data["scope"]
        scope = ContextScope(
            level=scope_data["level"],
            name=scope_data["name"],
            ttl_seconds=scope_data.get("ttl_seconds"),
            persistent=scope_data.get("persistent", True)
        )
        
        return cls(
            key=data["key"],
            value=data["value"],
            scope=scope,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "unknown"),
            version=data.get("version", 1),
            metadata=data.get("metadata", {})
        )


class ContextCallbackHandler(BaseCallbackHandler):
    """
    Callback handler that automatically captures and updates context.
    
    This handler:
    - Captures tool inputs/outputs for context propagation
    - Updates context with intermediate results
    - Tracks performance metrics and errors
    - Maintains conversation history
    """
    
    def __init__(self, context_manager: 'EnhancedContextManager'):
        self.context_manager = context_manager
        self.tool_executions: List[Dict[str, Any]] = []
        self.conversation_turns: List[Dict[str, Any]] = []
        
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Capture tool execution start."""
        tool_name = serialized.get("name", "unknown")
        execution = {
            "tool_name": tool_name,
            "input": input_str,
            "start_time": datetime.utcnow(),
            "run_id": kwargs.get("run_id")
        }
        self.tool_executions.append(execution)
        
        # Store tool input in context for potential reuse
        self.context_manager.set_context(
            f"last_tool_{tool_name}_input",
            input_str,
            scope=ContextScope(level=3, name="task", ttl_seconds=300),
            source="tool_callback"
        )
        
        logger.debug(f"Tool callback - started: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Capture tool execution completion."""
        if self.tool_executions:
            execution = self.tool_executions[-1]
            execution["output"] = output
            execution["end_time"] = datetime.utcnow()
            execution["duration"] = (execution["end_time"] - execution["start_time"]).total_seconds()
            
            # Store successful tool output in context
            tool_name = execution["tool_name"]
            self.context_manager.set_context(
                f"last_tool_{tool_name}_output",
                output,
                scope=ContextScope(level=3, name="task", ttl_seconds=600),
                source="tool_callback"
            )
            
            # Store execution metrics
            self.context_manager.set_context(
                f"tool_metrics_{tool_name}",
                {
                    "duration": execution["duration"],
                    "timestamp": execution["end_time"].isoformat(),
                    "success": True
                },
                scope=ContextScope(level=3, name="task", ttl_seconds=300),
                source="tool_callback"
            )
            
            logger.debug(f"Tool callback - completed: {tool_name} ({execution['duration']:.2f}s)")
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Capture tool execution error."""
        if self.tool_executions:
            execution = self.tool_executions[-1]
            execution["error"] = str(error)
            execution["end_time"] = datetime.utcnow()
            execution["duration"] = (execution["end_time"] - execution["start_time"]).total_seconds()
            
            # Store error in context for debugging
            tool_name = execution["tool_name"]
            self.context_manager.set_context(
                f"last_tool_{tool_name}_error", 
                str(error),
                scope=ContextScope(level=3, name="task", ttl_seconds=300),
                source="tool_callback"
            )
            
            logger.error(f"Tool callback - error: {tool_name} - {error}")
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Capture chain execution start."""
        chain_name = serialized.get("name", "unknown")
        
        # Store chain inputs for context
        self.context_manager.set_context(
            f"last_chain_{chain_name}_inputs",
            inputs,
            scope=ContextScope(level=3, name="task", ttl_seconds=300),
            source="chain_callback"
        )
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Capture chain execution completion."""
        # Store chain outputs
        self.context_manager.set_context(
            "last_chain_outputs",
            outputs,
            scope=ContextScope(level=3, name="task", ttl_seconds=300), 
            source="chain_callback"
        )
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Capture LLM call start."""
        # Store the prompt for debugging/optimization
        self.context_manager.set_context(
            "last_llm_prompt",
            prompts[0] if prompts else "",
            scope=ContextScope(level=3, name="task", ttl_seconds=600),
            source="llm_callback"
        )


class MemoryManager:
    """
    Manages different types of memory for different contexts.
    
    Provides:
    - Conversation memory per session
    - Summary memory for long sessions
    - Working memory for current tasks
    - Persistent memory across sessions
    """
    
    def __init__(self, config: LangChainConfig):
        self.config = config
        
        # Memory instances by session_id
        self._conversation_memories: Dict[str, ConversationBufferWindowMemory] = {}
        self._summary_memories: Dict[str, ConversationSummaryBufferMemory] = {}
        self._working_memories: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self._lock = threading.RLock()
    
    def get_conversation_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get conversation memory for session."""
        with self._lock:
            if session_id not in self._conversation_memories:
                self._conversation_memories[session_id] = ConversationBufferWindowMemory(
                    k=10,  # Keep last 10 messages
                    memory_key="conversation_history",
                    return_messages=True
                )
            return self._conversation_memories[session_id]
    
    def get_summary_memory(self, session_id: str) -> ConversationSummaryBufferMemory:
        """Get summary memory for long sessions."""
        with self._lock:
            if session_id not in self._summary_memories:
                # This would need LLM for summarization
                # For now, use buffer memory as fallback
                self._summary_memories[session_id] = ConversationBufferMemory(
                    memory_key="conversation_summary",
                    return_messages=True
                )
            return self._summary_memories[session_id]
    
    def get_working_memory(self, task_id: str) -> Dict[str, Any]:
        """Get working memory for current task."""
        with self._lock:
            if task_id not in self._working_memories:
                self._working_memories[task_id] = {}
            return self._working_memories[task_id]
    
    def clear_session(self, session_id: str):
        """Clear all memory for a session."""
        with self._lock:
            self._conversation_memories.pop(session_id, None)
            self._summary_memories.pop(session_id, None)
    
    def clear_task(self, task_id: str):
        """Clear working memory for a task."""
        with self._lock:
            self._working_memories.pop(task_id, None)


class EnhancedContextManager:
    """
    Enhanced context manager that integrates with LangChain memory and Enhanced MCP tools.
    
    This class provides:
    - Multi-level context hierarchy with proper scoping
    - Automatic variable resolution and interpolation  
    - Integration with LangChain memory systems
    - Persistent storage using Firestore
    - Smart caching and performance optimization
    - Context inheritance and propagation
    """
    
    def __init__(self, config: Optional[LangChainConfig] = None):
        """
        Initialize context manager.
        
        Args:
            config: LangChain configuration
        """
        self.config = config or get_config()
        
        # Context storage
        self._contexts: Dict[str, Dict[str, ContextEntry]] = defaultdict(dict)
        self._context_lock = threading.RLock()
        
        # Memory management
        self.memory_manager = MemoryManager(self.config)
        
        # Firestore for persistence
        self.firestore = get_firestore_client()
        self.cache = get_cache()
        
        # Predefined scope levels
        self.scopes = {
            "system": ContextScope(level=0, name="system", persistent=True),
            "client": ContextScope(level=1, name="client", persistent=True), 
            "session": ContextScope(level=2, name="session", ttl_seconds=3600, persistent=True),
            "task": ContextScope(level=3, name="task", ttl_seconds=600, persistent=False),
            "temp": ContextScope(level=4, name="temp", ttl_seconds=60, persistent=False)
        }
        
        # Variable resolvers
        self._resolvers: Dict[str, callable] = {}
        self._register_default_resolvers()
        
        logger.info("Enhanced Context Manager initialized")
    
    def _register_default_resolvers(self):
        """Register default variable resolvers."""
        
        @self.register_resolver("datetime")
        def resolve_datetime(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
            """Resolve current datetime."""
            return datetime.utcnow().strftime(format_str)
        
        @self.register_resolver("client_info")
        async def resolve_client_info(client_id: str) -> Dict[str, Any]:
            """Resolve client information from Firestore."""
            if not self.firestore:
                return {"client_id": client_id, "name": client_id}
            
            try:
                doc_ref = self.firestore.collection("clients").document(client_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    return doc.to_dict()
                else:
                    return {"client_id": client_id, "name": client_id, "status": "not_found"}
            except Exception as e:
                logger.error(f"Failed to resolve client info: {e}")
                return {"client_id": client_id, "error": str(e)}
        
        @self.register_resolver("month_info")
        def resolve_month_info(month_str: str) -> Dict[str, Any]:
            """Resolve month information."""
            try:
                month_date = datetime.strptime(month_str, "%Y-%m")
                return {
                    "month": month_str,
                    "year": month_date.year,
                    "month_num": month_date.month,
                    "month_name": month_date.strftime("%B"),
                    "quarter": f"Q{(month_date.month - 1) // 3 + 1}",
                    "days_in_month": (month_date.replace(month=month_date.month % 12 + 1, day=1) - timedelta(days=1)).day,
                    "fiscal_year": month_date.year if month_date.month >= 1 else month_date.year - 1
                }
            except Exception as e:
                logger.error(f"Failed to resolve month info: {e}")
                return {"month": month_str, "error": str(e)}
    
    def register_resolver(self, name: str):
        """Decorator to register variable resolvers."""
        def decorator(func):
            self._resolvers[name] = func
            return func
        return decorator
    
    def set_context(
        self,
        key: str,
        value: Any,
        scope: Optional[ContextScope] = None,
        source: str = "manual",
        context_id: str = "default"
    ) -> None:
        """
        Set context value with scoping.
        
        Args:
            key: Context key
            value: Context value
            scope: Context scope (defaults to task scope)
            source: Source of the context
            context_id: Context identifier (session_id, task_id, etc.)
        """
        if scope is None:
            scope = self.scopes["task"]
        
        entry = ContextEntry(
            key=key,
            value=value,
            scope=scope,
            source=source,
            timestamp=datetime.utcnow()
        )
        
        with self._context_lock:
            if context_id not in self._contexts:
                self._contexts[context_id] = {}
            self._contexts[context_id][key] = entry
        
        # Store in persistent storage if required
        if scope.persistent and self.firestore:
            self._store_persistent_context(context_id, entry)
        
        logger.debug(f"Set context: {key} = {str(value)[:100]} (scope: {scope.name})")
    
    def get_context(
        self,
        key: str,
        context_id: str = "default",
        default: Any = None,
        resolve_variables: bool = True
    ) -> Any:
        """
        Get context value with hierarchy resolution.
        
        Args:
            key: Context key
            context_id: Context identifier
            default: Default value if not found
            resolve_variables: Whether to resolve variable expressions
            
        Returns:
            Context value
        """
        # Check in-memory contexts first
        with self._context_lock:
            if context_id in self._contexts and key in self._contexts[context_id]:
                entry = self._contexts[context_id][key]
                
                # Check expiration
                if entry.is_expired():
                    del self._contexts[context_id][key]
                else:
                    value = entry.value
                    if resolve_variables and isinstance(value, str):
                        value = self._resolve_variables(value, context_id)
                    return value
        
        # Check persistent storage
        if self.firestore:
            value = self._load_persistent_context(context_id, key)
            if value is not None:
                if resolve_variables and isinstance(value, str):
                    value = self._resolve_variables(value, context_id)
                return value
        
        # Return default
        if resolve_variables and isinstance(default, str):
            default = self._resolve_variables(default, context_id)
        
        return default
    
    def get_all_context(self, context_id: str = "default") -> Dict[str, Any]:
        """Get all context for a given context_id."""
        result = {}
        
        # In-memory contexts
        with self._context_lock:
            if context_id in self._contexts:
                for key, entry in self._contexts[context_id].items():
                    if not entry.is_expired():
                        result[key] = entry.value
        
        # Persistent contexts
        if self.firestore:
            persistent = self._load_all_persistent_context(context_id)
            result.update(persistent)
        
        return result
    
    def create_tool_context(
        self,
        client_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        context_id: str = "default"
    ) -> ToolContext:
        """
        Create ToolContext with resolved variables.
        
        Args:
            client_id: Client identifier
            brand_id: Brand identifier
            session_id: Session identifier
            task_id: Task identifier
            agent_name: Agent name
            context_id: Context identifier for lookups
            
        Returns:
            ToolContext with resolved variables
        """
        # Resolve variables from context
        resolved_client_id = client_id or self.get_context("client_id", context_id)
        resolved_brand_id = brand_id or self.get_context("brand_id", context_id)
        resolved_session_id = session_id or self.get_context("session_id", context_id)
        resolved_task_id = task_id or self.get_context("task_id", context_id)
        
        # Get additional metadata from context
        metadata = self.get_context("tool_metadata", context_id, default={})
        
        return ToolContext(
            client_id=resolved_client_id,
            brand_id=resolved_brand_id,
            user_id=self.get_context("user_id", context_id),
            session_id=resolved_session_id,
            agent_name=agent_name,
            task_id=resolved_task_id,
            metadata=metadata
        )
    
    def create_callback_manager(self, context_id: str = "default") -> CallbackManager:
        """Create callback manager with context handler."""
        callback_handler = ContextCallbackHandler(self)
        return CallbackManager([callback_handler])
    
    def _resolve_variables(self, text: str, context_id: str) -> str:
        """
        Resolve variable expressions in text.
        
        Supports:
        - {{variable_name}} - Simple context lookup
        - {{resolver:arg}} - Resolver function call
        - {{client_info:client_id}} - Async resolver with argument
        """
        import re
        
        # Pattern for variable expressions
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace_var(match):
            expr = match.group(1).strip()
            
            # Check for resolver syntax
            if ':' in expr:
                resolver_name, arg = expr.split(':', 1)
                if resolver_name in self._resolvers:
                    try:
                        resolver = self._resolvers[resolver_name]
                        result = resolver(arg)
                        
                        # Handle async resolvers
                        if asyncio.iscoroutine(result):
                            # For now, return placeholder - would need proper async handling
                            return f"{{ASYNC:{resolver_name}:{arg}}}"
                        
                        return str(result) if result is not None else ""
                    except Exception as e:
                        logger.error(f"Resolver {resolver_name} failed: {e}")
                        return f"{{ERROR:{resolver_name}}}"
            
            # Simple context lookup
            value = self.get_context(expr, context_id, resolve_variables=False)
            return str(value) if value is not None else f"{{UNKNOWN:{expr}}}"
        
        return re.sub(pattern, replace_var, text)
    
    async def resolve_async_variables(self, text: str, context_id: str) -> str:
        """Resolve variables including async resolvers."""
        import re
        
        # First pass - resolve sync variables
        text = self._resolve_variables(text, context_id)
        
        # Second pass - resolve async placeholders
        async_pattern = r'\{ASYNC:([^:]+):([^}]+)\}'
        
        async def replace_async(match):
            resolver_name = match.group(1)
            arg = match.group(2)
            
            if resolver_name in self._resolvers:
                try:
                    resolver = self._resolvers[resolver_name]
                    result = await resolver(arg)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error(f"Async resolver {resolver_name} failed: {e}")
                    return f"{{ERROR:{resolver_name}}}"
            
            return match.group(0)  # Return unchanged if resolver not found
        
        # Process async placeholders
        matches = re.findall(async_pattern, text)
        for resolver_name, arg in matches:
            if resolver_name in self._resolvers:
                try:
                    resolver = self._resolvers[resolver_name] 
                    result = await resolver(arg)
                    placeholder = f"{{ASYNC:{resolver_name}:{arg}}}"
                    text = text.replace(placeholder, str(result) if result is not None else "")
                except Exception as e:
                    logger.error(f"Async resolver {resolver_name} failed: {e}")
                    error_placeholder = f"{{ERROR:{resolver_name}}}"
                    text = text.replace(f"{{ASYNC:{resolver_name}:{arg}}}", error_placeholder)
        
        return text
    
    def _store_persistent_context(self, context_id: str, entry: ContextEntry):
        """Store context entry in Firestore."""
        if not self.firestore:
            return
        
        try:
            doc_ref = self.firestore.collection("context").document(f"{context_id}_{entry.key}")
            doc_ref.set(entry.to_dict())
        except Exception as e:
            logger.error(f"Failed to store persistent context: {e}")
    
    def _load_persistent_context(self, context_id: str, key: str) -> Any:
        """Load context entry from Firestore."""
        if not self.firestore:
            return None
        
        try:
            doc_ref = self.firestore.collection("context").document(f"{context_id}_{key}")
            doc = doc_ref.get()
            
            if doc.exists:
                entry = ContextEntry.from_dict(doc.to_dict())
                
                # Check expiration
                if entry.is_expired():
                    doc_ref.delete()
                    return None
                
                return entry.value
            
            return None
        except Exception as e:
            logger.error(f"Failed to load persistent context: {e}")
            return None
    
    def _load_all_persistent_context(self, context_id: str) -> Dict[str, Any]:
        """Load all persistent context for context_id."""
        if not self.firestore:
            return {}
        
        try:
            docs = self.firestore.collection("context").where(
                "key", ">=", f"{context_id}_"
            ).where(
                "key", "<", f"{context_id}_\uf8ff"
            ).get()
            
            result = {}
            for doc in docs:
                entry = ContextEntry.from_dict(doc.to_dict())
                
                # Check expiration
                if entry.is_expired():
                    doc.reference.delete()
                    continue
                
                result[entry.key] = entry.value
            
            return result
        except Exception as e:
            logger.error(f"Failed to load all persistent context: {e}")
            return {}
    
    def cleanup_expired(self, context_id: Optional[str] = None):
        """Clean up expired context entries."""
        with self._context_lock:
            contexts_to_clean = [context_id] if context_id else list(self._contexts.keys())
            
            for ctx_id in contexts_to_clean:
                if ctx_id in self._contexts:
                    expired_keys = []
                    for key, entry in self._contexts[ctx_id].items():
                        if entry.is_expired():
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self._contexts[ctx_id][key]
                    
                    if not self._contexts[ctx_id]:
                        del self._contexts[ctx_id]
        
        logger.debug(f"Cleaned up expired context entries")
    
    @asynccontextmanager
    async def context_session(
        self,
        session_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ):
        """
        Async context manager for maintaining session context.
        
        Usage:
            async with context_manager.context_session("session_123") as ctx:
                # Context is automatically managed
                result = await some_agent.run(task, context=ctx)
        """
        # Set up session context
        if initial_context:
            for key, value in initial_context.items():
                self.set_context(
                    key, 
                    value, 
                    scope=self.scopes["session"],
                    context_id=session_id
                )
        
        try:
            yield session_id
        finally:
            # Cleanup session-specific temporary contexts
            self.cleanup_expired(session_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of context management components."""
        health = {
            "context_manager": True,
            "memory_manager": True,
            "firestore": False,
            "resolvers": len(self._resolvers),
            "active_contexts": len(self._contexts)
        }
        
        # Test Firestore
        if self.firestore:
            try:
                # Simple test operation
                test_ref = self.firestore.collection("context_health").document("test")
                test_ref.set({"timestamp": datetime.utcnow()})
                health["firestore"] = True
            except:
                pass
        
        return health


# Global instance
_context_manager: Optional[EnhancedContextManager] = None


def get_context_manager(config: Optional[LangChainConfig] = None) -> EnhancedContextManager:
    """Get global context manager instance."""
    global _context_manager
    
    if _context_manager is None:
        _context_manager = EnhancedContextManager(config)
    
    return _context_manager


# Convenience functions
def set_context(key: str, value: Any, scope: str = "task", context_id: str = "default"):
    """Set context value using global manager."""
    manager = get_context_manager()
    scope_obj = manager.scopes.get(scope, manager.scopes["task"])
    manager.set_context(key, value, scope_obj, context_id=context_id)


def get_context(key: str, context_id: str = "default", default: Any = None):
    """Get context value using global manager."""
    manager = get_context_manager()
    return manager.get_context(key, context_id, default)


def create_tool_context(**kwargs) -> ToolContext:
    """Create ToolContext using global manager."""
    manager = get_context_manager()
    return manager.create_tool_context(**kwargs)