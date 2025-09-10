"""
Calendar Planning Workflow Template
A reusable workflow for planning monthly email campaign calendars
"""

from typing import Dict, Any, TypedDict, List
from datetime import datetime, timedelta
from .base import WorkflowTemplate

# Try to import LangGraph components
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None

class CalendarState(TypedDict):
    """State for calendar planning workflow"""
    client_id: str
    month: str
    historical_campaigns: List[Dict]
    performance_metrics: Dict[str, Any]
    ai_recommendations: List[str]
    calendar_events: List[Dict]
    status: str
    error: str

class CalendarPlannerTemplate(WorkflowTemplate):
    """
    Reusable calendar planning workflow template
    Works for any client to plan monthly email campaigns
    """
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "id": "calendar_planner",
            "name": "AI Calendar Planning Workflow",
            "description": "Plan monthly email campaign calendars with AI recommendations based on historical performance",
            "category": "Planning",
            "author": "EmailPilot Team",
            "version": "2.0.0",
            "required_tools": [
                "klaviyo_campaigns",
                "klaviyo_campaign_metrics",
                "klaviyo_metrics_aggregate",
                "klaviyo_segments",
                "klaviyo_events"
            ],
            "required_agents": [
                "calendar_planner",
                "campaign_strategist",
                "performance_analyst"
            ],
            "parameters": {
                "month_offset": {
                    "type": "int",
                    "default": 1,
                    "description": "How many months ahead to plan (1 = next month)"
                },
                "campaign_count": {
                    "type": "int",
                    "default": 8,
                    "description": "Target number of campaigns to plan"
                },
                "include_holidays": {
                    "type": "bool",
                    "default": True,
                    "description": "Include holiday-specific campaigns"
                },
                "optimization_goal": {
                    "type": "str",
                    "default": "balanced",
                    "description": "Optimization goal: revenue, engagement, or balanced"
                },
                "min_days_between": {
                    "type": "int",
                    "default": 3,
                    "description": "Minimum days between campaigns"
                }
            }
        }
    
    def build_graph(self, client_id: str, params: Dict[str, Any]) -> Any:
        """
        Build the calendar planning workflow graph
        
        This creates a LangGraph workflow that:
        1. Fetches historical campaign data
        2. Analyzes performance metrics
        3. Generates AI recommendations
        4. Creates optimized calendar
        """
        
        if not LANGGRAPH_AVAILABLE:
            # Return a simple callable if LangGraph not available
            return self._build_simple_workflow(client_id, params)
        
        # Create the workflow graph
        workflow = StateGraph(CalendarState)
        
        # Add nodes
        workflow.add_node("fetch_historical", 
                         lambda s: self._fetch_historical_data(s, client_id))
        workflow.add_node("analyze_performance", 
                         lambda s: self._analyze_performance(s, client_id))
        workflow.add_node("generate_recommendations", 
                         lambda s: self._generate_ai_recommendations(s, client_id, params))
        workflow.add_node("create_calendar", 
                         lambda s: self._create_calendar(s, client_id, params))
        
        # Define edges
        workflow.set_entry_point("fetch_historical")
        workflow.add_edge("fetch_historical", "analyze_performance")
        workflow.add_edge("analyze_performance", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "create_calendar")
        workflow.add_edge("create_calendar", END)
        
        return workflow.compile()
    
    def _fetch_historical_data(self, state: Dict, client_id: str) -> Dict:
        """Fetch historical campaign data using Enhanced MCP"""
        
        # In production, this would use actual Enhanced MCP tools
        # For now, return mock structure
        state["historical_campaigns"] = [
            {
                "id": f"camp_{i}",
                "name": f"Campaign {i}",
                "sent_date": (datetime.now() - timedelta(days=30*i)).isoformat(),
                "metrics": {
                    "open_rate": 0.25,
                    "click_rate": 0.03,
                    "revenue": 5000
                }
            }
            for i in range(1, 6)
        ]
        state["status"] = "historical_fetched"
        return state
    
    def _analyze_performance(self, state: Dict, client_id: str) -> Dict:
        """Analyze campaign performance metrics"""
        
        campaigns = state.get("historical_campaigns", [])
        
        # Calculate aggregate metrics
        total_revenue = sum(c["metrics"]["revenue"] for c in campaigns)
        avg_open_rate = sum(c["metrics"]["open_rate"] for c in campaigns) / len(campaigns) if campaigns else 0
        avg_click_rate = sum(c["metrics"]["click_rate"] for c in campaigns) / len(campaigns) if campaigns else 0
        
        state["performance_metrics"] = {
            "total_revenue": total_revenue,
            "avg_open_rate": avg_open_rate,
            "avg_click_rate": avg_click_rate,
            "campaign_count": len(campaigns),
            "best_performer": max(campaigns, key=lambda c: c["metrics"]["revenue"])["name"] if campaigns else None
        }
        state["status"] = "performance_analyzed"
        return state
    
    def _generate_ai_recommendations(self, state: Dict, client_id: str, params: Dict) -> Dict:
        """Generate AI recommendations for calendar"""
        
        metrics = state.get("performance_metrics", {})
        optimization_goal = params.get("optimization_goal", "balanced")
        
        recommendations = []
        
        # Generate recommendations based on performance
        if metrics.get("avg_open_rate", 0) < 0.2:
            recommendations.append("Focus on subject line optimization to improve open rates")
        
        if metrics.get("avg_click_rate", 0) < 0.02:
            recommendations.append("Improve CTA placement and content relevance")
        
        if optimization_goal == "revenue":
            recommendations.append("Prioritize product-focused campaigns with clear purchase CTAs")
        elif optimization_goal == "engagement":
            recommendations.append("Include more interactive content and community-building campaigns")
        else:
            recommendations.append("Balance promotional and engagement content 60/40")
        
        # Add seasonal recommendations
        if params.get("include_holidays", True):
            recommendations.append("Include holiday-specific campaigns for maximum impact")
        
        state["ai_recommendations"] = recommendations
        state["status"] = "recommendations_generated"
        return state
    
    def _create_calendar(self, state: Dict, client_id: str, params: Dict) -> Dict:
        """Create the actual campaign calendar"""
        
        month_offset = params.get("month_offset", 1)
        campaign_count = params.get("campaign_count", 8)
        min_days_between = params.get("min_days_between", 3)
        
        # Calculate target month
        target_date = datetime.now() + timedelta(days=30 * month_offset)
        month = target_date.strftime("%Y-%m")
        
        # Generate calendar events
        events = []
        current_date = target_date.replace(day=1)
        
        for i in range(campaign_count):
            event_date = current_date + timedelta(days=min_days_between * i + i)
            
            # Determine campaign type based on recommendations
            campaign_types = ["Newsletter", "Product Launch", "Promotion", "Engagement", "Seasonal"]
            campaign_type = campaign_types[i % len(campaign_types)]
            
            events.append({
                "date": event_date.isoformat(),
                "type": campaign_type,
                "name": f"{campaign_type} - {event_date.strftime('%B %d')}",
                "status": "planned",
                "estimated_revenue": state.get("performance_metrics", {}).get("total_revenue", 5000) / campaign_count,
                "recommendations": state.get("ai_recommendations", [])[:2]  # Include top 2 recommendations
            })
        
        state["calendar_events"] = events
        state["month"] = month
        state["status"] = "calendar_created"
        
        return state
    
    def _build_simple_workflow(self, client_id: str, params: Dict) -> callable:
        """Build a simple callable workflow when LangGraph is not available"""
        
        def workflow_runner(input_state: Dict = None) -> Dict:
            state = input_state or {"client_id": client_id}
            
            # Run workflow steps sequentially
            state = self._fetch_historical_data(state, client_id)
            state = self._analyze_performance(state, client_id)
            state = self._generate_ai_recommendations(state, client_id, params)
            state = self._create_calendar(state, client_id, params)
            
            return state
        
        return workflow_runner
    
    def to_code(self, client_id: str = "{{CLIENT_ID}}") -> str:
        """Generate executable Python code for this template"""
        
        return f"""# AI Calendar Planning Workflow
# Auto-generated from CalendarPlannerTemplate v2.0.0

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from datetime import datetime, timedelta
from multi_agent.integrations.langchain_core.adapters.enhanced_mcp_adapter import get_enhanced_mcp_adapter

# Initialize Enhanced MCP
adapter = get_enhanced_mcp_adapter()

# Workflow State
class CalendarState(TypedDict):
    client_id: str
    month: str
    historical_campaigns: List[Dict]
    performance_metrics: Dict[str, Any]
    ai_recommendations: List[str]
    calendar_events: List[Dict]
    status: str

# Create workflow
def create_calendar_workflow(client_id: str = "{client_id}", **params):
    workflow = StateGraph(CalendarState)
    
    # Add your nodes here
    # ... (generated node implementations)
    
    return workflow.compile()

# Execute workflow
def run_calendar_planning(client_id: str = "{client_id}", month_offset: int = 1):
    workflow = create_calendar_workflow(client_id)
    result = workflow.invoke({{
        "client_id": client_id,
        "month_offset": month_offset
    }})
    return result["calendar_events"]

# Run with: python -c "from calendar_workflow import run_calendar_planning; print(run_calendar_planning())"
"""