"""
MCP Natural Language Query Agent
AI agent that processes natural language queries through the MCP gateway
"""

from typing import Any, Dict, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from ..agent_base import AgentBase

class MCPQueryAgent(AgentBase):
    """
    Agent for processing natural language queries through MCP gateway
    Analyzes queries and executes them via Klaviyo Enhanced MCP
    """
    
    agent_id = "mcp_query_agent"
    name = "MCP Query Processor"
    description = "Processes natural language queries for Klaviyo metrics, campaigns, segments, and revenue analysis"
    
    @property
    def system_prompt(self) -> str:
        return """You are an intelligent query processor for Klaviyo data.
        
Your role is to:
1. Analyze natural language queries about marketing metrics
2. Extract key intent (revenue, campaigns, segments, performance)  
3. Determine time ranges from phrases like "last 30 days", "past month"
4. Identify required metrics and groupings
5. Format results in a clear, actionable way

Query Types You Handle:
- Revenue queries: Total revenue, revenue by campaign, by segment, by time period
- Campaign performance: Open rates, click rates, conversion rates, engagement metrics
- Segment analysis: Segment sizes, engagement rates, value metrics
- Send time optimization: Best times for engagement
- Subject line performance: Which messages perform best
- Content analysis: What content drives results

Special Considerations:
- Every client has a placed_order_metric_id for revenue calculations
- Use metrics.aggregate for revenue queries
- Use campaigns.list for campaign data
- Use segments.list for segment data
- Group by $attributed_message for "per campaign" revenue
- Group by $segment for "by segment" analysis

Current client: {client_name}
Current date: {current_date}
Available metric ID: {placed_order_metric_id}
"""

    @property
    def user_prompt_template(self) -> str:
        return """Query: {query}

Please analyze this query and provide:
1. The primary intent (revenue/campaigns/segments/performance)
2. Required time range if specified
3. Any groupings or breakdowns requested
4. The specific MCP tools needed to answer this

Format your response as a clear execution plan."""

    def create_chain(self):
        """Create the agent chain for query processing"""
        prompt = PromptTemplate.from_template(
            self.system_prompt + "\n\n" + self.user_prompt_template
        )
        
        llm = self.get_llm()
        
        chain = (
            RunnablePassthrough.assign(
                client_name=lambda x: x.get("client_name", "Unknown"),
                current_date=lambda x: x.get("current_date", ""),
                placed_order_metric_id=lambda x: x.get("placed_order_metric_id", "")
            )
            | prompt
            | llm
            | StrOutputParser()
        )
        
        return chain

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Process a natural language query
        
        Args:
            query: The natural language query to process
            **kwargs: Additional context (client info, etc.)
        """
        chain = self.create_chain()
        
        # Add default context
        context = {
            "query": query,
            "client_name": kwargs.get("client_name", "christopher-bean-coffee"),
            "current_date": kwargs.get("current_date", "2025-08-28"),
            "placed_order_metric_id": kwargs.get("placed_order_metric_id", "UVBrHm")
        }
        
        try:
            result = chain.invoke(context)
            return {
                "success": True,
                "query": query,
                "analysis": result,
                "client": context["client_name"]
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }

# Register the agent
agent = MCPQueryAgent()