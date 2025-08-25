"""
Calendar Planning AI API

Integrates MCP Klaviyo data with AI agents to generate calendar plans.
Uses the calendar planning prompts with real-time client data.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from google.cloud import firestore

from app.deps import get_db
from app.services.calendar_planning_prompts import CalendarPlanningPrompts
from app.services.agent_service import AgentService
from app.services.mcp_service import MCPService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/planning/ai", tags=["Calendar Planning AI"])

@router.post("/generate-plan")
async def generate_calendar_plan(
    client_id: str = Body(..., description="Client ID"),
    month: str = Body(..., description="Target month name (e.g., 'September')"),
    year: int = Body(..., description="Target year (e.g., 2025)"),
    use_mcp_data: bool = Body(default=True, description="Whether to use MCP for real data"),
    custom_segments: Optional[list] = Body(default=None, description="Override affinity segments"),
    custom_revenue_goal: Optional[float] = Body(default=None, description="Override revenue goal"),
    custom_key_dates: Optional[list] = Body(default=None, description="Override key dates"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a comprehensive calendar plan using MCP data and AI
    
    This endpoint:
    1. Prepares context from Firestore
    2. Generates appropriate prompt
    3. Queries AI agent with MCP integration
    4. Returns structured calendar plan
    """
    try:
        logger.info(f"Generating calendar plan for client {client_id}, {month} {year}")
        
        # Initialize services
        agent_service = AgentService()
        mcp_service = MCPService(db)
        prompt_generator = CalendarPlanningPrompts()
        
        # Prepare context from Firestore
        context = prompt_generator.prepare_prompt_context(
            db=db,
            client_id=client_id,
            target_month=month,
            target_year=year
        )
        
        # Override with custom values if provided
        if custom_segments:
            context["affinity_segments"] = custom_segments
        if custom_revenue_goal:
            context["revenue_goal"] = custom_revenue_goal
        if custom_key_dates:
            context["key_dates"] = custom_key_dates
        
        # Check MCP connection if using real data
        mcp_available = False
        if use_mcp_data:
            try:
                mcp_status = await mcp_service.check_client_connection(client_id)
                mcp_available = mcp_status.get("connected", False)
                if mcp_available:
                    logger.info(f"MCP connection available for {client_id}")
                else:
                    logger.warning(f"MCP connection not available for {client_id}, will use historical data")
            except Exception as e:
                logger.error(f"MCP connection check failed: {e}")
                mcp_available = False
        
        # Generate the prompt
        planning_prompt = prompt_generator.generate_monthly_planning_prompt(
            client_name=context["client_name"],
            client_id=client_id,
            target_month=month,
            target_year=year,
            affinity_segments=context["affinity_segments"],
            revenue_goal=context["revenue_goal"],
            klaviyo_account_id=context["klaviyo_account_id"],
            mcp_connector_name=context["mcp_connector_name"],
            placed_order_metric_id=context["placed_order_metric_id"],
            utm_sources=context.get("utm_sources"),
            special_products=context.get("special_products"),
            key_dates=context.get("key_dates")
        )
        
        # Call AI agent with MCP context
        agent_request = {
            "prompt": planning_prompt,
            "context": {
                "client_id": client_id,
                "mcp_available": mcp_available,
                "mcp_connector": context["mcp_connector_name"] if mcp_available else None,
                "use_historical_data": not mcp_available,
                "target_period": f"{month} {year}",
                "client_timezone": context.get("primary_timezone", "America/Los_Angeles")
            },
            "model": "claude-3-opus-20240229",  # Use powerful model for planning
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        # Get AI response
        logger.info("Sending request to AI agent...")
        ai_response = await agent_service.generate_calendar_plan(agent_request)
        
        # Validate and parse response
        validation_result = prompt_generator.validate_prompt_response(
            ai_response.get("content", "")
        )
        
        if not validation_result["valid"]:
            logger.error(f"Invalid AI response: {validation_result['errors']}")
            raise HTTPException(
                status_code=500,
                detail=f"AI response validation failed: {', '.join(validation_result['errors'])}"
            )
        
        # Store the plan in Firestore
        plan_id = f"{client_id}_{month.lower()}_{year}_{int(datetime.now().timestamp())}"
        plan_doc = {
            "plan_id": plan_id,
            "client_id": client_id,
            "month": month,
            "year": year,
            "created_at": datetime.now().isoformat(),
            "status": "generated",
            "mcp_used": mcp_available,
            "revenue_goal": context["revenue_goal"],
            "affinity_segments": context["affinity_segments"],
            "ai_response": ai_response.get("content", ""),
            "validation": validation_result,
            "context": context
        }
        
        # Save to Firestore
        db.collection("clients").document(client_id).collection("calendar_plans").document(plan_id).set(plan_doc)
        
        logger.info(f"Calendar plan generated and saved: {plan_id}")
        
        return {
            "success": True,
            "plan_id": plan_id,
            "client_id": client_id,
            "period": f"{month} {year}",
            "mcp_data_used": mcp_available,
            "revenue_goal": context["revenue_goal"],
            "segments": context["affinity_segments"],
            "validation": validation_result,
            "ai_response": ai_response.get("content", ""),
            "warnings": validation_result.get("warnings", []),
            "created_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate calendar plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Calendar plan generation failed: {str(e)}"
        )

@router.get("/quick-analysis")
async def quick_calendar_analysis(
    client_id: str = Query(..., description="Client ID"),
    month: str = Query(..., description="Target month"),
    year: int = Query(..., description="Target year"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a quick analysis for calendar planning
    """
    try:
        # Initialize services
        agent_service = AgentService()
        prompt_generator = CalendarPlanningPrompts()
        
        # Get client info
        client_doc = db.collection("clients").document(client_id).get()
        if not client_doc.exists:
            raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
        
        client_data = client_doc.to_dict()
        client_name = client_data.get("name", client_id)
        
        # Get MCP connector name
        mcp_doc = db.collection("mcp_clients").document(client_id).get()
        mcp_connector = f"{client_name} Klaviyo"
        if mcp_doc.exists:
            mcp_data = mcp_doc.to_dict()
            mcp_connector = mcp_data.get("connector_name", mcp_connector)
        
        # Generate quick analysis prompt
        quick_prompt = prompt_generator.generate_quick_analysis_prompt(
            client_name=client_name,
            mcp_connector_name=mcp_connector,
            target_month=month,
            target_year=year
        )
        
        # Get AI response
        agent_request = {
            "prompt": quick_prompt,
            "context": {
                "client_id": client_id,
                "analysis_type": "quick",
                "target_period": f"{month} {year}"
            },
            "model": "claude-3-sonnet-20240229",  # Use faster model for quick analysis
            "max_tokens": 1000,
            "temperature": 0.5
        }
        
        ai_response = await agent_service.generate_calendar_plan(agent_request)
        
        return {
            "success": True,
            "client_id": client_id,
            "period": f"{month} {year}",
            "analysis": ai_response.get("content", ""),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/saved-plans/{client_id}")
async def get_saved_plans(
    client_id: str,
    month: Optional[str] = Query(default=None, description="Filter by month"),
    year: Optional[int] = Query(default=None, description="Filter by year"),
    limit: int = Query(default=10, ge=1, le=50),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve saved calendar plans for a client
    """
    try:
        query = db.collection("clients").document(client_id).collection("calendar_plans")
        
        if month:
            query = query.where("month", "==", month)
        if year:
            query = query.where("year", "==", year)
        
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        plans = []
        for doc in query.stream():
            plan_data = doc.to_dict()
            # Truncate AI response for list view
            if "ai_response" in plan_data:
                plan_data["ai_response_preview"] = plan_data["ai_response"][:500] + "..."
                del plan_data["ai_response"]
            plans.append(plan_data)
        
        return {
            "success": True,
            "client_id": client_id,
            "plans": plans,
            "count": len(plans),
            "filters": {
                "month": month,
                "year": year,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve saved plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan-details/{plan_id}")
async def get_plan_details(
    plan_id: str,
    client_id: str = Query(..., description="Client ID"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get full details of a saved calendar plan
    """
    try:
        doc = db.collection("clients").document(client_id).collection("calendar_plans").document(plan_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        
        plan_data = doc.to_dict()
        
        # Parse campaign table if present
        if plan_data.get("ai_response"):
            campaigns = _extract_campaigns_from_response(plan_data["ai_response"])
            plan_data["parsed_campaigns"] = campaigns
        
        return {
            "success": True,
            "plan": plan_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plan details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/apply-plan-to-calendar")
async def apply_plan_to_calendar(
    plan_id: str = Body(..., description="Plan ID to apply"),
    client_id: str = Body(..., description="Client ID"),
    auto_create_events: bool = Body(default=False, description="Automatically create calendar events"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Apply a generated plan to the calendar
    """
    try:
        # Get the plan
        plan_doc = db.collection("clients").document(client_id).collection("calendar_plans").document(plan_id).get()
        
        if not plan_doc.exists:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        
        plan_data = plan_doc.to_dict()
        
        # Extract campaigns from AI response
        campaigns = _extract_campaigns_from_response(plan_data.get("ai_response", ""))
        
        if not campaigns:
            raise HTTPException(
                status_code=400,
                detail="No campaigns found in plan to apply"
            )
        
        created_events = []
        
        if auto_create_events:
            # Create calendar events for each campaign
            for campaign in campaigns:
                # Determine type and color
                is_sms = "sms" in (campaign.get("segment", "").lower() or "") or "sms" in (campaign.get("ab_test", "").lower() or "")
                event_type = "sms" if is_sms else "email"
                title = campaign.get("subject", "Campaign")
                title_l = (title or "").lower()
                if "cheese club" in title_l:
                    color = "bg-green-200 text-green-800"
                elif "rrb" in title_l or "red ribbon" in title_l:
                    color = "bg-red-300 text-red-800"
                elif event_type == "sms":
                    color = "bg-orange-300 text-orange-800"
                else:
                    color = "bg-blue-200 text-blue-800"

                # Normalize event payload for calendar API expectations
                event_data_top = {
                    "client_id": client_id,
                    "title": title,
                    "content": f"{campaign.get('hero_h1', '')} - {campaign.get('preview', '')}",
                    "date": campaign.get("date"),
                    "color": color,
                    "event_type": event_type,
                    "segment": campaign.get("segment"),
                    "send_time": campaign.get("time"),
                    "status": "planned",
                    "source_plan_id": plan_id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "campaign_metadata": {
                        "cta": campaign.get("cta"),
                        "offer": campaign.get("offer"),
                        "ab_test": campaign.get("ab_test"),
                        "image_notes": campaign.get("image")
                    },
                    "generated_by_ai": True
                }

                # Create event in top-level calendar_events so current calendar UI can see it
                try:
                    top_ref = db.collection("calendar_events").add(event_data_top)
                    created_events.append(top_ref[1].id)
                except Exception as e:
                    logger.error(f"Failed to create top-level calendar event: {e}")

                # Also store under client subcollection for history/traceability
                try:
                    client_event_payload = {
                        **event_data_top,
                        # Maintain legacy keys for client subcollection
                        "time": campaign.get("time"),
                        "type": event_type,
                    }
                    db.collection("clients").document(client_id).collection("calendar_events").add(client_event_payload)
                except Exception as e:
                    logger.warning(f"Could not write client subcollection event: {e}")
        
        # Update plan status
        plan_doc.reference.update({
            "status": "applied" if auto_create_events else "reviewed",
            "applied_at": datetime.now().isoformat() if auto_create_events else None,
            "events_created": len(created_events)
        })
        
        return {
            "success": True,
            "plan_id": plan_id,
            "campaigns_found": len(campaigns),
            "events_created": len(created_events),
            "event_ids": created_events,
            "status": "applied" if auto_create_events else "reviewed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply plan to calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _extract_campaigns_from_response(response: str) -> list:
    """
    Extract campaign data from AI response
    
    This is a simplified parser - enhance based on actual response format
    """
    campaigns = []
    
    try:
        # Look for markdown table
        if "| Week |" in response or "| Week #|" in response:
            lines = response.split("\n")
            in_table = False
            
            for line in lines:
                if "| Week" in line:
                    in_table = True
                    continue
                if in_table and line.startswith("|") and "---" not in line:
                    # Parse table row
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 13:
                        campaign = {
                            "week": parts[0],
                            "date": parts[1],
                            "time": parts[2],
                            "segment": parts[3],
                            "subject": parts[4],
                            "preview": parts[5],
                            "hero_h1": parts[6],
                            "subhead": parts[7],
                            "image": parts[8],
                            "cta": parts[9],
                            "offer": parts[10],
                            "ab_test": parts[11],
                            "sms": parts[12] if len(parts) > 12 else ""
                        }
                        campaigns.append(campaign)
                elif in_table and not line.startswith("|"):
                    in_table = False
        
        logger.info(f"Extracted {len(campaigns)} campaigns from AI response")
        
    except Exception as e:
        logger.error(f"Error extracting campaigns: {e}")
    
    return campaigns

@router.get("/health")
async def calendar_planning_ai_health() -> Dict[str, Any]:
    """
    Health check for calendar planning AI system
    """
    return {
        "service": "calendar_planning_ai",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "generate_plan",
            "quick_analysis",
            "saved_plans",
            "apply_to_calendar"
        ]
    }
