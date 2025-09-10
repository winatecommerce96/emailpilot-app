"""
AI-Powered Calendar Planning API Router for EmailPilot
Provides intelligent calendar planning with MCP Klaviyo integration and Gemini AI
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
import json
import logging
import os
import re
from google.cloud import firestore
import requests
import httpx
from app.services.gemini_service import GeminiService
from app.services.client_key_resolver import get_client_key_resolver
from app.deps.firestore import get_db
from app.deps.secrets import get_secret_manager_service
from app.services.secrets import SecretManagerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/planning", tags=["Calendar Planning"])

# Initialize Firestore via helper (respects Secret Manager / env)
db = get_db()

# Pydantic models for calendar planning
class CalendarPlanningRequest(BaseModel):
    client_id: str = Field(..., description="Client ID for planning")
    month: int = Field(..., ge=1, le=12, description="Target month (1-12)")
    year: int = Field(..., ge=2024, le=2030, description="Target year")
    additional_context: Optional[str] = Field(None, description="Additional planning context")

class CalendarPlanningResponse(BaseModel):
    success: bool
    events: List[Dict[str, Any]]
    planning_summary: str
    client_context: Dict[str, Any]
    klaviyo_data_summary: Dict[str, Any]

class PromptTemplate(BaseModel):
    template_id: str = "default_calendar_planning"
    name: str = "Default Calendar Planning Template"
    template: str
    variables: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template: Optional[str] = None
    variables: Optional[List[str]] = None

# MCP Klaviyo Integration Service
class MCPKlaviyoService:
    def __init__(self):
        self.db = get_db()

    async def fetch_klaviyo_data(self, client_id: str, month: int, year: int) -> Dict[str, Any]:
        """Fetch comprehensive Klaviyo data for the specified client and time period from Firestore."""
        try:
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, 1) + timedelta(days=32) # A bit more than a month to cover all days

            # Fetch campaign history from client-scoped collection
            campaigns_ref = (
                self.db.collection('clients')
                .document(client_id)
                .collection('klaviyo')
                .document('data')
                .collection('campaigns')
                .where('send_time', '>=', start_date.isoformat())
                .where('send_time', '<', end_date.isoformat())
            )
            campaign_docs = list(campaigns_ref.stream())
            campaign_history = [doc.to_dict() for doc in campaign_docs if doc.exists]

            # Fetch recent performance metrics (MTD summary if available)
            metrics_ref = (
                self.db.collection('clients')
                .document(client_id)
                .collection('klaviyo')
                .document('data')
                .collection('metrics')
                .document('mtd')
            )
            metrics_doc = metrics_ref.get()
            if metrics_doc.exists:
                md = metrics_doc.to_dict()
                recent_performance = {"summary": md.get("summary", {}), "as_of": md.get("as_of")}
            else:
                recent_performance = {"metrics": []}

            # Fetch segments
            # This is a simplified implementation. A real implementation would fetch segments from Klaviyo.
            segments = []

            return {
                "campaign_history": campaign_history,
                "recent_performance": recent_performance,
                "segments": segments,
                "data_fetched_at": datetime.now().isoformat(),
                "target_month": month,
                "target_year": year
            }

        except Exception as e:
            logger.error(f"An unexpected error occurred during MCP Data Service request: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected MCP Data Service error: {e}")

# Client Context Service
async def get_client_context(client_id: str) -> Dict[str, Any]:
    """Fetch comprehensive client context from Firestore"""
    try:
        client_doc = db.collection('clients').document(client_id).get()
        if not client_doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client_data = client_doc.to_dict()
        
        # Fetch client goals
        goals_ref = db.collection('goals').where('client_id', '==', client_id)
        goals_docs = list(goals_ref.stream())
        goals = [doc.to_dict() for doc in goals_docs if doc.exists]
        
        return {
            "client_info": {
                "id": client_id,
                "name": client_data.get('name', 'Unknown'),
                "industry": client_data.get('industry', ''),
                "background": client_data.get('background', ''),
                "voice": client_data.get('voice', ''),
                "key_growth_objective": client_data.get('key_growth_objective', '')
            },
            "affinity_segments": {
                "segment_1": client_data.get('affinity_segment_1', ''),
                "segment_2": client_data.get('affinity_segment_2', ''),
                "segment_3": client_data.get('affinity_segment_3', '')
            },
            "goals": goals,
            "additional_context": {
                "timezone": client_data.get('timezone', 'UTC'),
                "preferred_send_times": client_data.get('preferred_send_times', []),
                "brand_guidelines": client_data.get('brand_guidelines', '')
            }
        }
    except Exception as e:
        logger.error(f"Failed to get client context: {e}")
        return {"error": str(e)}

# Prompt Template Management
async def get_prompt_template(template_id: str = "default_calendar_planning") -> Dict[str, Any]:
    """Get or create the default prompt template"""
    try:
        template_doc = db.collection('prompt_templates').document(template_id).get()
        
        if template_doc.exists:
            return template_doc.to_dict()
        else:
            # Create default template
            default_template = {
                "template_id": template_id,
                "name": "Default Calendar Planning Template",
                "template": """You are an expert email marketing strategist creating a comprehensive calendar plan for {client_name}.

**Client Context:**
- Name: {client_name}
- Industry: {industry}  
- Background: {background}
- Voice: {voice}
- Key Growth Objective: {key_growth_objective}

**Affinity Segments:**
- Segment 1: {affinity_segment_1}
- Segment 2: {affinity_segment_2} 
- Segment 3: {affinity_segment_3}

**Goals for Planning Period:**
{goals_summary}

**Historical Campaign Data (from previous years for the same month):**
{campaign_history_summary}

**Recent Performance (Last 30 days):**
{recent_performance_summary}

**Planning Request:**
- Target Month: {target_month}/{target_year}
- Additional Context: {additional_context}

**Instructions for Calendar Plan Generation:**
Create a strategic and actionable calendar plan with 8-12 distinct marketing events throughout {target_month}/{target_year}. The plan MUST be designed to achieve the client's stated goals, especially the revenue goals outlined in "Goals for Planning Period."

**Event Types to Include:**
1.  **Email Campaigns**: Primary marketing touchpoints (e.g., promotions, newsletters, product launches, educational series).
2.  **SMS Campaigns**: Urgent/time-sensitive messages, transactional alerts, or complementary to email campaigns.
3.  **Flow Optimizations**: Recommendations for improving automated email/SMS flows (e.g., welcome series, abandoned cart, post-purchase).
4.  **Segment Campaigns**: Highly targeted campaigns for each affinity segment, leveraging their specific interests.

**Key Considerations for the AI:**
-   **Goal Alignment:** Directly address and strategize to meet the {goals_summary}. If a revenue goal is present, propose campaigns that drive sales.
-   **Strategic Spacing:** Events should be strategically spaced, avoiding daily sends unless explicitly justified (e.g., flash sale).
-   **Seasonality & Trends:** Incorporate relevant seasonal events, holidays, or industry trends for {target_month}/{target_year}.
-   **Content Variety:** Ensure a mix of promotional, educational, nurturing, and community-building content.
-   **Audience Segmentation:** Propose how different segments will be targeted.
-   **Conversion Focus:** For revenue goals, suggest clear calls to action and conversion-oriented strategies.
-   **Color Coding:** Use appropriate colors for events:
    -   `bg-red-300`: Promotional/Sales (e.g., discounts, flash sales)
    -   `bg-blue-200`: Educational/Nurturing (e.g., blog updates, how-to guides, brand story)
    -   `bg-green-200`: Community/Engagement (e.g., user-generated content, surveys, brand values)
    -   `bg-purple-200`: Product Launch/Announcement
    -   `bg-yellow-200`: Re-engagement/Win-back
    -   `bg-orange-300`: SMS Alerts/Urgent Communications

**Response Format:**
Provide ONLY a valid JSON response. The JSON MUST strictly adhere to the following structure. Do NOT include any additional text or markdown outside the JSON block.

```json
{
  "events": [
    {
      "title": "Concise Campaign Title",
      "date": "YYYY-MM-DD",
      "event_type": "email|sms|flow|segment",
      "color": "bg-color-code",
      "content": "Detailed description of the campaign, its objective, and how it aligns with client goals. Include specific content ideas, target audience, and expected outcome.",
      "target_segment": "Specific segment name (e.g., 'Engaged Buyers', 'All Subscribers', 'VIPs')",
      "campaign_objective": "Specific objective (e.g., 'Increase Q4 Revenue by 15%', 'Improve Email Open Rates', 'Drive Repeat Purchases')"
    }
  ],
  "planning_summary": "A strategic overview of the entire calendar plan, explaining how it addresses the client's goals, leverages historical data, and incorporates the requested event types. Highlight key themes and expected impact."
}
```
Ensure all fields are populated with relevant and specific information. Dates must be valid for {target_month}/{target_year}.
""",
                "variables": [
                    "client_name", "industry", "background", "voice", "key_growth_objective",
                    "affinity_segment_1", "affinity_segment_2", "affinity_segment_3", 
                    "goals_summary", "campaign_history_summary", "recent_performance_summary",
                    "target_month", "target_year", "additional_context"
                ],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Save to Firestore
            db.collection('prompt_templates').document(template_id).set(default_template)
            return default_template
            
    except Exception as e:
        logger.error(f"Failed to get prompt template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get prompt template: {e}")

# AI Calendar Generation Service
class AICalendarGenerator:
    def __init__(self, secret_manager: SecretManagerService):
        self.gemini_service = GeminiService(secret_manager=secret_manager)
        self.mcp_service = MCPKlaviyoService()
        self.key_resolver = get_client_key_resolver()
    
    async def generate_calendar_plan(
        self,
        client_id: str,
        month: int,
        year: int,
        additional_context: Optional[str] = None
    ) -> CalendarPlanningResponse:
        """Generate AI-powered calendar plan"""
        try:
            # 1. Fetch client context
            client_context = await get_client_context(client_id)
            if "error" in client_context:
                raise HTTPException(status_code=500, detail=client_context["error"])
            
            # 2. Fetch Klaviyo data via MCP
            klaviyo_data = await self.mcp_service.fetch_klaviyo_data(client_id, month, year)
            
            # 3. Get provider configuration for calendar planning
            provider_cfg = self._resolve_pipeline_config()

            # 4. Get prompt template
            template_data = await get_prompt_template()
            
            # 5. Prepare template variables
            template_vars = {
                "client_name": client_context["client_info"]["name"],
                "industry": client_context["client_info"]["industry"],
                "background": client_context["client_info"]["background"],
                "voice": client_context["client_info"]["voice"],
                "key_growth_objective": client_context["client_info"]["key_growth_objective"],
                "affinity_segment_1": client_context["affinity_segments"]["segment_1"],
                "affinity_segment_2": client_context["affinity_segments"]["segment_2"],
                "affinity_segment_3": client_context["affinity_segments"]["segment_3"],
                "goals_summary": self._format_goals_summary(client_context["goals"]),
                "campaign_history_summary": self._format_campaign_history(klaviyo_data["campaign_history"]),
                "recent_performance_summary": self._format_performance_summary(klaviyo_data["recent_performance"]),
                "target_month": month,
                "target_year": year,
                "additional_context": additional_context or "None provided"
            }
            
            # 6. Format prompt with variables
            formatted_prompt = template_data["template"].format(**template_vars)
            
            # 7. Generate calendar plan with the configured provider
            if provider_cfg.get("provider") != "gemini":
                raise HTTPException(status_code=503, detail=f"Configured provider '{provider_cfg.get('provider')}' is not enabled for calendar planning")

            ai_response = await self._call_gemini_api(formatted_prompt)
            calendar_data = self._parse_gemini_response(ai_response)
            
            return CalendarPlanningResponse(
                success=True,
                events=calendar_data["events"],
                planning_summary=calendar_data["planning_summary"],
                client_context=client_context,
                klaviyo_data_summary={
                    "campaign_history_count": len(klaviyo_data.get("campaign_history", [])),
                    "has_recent_performance": bool(klaviyo_data.get("recent_performance")),
                    # MCP returns segments as a flat list
                    "segments_count": len(klaviyo_data.get("segments", [])),
                    "data_fetched_at": klaviyo_data.get("data_fetched_at")
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate calendar plan: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate calendar plan: {e}")

    def _resolve_pipeline_config(self) -> Dict[str, Any]:
        try:
            doc = db.collection('ai_pipelines').document('calendar_planning').get()
            if not doc.exists:
                return {
                    "provider": "gemini",
                    "model_name": "gemini-1.5-pro-latest",
                    "use_orchestrator": False,
                    "prompt_id": None
                }
            return doc.to_dict()
        except Exception:
            return {
                "provider": "gemini",
                "model_name": "gemini-1.5-pro-latest",
                "use_orchestrator": False,
                "prompt_id": None
            }
    
    def _format_goals_summary(self, goals: List[Dict]) -> str:
        if not goals:
            return "No specific goals defined for this period. The AI should generate a general engagement and sales calendar."
        
        summary = []
        for goal in goals:
            goal_type = goal.get('type', 'General Goal')
            target_value = goal.get('target_value', 'N/A')
            target_date = goal.get('target_date', 'N/A')
            description = goal.get('description', 'No description provided.')
            
            summary.append(
                f"- Type: {goal_type}, Target: {target_value}, By: {target_date}. Description: {description}"
            )
        return "Goals for the planning period:\n" + "\n".join(summary)
    
    def _format_campaign_history(self, history: List[Dict]) -> str:
        """Summarize campaign history from MCP.
        Accepts either a pre-aggregated list by year, or a flat list of Klaviyo campaign records.
        """
        if not history:
            return "No historical campaign data available for this period."

        # Case 1: Pre-aggregated objects with year + campaigns keys
        if isinstance(history[0], dict) and (
            "year" in history[0] or "campaigns" in history[0]
        ):
            summary = []
            for year_data in history:
                year = year_data.get("year", "Unknown Year")
                campaigns = year_data.get("campaigns", [])
                try:
                    count = len(campaigns)
                except Exception:
                    count = 0
                summary.append(f"- {year}: {count} campaigns")
            return "\n".join(summary)

        # Case 2: Flat Klaviyo v2 campaign records (id/type/attributes)
        try:
            count = len(history)
            return f"Campaigns in selected period: {count}"
        except Exception:
            return "Campaign history available."
    
    def _format_performance_summary(self, performance: Dict) -> str:
        if not performance or "error" in performance:
            return "Recent performance data not available."

        # Klaviyo metric-aggregates returns under data/attributes/results (implementation TBD)
        if isinstance(performance, dict) and "data" in performance:
            return "Recent metrics available (last 30 days)"

        # Fallback if an alternate shape is provided
        try:
            points = len(performance.get("metrics", []))
            if points:
                return f"Recent metrics available (last 30 days): {points} data points"
        except Exception:
            pass
        return "Recent performance data available."
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API with formatted prompt"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            
            if response.status_code != 200:
                status = 503 if response.status_code in (429, 500, 502, 503) else 500
                raise HTTPException(status_code=status, detail=f"Gemini API error: {response.text}")
            
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
    
    def _parse_gemini_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate Gemini response, robustly extracting JSON from markdown."""
        try:
            # Try to extract JSON from a markdown code block
            json_match = re.search(r"```json\n(.*?)```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # Fallback: try to find the first { and last }
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx == -1 or end_idx == 0:
                    raise ValueError("No JSON found in response")
                json_str = response[start_idx:end_idx]

            calendar_data = json.loads(json_str)

            # Validate required fields
            if "events" not in calendar_data:
                raise ValueError("Missing 'events' field in response")

            if "planning_summary" not in calendar_data:
                calendar_data["planning_summary"] = "AI-generated calendar plan created successfully."

            return calendar_data

        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            # Return fallback response
            return {
                "events": [],
                "planning_summary": f"Failed to parse AI response: {e}"
            }

# API Endpoints
ai_generator = AICalendarGenerator(secret_manager=get_secret_manager_service())

@router.post("/generate", response_model=CalendarPlanningResponse)
async def generate_calendar_plan(request: CalendarPlanningRequest):
    """Generate AI-powered calendar plan for a client"""
    return await ai_generator.generate_calendar_plan(
        client_id=request.client_id,
        month=request.month,
        year=request.year,
        additional_context=request.additional_context
    )

@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a prompt template"""
    return await get_prompt_template(template_id)

@router.put("/templates/{template_id}")
async def update_template(template_id: str, update: PromptTemplateUpdate):
    """Update a prompt template (admin only)"""
    try:
        template_doc = db.collection('prompt_templates').document(template_id)
        current_template = template_doc.get()
        
        if not current_template.exists:
            raise HTTPException(status_code=404, detail="Template not found")
        
        current_data = current_template.to_dict()
        
        # Update only provided fields
        update_data = {"updated_at": datetime.now()}
        if update.name is not None:
            update_data["name"] = update.name
        if update.template is not None:
            update_data["template"] = update.template
        if update.variables is not None:
            update_data["variables"] = update.variables
        
        template_doc.update(update_data)
        
        # Return updated template
        updated_template = template_doc.get().to_dict()
        return updated_template
        
    except Exception as e:
        logger.error(f"Failed to update template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update template: {e}")

@router.get("/client/{client_id}/context")
async def get_client_planning_context(client_id: str):
    """Get comprehensive client context for calendar planning"""
    return await get_client_context(client_id)

@router.post("/klaviyo-data")
async def fetch_klaviyo_planning_data(client_id: str, month: int, year: int):
    """Fetch Klaviyo data for calendar planning"""
    mcp_service = MCPKlaviyoService()
    return await mcp_service.fetch_klaviyo_data(client_id, month, year)
