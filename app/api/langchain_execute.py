"""
LangChain Agent Execution API - Synchronous execution endpoint
Provides immediate agent responses for debugging and testing
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/langchain/execute", tags=["LangChain Execute"])


class ExecuteRequest(BaseModel):
    """Request model for agent execution"""
    input: str
    context: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.0


@router.post("/{agent_name}")
async def execute_agent_sync(
    agent_name: str, 
    request: ExecuteRequest
) -> Dict[str, Any]:
    """
    Execute an agent synchronously and return the result immediately.
    This endpoint is designed for debugging and testing.
    """
    start_time = datetime.utcnow()
    
    try:
        # Import LangChain components - use correct path
        import sys
        import os
        # Add multi-agent to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'multi-agent'))
        
        from integrations.langchain_core.config import get_config
        from integrations.langchain_core.deps import get_llm, get_embeddings
        
        config = get_config()
        
        # Handle special agent types
        if agent_name == "rag":
            # RAG agent - use proper RAG chain
            from integrations.langchain_core.rag import create_rag_chain, RAGResponse
            from integrations.langchain_core.deps import get_vectorstore
            
            # Create RAG chain
            rag_chain = create_rag_chain(config)
            
            # Run the chain
            try:
                response = await asyncio.to_thread(
                    rag_chain.answer,
                    request.input
                )
                
                # Format response
                if isinstance(response, RAGResponse):
                    answer = response.answer
                    sources = [
                        {
                            "content": citation.text[:200],
                            "source": citation.source
                        }
                        for citation in response.citations[:3]
                    ]
                else:
                    answer = str(response)
                    sources = []
            except Exception as e:
                logger.warning(f"RAG chain error, falling back to simple response: {e}")
                # Fallback to simple retrieval
                docs = vectorstore.similarity_search(request.input, k=3)
                context = "\n\n".join([doc.page_content for doc in docs])
                
                from langchain.prompts import ChatPromptTemplate
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Answer based on this context:\n{context}"),
                    ("human", "{question}")
                ])
                
                from langchain.chains import LLMChain
                chain = LLMChain(llm=get_llm(config), prompt=prompt)
                result = await asyncio.to_thread(
                    chain.invoke,
                    {"context": context, "question": request.input}
                )
                answer = result.get("text", "No answer generated")
                sources = [
                    {"content": doc.page_content[:200], "source": doc.metadata.get("source", "unknown")}
                    for doc in docs
                ]
            
            return {
                "success": True,
                "agent": agent_name,
                "input": request.input,
                "output": answer,
                "sources": sources,
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }
            
        else:
            # Standard agent - use prompt template
            from langchain.chains import LLMChain
            from langchain.prompts import ChatPromptTemplate
            
            llm = get_llm(config)
            
            # Get agent prompt from registry
            try:
                from integrations.langchain_core.admin import get_agent_registry
                registry = get_agent_registry()
                agent_def = registry.get_agent(agent_name)
                
                if not agent_def:
                    # Fallback to default prompt
                    system_prompt = f"You are a helpful AI assistant named {agent_name}."
                else:
                    system_prompt = agent_def.get("prompt", f"You are {agent_name}")
                    
            except Exception as e:
                logger.warning(f"Could not get agent prompt: {e}")
                system_prompt = f"You are a helpful AI assistant named {agent_name}."
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
            
            # Create and run chain
            chain = LLMChain(llm=llm, prompt=prompt)
            
            result = await asyncio.to_thread(
                chain.invoke,
                {"input": request.input}
            )
            
            return {
                "success": True,
                "agent": agent_name,
                "input": request.input,
                "output": result.get("text", "No response generated"),
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"LangChain components not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error executing agent {agent_name}: {e}")
        return {
            "success": False,
            "agent": agent_name,
            "input": request.input,
            "error": str(e),
            "execution_time": (datetime.utcnow() - start_time).total_seconds()
        }


@router.get("/health")
async def health_check():
    """Check if the execution endpoint is healthy"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'multi-agent'))
        from integrations.langchain_core.config import get_config
        config = get_config()
        
        return {
            "status": "healthy",
            "provider": config.lc_provider,
            "model": config.lc_model
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }