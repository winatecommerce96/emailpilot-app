"""
Agent Data Requirements Analyzer
Analyzes what data each agent needs and generates appropriate MCP queries
Dynamically extracts requirements from agent prompts
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataRequirement(Enum):
    """Types of data requirements agents might have"""
    CAMPAIGN_METRICS = "campaign_metrics"
    SEGMENT_DATA = "segment_data"
    REVENUE_DATA = "revenue_data"
    ENGAGEMENT_METRICS = "engagement_metrics"
    TIMING_ANALYTICS = "timing_analytics"
    CONTENT_PERFORMANCE = "content_performance"
    FLOW_DATA = "flow_data"
    CUSTOMER_LIFECYCLE = "customer_lifecycle"
    PRODUCT_PERFORMANCE = "product_performance"


@dataclass
class AgentDataSpec:
    """Specification of what data an agent needs"""
    agent_name: str
    required_data: List[DataRequirement]
    time_range_days: int
    metrics_needed: List[str]
    custom_queries: List[str]
    extracted_from_prompt: bool = False


class AgentDataRequirements:
    """Analyzes agent requirements and generates appropriate queries"""
    
    def __init__(self):
        # Keywords that indicate data requirements
        self.data_keywords = {
            DataRequirement.CAMPAIGN_METRICS: [
                "campaign", "email performance", "open rate", "click rate", 
                "conversion", "bounce", "unsubscribe", "campaign metrics"
            ],
            DataRequirement.SEGMENT_DATA: [
                "segment", "audience", "customer group", "affinity", 
                "segmentation", "customer base", "target group"
            ],
            DataRequirement.REVENUE_DATA: [
                "revenue", "sales", "purchase", "order", "transaction",
                "monetary", "AOV", "LTV", "lifetime value"
            ],
            DataRequirement.ENGAGEMENT_METRICS: [
                "engagement", "interaction", "activity", "response",
                "click", "open", "view", "read"
            ],
            DataRequirement.TIMING_ANALYTICS: [
                "timing", "send time", "schedule", "cadence", "frequency",
                "optimal time", "best time", "when to send"
            ],
            DataRequirement.CONTENT_PERFORMANCE: [
                "subject line", "content", "creative", "copy", "message",
                "template", "design", "CTA", "call to action"
            ],
            DataRequirement.FLOW_DATA: [
                "flow", "automation", "trigger", "journey", "workflow",
                "series", "drip", "sequence"
            ],
            DataRequirement.CUSTOMER_LIFECYCLE: [
                "lifecycle", "retention", "churn", "acquisition",
                "onboarding", "activation", "loyalty"
            ],
            DataRequirement.PRODUCT_PERFORMANCE: [
                "product", "SKU", "category", "item", "merchandise",
                "bestseller", "inventory"
            ]
        }
        
        # Metrics that might be mentioned in prompts
        self.metric_patterns = {
            "open_rate": r"open\s*rate|opens|opened",
            "click_rate": r"click\s*rate|clicks|clicked|CTR",
            "conversion_rate": r"conversion\s*rate|conversions|converted|CVR",
            "bounce_rate": r"bounce\s*rate|bounces|bounced",
            "unsubscribe_rate": r"unsubscribe\s*rate|unsubscribes|opted out",
            "revenue": r"revenue|sales|income|earnings",
            "revenue_per_recipient": r"revenue per|RPR|revenue/recipient",
            "engagement_rate": r"engagement\s*rate|engaged",
            "ltv": r"lifetime value|LTV|customer value",
            "segment_size": r"segment size|audience size|list size",
            "growth_rate": r"growth|growing|increase",
            "churn_rate": r"churn|attrition|leaving",
            "aov": r"average order|AOV|basket size",
            "purchase_frequency": r"purchase frequency|buying frequency|repeat purchase"
        }
        
        # Time range patterns
        self.time_patterns = {
            7: r"week|7 days|weekly",
            30: r"month|30 days|monthly",
            60: r"2 months|60 days|two months",
            90: r"quarter|3 months|90 days|quarterly",
            180: r"6 months|180 days|half year",
            365: r"year|365 days|annual|yearly"
        }
    
    def analyze_agent_prompt(self, agent_name: str, prompt_template: str) -> AgentDataSpec:
        """
        Dynamically analyze an agent's prompt to extract data requirements
        """
        prompt_lower = prompt_template.lower()
        
        # Extract data requirements
        required_data = []
        for req_type, keywords in self.data_keywords.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    required_data.append(req_type)
                    break
        
        # Remove duplicates
        required_data = list(set(required_data))
        
        # Extract metrics
        metrics_needed = []
        for metric, pattern in self.metric_patterns.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                metrics_needed.append(metric)
        
        # Extract time range
        time_range_days = 90  # Default
        for days, pattern in self.time_patterns.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                time_range_days = days
                break
        
        # Generate custom queries based on requirements
        custom_queries = self.generate_queries_for_requirements(
            required_data, metrics_needed, time_range_days, agent_name
        )
        
        return AgentDataSpec(
            agent_name=agent_name,
            required_data=required_data,
            time_range_days=time_range_days,
            metrics_needed=metrics_needed,
            custom_queries=custom_queries,
            extracted_from_prompt=True
        )
    
    def generate_queries_for_requirements(self, 
                                         requirements: List[DataRequirement],
                                         metrics: List[str],
                                         time_range: int,
                                         agent_name: str) -> List[str]:
        """Generate specific queries based on extracted requirements"""
        queries = []
        
        # Campaign metrics query
        if DataRequirement.CAMPAIGN_METRICS in requirements:
            campaign_metrics = [m for m in metrics if m in [
                "open_rate", "click_rate", "conversion_rate", 
                "bounce_rate", "unsubscribe_rate"
            ]]
            if campaign_metrics:
                metrics_str = ", ".join(campaign_metrics)
                queries.append(
                    f"Get campaign performance metrics for last {time_range} days including: {metrics_str}"
                )
            else:
                queries.append(
                    f"Get all campaign performance metrics for last {time_range} days"
                )
        
        # Segment data query
        if DataRequirement.SEGMENT_DATA in requirements:
            segment_metrics = [m for m in metrics if m in [
                "segment_size", "engagement_rate", "ltv", 
                "purchase_frequency", "growth_rate", "churn_rate"
            ]]
            if segment_metrics:
                metrics_str = ", ".join(segment_metrics)
                queries.append(
                    f"List all segments with metrics: {metrics_str}"
                )
            else:
                queries.append(
                    "List all active segments with size, engagement rates, and value metrics"
                )
        
        # Revenue query
        if DataRequirement.REVENUE_DATA in requirements:
            queries.append(
                f"Calculate revenue metrics for last {time_range} days including total revenue, revenue per campaign, and revenue by segment"
            )
        
        # Timing analytics
        if DataRequirement.TIMING_ANALYTICS in requirements:
            queries.append(
                "Analyze optimal send times by day of week and hour based on engagement metrics"
            )
        
        # Content performance
        if DataRequirement.CONTENT_PERFORMANCE in requirements:
            queries.append(
                "Analyze top performing subject lines, content themes, and CTAs with their performance metrics"
            )
        
        return queries
    
    def analyze_workflow_agents(self, agents_config: Dict[str, Any]) -> Dict[str, AgentDataSpec]:
        """
        Analyze all agents in a workflow and extract their data requirements
        """
        agent_specs = {}
        
        for agent_name, agent_config in agents_config.items():
            if isinstance(agent_config, dict) and "prompt_template" in agent_config:
                spec = self.analyze_agent_prompt(
                    agent_name, 
                    agent_config["prompt_template"]
                )
                agent_specs[agent_name] = spec
                logger.info(f"Analyzed {agent_name}: {len(spec.metrics_needed)} metrics, {len(spec.required_data)} data types")
        
        return agent_specs
    
    def combine_workflow_requirements(self, agent_specs: Dict[str, AgentDataSpec]) -> Dict[str, Any]:
        """
        Combine requirements from all agents in a workflow
        """
        all_requirements = set()
        all_metrics = set()
        all_queries = []
        max_time_range = 30
        
        for spec in agent_specs.values():
            all_requirements.update(spec.required_data)
            all_metrics.update(spec.metrics_needed)
            all_queries.extend(spec.custom_queries)
            max_time_range = max(max_time_range, spec.time_range_days)
        
        # Remove duplicate queries
        unique_queries = list(dict.fromkeys(all_queries))
        
        return {
            "data_types": [r.value for r in all_requirements],
            "metrics": list(all_metrics),
            "time_range_days": max_time_range,
            "queries": unique_queries,
            "agent_count": len(agent_specs)
        }
    
    def validate_data_completeness(self, 
                                  spec: AgentDataSpec,
                                  retrieved_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if retrieved data meets agent requirements
        """
        missing_metrics = []
        
        # Check for required metrics
        for metric in spec.metrics_needed:
            if not self._find_metric_in_data(metric, retrieved_data):
                missing_metrics.append(metric)
        
        # Check for required data types
        missing_data_types = []
        for req_type in spec.required_data:
            if not self._check_data_type_present(req_type, retrieved_data):
                missing_data_types.append(req_type.value)
        
        is_complete = len(missing_metrics) == 0 and len(missing_data_types) == 0
        
        return {
            "complete": is_complete,
            "missing_metrics": missing_metrics,
            "missing_data_types": missing_data_types,
            "missing_queries": self._generate_queries_for_missing(
                missing_metrics, missing_data_types
            ) if not is_complete else []
        }
    
    def _find_metric_in_data(self, metric: str, data: Dict[str, Any]) -> bool:
        """Recursively search for a metric in retrieved data"""
        if metric in data:
            return True
        
        # Also check for variations (e.g., open_rate vs openRate)
        metric_variations = [
            metric,
            metric.replace("_", ""),
            metric.replace("_", "-"),
            "".join(word.capitalize() for word in metric.split("_"))  # camelCase
        ]
        
        for variant in metric_variations:
            if variant in data:
                return True
        
        # Recursive search
        for value in data.values():
            if isinstance(value, dict):
                if self._find_metric_in_data(metric, value):
                    return True
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                for item in value:
                    if self._find_metric_in_data(metric, item):
                        return True
        
        return False
    
    def _check_data_type_present(self, req_type: DataRequirement, data: Dict[str, Any]) -> bool:
        """Check if a required data type is present in the response"""
        # Map data types to expected keys in response
        type_indicators = {
            DataRequirement.CAMPAIGN_METRICS: ["campaigns", "campaign_data", "email_metrics"],
            DataRequirement.SEGMENT_DATA: ["segments", "audiences", "segment_data"],
            DataRequirement.REVENUE_DATA: ["revenue", "sales", "transactions"],
            DataRequirement.TIMING_ANALYTICS: ["timing", "send_times", "schedule_analysis"],
            DataRequirement.CONTENT_PERFORMANCE: ["content", "subject_lines", "creative_performance"]
        }
        
        indicators = type_indicators.get(req_type, [])
        for indicator in indicators:
            if indicator in data and data[indicator]:
                return True
        
        return False
    
    def _generate_queries_for_missing(self, 
                                     missing_metrics: List[str],
                                     missing_data_types: List[str]) -> List[str]:
        """Generate specific queries to retrieve missing data"""
        queries = []
        
        # Group metrics by type for efficient querying
        if missing_metrics:
            campaign_metrics = [m for m in missing_metrics if m in [
                "open_rate", "click_rate", "conversion_rate", "bounce_rate"
            ]]
            if campaign_metrics:
                queries.append(f"Get missing campaign metrics: {', '.join(campaign_metrics)}")
            
            segment_metrics = [m for m in missing_metrics if m in [
                "segment_size", "engagement_rate", "ltv"
            ]]
            if segment_metrics:
                queries.append(f"Get missing segment metrics: {', '.join(segment_metrics)}")
            
            revenue_metrics = [m for m in missing_metrics if "revenue" in m]
            if revenue_metrics:
                queries.append(f"Get missing revenue data: {', '.join(revenue_metrics)}")
        
        # Add queries for missing data types
        for data_type in missing_data_types:
            if data_type == "timing_analytics":
                queries.append("Get send time performance analysis")
            elif data_type == "content_performance":
                queries.append("Get content and subject line performance data")
            elif data_type == "customer_lifecycle":
                queries.append("Get customer lifecycle and retention metrics")
        
        return queries


# Singleton instance
_requirements_analyzer: Optional[AgentDataRequirements] = None


def get_requirements_analyzer() -> AgentDataRequirements:
    """Get singleton requirements analyzer instance"""
    global _requirements_analyzer
    if _requirements_analyzer is None:
        _requirements_analyzer = AgentDataRequirements()
    return _requirements_analyzer