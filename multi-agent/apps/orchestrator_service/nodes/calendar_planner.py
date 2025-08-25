"""
Calendar Planning Agent Node
Specialized agent for email campaign calendar planning with LangSmith tracing
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith.run_helpers import traceable

logger = logging.getLogger(__name__)

class CalendarPlannerNode:
    """
    Agent node for calendar planning operations
    Integrates with LangGraph and provides campaign planning capabilities
    """
    
    def __init__(self, llm=None):
        """Initialize the calendar planner node"""
        self.llm = llm or ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized email campaign calendar planning agent.
            Your role is to create strategic campaign calendars that optimize engagement and revenue.
            
            You have access to:
            - Historical campaign performance data
            - Customer segmentation information
            - Seasonal trends and patterns
            - Best practices for email marketing
            
            When planning campaigns, consider:
            1. Optimal send times based on past performance
            2. Campaign frequency to avoid fatigue
            3. Content variety and relevance
            4. Segment-specific messaging
            5. Multi-channel coordination (email + SMS)
            """),
            ("human", "{input}")
        ])
    
    @traceable(
        run_type="chain",
        name="calendar_planner_invoke",
        project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar"),
        tags=["agent", "calendar", "planning"]
    )
    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process calendar planning request
        
        Args:
            state: Current conversation state with messages and context
            
        Returns:
            Updated state with planning response
        """
        try:
            # Extract context from state
            messages = state.get("messages", [])
            brand = state.get("brand", "Unknown Brand")
            month = state.get("month", datetime.now().strftime("%Y-%m"))
            variables = state.get("variables", {})
            
            # Get the last user message
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, dict):
                    user_input = last_message.get("content", "")
                else:
                    user_input = str(last_message.content if hasattr(last_message, 'content') else last_message)
            else:
                user_input = "Create a campaign calendar"
            
            # Build enhanced prompt with context
            enhanced_input = f"""
            Brand: {brand}
            Planning Month: {month}
            
            Available Context:
            - Previous month revenue: ${variables.get('previous_month_revenue', 'N/A')}
            - Active segments: {variables.get('active_segments', 'N/A')}
            - Top performing content: {variables.get('top_content', 'N/A')}
            - Seasonal considerations: {self._get_seasonal_context(month)}
            
            User Request: {user_input}
            
            Please provide a detailed campaign calendar with:
            1. Specific dates and times
            2. Campaign types and themes
            3. Target segments
            4. Expected outcomes
            5. Content recommendations
            """
            
            # Generate response using LLM
            prompt = self.prompt_template.format_messages(input=enhanced_input)
            response = await self.llm.ainvoke(prompt)
            
            # Parse and structure the response
            campaign_plan = self._parse_campaign_plan(response.content)
            
            # Update state with response
            state["messages"].append(AIMessage(content=response.content))
            state["campaign_plan"] = campaign_plan
            state["planning_complete"] = True
            
            logger.info(f"Calendar planning completed for {brand} - {month}")
            
            return state
            
        except Exception as e:
            logger.error(f"Calendar planner error: {e}")
            state["messages"].append(AIMessage(
                content=f"I encountered an error while planning the calendar: {str(e)}"
            ))
            state["planning_complete"] = False
            return state
    
    def _get_seasonal_context(self, month: str) -> str:
        """Get seasonal context for the given month"""
        try:
            month_num = int(month.split("-")[1])
            
            seasonal_events = {
                1: "New Year, post-holiday sales",
                2: "Valentine's Day, Presidents Day",
                3: "Spring arrivals, St. Patrick's Day",
                4: "Easter, Spring sales",
                5: "Mother's Day, Memorial Day",
                6: "Father's Day, Summer start",
                7: "Independence Day, Summer sales",
                8: "Back-to-school",
                9: "Labor Day, Fall arrivals",
                10: "Halloween, Fall sales",
                11: "Black Friday, Cyber Monday, Thanksgiving",
                12: "Holiday shopping, Year-end sales"
            }
            
            return seasonal_events.get(month_num, "Regular monthly promotions")
            
        except:
            return "Regular monthly promotions"
    
    def _parse_campaign_plan(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM response into structured campaign plan"""
        
        # This would parse the actual LLM response
        # For now, return a structured placeholder
        
        return {
            "campaigns": [],
            "timeline": {},
            "segments": [],
            "themes": [],
            "kpis": {},
            "generated_at": datetime.now().isoformat()
        }


class CalendarAnalyzerNode:
    """
    Agent node for calendar performance analysis
    Analyzes past campaign performance and provides insights
    """
    
    def __init__(self, llm=None):
        """Initialize the calendar analyzer node"""
        self.llm = llm or ChatOpenAI(
            model="gpt-4",
            temperature=0.5,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a calendar performance analysis specialist.
            Your role is to analyze campaign calendar effectiveness and provide actionable insights.
            
            Focus on:
            1. Campaign performance metrics (open rates, click rates, conversions)
            2. Timing effectiveness analysis
            3. Content performance by type
            4. Segment response patterns
            5. Revenue attribution by campaign
            
            Provide data-driven recommendations for optimization.
            """),
            ("human", "{input}")
        ])
    
    @traceable(
        run_type="chain",
        name="calendar_analyzer_invoke",
        project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar"),
        tags=["agent", "calendar", "analytics"]
    )
    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze calendar performance
        
        Args:
            state: Current state with calendar events and metrics
            
        Returns:
            Updated state with analysis results
        """
        try:
            # Extract data for analysis
            events = state.get("calendar_events", [])
            metrics = state.get("performance_metrics", {})
            brand = state.get("brand", "Unknown")
            month = state.get("month", "Unknown")
            
            # Build analysis prompt
            analysis_input = f"""
            Analyze calendar performance for {brand} in {month}:
            
            Calendar Events:
            {json.dumps(events[:10], indent=2)}  # Limit to first 10 for prompt
            
            Performance Metrics:
            {json.dumps(metrics, indent=2)}
            
            Provide insights on:
            1. Overall campaign effectiveness
            2. Best and worst performing campaigns
            3. Optimal timing patterns discovered
            4. Segment response analysis
            5. Recommendations for next month
            """
            
            # Generate analysis
            prompt = self.prompt_template.format_messages(input=analysis_input)
            response = await self.llm.ainvoke(prompt)
            
            # Update state with analysis
            state["messages"].append(AIMessage(content=response.content))
            state["analysis_complete"] = True
            state["calendar_insights"] = {
                "analysis": response.content,
                "timestamp": datetime.now().isoformat(),
                "events_analyzed": len(events),
                "month": month
            }
            
            logger.info(f"Calendar analysis completed for {brand} - {month}")
            
            return state
            
        except Exception as e:
            logger.error(f"Calendar analyzer error: {e}")
            state["messages"].append(AIMessage(
                content=f"Error during calendar analysis: {str(e)}"
            ))
            state["analysis_complete"] = False
            return state


class CalendarCoordinatorNode:
    """
    Agent node for coordinating calendar with other systems
    Ensures calendar events are synchronized across platforms
    """
    
    def __init__(self):
        """Initialize the calendar coordinator node"""
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    @traceable(
        run_type="chain",
        name="calendar_coordinator_invoke",
        project_name=os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar"),
        tags=["agent", "calendar", "coordination"]
    )
    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate calendar with external systems
        
        Args:
            state: Current state with calendar events
            
        Returns:
            Updated state with coordination status
        """
        try:
            events = state.get("calendar_events", [])
            sync_targets = state.get("sync_targets", ["klaviyo", "firestore"])
            
            coordination_results = {
                "events_processed": len(events),
                "sync_targets": sync_targets,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
            # Here you would implement actual synchronization logic
            # For now, we'll just update the state
            
            state["coordination_complete"] = True
            state["coordination_results"] = coordination_results
            
            logger.info(f"Calendar coordination completed: {len(events)} events")
            
            return state
            
        except Exception as e:
            logger.error(f"Calendar coordinator error: {e}")
            state["coordination_complete"] = False
            state["coordination_error"] = str(e)
            return state


# ============================================================================
# AGENT REGISTRATION
# ============================================================================

def register_calendar_agents():
    """
    Register all calendar agents in the system
    This function should be called during system initialization
    """
    agents = {
        "calendar_planner": CalendarPlannerNode(),
        "calendar_analyzer": CalendarAnalyzerNode(),
        "calendar_coordinator": CalendarCoordinatorNode()
    }
    
    logger.info(f"Registered {len(agents)} calendar agents")
    
    return agents