"""
Gemini service for AI chat and document processing
"""

import logging
from typing import List, Dict, Any, Optional
import json
import requests
import os
from datetime import datetime, timedelta

from app.schemas.calendar import CalendarEventResponse, AIResponse, AIAction

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"

    async def plan_campaign(
        self,
        client_id: str,
        campaign_type: str,
        start_date: str,
        end_date: str,
        promotion_details: str
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive email/SMS campaign plan using Gemini AI
        """
        prompt = f"""You are an expert email marketing strategist. Create a comprehensive campaign plan for the following:

**Campaign Details:**
- Client ID: {client_id}
- Campaign Type: {campaign_type}
- Start Date: {start_date}
- End Date: {end_date}
- Promotion Details: {promotion_details}

**Requirements:**
1. Create a strategic campaign plan with multiple touchpoints
2. Include both EMAIL and SMS campaigns
3. Space events intelligently throughout the campaign period
4. Use these event types: email, sms, push
5. Use appropriate color coding based on campaign types

**Event Color Guidelines:**
- New Product Launch: "bg-blue-200 text-blue-800"
- Limited Time Offer: "bg-red-200 text-red-800"
- Flash Sale: "bg-orange-200 text-orange-800"
- RRB Promotion: "bg-red-300 text-red-800"
- Cheese Club: "bg-green-200 text-green-800"
- SMS Alert: "bg-orange-300 text-orange-800"
- Re-engagement: "bg-yellow-200 text-yellow-800"
- Nurturing/Education: "bg-blue-200 text-blue-800"

**Output Format:**
Return a JSON object with this exact structure:
{{
  "campaign_strategy": "Brief strategic overview of the campaign approach",
  "events": [
    {{
      "title": "Event Title",
      "date": "YYYY-MM-DD",
      "content": "Detailed event description including segment, send time, subject lines, key messaging",
      "color": "bg-color-class text-color-class",
      "event_type": "email|sms|push",
      "campaign_metadata": {{
        "campaign_type": "{campaign_type}",
        "sequence_order": 1,
        "touchpoint_type": "announcement|reminder|urgency|last_chance|follow_up"
      }}
    }}
  ]
}}

**Campaign Strategy Guidelines:**
- Start with announcement/teaser (email)
- Include mid-campaign reminders (email + SMS)
- Build urgency near end (SMS alerts)
- End with last chance messaging
- Include post-campaign follow-up if appropriate
- Aim for 4-8 touchpoints depending on campaign length
- Space events to maximize engagement without oversaturation

Create a strategic, well-timed campaign that drives results!"""

        try:
            response = await self._make_gemini_request(prompt)
            
            if response:
                # Extract JSON from response
                json_match = self._extract_json_from_response(response)
                if json_match:
                    campaign_data = json.loads(json_match)
                    logger.info(f"Generated campaign plan with {len(campaign_data.get('events', []))} events")
                    return campaign_data
                else:
                    logger.error("No valid JSON found in Gemini campaign response")
                    return self._get_fallback_campaign_plan(campaign_type, start_date, end_date, promotion_details)
            else:
                logger.error("No response from Gemini for campaign planning")
                return self._get_fallback_campaign_plan(campaign_type, start_date, end_date, promotion_details)
                
        except Exception as e:
            logger.error(f"Error generating campaign plan with Gemini: {e}")
            return self._get_fallback_campaign_plan(campaign_type, start_date, end_date, promotion_details)

    def _get_fallback_campaign_plan(
        self,
        campaign_type: str,
        start_date: str,
        end_date: str,
        promotion_details: str
    ) -> Dict[str, Any]:
        """
        Generate a fallback campaign plan when Gemini is unavailable
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            campaign_length = (end_dt - start_dt).days
            
            # Determine color scheme based on campaign type
            color_map = {
                "New Product": "bg-blue-200 text-blue-800",
                "Limited Time Offer": "bg-red-200 text-red-800", 
                "Flash Sale": "bg-orange-200 text-orange-800",
                "Other": "bg-purple-200 text-purple-800"
            }
            
            primary_color = color_map.get(campaign_type, "bg-gray-200 text-gray-800")
            sms_color = "bg-orange-300 text-orange-800"
            
            events = []
            
            # Announcement email (Day 1)
            events.append({
                "title": f"{campaign_type} - Announcement",
                "date": start_date,
                "content": f"Launch announcement for {promotion_details}. Includes product highlights, key benefits, and clear CTA.",
                "color": primary_color,
                "event_type": "email",
                "campaign_metadata": {
                    "campaign_type": campaign_type,
                    "sequence_order": 1,
                    "touchpoint_type": "announcement"
                }
            })
            
            # Mid-campaign reminder (if campaign > 3 days)
            if campaign_length > 3:
                mid_date = start_dt + timedelta(days=campaign_length // 2)
                events.append({
                    "title": f"{campaign_type} - Reminder",
                    "date": mid_date.strftime("%Y-%m-%d"),
                    "content": f"Mid-campaign reminder for {promotion_details}. Reinforces value proposition and includes social proof.",
                    "color": primary_color,
                    "event_type": "email",
                    "campaign_metadata": {
                        "campaign_type": campaign_type,
                        "sequence_order": 2,
                        "touchpoint_type": "reminder"
                    }
                })
            
            # SMS alert (if campaign > 5 days, 2 days before end)
            if campaign_length > 5:
                sms_date = end_dt - timedelta(days=2)
                events.append({
                    "title": f"{campaign_type} - SMS Alert",
                    "date": sms_date.strftime("%Y-%m-%d"),
                    "content": f"SMS urgency alert: {promotion_details} ends soon! Quick, mobile-optimized message with direct link.",
                    "color": sms_color,
                    "event_type": "sms",
                    "campaign_metadata": {
                        "campaign_type": campaign_type,
                        "sequence_order": 3,
                        "touchpoint_type": "urgency"
                    }
                })
            
            # Last chance email (Final day)
            if campaign_length > 1:
                events.append({
                    "title": f"{campaign_type} - Last Chance",
                    "date": end_date,
                    "content": f"Final opportunity email for {promotion_details}. Creates urgency with countdown timer and FOMO messaging.",
                    "color": "bg-red-300 text-red-800",
                    "event_type": "email",
                    "campaign_metadata": {
                        "campaign_type": campaign_type,
                        "sequence_order": len(events) + 1,
                        "touchpoint_type": "last_chance"
                    }
                })
            
            return {
                "campaign_strategy": f"Strategic {campaign_type.lower()} campaign with {len(events)} touchpoints across email and SMS channels, designed to maximize engagement and conversions.",
                "events": events
            }
            
        except Exception as e:
            logger.error(f"Error creating fallback campaign plan: {e}")
            return {
                "campaign_strategy": "Basic campaign plan due to system limitations",
                "events": [{
                    "title": f"{campaign_type} Campaign",
                    "date": start_date,
                    "content": f"Campaign event for {promotion_details}",
                    "color": "bg-blue-200 text-blue-800",
                    "event_type": "email",
                    "campaign_metadata": {
                        "campaign_type": campaign_type,
                        "sequence_order": 1,
                        "touchpoint_type": "announcement"
                    }
                }]
            }

    async def process_campaign_document(self, doc_content: str) -> List[Dict[str, Any]]:
        """
        Process Google Doc content to extract campaign information
        """
        prompt = f"""
You are a marketing campaign calendar assistant. Please analyze this campaign planning document and extract campaign information. Return a JSON array of campaign objects with this exact structure:

[
  {{
    "date": "YYYY-MM-DD",
    "title": "Campaign Title",
    "content": "Campaign details including segment, send time, subject lines, etc.",
    "color": "bg-blue-200 text-blue-800"
  }}
]

Use these color classes based on campaign type:
- RRB Promotion: "bg-red-300 text-red-800"
- Cheese Club: "bg-green-200 text-green-800"  
- Nurturing/Education: "bg-blue-200 text-blue-800"
- Community/Lifestyle: "bg-purple-200 text-purple-800"
- Re-engagement: "bg-yellow-200 text-yellow-800"
- SMS Alert: "bg-orange-300 text-orange-800"

Document content:
{doc_content}
"""
        
        try:
            response = await self._make_gemini_request(prompt)
            
            if response:
                # Extract JSON from response
                json_match = self._extract_json_from_response(response)
                if json_match:
                    campaigns = json.loads(json_match)
                    logger.info(f"Extracted {len(campaigns)} campaigns from document")
                    return campaigns
                else:
                    logger.error("No valid JSON found in Gemini response")
                    return []
            else:
                logger.error("No response from Gemini")
                return []
                
        except Exception as e:
            logger.error(f"Error processing document with Gemini: {e}")
            return []

    async def process_calendar_chat(
        self,
        message: str,
        client_name: str,
        events: List[CalendarEventResponse],
        chat_history: List[Dict[str, Any]]
    ) -> AIResponse:
        """
        Process chat message about calendar events
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Convert events to simple dict format for context
        events_data = {}
        for event in events:
            events_data[f"event-{event.id}"] = {
                "date": event.event_date.strftime("%Y-%m-%d"),
                "title": event.title,
                "content": event.content or "",
                "event_type": event.event_type or ""
            }
        
        system_instruction = f"""You are a Calendar AI Assistant. Your capabilities are to answer questions about the calendar events and to perform actions to modify the calendar. The calendar contains ONLY Email, SMS, and Push notification campaigns.

**CONTEXT**
- Today's date is: {today}.
- The current client is: {client_name}.
- The calendar data is a JSON object where the keys are unique event IDs.

**INSTRUCTIONS**
1.  **Analyze the User's Request:** Understand if the user is asking a question or requesting an action (create, delete, update).
2.  **For Questions:** If the user asks a question (e.g., "how many campaigns in September?", "what is the SMS campaign about?"), answer conversationally based on the provided Campaign Data and chat history.
3.  **For Actions:** If the user requests a change, you MUST identify the correct eventId from the campaign data and respond ONLY with a single, minified JSON object describing the action. Do NOT add any other text.

**ACTION JSON FORMATS**
- **Delete:** `{{"action": "delete", "eventId": "EVENT_ID_TO_DELETE"}}`
- **Update:** `{{"action": "update", "eventId": "EVENT_ID_TO_UPDATE", "updates": {{"field_to_change": "new_value"}}}}` (Fields can be "title", "date", "content")
- **Create:** `{{"action": "create", "event": {{"date": "YYYY-MM-DD", "title": "New Event Title", "content": "Details..."}}}}`

**EXAMPLE**
- User asks: "delete the cheese club event next tuesday"
- You find the event in the data with title "Cheese Club" on the correct date and get its eventId, for example, "event-1678886400000".
- Your response MUST be exactly: `{{"action":"delete","eventId":"event-1678886400000"}}`

**Campaign Data:**
{json.dumps(events_data, indent=2)}
"""
        
        # Build conversation history for Gemini
        contents = []
        for msg in chat_history[-10:]:  # Keep last 10 messages
            contents.append({
                "role": msg.get("role", "user"),
                "parts": [{"text": msg.get("text", "")}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })
        
        try:
            response = await self._make_gemini_request(
                message=None,
                contents=contents,
                system_instruction=system_instruction
            )
            
            if response:
                # Check if response is a JSON action
                try:
                    action_data = json.loads(response.strip())
                    if "action" in action_data:
                        return AIResponse(
                            message="Action processed",
                            is_action=True,
                            action=AIAction(**action_data)
                        )
                except json.JSONDecodeError:
                    pass
                
                # Regular conversational response
                return AIResponse(
                    message=response,
                    is_action=False
                )
            else:
                return AIResponse(
                    message="I'm sorry, I encountered an error trying to process your request.",
                    is_action=False
                )
                
        except Exception as e:
            logger.error(f"Error processing calendar chat: {e}")
            return AIResponse(
                message="I'm sorry, I encountered an error trying to process your request.",
                is_action=False
            )

    async def _make_gemini_request(
        self,
        message: Optional[str] = None,
        contents: Optional[List[Dict]] = None,
        system_instruction: Optional[str] = None
    ) -> Optional[str]:
        """
        Make request to Gemini API
        """
        try:
            payload = {}
            
            if contents:
                payload["contents"] = contents
            elif message:
                payload["contents"] = [{"role": "user", "parts": [{"text": message}]}]
            else:
                raise ValueError("Either message or contents must be provided")
            
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if (result.get("candidates") and 
                    len(result["candidates"]) > 0 and
                    result["candidates"][0].get("content") and
                    result["candidates"][0]["content"].get("parts") and
                    len(result["candidates"][0]["content"]["parts"]) > 0):
                    
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    logger.error("Unexpected Gemini response structure")
                    return None
            else:
                logger.error(f"Gemini API error: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making Gemini request: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """
        Extract JSON array from Gemini response text
        """
        try:
            # Look for JSON array or object in the response
            import re
            json_match = re.search(r'[\[\{][\s\S]*[\]\}]', response)
            if json_match:
                return json_match.group(0)
            else:
                return None
        except Exception as e:
            logger.error(f"Error extracting JSON from response: {e}")
            return None