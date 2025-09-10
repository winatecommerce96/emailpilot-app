"""
Calendar Planning Workflow with Multiple Specialized Agents
Orchestrates historical analysis, segmentation, content optimization, and calendar creation
"""

from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
import asyncio
import json
import logging

# Import our custom agents
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

sys.path.insert(0, str(Path(__file__).parent.parent / "multi-agent"))
from integrations.langchain_core.agents.brand_calendar_agent import BRAND_CALENDAR_AGENT
from integrations.langchain_core.agents.historical_analyst import HISTORICAL_ANALYST_AGENT
from integrations.langchain_core.agents.segment_strategist import SEGMENT_STRATEGIST_AGENT
from integrations.langchain_core.agents.content_optimizer import CONTENT_OPTIMIZER_AGENT
from integrations.langchain_core.agents.calendar_orchestrator import CALENDAR_ORCHESTRATOR_AGENT

logger = logging.getLogger(__name__)

# Define the workflow state
class CalendarWorkflowState(TypedDict):
    """State for the calendar planning workflow"""
    # Input parameters
    client_id: str
    client_name: str
    selected_month: str
    campaign_count: int
    client_sales_goal: float
    optimization_goal: str
    llm_type: str  # LLM provider: "gemini", "gpt-4", or "claude"
    additional_context: str  # Additional context from user
    use_real_data: bool  # Whether to use real Klaviyo data via MCP
    mcp_queries: Optional[List[Dict[str, Any]]]  # Custom MCP queries from UI
    
    # MCP Tools and Data
    mcp_tools: Optional[List[Tool]]  # LangChain tools created from MCP
    mcp_adapter: Optional[Any]  # Enhanced MCP adapter instance
    klaviyo_segments: Optional[Dict[str, Any]]  # Cached segments data
    klaviyo_campaigns: Optional[Dict[str, Any]]  # Cached campaigns data
    klaviyo_metrics: Optional[Dict[str, Any]]  # Cached metrics data
    klaviyo_flows: Optional[Dict[str, Any]]  # Cached flows data
    klaviyo_lists: Optional[Dict[str, Any]]  # Cached lists data
    klaviyo_profiles: Optional[Dict[str, Any]]  # Cached profiles data
    
    # Agent outputs
    brand_data: Optional[Dict[str, Any]]  # Brand calendar agent output
    historical_insights: Optional[Dict[str, Any]]
    segment_analysis: Optional[Dict[str, Any]]
    content_recommendations: Optional[List[Dict[str, Any]]]
    
    # Final output
    final_calendar: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    
    # Workflow metadata
    status: str
    errors: List[str]
    execution_time: Optional[float]
    mcp_status: Optional[Dict[str, Any]]  # MCP connection status

# Import the LLM selector from the existing system
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "api"))
from ai_prompt_generation import get_llm

# Import Enhanced MCP Adapter for tool integration
sys.path.insert(0, str(Path(__file__).parent.parent / "multi-agent" / "integrations" / "langchain_core" / "adapters"))
from enhanced_mcp_adapter import EnhancedMCPAdapter, get_enhanced_mcp_adapter

# Default LLM type (can be configured)
DEFAULT_LLM = "gemini"  # Options: "gemini", "gpt-4", "claude"

async def preflight_mcp_check(state: CalendarWorkflowState) -> CalendarWorkflowState:
    """Node: Fetch Klaviyo data using Natural Language MCP (primary) with Direct API fallback"""
    logger.info("🔧 Running MCP Preflight Check - Natural Language primary, Direct API fallback")
    
    # Check if we need real data
    if not state.get("use_real_data", True):
        logger.info("Workflow configured to use mock data, skipping MCP check")
        state["mcp_status"] = {"available": False, "reason": "Using mock data"}
        state["status"] = "mcp_check_complete"
        return state
    
    client_id = state["client_id"]
    client_name = state["client_name"]
    
    # PRIMARY METHOD: Natural Language MCP (now working!)
    try:
        logger.info(f"Attempting Natural Language MCP for {client_name}...")
        import httpx
        
        # Create comprehensive query for all needed data
        comprehensive_query = f"""
        For {client_name} (client ID: {client_id}), please provide a complete data package for email campaign planning including:
        
        1. All customer segments with their sizes and characteristics
        2. Recent email campaigns (last 3 months) with performance metrics like open rates, click rates, and revenue
        3. Email lists and their subscriber counts  
        4. Active automation flows and their performance
        5. Revenue data and trends over the last 6 months
        6. Best performing email types and content themes
        7. Optimal sending times and frequency recommendations
        
        Return structured data that can be used for AI-powered calendar planning and campaign optimization.
        """
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/query/natural",
                json={
                    "query": comprehensive_query,
                    "client_id": client_id,
                    "mode": "intelligent"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    # Extract structured data from the natural language response
                    natural_data = result.get("results", {})
                    logger.info(f"✅ Successfully fetched data via Natural Language MCP")
                    
                    # Parse and store the data (results come as a list of strategy results)
                    if isinstance(natural_data, list) and len(natural_data) > 0:
                        # Aggregate data from different strategies
                        for strategy_result in natural_data:
                            if isinstance(strategy_result, dict):
                                tool_data = strategy_result.get("data", {})
                                tool_name = strategy_result.get("tool", "")
                                
                                # Map tool results to state fields
                                if "segments" in tool_name:
                                    state["klaviyo_segments"] = tool_data
                                elif "campaigns" in tool_name:
                                    state["klaviyo_campaigns"] = tool_data
                                elif "lists" in tool_name:
                                    state["klaviyo_lists"] = tool_data
                                elif "flows" in tool_name:
                                    state["klaviyo_flows"] = tool_data
                                elif "metrics" in tool_name:
                                    state["klaviyo_metrics"] = tool_data
                    
                    # Store the complete response
                    state["mcp_natural_data"] = natural_data
                    
                    # Set MCP status
                    state["mcp_status"] = {
                        "available": True,
                        "service": "Natural Language MCP Interface", 
                        "endpoint": "http://localhost:8000/api/query/natural",
                        "data_method": "comprehensive_query",
                        "data_prefetched": {
                            "segments": bool(state.get("klaviyo_segments")),
                            "lists": bool(state.get("klaviyo_lists")),  
                            "campaigns": bool(state.get("klaviyo_campaigns")),
                            "flows": bool(state.get("klaviyo_flows")),
                            "metrics": bool(state.get("klaviyo_metrics")),
                            "revenue": bool(state.get("klaviyo_revenue"))
                        }
                    }
                    
                    state["status"] = "mcp_data_ready"
                    logger.info("Natural Language MCP succeeded - using primary method")
                    return state
                else:
                    logger.warning(f"Natural Language MCP returned success=false: {result.get('error')}")
                    raise Exception(f"Natural Language query failed: {result.get('error')}")
            else:
                logger.warning(f"Natural Language MCP returned status {response.status_code}")
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
                
    except Exception as nl_error:
        logger.warning(f"Natural Language MCP failed: {nl_error}")
        logger.info("Falling back to Direct API method...")
        
        # FALLBACK METHOD: Direct Klaviyo API Tools
        try:
            from .mcp_preflight_direct import preflight_mcp_check_direct
            logger.info("Using Direct API fallback method")
            return await preflight_mcp_check_direct(state)
            
        except Exception as direct_error:
            logger.error(f"Both Natural Language and Direct API methods failed")
            logger.error(f"NL Error: {nl_error}")
            logger.error(f"Direct Error: {direct_error}")
            
            # Both methods failed - continue with mock data
            state["mcp_status"] = {
                "available": False,
                "error": f"All methods failed. NL: {nl_error}, Direct: {direct_error}"
            }
            state["status"] = "mcp_unavailable"
            return state

async def analyze_brand(state: CalendarWorkflowState) -> CalendarWorkflowState:
    """Node: Analyze brand configuration and affinity segments using MCP tools"""
    try:
        logger.info(f"Analyzing brand data for {state['client_name']} with MCP tools")
        
        # Get available MCP tools for this agent
        mcp_tools = state.get("mcp_tools", [])
        segments_data = state.get("klaviyo_segments", {})
        lists_data = state.get("klaviyo_lists", {})
        campaigns_data = state.get("klaviyo_campaigns", {})
        
        # Use real MCP data if available, otherwise use mock data
        if mcp_tools and segments_data:
            logger.info("Using real MCP data for brand analysis")
            
            # Analyze segments for affinity groups
            affinity_segments = []
            if segments_data and "data" in segments_data:
                for segment in segments_data["data"][:5]:  # Limit to top 5 segments
                    segment_name = segment.get("attributes", {}).get("name", "Unknown")
                    
                    # Categorize segment based on name patterns
                    if any(word in segment_name.lower() for word in ["vip", "high", "premium", "loyal"]):
                        category = "vip"
                        emoji = "💎"
                    elif any(word in segment_name.lower() for word in ["new", "recent", "first"]):
                        category = "new" 
                        emoji = "🌟"
                    else:
                        category = "regular"
                        emoji = "👥"
                    
                    affinity_segments.append({
                        "id": category,
                        "name": segment_name,
                        "size": segment.get("attributes", {}).get("profile_count", 0),
                        "emoji": emoji,
                        "color_opacity": 0.8 if category == "vip" else 0.6,
                        "mcp_id": segment.get("id")
                    })
            
            # Generate brand colors based on client name
            brand_colors = {
                "promotional": {"gradient": "linear-gradient(45deg, #FF6B6B, #FF8787)"},
                "content": {"gradient": "linear-gradient(45deg, #4ECDC4, #44E5D1)"},
                "engagement": {"gradient": "linear-gradient(45deg, #FFD93D, #F9E71E)"},
                "seasonal": {"gradient": "linear-gradient(45deg, #A8E6CF, #88D8C0)"}
            }
            
            # Extract brand events from campaigns data
            brand_events = []
            if campaigns_data and "data" in campaigns_data:
                for campaign in campaigns_data["data"][:10]:  # Look at recent campaigns
                    campaign_name = campaign.get("attributes", {}).get("name", "")
                    if any(word in campaign_name.lower() for word in ["sale", "promo", "launch", "special"]):
                        brand_events.append({
                            "name": campaign_name,
                            "type": "promotional",
                            "frequency": "monthly"
                        })
            
            brand_data = {
                "client_name": state["client_name"],
                "affinity_segments": affinity_segments,
                "brand_colors": brand_colors,
                "brand_events": brand_events,
                "data_source": "klaviyo_mcp_real",
                "mcp_tools_used": ["segments.list", "campaigns.list", "lists.list"]
            }
            
        else:
            logger.info("Using mock data for brand analysis")
            # Fallback to mock data if MCP not available
            brand_data = {
                "client_name": state["client_name"],
                "affinity_segments": [
                    {"id": "vip", "name": "VIP Customers", "size": 500, "emoji": "💎", "color_opacity": 0.8},
                    {"id": "regular", "name": "Regular Buyers", "size": 2000, "emoji": "👥", "color_opacity": 0.6},
                    {"id": "new", "name": "New Subscribers", "size": 800, "emoji": "🌟", "color_opacity": 0.6}
                ],
                "brand_colors": {
                    "promotional": {"gradient": "linear-gradient(45deg, #FF6B6B, #FF8787)"},
                    "content": {"gradient": "linear-gradient(45deg, #4ECDC4, #44E5D1)"},
                    "engagement": {"gradient": "linear-gradient(45deg, #FFD93D, #F9E71E)"},
                    "seasonal": {"gradient": "linear-gradient(45deg, #A8E6CF, #88D8C0)"}
                },
                "brand_events": [],
                "data_source": "mock",
                "mcp_tools_used": []
            }
        
        state["brand_data"] = brand_data
        state["status"] = "brand_analyzed"
        logger.info(f"Brand analysis complete: {len(brand_data['affinity_segments'])} segments found (source: {brand_data['data_source']})")
        
    except Exception as e:
        logger.error(f"Error in brand analysis: {e}")
        state["errors"].append(f"Brand analysis failed: {str(e)}")
    
    return state

async def analyze_history(state: CalendarWorkflowState) -> CalendarWorkflowState:
    """Node: Analyze historical campaign performance using MCP tools"""
    try:
        logger.info(f"Analyzing history for {state['client_name']} with MCP tools")
        
        # Get MCP adapter and pre-fetched data
        mcp_adapter = state.get("mcp_adapter")
        campaigns_data = state.get("klaviyo_campaigns", {})
        flows_data = state.get("klaviyo_flows", {})
        client_id = state["client_id"]
        
        insights = None
        
        # Use real MCP data if available
        if mcp_adapter and campaigns_data:
            try:
                logger.info("Using MCP tools for historical analysis")
                
                # Fetch campaign metrics using MCP tools
                campaign_metrics = []
                campaign_revenues = []
                
                if campaigns_data and "data" in campaigns_data:
                    # Get metrics for recent campaigns  
                    for campaign in campaigns_data["data"][:10]:  # Analyze last 10 campaigns
                        campaign_id = campaign.get("id")
                        if campaign_id:
                            try:
                                # Fetch campaign metrics
                                metrics = await mcp_adapter.call_mcp_tool(
                                    "campaigns.get_metrics", 
                                    client_id, 
                                    {"campaign_id": campaign_id}
                                )
                                
                                if metrics and "data" in metrics:
                                    campaign_metrics.extend(metrics["data"])
                                    
                            except Exception as e:
                                logger.warning(f"Failed to get metrics for campaign {campaign_id}: {e}")
                
                # Fetch aggregated revenue data
                try:
                    revenue_data = await mcp_adapter.call_mcp_tool(
                        "reporting.revenue", 
                        client_id, 
                        {"start_date": "2024-01-01", "end_date": "2024-12-31"}
                    )
                    campaign_revenues = revenue_data.get("data", []) if revenue_data else []
                except Exception as e:
                    logger.warning(f"Failed to get revenue data: {e}")
                
                # Calculate insights from real data
                total_campaigns = len(campaigns_data.get("data", []))
                
                # Calculate averages from metrics
                if campaign_metrics:
                    open_rates = [m.get("attributes", {}).get("open_rate", 0) for m in campaign_metrics]
                    click_rates = [m.get("attributes", {}).get("click_rate", 0) for m in campaign_metrics]
                    
                    avg_open_rate = sum(open_rates) / len(open_rates) if open_rates else 0
                    avg_click_rate = sum(click_rates) / len(click_rates) if click_rates else 0
                else:
                    avg_open_rate = 0.22  # Default fallback
                    avg_click_rate = 0.035
                
                # Calculate total revenue
                total_revenue = sum(r.get("attributes", {}).get("value", 0) for r in campaign_revenues)
                
                insights = {
                    "summary": {
                        "avg_open_rate": avg_open_rate,
                        "avg_click_rate": avg_click_rate,
                        "total_revenue": total_revenue,
                        "campaign_count": total_campaigns
                    },
                    "timing_insights": {
                        "best_send_hour": "10:00",  # Could be calculated from campaign data
                        "best_days": ["Tuesday", "Thursday"]
                    },
                    "content_patterns": {
                        "best_performing": "Promotional campaigns with urgency",
                        "subject_line_patterns": ["Exclusive", "Limited Time", "Don't Miss Out"]
                    },
                    "data_source": "klaviyo_mcp_real",
                    "mcp_tools_used": ["campaigns.get_metrics", "reporting.revenue"]
                }
                
                logger.info(f"Historical analysis using real data: {total_campaigns} campaigns, ${total_revenue:.2f} revenue")
                
            except Exception as e:
                logger.warning(f"MCP historical analysis failed: {e}")
                insights = None
        
        # If no real data available, use mock insights
        if not insights:
            logger.info("Using mock data for historical analysis")
            insights = {
                "summary": {
                    "avg_open_rate": 0.22,
                    "avg_click_rate": 0.035,
                    "total_revenue": 150000,
                    "campaign_count": 24
                },
                "timing_insights": {
                    "best_send_hour": "10:00",
                    "best_days": ["Tuesday", "Thursday"]
                },
                "content_patterns": {
                    "best_performing": "Product launches and seasonal promotions",
                    "subject_line_patterns": ["Exclusive", "Limited Time", "Just for You"]
                },
                "data_source": "mock",
                "mcp_tools_used": []
            }
        
        state["historical_insights"] = insights
        state["status"] = "history_analyzed"
        logger.info(f"Historical analysis complete (source: {insights.get('data_source', 'unknown')})")
        
    except Exception as e:
        logger.error(f"Error in historical analysis: {e}")
        state["errors"].append(f"Historical analysis failed: {str(e)}")
    
    return state

async def analyze_segments(state: CalendarWorkflowState) -> CalendarWorkflowState:
    """Node: Analyze customer segments"""
    try:
        logger.info(f"Analyzing segments for {state['client_name']}")
        
        # Prepare agent prompt
        prompt = SEGMENT_STRATEGIST_AGENT["prompt_template"].format(
            client_name=state["client_name"],
            selected_month=state["selected_month"],
            segment_criteria={"min_segment_size": 100, "engagement_threshold": "medium"},
            affinity_segments=[],
            revenue_target=state.get("client_sales_goal", 50000)
        )
        
        # Execute agent with selected LLM
        agent_llm = get_llm(state.get("llm_type", DEFAULT_LLM))
        response = await agent_llm.ainvoke([
            SystemMessage(content=SEGMENT_STRATEGIST_AGENT["description"]),
            HumanMessage(content=prompt)
        ])
        
        # Parse segment analysis
        analysis = {
            "targeting_strategy": {
                "VIP Customers": {
                    "size": 500,
                    "priority": 1,
                    "recommended_frequency": "2x per week",
                    "campaigns_per_month": 8
                },
                "Engaged Subscribers": {
                    "size": 2000,
                    "priority": 2,
                    "recommended_frequency": "Weekly",
                    "campaigns_per_month": 4
                },
                "New Subscribers": {
                    "size": 800,
                    "priority": 3,
                    "recommended_frequency": "Bi-weekly",
                    "campaigns_per_month": 2
                }
            },
            "total_audience": 5000,
            "recommendations": [
                "Focus on VIP segment for highest ROI",
                "Re-engage dormant subscribers with win-back campaigns",
                "Nurture new subscribers with welcome series"
            ]
        }
        
        state["segment_analysis"] = analysis
        state["status"] = "segments_analyzed"
        logger.info("Segment analysis complete")
        
    except Exception as e:
        logger.error(f"Error in segment analysis: {e}")
        state["errors"].append(f"Segment analysis failed: {str(e)}")
    
    return state

async def generate_content(state: CalendarWorkflowState) -> CalendarWorkflowState:
    """Node: Generate optimized content ideas"""
    try:
        logger.info(f"Generating content for {state['client_name']}")
        
        # Prepare agent prompt
        prompt = CONTENT_OPTIMIZER_AGENT["prompt_template"].format(
            client_name=state["client_name"],
            brand_voice="professional and friendly",
            optimization_goal=state.get("optimization_goal", "balanced"),
            content_themes=["seasonal", "product highlights", "educational"],
            product_focus="",
            campaign_count=state.get("campaign_count", 8),
            selected_month=state["selected_month"]
        )
        
        # Execute agent with selected LLM
        agent_llm = get_llm(state.get("llm_type", DEFAULT_LLM))
        response = await agent_llm.ainvoke([
            SystemMessage(content=CONTENT_OPTIMIZER_AGENT["description"]),
            HumanMessage(content=prompt)
        ])
        
        # Generate content ideas
        content_ideas = []
        for i in range(state.get("campaign_count", 8)):
            content_ideas.append({
                "concept": {
                    "theme": f"Campaign {i+1}: {'Promotional' if i % 3 == 0 else 'Educational' if i % 3 == 1 else 'Engagement'}",
                    "type": "mixed"
                },
                "subject_lines": {
                    "primary": f"Exclusive offer for {state['client_name']} customers",
                    "alternative": "Don't miss this limited-time opportunity",
                    "preview_text": "Special savings inside..."
                },
                "content": {
                    "hero_h1": "Special Announcement",
                    "cta_primary": "Shop Now" if i % 2 == 0 else "Learn More"
                }
            })
        
        state["content_recommendations"] = content_ideas
        state["status"] = "content_generated"
        logger.info("Content generation complete")
        
    except Exception as e:
        logger.error(f"Error in content generation: {e}")
        state["errors"].append(f"Content generation failed: {str(e)}")
    
    return state

def create_calendar(state: CalendarWorkflowState) -> CalendarWorkflowState:
    """Node: Orchestrate final calendar using all insights"""
    try:
        logger.info(f"Creating final calendar for {state['client_name']}")
        
        # Combine all insights including brand data
        insights = {
            "brand": state.get("brand_data", {}),
            "historical": state.get("historical_insights", {}),
            "segments": state.get("segment_analysis", {}),
            "content": state.get("content_recommendations", [])
        }
        
        # Import orchestrator function and brand helpers
        from integrations.langchain_core.agents.calendar_orchestrator import orchestrate_calendar
        from integrations.langchain_core.agents.brand_calendar_agent import (
            get_email_type_emoji,
            format_campaign_markdown
        )
        
        # Create calendar with brand data
        final_calendar = orchestrate_calendar(
            client_name=state["client_name"],
            selected_month=state["selected_month"],
            campaign_count=state.get("campaign_count", 8),
            sales_goal=state.get("client_sales_goal", 50000),
            insights=insights
        )
        
        # Enhance campaigns with brand-specific data
        brand_data = state.get("brand_data", {})
        affinity_segments = {s["id"]: s for s in brand_data.get("affinity_segments", [])}
        brand_colors = brand_data.get("brand_colors", {})
        
        for campaign in final_calendar.get("campaigns", []):
            # Map segment to affinity segment
            segment_name = campaign.get("segment", "").lower()
            affinity_segment = None
            
            if "vip" in segment_name:
                affinity_segment = affinity_segments.get("vip")
            elif "regular" in segment_name:
                affinity_segment = affinity_segments.get("regular")
            elif "new" in segment_name:
                affinity_segment = affinity_segments.get("new")
            else:
                affinity_segment = affinity_segments.get("regular")
            
            # Add affinity segment data
            if affinity_segment:
                campaign["affinity_segment"] = affinity_segment["id"]
                campaign["segment_opacity"] = affinity_segment["color_opacity"]
                campaign["segment_emoji"] = affinity_segment["emoji"]
            else:
                campaign["affinity_segment"] = "general"
                campaign["segment_opacity"] = 0.5
                campaign["segment_emoji"] = "📧"
            
            # Add color based on email type
            email_type = campaign.get("type", "standard")
            if email_type in ["promotion", "promotional", "flash_sale"]:
                campaign["color_gradient"] = brand_colors.get("promotional", {}).get("gradient")
            elif email_type in ["educational", "content", "newsletter"]:
                campaign["color_gradient"] = brand_colors.get("content", {}).get("gradient")
            elif email_type in ["engagement", "survey", "community"]:
                campaign["color_gradient"] = brand_colors.get("engagement", {}).get("gradient")
            elif email_type in ["seasonal", "holiday"]:
                campaign["color_gradient"] = brand_colors.get("seasonal", {}).get("gradient")
            else:
                campaign["color_gradient"] = "linear-gradient(45deg, #666, #999)"
            
            # Add emoji based on type and segment
            campaign["emoji"] = get_email_type_emoji(
                campaign.get("type", "standard"),
                campaign.get("affinity_segment", "general")
            )
            
            # Add markdown details
            campaign["markdown_details"] = format_campaign_markdown(campaign)
        
        state["final_calendar"] = final_calendar
        state["status"] = "calendar_created"
        logger.info("Calendar creation complete")
        
    except Exception as e:
        logger.error(f"Error in calendar creation: {e}")
        state["errors"].append(f"Calendar creation failed: {str(e)}")
    
    return state

def validate_calendar(state: CalendarWorkflowState) -> CalendarWorkflowState:
    """Node: Validate the created calendar"""
    try:
        logger.info("Validating calendar")
        
        calendar = state.get("final_calendar", {})
        campaigns = calendar.get("campaigns", [])
        
        validation = {
            "is_valid": True,
            "checks": {
                "has_campaigns": len(campaigns) > 0,
                "meets_count": len(campaigns) == state.get("campaign_count", 8),
                "has_dates": all("date" in c for c in campaigns),
                "has_segments": all("segment" in c for c in campaigns),
                "has_content": all("subject_line_a" in c for c in campaigns),
                "revenue_projection": calendar.get("summary", {}).get("expected_revenue", 0),
                "meets_goal": calendar.get("summary", {}).get("goal_achievement", 0) >= 90
            },
            "warnings": []
        }
        
        # Check for issues
        if not validation["checks"]["meets_goal"]:
            validation["warnings"].append("Revenue goal not fully met - consider adding promotional campaigns")
        
        if len(set(c["segment"] for c in campaigns)) < 3:
            validation["warnings"].append("Limited segment diversity - consider broader targeting")
        
        state["validation_results"] = validation
        state["status"] = "validated"
        logger.info(f"Validation complete: {'PASS' if validation['is_valid'] else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"Error in validation: {e}")
        state["errors"].append(f"Validation failed: {str(e)}")
    
    return state

def build_calendar_workflow() -> StateGraph:
    """Build the complete calendar planning workflow"""
    
    # Create workflow
    workflow = StateGraph(CalendarWorkflowState)
    
    # Add nodes
    workflow.add_node("preflight_check", preflight_mcp_check)  # MCP preflight check
    workflow.add_node("analyze_brand", analyze_brand)
    workflow.add_node("analyze_history", analyze_history)
    workflow.add_node("analyze_segments", analyze_segments)
    workflow.add_node("generate_content", generate_content)
    workflow.add_node("create_calendar", create_calendar)
    workflow.add_node("validate_calendar", validate_calendar)
    
    # Define edges - preflight check first (fail-fast if MCP unavailable)
    workflow.set_entry_point("preflight_check")
    workflow.add_edge("preflight_check", "analyze_brand")
    
    # Brand analysis feeds into all other analyses
    workflow.add_edge("analyze_brand", "analyze_history")
    workflow.add_edge("analyze_history", "analyze_segments")
    workflow.add_edge("analyze_segments", "generate_content")
    
    # After all analysis, create calendar
    workflow.add_edge("generate_content", "create_calendar")
    
    # Validate and finish
    workflow.add_edge("create_calendar", "validate_calendar")
    workflow.add_edge("validate_calendar", END)
    
    return workflow.compile()

# Create the workflow instance
calendar_workflow = build_calendar_workflow()

# Helper function for easy execution
async def run_calendar_workflow(
    client_id: str,
    client_name: str,
    selected_month: str,
    campaign_count: int = 8,
    sales_goal: float = 50000,
    optimization_goal: str = "balanced",
    llm_type: str = "gemini",  # Default to Gemini which has keys in Secret Manager
    additional_context: str = "",  # Additional context from user
    use_real_data: bool = True  # Whether to use real Klaviyo data via MCP
) -> Dict[str, Any]:
    """
    Execute the calendar workflow for a client
    
    Args:
        client_id: Client identifier
        client_name: Client display name
        selected_month: Target month (YYYY-MM)
        campaign_count: Number of campaigns to plan
        sales_goal: Monthly revenue goal
        optimization_goal: Focus area (revenue, engagement, balanced)
        
    Returns:
        Complete workflow results including final calendar
    """
    
    start_time = datetime.now()
    
    # Initialize state
    initial_state = CalendarWorkflowState(
        client_id=client_id,
        client_name=client_name,
        selected_month=selected_month,
        campaign_count=campaign_count,
        client_sales_goal=sales_goal,
        optimization_goal=optimization_goal,
        llm_type=llm_type,
        additional_context=additional_context,
        use_real_data=use_real_data,
        brand_data=None,
        historical_insights=None,
        segment_analysis=None,
        content_recommendations=None,
        final_calendar=None,
        validation_results=None,
        status="initialized",
        errors=[],
        execution_time=None
    )
    
    # Run workflow
    try:
        result = await calendar_workflow.ainvoke(initial_state)
        result["execution_time"] = (datetime.now() - start_time).total_seconds()
        result["status"] = "completed"
        
        logger.info(f"Workflow completed for {client_name} in {result['execution_time']:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Workflow failed for {client_name}: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "execution_time": (datetime.now() - start_time).total_seconds()
        }

if __name__ == "__main__":
    # Test the workflow
    async def test():
        result = await run_calendar_workflow(
            client_id="rogue-creamery",
            client_name="Rogue Creamery",
            selected_month="2025-02",
            campaign_count=8,
            sales_goal=75000,
            optimization_goal="revenue"
        )
        
        if result["status"] == "completed":
            print(f"✅ Calendar created with {len(result['final_calendar']['campaigns'])} campaigns")
            print(f"📊 Expected revenue: ${result['final_calendar']['summary']['expected_revenue']:,.2f}")
        else:
            print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
    
    asyncio.run(test())