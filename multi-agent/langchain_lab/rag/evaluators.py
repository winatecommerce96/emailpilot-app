"""
Evaluators for RAG system responses.

Provides faithfulness and relevance evaluation using LLM judges
with few-shot examples and structured rubrics.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvaluationScore:
    """Evaluation scores for a RAG response."""
    faithfulness: float  # 0-1: How well the answer is grounded in sources
    relevance: float     # 0-1: How relevant the answer is to the question
    completeness: float  # 0-1: How complete the answer is
    clarity: float       # 0-1: How clear and well-structured the answer is
    overall: float       # 0-1: Overall quality score
    feedback: str        # Detailed feedback
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "faithfulness": self.faithfulness,
            "relevance": self.relevance,
            "completeness": self.completeness,
            "clarity": self.clarity,
            "overall": self.overall,
            "feedback": self.feedback
        }


class RAGEvaluator:
    """Evaluates RAG responses using LLM judges."""
    
    FAITHFULNESS_PROMPT = """You are an expert evaluator assessing the faithfulness of an AI assistant's answer.

Evaluate how well the answer is grounded in the provided source documents.

Question: {question}

Source Documents:
{sources}

Generated Answer:
{answer}

Evaluation Criteria:
1. All claims in the answer should be directly supported by the source documents
2. The answer should not include information not present in the sources
3. Citations should be accurate and point to the correct sources

Scoring:
- 1.0: Perfectly faithful - all claims are fully supported by sources
- 0.8: Mostly faithful - minor unsupported details
- 0.6: Partially faithful - some unsupported claims
- 0.4: Weakly faithful - many unsupported claims
- 0.2: Largely unfaithful - most claims unsupported
- 0.0: Completely unfaithful - no connection to sources

Output your evaluation as JSON:
{{"score": <float>, "reasoning": "<explanation>"}}"""
    
    RELEVANCE_PROMPT = """You are an expert evaluator assessing the relevance of an AI assistant's answer.

Evaluate how well the answer addresses the user's question.

Question: {question}

Generated Answer:
{answer}

Evaluation Criteria:
1. The answer should directly address the question asked
2. The answer should not include irrelevant information
3. The answer should cover all aspects of the question

Scoring:
- 1.0: Perfectly relevant - directly and completely addresses the question
- 0.8: Mostly relevant - addresses main points with minor gaps
- 0.6: Partially relevant - addresses some aspects but misses others
- 0.4: Weakly relevant - tangentially related
- 0.2: Largely irrelevant - mostly off-topic
- 0.0: Completely irrelevant - does not address the question

Output your evaluation as JSON:
{{"score": <float>, "reasoning": "<explanation>"}}"""
    
    def __init__(self, llm: Optional[Any] = None, config: Optional[Any] = None):
        """
        Initialize the evaluator.
        
        Args:
            llm: Language model for evaluation (will create if not provided)
            config: LangChainConfig instance
        """
        if config is None:
            from ..config import get_config
            config = get_config()
        
        self.config = config
        
        if llm is None:
            from ..deps import get_llm
            llm = get_llm(config)
        
        self.llm = llm
    
    def _parse_llm_score(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM evaluation response.
        
        Args:
            response: LLM response string
        
        Returns:
            Dictionary with score and reasoning
        """
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback: try to extract score
                score_match = re.search(r'(\d+\.?\d*)', response)
                score = float(score_match.group(1)) if score_match else 0.5
                return {"score": score, "reasoning": response}
        except Exception as e:
            logger.warning(f"Failed to parse LLM score: {e}")
            return {"score": 0.5, "reasoning": "Failed to parse evaluation"}
    
    def evaluate_faithfulness(
        self,
        question: str,
        answer: str,
        source_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate the faithfulness of an answer to its sources.
        
        Args:
            question: Original question
            answer: Generated answer
            source_documents: Source documents used
        
        Returns:
            Dictionary with score and reasoning
        """
        # Format source documents
        sources_text = "\n\n".join([
            f"Source {i+1} ({doc.get('metadata', {}).get('source', 'unknown')}):\n{doc.get('content', '')}"
            for i, doc in enumerate(source_documents)
        ])
        
        prompt = self.FAITHFULNESS_PROMPT.format(
            question=question,
            sources=sources_text,
            answer=answer
        )
        
        response = self.llm.invoke(prompt).content
        return self._parse_llm_score(response)
    
    def evaluate_relevance(
        self,
        question: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        Evaluate the relevance of an answer to the question.
        
        Args:
            question: Original question
            answer: Generated answer
        
        Returns:
            Dictionary with score and reasoning
        """
        prompt = self.RELEVANCE_PROMPT.format(
            question=question,
            answer=answer
        )
        
        response = self.llm.invoke(prompt).content
        return self._parse_llm_score(response)
    
    def evaluate(
        self,
        question: str,
        answer: str,
        source_documents: List[Dict[str, Any]]
    ) -> EvaluationScore:
        """
        Perform complete evaluation of a RAG response.
        
        Args:
            question: Original question
            answer: Generated answer
            source_documents: Source documents used
        
        Returns:
            EvaluationScore with all metrics
        """
        # Evaluate faithfulness
        faithfulness_result = self.evaluate_faithfulness(
            question, answer, source_documents
        )
        faithfulness_score = faithfulness_result.get("score", 0.5)
        
        # Evaluate relevance
        relevance_result = self.evaluate_relevance(question, answer)
        relevance_score = relevance_result.get("score", 0.5)
        
        # Simple heuristics for other metrics
        completeness = 0.8 if len(answer) > 100 else 0.6
        clarity = 0.8 if "\n" in answer or "." in answer else 0.6
        
        # Calculate overall score
        overall = (
            faithfulness_score * 0.4 +
            relevance_score * 0.3 +
            completeness * 0.2 +
            clarity * 0.1
        )
        
        # Compile feedback
        feedback = (
            f"Faithfulness: {faithfulness_result.get('reasoning', 'N/A')}\n"
            f"Relevance: {relevance_result.get('reasoning', 'N/A')}"
        )
        
        return EvaluationScore(
            faithfulness=faithfulness_score,
            relevance=relevance_score,
            completeness=completeness,
            clarity=clarity,
            overall=overall,
            feedback=feedback
        )


def evaluate_response(
    question: str,
    answer: str,
    source_documents: List[Dict[str, Any]],
    llm: Optional[Any] = None,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Convenience function to evaluate a RAG response.
    
    Args:
        question: Original question
        answer: Generated answer
        source_documents: Source documents used
        llm: Language model for evaluation
        config: Configuration instance
    
    Returns:
        Dictionary with evaluation scores
    """
    evaluator = RAGEvaluator(llm, config)
    score = evaluator.evaluate(question, answer, source_documents)
    return score.to_dict()