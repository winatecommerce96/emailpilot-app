"""
RAG evaluators for measuring answer quality.

Provides LLM-based evaluation of faithfulness and relevance.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..config import LangChainConfig, get_config
from ..deps import get_llm

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Evaluates RAG responses for quality metrics."""
    
    FAITHFULNESS_PROMPT = """You are an expert evaluator assessing the faithfulness of an answer to its source documents.

Question: {question}

Source Documents:
{sources}

Generated Answer:
{answer}

Evaluate the faithfulness of the answer on these criteria:
1. All claims in the answer are supported by the source documents
2. No information is added beyond what's in the sources
3. The answer accurately represents the source information

Provide your evaluation as JSON with this structure:
{{
    "score": <float between 0 and 1>,
    "reasoning": "<brief explanation>",
    "unsupported_claims": ["<any claims not in sources>"]
}}

JSON evaluation:"""
    
    RELEVANCE_PROMPT = """You are an expert evaluator assessing the relevance of an answer to a question.

Question: {question}

Generated Answer:
{answer}

Evaluate the relevance of the answer on these criteria:
1. The answer directly addresses the question
2. The answer provides appropriate detail
3. The answer stays on topic

Provide your evaluation as JSON with this structure:
{{
    "score": <float between 0 and 1>,
    "reasoning": "<brief explanation>",
    "missing_aspects": ["<any aspects of question not addressed>"]
}}

JSON evaluation:"""
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        config: Optional[LangChainConfig] = None
    ):
        """
        Initialize evaluator.
        
        Args:
            llm: LLM instance for evaluation
            config: Configuration instance
        """
        self.config = config or get_config()
        self.llm = llm or get_llm(self.config)
        
        # Create prompts
        self.faithfulness_prompt = PromptTemplate(
            input_variables=["question", "sources", "answer"],
            template=self.FAITHFULNESS_PROMPT
        )
        
        self.relevance_prompt = PromptTemplate(
            input_variables=["question", "answer"],
            template=self.RELEVANCE_PROMPT
        )
        
        # JSON parser
        self.json_parser = JsonOutputParser()
    
    def evaluate_faithfulness(
        self,
        question: str,
        answer: str,
        source_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate faithfulness of answer to sources.
        
        Args:
            question: Original question
            answer: Generated answer
            source_documents: Source documents used
        
        Returns:
            Evaluation results
        """
        logger.info("Evaluating faithfulness")
        
        # Format source documents
        sources = self._format_sources(source_documents)
        
        # Generate evaluation
        prompt_value = self.faithfulness_prompt.format(
            question=question,
            sources=sources,
            answer=answer
        )
        
        try:
            result = self.llm.invoke(prompt_value)
            
            # Parse JSON result
            if hasattr(result, 'content'):
                result_text = result.content
            else:
                result_text = str(result)
            
            # Extract JSON from response
            evaluation = self._extract_json(result_text)
            
            # Ensure required fields
            if "score" not in evaluation:
                evaluation["score"] = 0.5
            if "reasoning" not in evaluation:
                evaluation["reasoning"] = "Evaluation parsing failed"
            
            return evaluation
        
        except Exception as e:
            logger.error(f"Faithfulness evaluation failed: {e}")
            return {
                "score": 0.5,
                "reasoning": f"Evaluation error: {str(e)}",
                "unsupported_claims": []
            }
    
    def evaluate_relevance(
        self,
        question: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        Evaluate relevance of answer to question.
        
        Args:
            question: Original question
            answer: Generated answer
        
        Returns:
            Evaluation results
        """
        logger.info("Evaluating relevance")
        
        # Generate evaluation
        prompt_value = self.relevance_prompt.format(
            question=question,
            answer=answer
        )
        
        try:
            result = self.llm.invoke(prompt_value)
            
            # Parse JSON result
            if hasattr(result, 'content'):
                result_text = result.content
            else:
                result_text = str(result)
            
            # Extract JSON from response
            evaluation = self._extract_json(result_text)
            
            # Ensure required fields
            if "score" not in evaluation:
                evaluation["score"] = 0.5
            if "reasoning" not in evaluation:
                evaluation["reasoning"] = "Evaluation parsing failed"
            
            return evaluation
        
        except Exception as e:
            logger.error(f"Relevance evaluation failed: {e}")
            return {
                "score": 0.5,
                "reasoning": f"Evaluation error: {str(e)}",
                "missing_aspects": []
            }
    
    def evaluate_complete(
        self,
        question: str,
        answer: str,
        source_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Complete evaluation of RAG response.
        
        Args:
            question: Original question
            answer: Generated answer
            source_documents: Source documents used
        
        Returns:
            Complete evaluation results
        """
        start_time = datetime.utcnow()
        
        # Evaluate faithfulness
        faithfulness = self.evaluate_faithfulness(question, answer, source_documents)
        
        # Evaluate relevance
        relevance = self.evaluate_relevance(question, answer)
        
        # Calculate overall score
        overall_score = (faithfulness["score"] + relevance["score"]) / 2
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "faithfulness": faithfulness,
            "relevance": relevance,
            "overall": {
                "score": overall_score,
                "confidence": self._calculate_confidence(faithfulness, relevance)
            },
            "metadata": {
                "evaluated_at": end_time.isoformat(),
                "duration_ms": duration_ms,
                "evaluator_model": self.config.lc_model
            }
        }
    
    def _format_sources(self, source_documents: List[Dict[str, Any]]) -> str:
        """Format source documents for evaluation."""
        formatted = []
        
        for i, doc in enumerate(source_documents):
            source = doc.get("metadata", {}).get("source", f"Document {i+1}")
            content = doc.get("content", "")
            
            formatted.append(f"[{source}]\n{content}")
        
        return "\n\n".join(formatted)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON in the response
        try:
            # Look for JSON block
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # Try parsing entire response
                return json.loads(text)
        
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from evaluation")
            return {}
    
    def _calculate_confidence(
        self,
        faithfulness: Dict[str, Any],
        relevance: Dict[str, Any]
    ) -> float:
        """Calculate confidence in evaluation."""
        # Simple confidence based on score agreement
        score_diff = abs(faithfulness["score"] - relevance["score"])
        
        if score_diff < 0.1:
            return 0.9
        elif score_diff < 0.2:
            return 0.7
        elif score_diff < 0.3:
            return 0.5
        else:
            return 0.3


def evaluate_response(
    question: str,
    answer: str,
    source_documents: List[Dict[str, Any]],
    config: Optional[LangChainConfig] = None
) -> Dict[str, float]:
    """
    Convenience function to evaluate a RAG response.
    
    Args:
        question: Original question
        answer: Generated answer
        source_documents: Source documents
        config: Configuration instance
    
    Returns:
        Dictionary with faithfulness, relevance, and overall scores
    """
    evaluator = RAGEvaluator(config=config)
    
    result = evaluator.evaluate_complete(question, answer, source_documents)
    
    return {
        "faithfulness": result["faithfulness"]["score"],
        "relevance": result["relevance"]["score"],
        "overall": result["overall"]["score"]
    }