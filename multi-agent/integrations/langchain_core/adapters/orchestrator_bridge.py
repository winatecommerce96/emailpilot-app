"""
Bridge functions for orchestrator service integration.

Provides functions that orchestrator_service can call to use LangChain features.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


def check_langchain_available() -> bool:
    """
    Check if LangChain dependencies are available.
    
    Returns:
        True if available
    """
    try:
        import langchain
        import langgraph
        from ..config import get_config
        
        # Try to initialize config
        config = get_config()
        
        return True
    except ImportError:
        return False
    except Exception as e:
        logger.warning(f"LangChain check failed: {e}")
        return False


def get_langchain_status() -> Dict[str, Any]:
    """
    Get LangChain module status.
    
    Returns:
        Status dictionary
    """
    status = {
        "available": False,
        "version": None,
        "components": {},
        "config": None,
        "error": None
    }
    
    try:
        import langchain
        import langgraph
        
        status["available"] = True
        status["version"] = {
            "langchain": getattr(langchain, "__version__", "unknown"),
            "langgraph": getattr(langgraph, "__version__", "unknown")
        }
        
        # Check components
        from ..deps import check_dependencies
        status["components"] = check_dependencies()
        
        # Check config
        from ..config import get_config
        config = get_config()
        status["config"] = {
            "provider": config.lc_provider,
            "model": config.lc_model,
            "vectorstore": config.vectorstore,
            "mcp_url": config.mcp_base_url
        }
        
    except Exception as e:
        status["error"] = str(e)
    
    return status


def lc_rag(
    question: str,
    k: int = 5,
    max_tokens: int = 600,
    evaluate: bool = False
) -> Dict[str, Any]:
    """
    Run RAG query via LangChain.
    
    Args:
        question: Question to ask
        k: Number of documents to retrieve
        max_tokens: Maximum response tokens
        evaluate: Whether to run evaluation
    
    Returns:
        Structured result with answer and citations
    """
    start_time = datetime.utcnow()
    
    try:
        from ..rag import create_rag_chain
        from ..rag.evaluators import evaluate_response
        from ..config import get_config
        from ..deps import initialize_tracing
        
        # Initialize tracing if enabled
        config = get_config()
        initialize_tracing(config)
        
        # Update k if specified
        if k != config.rag_k_documents:
            config.rag_k_documents = k
        
        # Log configuration
        logger.info(config.model_banner())
        
        # Create and run RAG chain
        chain = create_rag_chain(config=config)
        response = chain.ask(
            question=question,
            max_tokens=max_tokens
        )
        
        # Run evaluation if requested
        evaluation = None
        if evaluate:
            evaluation = evaluate_response(
                question=question,
                answer=response.answer,
                source_documents=response.source_documents
            )
        
        # Calculate duration
        duration_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )
        
        return {
            "success": True,
            "question": question,
            "answer": response.answer,
            "citations": [
                {
                    "source": c.source,
                    "text": c.text,
                    "confidence": c.confidence
                }
                for c in response.citations
            ],
            "source_documents": response.source_documents,
            "confidence": response.confidence,
            "evaluation": evaluation,
            "diagnostics": {
                "duration_ms": duration_ms,
                "num_sources": len(response.source_documents),
                "num_citations": len(response.citations),
                "model": config.lc_model,
                "provider": config.lc_provider,
                "k_documents": k
            }
        }
    
    except ImportError as e:
        logger.error(f"LangChain not available: {e}")
        return {
            "success": False,
            "error": "LangChain not installed",
            "message": "Install with: pip install -r requirements.txt"
        }
    
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "question": question
        }


def lc_agent(
    task: str,
    brand: Optional[str] = None,
    month: Optional[str] = None,
    timeout: int = 30,
    max_tools: int = 15,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run agent task via LangChain.
    
    Args:
        task: Task description
        brand: Brand identifier
        month: Month context
        timeout: Timeout in seconds
        max_tools: Maximum tool calls
        context: Additional context
    
    Returns:
        Structured result with plan, steps, and answer
    """
    start_time = datetime.utcnow()
    
    try:
        from ..agents import run_agent_task
        from ..agents.policies import AgentPolicy
        from ..config import get_config
        from ..deps import initialize_tracing
        
        # Initialize tracing if enabled
        config = get_config()
        initialize_tracing(config)
        
        # Log configuration
        logger.info(config.model_banner())
        
        # Build context
        if context is None:
            context = {}
        
        if brand:
            context["brand"] = brand
        if month:
            context["month"] = month
        
        # Create policy
        policy = AgentPolicy(
            max_tool_calls=max_tools,
            timeout_seconds=timeout
        )
        
        # Run agent
        result = run_agent_task(
            task=task,
            context=context,
            policy=policy,
            config=config
        )
        
        # Calculate duration
        duration_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )
        
        # Add diagnostics
        result["diagnostics"] = {
            "duration_ms": duration_ms,
            "model": config.lc_model,
            "provider": config.lc_provider,
            "timeout": timeout,
            "max_tools": max_tools
        }
        
        return result
    
    except ImportError as e:
        logger.error(f"LangChain not available: {e}")
        return {
            "success": False,
            "error": "LangChain not installed",
            "message": "Install with: pip install -r requirements.txt",
            "task": task
        }
    
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "task": task,
            "context": context
        }