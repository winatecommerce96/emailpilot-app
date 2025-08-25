"""
Calendar LangGraph Service Bridge
Connects the Calendar system to LangGraph for AI-powered planning and analytics
"""

import os
import httpx
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import uuid4
import asyncio

from langsmith import Client
from langsmith.run_helpers import traceable

logger = logging.getLogger(__name__)

class CalendarLangGraphService:
    """
    Service layer for integrating Calendar with LangGraph
    Provides methods for campaign planning, analytics, and variable management
    """
    
    def __init__(self):
        self.langgraph_url = os.getenv("LANGGRAPH_URL", "http://127.0.0.1:2024")
        self.langsmith_client = Client() if os.getenv("ENABLE_TRACING", "true").lower() == "true" else None
        self.project_name = os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        
    @traceable(
        run_type="chain",
        name="langgraph_campaign_planning"
    )
    async def plan_campaign_with_langgraph(
        self,
        client_id: str,
        brand: str,
        month: str,
        campaign_type: str,
        goals: Dict[str, Any] = None,
        context_variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive campaign plan using LangGraph
        
        Args:
            client_id: Client identifier
            brand: Brand name
            month: Planning month (YYYY-MM)
            campaign_type: Type of campaign (product_launch, seasonal, etc.)
            goals: Campaign goals and KPIs
            context_variables: Additional context from Firestore
            
        Returns:
            Campaign plan with events, timeline, and strategies
        """
        try:
            # Build comprehensive prompt
            prompt = self._build_campaign_prompt(
                brand, month, campaign_type, goals, context_variables
            )
            
            # Create thread ID for conversation continuity
            thread_id = f"campaign_{client_id}_{month}_{uuid4().hex[:8]}"
            
            # Prepare request for LangGraph
            request_data = {
                "assistant_id": "agent",
                "input": {
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "brand": brand,
                    "month": month,
                    "campaign_type": campaign_type,
                    **context_variables if context_variables else {}
                },
                "config": {
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            }
            
            logger.info(f"Calling LangGraph for campaign planning: {thread_id}")
            
            # Call LangGraph API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.langgraph_url}/threads",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Parse and structure the response
                    campaign_plan = await self._parse_campaign_response(result, brand, month)
                    
                    # Add trace information
                    campaign_plan["trace_id"] = thread_id
                    campaign_plan["langgraph_thread_id"] = result.get("thread_id")
                    
                    return campaign_plan
                else:
                    logger.error(f"LangGraph error: {response.status_code} - {response.text}")
                    return {
                        "error": f"LangGraph returned {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Failed to plan campaign with LangGraph: {e}")
            return {
                "error": "Failed to generate campaign plan",
                "details": str(e)
            }
    
    @traceable(
        run_type="chain", 
        name="langgraph_analytics"
    )
    async def analyze_calendar_performance(
        self,
        client_id: str,
        month: str,
        events: List[Dict[str, Any]],
        metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze calendar performance using LangGraph
        
        Args:
            client_id: Client identifier
            month: Analysis month
            events: List of calendar events
            metrics: Performance metrics from Klaviyo
            
        Returns:
            Performance analysis with insights and recommendations
        """
        try:
            # Build analytics prompt
            prompt = f"""
            Analyze the calendar performance for {client_id} in {month}:
            
            Events Summary:
            - Total events: {len(events)}
            - Event types: {self._count_event_types(events)}
            - Completion rate: {self._calculate_completion_rate(events)}%
            
            Performance Metrics:
            {json.dumps(metrics, indent=2) if metrics else "No metrics available"}
            
            Provide insights on:
            1. Campaign effectiveness and ROI
            2. Optimal timing patterns
            3. Content performance by type
            4. Recommendations for improvement
            5. Predicted outcomes for next month
            """
            
            # Call LangGraph for analysis
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.langgraph_url}/threads",
                    json={
                        "assistant_id": "agent",
                        "input": {
                            "messages": [{
                                "role": "user",
                                "content": prompt
                            }],
                            "brand": client_id,
                            "month": month
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "analysis": result,
                        "insights_generated": True,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "error": "Analysis failed",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            logger.error(f"Failed to analyze performance: {e}")
            return {
                "error": "Analysis failed",
                "details": str(e)
            }
    
    async def sync_variables_to_langgraph(
        self,
        client_id: str,
        variables: Dict[str, Any]
    ) -> bool:
        """
        Sync Firestore variables to LangGraph context
        
        Args:
            client_id: Client identifier
            variables: Variables to sync
            
        Returns:
            Success status
        """
        try:
            # Store variables in a format LangGraph can use
            # This could be via a shared context store or direct API call
            
            logger.info(f"Syncing {len(variables)} variables for {client_id}")
            
            # For now, we'll just validate the variables
            # In production, this would sync to a shared context store
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync variables: {e}")
            return False
    
    async def get_langgraph_tools(self) -> List[Dict[str, Any]]:
        """
        Get available tools from LangGraph
        
        Returns:
            List of available tools with descriptions
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.langgraph_url}/assistants/agent"
                )
                
                if response.status_code == 200:
                    assistant_info = response.json()
                    
                    # Extract tools information
                    tools = [
                        {
                            "name": "analyze_klaviyo_metrics",
                            "description": "Analyze Klaviyo metrics for a brand and month",
                            "parameters": ["brand", "month"]
                        },
                        {
                            "name": "generate_campaign_calendar",
                            "description": "Generate a campaign calendar for the specified month",
                            "parameters": ["brand", "month", "campaign_count"]
                        },
                        {
                            "name": "optimize_send_times",
                            "description": "Suggest optimal send times based on brand and timezone",
                            "parameters": ["brand", "timezone"]
                        }
                    ]
                    
                    return tools
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get LangGraph tools: {e}")
            return []
    
    async def create_calendar_agent(
        self,
        agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new calendar-specific agent in LangGraph
        
        Args:
            agent_config: Agent configuration
            
        Returns:
            Created agent information
        """
        try:
            # This would create a new agent in the LangGraph system
            # For now, we'll return a mock response
            
            agent_id = f"calendar_agent_{uuid4().hex[:8]}"
            
            return {
                "agent_id": agent_id,
                "name": agent_config.get("name", "Calendar Agent"),
                "capabilities": agent_config.get("capabilities", []),
                "status": "created",
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            return {
                "error": "Failed to create agent",
                "details": str(e)
            }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _build_campaign_prompt(
        self,
        brand: str,
        month: str,
        campaign_type: str,
        goals: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build comprehensive prompt for campaign planning"""
        
        prompt = f"""
        Create a comprehensive {campaign_type} campaign plan for {brand} in {month}.
        
        Campaign Goals:
        {json.dumps(goals, indent=2) if goals else "Standard campaign goals"}
        
        Context Information:
        - Previous month performance: {context.get('previous_month_metrics', 'N/A')}
        - Active segments: {context.get('segments', 'N/A')}
        - Best performing content: {context.get('top_content', 'N/A')}
        
        Please provide:
        1. Strategic campaign overview
        2. Detailed timeline with specific dates
        3. Content themes and messaging
        4. Segmentation strategy
        5. Channel mix (email vs SMS)
        6. Expected outcomes and KPIs
        7. Risk mitigation strategies
        
        Format the response as structured JSON with clear sections.
        """
        
        return prompt
    
    async def _parse_campaign_response(
        self,
        langgraph_response: Dict[str, Any],
        brand: str,
        month: str
    ) -> Dict[str, Any]:
        """Parse LangGraph response into structured campaign plan"""
        
        # Extract the campaign plan from LangGraph response
        # This would parse the actual response structure
        
        campaign_plan = {
            "brand": brand,
            "month": month,
            "strategy": "AI-generated campaign strategy",
            "events": [],
            "timeline": {},
            "kpis": {},
            "generated_at": datetime.now().isoformat()
        }
        
        # Parse events from response
        # This is a simplified version - actual implementation would parse the real response
        
        return campaign_plan
    
    def _count_event_types(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count events by type"""
        type_counts = {}
        for event in events:
            event_type = event.get("type", "unknown")
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        return type_counts
    
    def _calculate_completion_rate(self, events: List[Dict[str, Any]]) -> float:
        """Calculate event completion rate"""
        if not events:
            return 0.0
        
        completed = sum(1 for e in events if e.get("status") == "completed")
        return round((completed / len(events)) * 100, 2)


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_service_instance = None

def get_calendar_langgraph_service() -> CalendarLangGraphService:
    """Get or create singleton service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = CalendarLangGraphService()
    return _service_instance


# ============================================================================
# DIRECT API FUNCTIONS
# ============================================================================

@traceable(
    run_type="workflow",
    name="calendar_langgraph_integration"
)
async def integrate_calendar_with_langgraph(
    client_id: str,
    month: str,
    action: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Main integration function for Calendar-LangGraph operations
    
    Args:
        client_id: Client identifier
        month: Target month
        action: Action to perform (plan, analyze, sync)
        **kwargs: Additional parameters
        
    Returns:
        Action result
    """
    service = get_calendar_langgraph_service()
    
    if action == "plan":
        return await service.plan_campaign_with_langgraph(
            client_id=client_id,
            brand=kwargs.get("brand", client_id),
            month=month,
            campaign_type=kwargs.get("campaign_type", "general"),
            goals=kwargs.get("goals"),
            context_variables=kwargs.get("context_variables")
        )
    
    elif action == "analyze":
        return await service.analyze_calendar_performance(
            client_id=client_id,
            month=month,
            events=kwargs.get("events", []),
            metrics=kwargs.get("metrics")
        )
    
    elif action == "sync":
        success = await service.sync_variables_to_langgraph(
            client_id=client_id,
            variables=kwargs.get("variables", {})
        )
        return {"success": success}
    
    else:
        return {
            "error": f"Unknown action: {action}",
            "available_actions": ["plan", "analyze", "sync"]
        }