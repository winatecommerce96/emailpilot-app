"""
Centralized, version-tolerant import for LangGraph MemorySaver.
Prefer new path; gracefully fall back to legacy path; raise informative error otherwise.
"""
from typing import Any
import logging

logger = logging.getLogger(__name__)


def resolve_memory_saver() -> Any:
    """
    Resolve MemorySaver import from appropriate LangGraph module.
    
    Returns:
        MemorySaver class or compatible alternative
        
    Raises:
        ImportError: If no compatible checkpoint saver can be found
    """
    
    # Newer LangGraph (v0.2+ often uses module-scoped subpackages)
    try:
        from langgraph.checkpoint.memory import MemorySaver  # type: ignore
        logger.debug("Using langgraph.checkpoint.memory.MemorySaver")
        return MemorySaver
    except ImportError:
        logger.debug("langgraph.checkpoint.memory.MemorySaver not available")
        pass
    except Exception as e:
        logger.debug(f"Error importing from langgraph.checkpoint.memory: {e}")
        pass

    # Try InMemorySaver (actual class name in some versions)
    try:
        from langgraph.checkpoint.memory import InMemorySaver  # type: ignore
        logger.debug("Using langgraph.checkpoint.memory.InMemorySaver")
        return InMemorySaver
    except ImportError:
        logger.debug("langgraph.checkpoint.memory.InMemorySaver not available")
        pass
    except Exception as e:
        logger.debug(f"Error importing InMemorySaver from langgraph.checkpoint.memory: {e}")
        pass

    # Legacy path (older LangGraph exposed from langgraph.checkpoint)
    try:
        from langgraph.checkpoint import MemorySaver  # type: ignore
        logger.debug("Using langgraph.checkpoint.MemorySaver (legacy path)")
        return MemorySaver
    except ImportError:
        logger.debug("langgraph.checkpoint.MemorySaver not available")
        pass
    except Exception as e:
        logger.debug(f"Error importing from langgraph.checkpoint: {e}")
        pass

    # Check for langgraph-checkpoint package (separate package in newer versions)
    try:
        from langgraph_checkpoint.memory import MemorySaver  # type: ignore
        logger.debug("Using langgraph_checkpoint.memory.MemorySaver (separate package)")
        return MemorySaver
    except ImportError:
        logger.debug("langgraph_checkpoint.memory.MemorySaver not available")
        pass
    except Exception as e:
        logger.debug(f"Error importing from langgraph_checkpoint.memory: {e}")
        pass

    # Some environments expose sqlite saver but not memory; offer a clear error.
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
        logger.warning("MemorySaver not found, using SqliteSaver as compatibility fallback")
        
        # Provide a compatibility alias with a helpful message.
        class _CompatMemorySaver(SqliteSaver):  # type: ignore
            """
            Compatibility wrapper: using SqliteSaver in place of MemorySaver.
            
            Note: This fallback persists checkpoints to SQLite instead of memory.
            For pure memory checkpointing, install a compatible LangGraph version.
            """
            
            def __init__(self, *args, **kwargs):
                # Initialize with in-memory SQLite database
                super().__init__(":memory:", *args, **kwargs)
        
        return _CompatMemorySaver
    except ImportError:
        logger.debug("SqliteSaver also not available as fallback")
        pass
    except Exception as e:
        logger.debug(f"Error importing SqliteSaver fallback: {e}")
        pass

    # Final fallback: create a basic in-memory implementation
    try:
        logger.warning("Creating basic in-memory checkpoint saver as last resort")
        
        class _BasicMemorySaver:
            """
            Basic in-memory checkpoint saver implementation.
            
            WARNING: This is a minimal fallback that may not support all features.
            Consider upgrading LangGraph to use the official MemorySaver.
            """
            
            def __init__(self):
                self._checkpoints = {}
                logger.info("Using basic in-memory checkpoint saver (fallback implementation)")
            
            def get(self, config):
                return self._checkpoints.get(config.get("configurable", {}).get("thread_id"))
            
            def put(self, config, checkpoint, metadata):
                thread_id = config.get("configurable", {}).get("thread_id")
                if thread_id:
                    self._checkpoints[thread_id] = (checkpoint, metadata)
        
        return _BasicMemorySaver
        
    except Exception as e:
        logger.error(f"Failed to create basic memory saver: {e}")
        pass
    
    # All import attempts failed
    raise ImportError(
        "Could not import MemorySaver or create compatible alternative. Tried:\n"
        "  1. `langgraph.checkpoint.memory.MemorySaver` (recommended)\n"
        "  2. `langgraph.checkpoint.MemorySaver` (legacy)\n"
        "  3. `langgraph_checkpoint.memory.MemorySaver` (separate package)\n"
        "  4. `langgraph.checkpoint.sqlite.SqliteSaver` (fallback)\n"
        "  5. Basic in-memory implementation (last resort)\n\n"
        "Fix by installing a compatible LangGraph version:\n"
        "  pip install 'langgraph>=0.2,<1.0'\n\n"
        "Or check if langgraph-checkpoint is needed as separate package:\n"
        "  pip install langgraph-checkpoint"
    )