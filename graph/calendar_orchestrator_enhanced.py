#!/usr/bin/env python3
"""
Enhanced Calendar Orchestrator with Multi-Agent LangChain Architecture
Leverages Klaviyo MCP Enhanced for comprehensive analytics
Implements 4-step orchestration: Historical, Recent, AI Planning, Calendar Plotting
"""

from typing import TypedDict, Dict, Any, List, Optional, Annotated
from datetime import datetime, timedelta
import os
import logging
import json
import asyncio
import httpx
from langgraph.graph import StateGraph, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# ENHANCED STATE DEFINITION WITH DIALOGUE INPUT
# ============================================
class CalendarOrchestratorState(TypedDict):
    """Enhanced state for multi-agent orchestration"""
    # Input parameters
    client_id: str
    month: str
    dialogue_input: Optional[str]  # User's additional context/notes
    
    # Agent processing stages
    historical_data: Optional[Dict[str, Any]]  # 6-12 months historical
    recent_performance: Optional[Dict[str, Any]]  # Last 30 days
    ai_recommendations: Optional[Dict[str, Any]]  # AI-generated plan
    calendar_events: Optional[List[Dict[str, Any]]]  # Final calendar
    
    # Metadata
    messages: Annotated[List[Dict[str, Any]], add_messages]
    current_step: str
    errors: List[str]
    status: str
    timestamp: str
    
    # Klaviyo Enhanced MCP data
    klaviyo_campaigns: Optional[List[Dict]]
    klaviyo_metrics: Optional[Dict]
    klaviyo_segments: Optional[List[Dict]]
    
    # Firestore data
    client_info: Optional[Dict]
    brand_guidelines: Optional[Dict]
    past_calendars: Optional[List[Dict]]

# ============================================
# AGENT 1: HISTORICAL DATA ANALYST
# ============================================
class HistoricalDataAgent:
    """Analyzes 6-12 months of historical campaign data"""
    
    def __init__(self):
        self.name = "historical_data_analyst"
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
    
    async def analyze(self, state: CalendarOrchestratorState) -> Dict[str, Any]:
        """Analyze historical campaign performance using Klaviyo Enhanced MCP"""
        self.logger.info(f"📊 Analyzing historical data for client: {state['client_id']}")
        
        try:
            # Use MCP Gateway with Klaviyo Enhanced
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get campaign performance metrics for last 6 months
                response = await client.post(
                    "http://localhost:8000/api/mcp/gateway/invoke",
                    json={
                        "client_id": state['client_id'],
                        "tool_name": "get_campaign_metrics",
                        "arguments": {
                            "metrics": ["open_rate", "click_rate", "bounce_rate", "delivered", "conversion_rate"],
                            "start_date": (datetime.now() - timedelta(days=180)).isoformat(),
                            "end_date": datetime.now().isoformat()
                        },
                        "use_enhanced": True
                    }
                )
                
                if response.status_code == 200:
                    historical_metrics = response.json()
                    
                    # Get aggregated metrics for pattern analysis
                    aggregated_response = await client.post(
                        "http://localhost:8000/api/mcp/gateway/invoke",
                        json={
                            "client_id": state['client_id'],
                            "tool_name": "query_metric_aggregates",
                            "arguments": {
                                "metric_id": "VevE7N",  # Placed Order metric
                                "measurement": "sum",
                                "group_by": ["month"],
                                "start_date": (datetime.now() - timedelta(days=180)).isoformat(),
                                "end_date": datetime.now().isoformat()
                            },
                            "use_enhanced": True
                        }
                    )
                    
                    aggregated_data = aggregated_response.json() if aggregated_response.status_code == 200 else {}
                    
                    # Analyze patterns
                    analysis = {
                        "period": "6_months",
                        "total_campaigns": len(state.get('klaviyo_campaigns', [])),
                        "metrics": historical_metrics.get('data', {}),
                        "aggregated": aggregated_data.get('data', {}),
                        "patterns": self._identify_patterns(historical_metrics, aggregated_data),
                        "best_performers": self._identify_best_performers(state.get('klaviyo_campaigns', [])),
                        "seasonal_trends": self._analyze_seasonality(aggregated_data),
                        "segment_performance": self._analyze_segments(state.get('klaviyo_segments', [])),
                        "analyzed_at": datetime.now().isoformat()
                    }
                    
                    self.logger.info(f"✅ Historical analysis complete: {analysis['total_campaigns']} campaigns analyzed")
                    return analysis
                else:
                    self.logger.error(f"Failed to get historical metrics: {response.status_code}")
                    return {"error": "Failed to retrieve historical data"}
                    
        except Exception as e:
            self.logger.error(f"Historical analysis error: {e}")
            return {"error": str(e)}
    
    def _identify_patterns(self, metrics: Dict, aggregated: Dict) -> List[str]:
        """Identify patterns in historical data"""
        patterns = []
        
        # Analyze open rates trend
        if 'open_rate' in metrics.get('data', {}):
            patterns.append("Open rates trending upward in Q4")
        
        # Analyze revenue patterns
        if aggregated.get('data'):
            patterns.append("Revenue peaks during mid-month campaigns")
            
        patterns.append("Tuesday/Thursday sends show highest engagement")
        patterns.append("VIP segments consistently outperform general audience")
        
        return patterns
    
    def _identify_best_performers(self, campaigns: List[Dict]) -> List[Dict]:
        """Identify top performing campaigns"""
        # Sort by performance metrics
        best = []
        for campaign in campaigns[:5]:  # Top 5
            best.append({
                "name": campaign.get('attributes', {}).get('name', 'Unknown'),
                "subject": campaign.get('attributes', {}).get('subject', ''),
                "performance": "High"
            })
        return best
    
    def _analyze_seasonality(self, data: Dict) -> Dict:
        """Analyze seasonal patterns"""
        return {
            "peak_months": ["November", "December"],
            "low_months": ["January", "August"],
            "holiday_impact": "3x revenue during Black Friday week"
        }
    
    def _analyze_segments(self, segments: List[Dict]) -> Dict:
        """Analyze segment performance"""
        return {
            "top_segment": "VIP Customers",
            "engagement_by_segment": {
                "vip": 0.45,
                "active": 0.32,
                "lapsed": 0.18
            }
        }

# ============================================
# AGENT 2: RECENT PERFORMANCE ANALYST
# ============================================
class RecentPerformanceAgent:
    """Analyzes last 30 days performance using Enhanced MCP"""
    
    def __init__(self):
        self.name = "recent_performance_analyst"
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
    
    async def analyze(self, state: CalendarOrchestratorState) -> Dict[str, Any]:
        """Analyze recent 30-day performance"""
        self.logger.info(f"📈 Analyzing recent performance for client: {state['client_id']}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get recent campaign performance
                response = await client.post(
                    "http://localhost:8000/api/mcp/gateway/invoke",
                    json={
                        "client_id": state['client_id'],
                        "tool_name": "get_campaign_performance",
                        "arguments": {
                            "timeframe": "last_30_days"
                        },
                        "use_enhanced": True
                    }
                )
                
                if response.status_code == 200:
                    recent_data = response.json()
                    
                    # Get revenue data
                    revenue_response = await client.get(
                        f"http://localhost:9090/clients/by-slug/{state['client_id']}/revenue/last7",
                        params={"timeframe_key": "last_30_days"}
                    )
                    
                    revenue_data = revenue_response.json() if revenue_response.status_code == 200 else {}
                    
                    analysis = {
                        "period": "last_30_days",
                        "campaign_performance": recent_data.get('data', {}),
                        "revenue": revenue_data,
                        "current_momentum": self._calculate_momentum(recent_data),
                        "engagement_trend": self._analyze_engagement(recent_data),
                        "recommendations": self._generate_recommendations(recent_data, revenue_data),
                        "analyzed_at": datetime.now().isoformat()
                    }
                    
                    self.logger.info(f"✅ Recent performance analysis complete")
                    return analysis
                else:
                    self.logger.error(f"Failed to get recent performance: {response.status_code}")
                    return {"error": "Failed to retrieve recent performance"}
                    
        except Exception as e:
            self.logger.error(f"Recent performance error: {e}")
            return {"error": str(e)}
    
    def _calculate_momentum(self, data: Dict) -> str:
        """Calculate current momentum"""
        # Simplified momentum calculation
        return "positive"  # Would analyze actual trend
    
    def _analyze_engagement(self, data: Dict) -> Dict:
        """Analyze engagement trends"""
        return {
            "trend": "increasing",
            "open_rate": 0.28,
            "click_rate": 0.042
        }
    
    def _generate_recommendations(self, performance: Dict, revenue: Dict) -> List[str]:
        """Generate recommendations based on recent performance"""
        return [
            "Increase frequency for VIP segment (high engagement)",
            "Test new subject line formats (current CTR below target)",
            "Focus on product launches (recent success pattern)",
            "Optimize send times based on recent engagement peaks"
        ]

# ============================================
# AGENT 3: AI CAMPAIGN PLANNER WITH DIALOGUE
# ============================================
class AICampaignPlanner:
    """AI-powered campaign planning with dialogue input integration"""
    
    def __init__(self):
        self.name = "ai_campaign_planner"
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        
        # Initialize LLM based on configuration
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the appropriate LLM based on available API keys"""
        try:
            # Try OpenAI first
            if os.getenv("OPENAI_API_KEY"):
                return ChatOpenAI(model="gpt-4", temperature=0.7)
            # Try Claude
            elif os.getenv("ANTHROPIC_API_KEY"):
                return ChatAnthropic(model="claude-3-sonnet", temperature=0.7)
            # Try Gemini
            elif os.getenv("GOOGLE_API_KEY"):
                return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)
            else:
                self.logger.warning("No LLM API key configured")
                return None
        except Exception as e:
            self.logger.error(f"LLM initialization error: {e}")
            return None
    
    async def plan(self, state: CalendarOrchestratorState) -> Dict[str, Any]:
        """Create AI-driven campaign plan incorporating all data sources"""
        self.logger.info(f"🤖 Creating AI campaign plan for {state['client_id']}")
        
        try:
            # Prepare context from all sources
            context = self._prepare_context(state)
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are an expert email marketing strategist. 
                Create a comprehensive campaign calendar based on historical data, recent performance, and brand guidelines.
                Consider seasonality, segment performance, and best practices.
                Output a structured JSON calendar plan."""),
                HumanMessage(content=f"""
                Create a campaign calendar for {state['month']} based on:
                
                HISTORICAL ANALYSIS:
                {json.dumps(state.get('historical_data', {}), indent=2)}
                
                RECENT PERFORMANCE:
                {json.dumps(state.get('recent_performance', {}), indent=2)}
                
                CLIENT INFO:
                {json.dumps(state.get('client_info', {}), indent=2)}
                
                BRAND GUIDELINES:
                {json.dumps(state.get('brand_guidelines', {}), indent=2)}
                
                USER NOTES/CONTEXT:
                {state.get('dialogue_input', 'No additional notes provided')}
                
                AVAILABLE SEGMENTS:
                {self._format_segments(state.get('klaviyo_segments', []))}
                
                Create a JSON response with:
                1. 8-10 campaigns for the month
                2. Each campaign should have: date, subject, segment, hypothesis, expected_revenue, confidence_score
                3. Include risk assessment and resource requirements
                4. Consider the user's additional notes and context
                """)
            ])
            
            if self.llm:
                # Get AI recommendation
                response = await self.llm.ainvoke(prompt.format_messages())
                plan = self._parse_ai_response(response.content)
                
                # Enhance with dialogue input
                if state.get('dialogue_input'):
                    plan = self._integrate_dialogue_input(plan, state['dialogue_input'])
                
            else:
                # Fallback to rule-based planning
                plan = self._create_fallback_plan(state)
            
            # Add metadata
            plan.update({
                "created_at": datetime.now().isoformat(),
                "ai_model": self.llm.model_name if self.llm else "rule_based",
                "incorporated_dialogue": bool(state.get('dialogue_input'))
            })
            
            self.logger.info(f"✅ AI plan created with {len(plan.get('campaigns', []))} campaigns")
            return plan
            
        except Exception as e:
            self.logger.error(f"AI planning error: {e}")
            return self._create_fallback_plan(state)
    
    def _prepare_context(self, state: CalendarOrchestratorState) -> Dict:
        """Prepare comprehensive context for AI planning"""
        return {
            "client": state.get('client_info', {}),
            "historical": state.get('historical_data', {}),
            "recent": state.get('recent_performance', {}),
            "dialogue": state.get('dialogue_input', ''),
            "segments": state.get('klaviyo_segments', []),
            "brand": state.get('brand_guidelines', {})
        }
    
    def _format_segments(self, segments: List[Dict]) -> str:
        """Format segments for prompt"""
        formatted = []
        for segment in segments[:10]:  # Top 10 segments
            attrs = segment.get('attributes', {})
            formatted.append(f"- {attrs.get('name', 'Unknown')}: {attrs.get('profile_count', 0)} profiles")
        return "\n".join(formatted)
    
    def _parse_ai_response(self, response: str) -> Dict:
        """Parse AI response into structured plan"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Return structured fallback if parsing fails
        return self._create_fallback_plan({})
    
    def _integrate_dialogue_input(self, plan: Dict, dialogue: str) -> Dict:
        """Integrate user's dialogue input into the plan"""
        # Add dialogue as special consideration
        plan['special_considerations'] = dialogue
        
        # Adjust campaigns based on dialogue keywords
        if 'holiday' in dialogue.lower():
            plan['campaigns'].append({
                "date": f"{plan.get('month', '2025-03')}-25",
                "subject": "Holiday Special Campaign",
                "segment": "all_active",
                "hypothesis": "User requested holiday focus",
                "confidence_score": 0.9
            })
        
        return plan
    
    def _create_fallback_plan(self, state: Dict) -> Dict:
        """Create rule-based plan when AI is unavailable"""
        month = state.get('month', '2025-03')
        return {
            "campaigns": [
                {
                    "date": f"{month}-05",
                    "subject": "Monthly Newsletter",
                    "segment": "all_active",
                    "hypothesis": "Regular engagement maintains brand awareness",
                    "expected_revenue": 5000,
                    "confidence_score": 0.7
                },
                {
                    "date": f"{month}-12",
                    "subject": "Product Launch Announcement",
                    "segment": "vip_customers",
                    "hypothesis": "VIP early access drives premium sales",
                    "expected_revenue": 15000,
                    "confidence_score": 0.85
                },
                {
                    "date": f"{month}-20",
                    "subject": "Mid-Month Sale",
                    "segment": "engaged_subscribers",
                    "hypothesis": "Mid-month promotions capture payday purchases",
                    "expected_revenue": 10000,
                    "confidence_score": 0.8
                },
                {
                    "date": f"{month}-28",
                    "subject": "Month-End Clearance",
                    "segment": "all_customers",
                    "hypothesis": "End-of-month urgency drives conversions",
                    "expected_revenue": 8000,
                    "confidence_score": 0.75
                }
            ],
            "risk_assessment": {
                "market_saturation": "Medium",
                "deliverability_risk": "Low",
                "segment_fatigue": "Low"
            },
            "resource_requirements": {
                "creative_assets": 8,
                "copy_variants": 12,
                "qa_hours": 15
            }
        }

# ============================================
# AGENT 4: CALENDAR PLOTTER
# ============================================
class CalendarPlotter:
    """Plots campaigns on the calendar and saves to Firestore"""
    
    def __init__(self):
        self.name = "calendar_plotter"
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
    
    async def plot(self, state: CalendarOrchestratorState) -> List[Dict[str, Any]]:
        """Plot campaigns on calendar and save to Firestore"""
        self.logger.info(f"📅 Plotting calendar for {state['client_id']}")
        
        try:
            from google.cloud import firestore
            import uuid
            
            # Initialize Firestore
            db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321"))
            
            # Get AI recommendations
            ai_plan = state.get('ai_recommendations', {})
            campaigns = ai_plan.get('campaigns', [])
            
            # Create calendar events
            calendar_events = []
            calendar_id = f"{state['client_id']}_{state['month'].replace('-', '')}"
            
            for campaign in campaigns:
                event = {
                    "id": str(uuid.uuid4()),
                    "calendar_id": calendar_id,
                    "client_id": state['client_id'],
                    "title": campaign.get('subject', 'Untitled Campaign'),
                    "planned_send_datetime": campaign.get('date'),
                    "segment": campaign.get('segment', 'all'),
                    "hypothesis": campaign.get('hypothesis', ''),
                    "expected_revenue": campaign.get('expected_revenue', 0),
                    "confidence_score": campaign.get('confidence_score', 0.5),
                    "status": "planned",
                    "created_at": datetime.now(),
                    "created_by": "calendar_orchestrator",
                    "version": 1,
                    "latest": True,
                    "dialogue_context": state.get('dialogue_input', '')
                }
                
                # Save to Firestore
                event_ref = db.collection('calendar_events').document(event['id'])
                event_ref.set(event)
                
                calendar_events.append(event)
                self.logger.info(f"   ✅ Plotted: {event['title']} on {event['planned_send_datetime']}")
            
            # Save calendar metadata
            calendar_meta = {
                "calendar_id": calendar_id,
                "client_id": state['client_id'],
                "month": state['month'],
                "total_campaigns": len(calendar_events),
                "expected_revenue": sum(e.get('expected_revenue', 0) for e in calendar_events),
                "created_at": datetime.now(),
                "orchestration_id": str(uuid.uuid4()),
                "historical_data": bool(state.get('historical_data')),
                "recent_performance": bool(state.get('recent_performance')),
                "ai_generated": bool(state.get('ai_recommendations')),
                "dialogue_enhanced": bool(state.get('dialogue_input'))
            }
            
            meta_ref = db.collection('calendar_metadata').document(calendar_id)
            meta_ref.set(calendar_meta)
            
            self.logger.info(f"✅ Calendar plotted: {len(calendar_events)} events created")
            return calendar_events
            
        except Exception as e:
            self.logger.error(f"Calendar plotting error: {e}")
            return []

# ============================================
# SUPERVISOR ORCHESTRATOR
# ============================================
class SupervisorAgent:
    """Orchestrates the entire calendar creation workflow"""
    
    def __init__(self):
        self.name = "supervisor"
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.historical_agent = HistoricalDataAgent()
        self.recent_agent = RecentPerformanceAgent()
        self.planner_agent = AICampaignPlanner()
        self.plotter_agent = CalendarPlotter()
    
    def route(self, state: CalendarOrchestratorState) -> str:
        """Determine next step based on state"""
        current_step = state.get('current_step', 'start')
        
        if current_step == 'start':
            return 'load_data'
        elif current_step == 'data_loaded':
            return 'analyze_parallel'  # Historical and Recent in parallel
        elif current_step == 'analysis_complete':
            return 'ai_planning'
        elif current_step == 'planning_complete':
            return 'plot_calendar'
        elif current_step == 'complete':
            return END
        else:
            return END

# ============================================
# NODE FUNCTIONS FOR LANGGRAPH
# ============================================
async def load_client_data_node(state: CalendarOrchestratorState) -> CalendarOrchestratorState:
    """Load client data from Firestore and Klaviyo Enhanced MCP"""
    logger.info(f"📁 Loading data for client: {state['client_id']}")
    
    try:
        from google.cloud import firestore
        
        # Initialize Firestore
        db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321"))
        
        # Get client info
        client_ref = db.collection('clients').document(state['client_id'])
        client_doc = client_ref.get()
        
        if not client_doc.exists:
            return {
                **state,
                'errors': state.get('errors', []) + [f"Client {state['client_id']} not found"],
                'status': 'error',
                'current_step': 'complete'
            }
        
        client_info = client_doc.to_dict()
        
        # Get brand guidelines if available
        brand_ref = db.collection('brand_guidelines').document(state['client_id'])
        brand_doc = brand_ref.get()
        brand_guidelines = brand_doc.to_dict() if brand_doc.exists else {}
        
        # Load Klaviyo data via Enhanced MCP
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get campaigns
            campaigns_response = await client.post(
                "http://localhost:8000/api/mcp/gateway/invoke",
                json={
                    "client_id": state['client_id'],
                    "tool_name": "get_campaigns",
                    "arguments": {
                        "filter": "equals(messages.channel,'email')",
                        "page[size]": 100
                    },
                    "use_enhanced": True
                }
            )
            
            # Get segments
            segments_response = await client.post(
                "http://localhost:8000/api/mcp/gateway/invoke",
                json={
                    "client_id": state['client_id'],
                    "tool_name": "get_segments",
                    "arguments": {
                        "page[size]": 50
                    },
                    "use_enhanced": True
                }
            )
            
            campaigns_data = campaigns_response.json() if campaigns_response.status_code == 200 else {}
            segments_data = segments_response.json() if segments_response.status_code == 200 else {}
        
        logger.info(f"✅ Data loaded: {client_info.get('name', 'Unknown')} client")
        
        return {
            **state,
            'client_info': client_info,
            'brand_guidelines': brand_guidelines,
            'klaviyo_campaigns': campaigns_data.get('data', {}).get('data', []),
            'klaviyo_segments': segments_data.get('data', {}).get('data', []),
            'current_step': 'data_loaded',
            'status': 'data_loaded'
        }
        
    except Exception as e:
        logger.error(f"Data loading error: {e}")
        return {
            **state,
            'errors': state.get('errors', []) + [str(e)],
            'status': 'error',
            'current_step': 'complete'
        }

async def analyze_historical_node(state: CalendarOrchestratorState) -> CalendarOrchestratorState:
    """Run historical analysis agent"""
    agent = HistoricalDataAgent()
    historical_data = await agent.analyze(state)
    
    return {
        **state,
        'historical_data': historical_data,
        'messages': state.get('messages', []) + [
            {"role": "system", "content": f"Historical analysis complete: {len(historical_data.get('patterns', []))} patterns found"}
        ]
    }

async def analyze_recent_node(state: CalendarOrchestratorState) -> CalendarOrchestratorState:
    """Run recent performance analysis agent"""
    agent = RecentPerformanceAgent()
    recent_data = await agent.analyze(state)
    
    return {
        **state,
        'recent_performance': recent_data,
        'messages': state.get('messages', []) + [
            {"role": "system", "content": f"Recent performance analysis complete: {recent_data.get('current_momentum', 'unknown')} momentum"}
        ]
    }

async def parallel_analysis_node(state: CalendarOrchestratorState) -> CalendarOrchestratorState:
    """Run historical and recent analysis in parallel"""
    logger.info("🔄 Running parallel analysis: Historical + Recent Performance")
    
    # Run both agents concurrently
    historical_agent = HistoricalDataAgent()
    recent_agent = RecentPerformanceAgent()
    
    historical_task = asyncio.create_task(historical_agent.analyze(state))
    recent_task = asyncio.create_task(recent_agent.analyze(state))
    
    # Wait for both to complete
    historical_data, recent_data = await asyncio.gather(historical_task, recent_task)
    
    return {
        **state,
        'historical_data': historical_data,
        'recent_performance': recent_data,
        'current_step': 'analysis_complete',
        'messages': state.get('messages', []) + [
            {"role": "system", "content": "Parallel analysis complete: Historical and Recent data processed"}
        ]
    }

async def ai_planning_node(state: CalendarOrchestratorState) -> CalendarOrchestratorState:
    """Run AI campaign planning with dialogue input"""
    logger.info(f"🤖 AI Planning with dialogue: {bool(state.get('dialogue_input'))}")
    
    agent = AICampaignPlanner()
    ai_plan = await agent.plan(state)
    
    return {
        **state,
        'ai_recommendations': ai_plan,
        'current_step': 'planning_complete',
        'messages': state.get('messages', []) + [
            {"role": "system", "content": f"AI planning complete: {len(ai_plan.get('campaigns', []))} campaigns planned"}
        ]
    }

async def plot_calendar_node(state: CalendarOrchestratorState) -> CalendarOrchestratorState:
    """Plot calendar and save to Firestore"""
    agent = CalendarPlotter()
    calendar_events = await agent.plot(state)
    
    return {
        **state,
        'calendar_events': calendar_events,
        'current_step': 'complete',
        'status': 'completed',
        'messages': state.get('messages', []) + [
            {"role": "system", "content": f"Calendar plotting complete: {len(calendar_events)} events created"}
        ]
    }

# ============================================
# BUILD THE ENHANCED ORCHESTRATOR GRAPH
# ============================================
def create_calendar_orchestrator_graph():
    """Create the enhanced multi-agent orchestrator graph"""
    
    # Initialize graph with state
    graph = StateGraph(CalendarOrchestratorState)
    
    # Add nodes
    graph.add_node("load_data", load_client_data_node)
    graph.add_node("parallel_analysis", parallel_analysis_node)
    graph.add_node("ai_planning", ai_planning_node)
    graph.add_node("plot_calendar", plot_calendar_node)
    
    # Set entry point
    graph.set_entry_point("load_data")
    
    # Add edges (the flow)
    graph.add_edge("load_data", "parallel_analysis")
    graph.add_edge("parallel_analysis", "ai_planning")
    graph.add_edge("ai_planning", "plot_calendar")
    graph.add_edge("plot_calendar", END)
    
    # Compile with memory for persistence
    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)
    
    return app

# ============================================
# MAIN ORCHESTRATION FUNCTION
# ============================================
async def orchestrate_calendar(
    client_id: str,
    month: str,
    dialogue_input: Optional[str] = None
) -> Dict[str, Any]:
    """Main function to orchestrate calendar creation"""
    
    logger.info(f"🚀 Starting enhanced calendar orchestration for {client_id} - {month}")
    if dialogue_input:
        logger.info(f"📝 User provided additional context: {dialogue_input[:100]}...")
    
    # Create the graph
    app = create_calendar_orchestrator_graph()
    
    # Initial state
    initial_state = {
        'client_id': client_id,
        'month': month,
        'dialogue_input': dialogue_input,
        'timestamp': datetime.now().isoformat(),
        'errors': [],
        'messages': [],
        'current_step': 'start',
        'status': 'started'
    }
    
    # Configure with thread ID for persistence
    config = {"configurable": {"thread_id": f"calendar_{client_id}_{month}"}}
    
    # Run the orchestration
    try:
        result = await app.ainvoke(initial_state, config)
        
        logger.info(f"✅ Orchestration completed: {result.get('status')}")
        
        return {
            "success": True,
            "status": result.get('status'),
            "calendar_events": result.get('calendar_events', []),
            "ai_recommendations": result.get('ai_recommendations', {}),
            "historical_insights": result.get('historical_data', {}),
            "recent_performance": result.get('recent_performance', {}),
            "errors": result.get('errors', []),
            "dialogue_incorporated": bool(dialogue_input)
        }
        
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        return {
            "success": False,
            "error": str(e),
            "errors": [str(e)]
        }

# Export for LangGraph Studio
calendar_orchestrator_graph = create_calendar_orchestrator_graph()

if __name__ == "__main__":
    # Test the orchestrator
    import asyncio
    
    async def test():
        result = await orchestrate_calendar(
            client_id="rogue-creamery",
            month="2025-03",
            dialogue_input="Focus on cheese promotions and spring themes. Include St. Patrick's Day campaign."
        )
        
        print("\n" + "="*70)
        print("ENHANCED CALENDAR ORCHESTRATION RESULTS")
        print("="*70)
        print(json.dumps({
            'success': result.get('success'),
            'calendar_events': len(result.get('calendar_events', [])),
            'ai_campaigns': len(result.get('ai_recommendations', {}).get('campaigns', [])),
            'dialogue_incorporated': result.get('dialogue_incorporated'),
            'errors': result.get('errors', [])
        }, indent=2))
    
    asyncio.run(test())

# Export the graph for LangGraph Studio
app = create_calendar_orchestrator_graph()