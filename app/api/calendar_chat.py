"""
Calendar Chat API - Natural language interface for calendar operations.
Processes commands like "Add a promotional campaign on the 15th" and returns structured responses.
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.deps import get_db
from app.deps.secrets import get_secret_manager_service
from app.services.ai_models_service import AIModelsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar-chat"])


class CalendarChatRequest(BaseModel):
    """Request model for calendar chat."""
    message: str
    context: Optional[Dict[str, Any]] = {}
    provider: Optional[str] = "openai"  # openai, anthropic, google


class CalendarChatResponse(BaseModel):
    """Response model for calendar chat."""
    success: bool
    response: str  # Natural language response
    action: Optional[Dict[str, Any]] = None  # Structured action to execute
    debug: Optional[Dict[str, Any]] = None  # Debug information


class CalendarCommandParser:
    """Parse natural language commands into structured calendar operations."""
    
    @staticmethod
    def parse_add_command(message: str) -> Optional[Dict[str, Any]]:
        """Parse add campaign/event commands."""
        message_lower = message.lower()
        
        # First check for custom event creation with "make" or "create event"
        if ("make" in message_lower or "create" in message_lower) and ("event" in message_lower or "campaign" in message_lower):
            # Extract date - handle various formats
            day = None
            custom_name = None
            
            # Try to extract month and day (e.g., "January 28th, 2026")
            month_patterns = [
                r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?",
                r"(\d+)(?:st|nd|rd|th)?\s+(?:of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)(?:,?\s+(\d{4}))?",
            ]

            month_name = None
            year = None
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }

            for pattern in month_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    if pattern.startswith(r"(\d+)"):
                        day = int(match.group(1))
                        month_name = match.group(2)
                        year = int(match.group(3)) if match.group(3) else None
                    else:
                        month_name = match.group(1)
                        day = int(match.group(2))
                        year = int(match.group(3)) if match.group(3) else None
                    break
            
            # If no month pattern, try simple day extraction
            if day is None:
                day_match = re.search(r'(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?', message_lower)
                if day_match:
                    day = int(day_match.group(1))
            
            # Extract custom text after "says" or "that says" or "called"
            custom_match = re.search(r'(?:that\s+says|says|called|named|text|with\s+text)\s+(.+?)(?:\.|,|$)', message, re.IGNORECASE)
            if custom_match:
                custom_name = custom_match.group(1).strip()
            
            if day:
                result = {
                    "action": "add",
                    "type": "custom",
                    "day": day,
                    "time": "10:00",
                    "custom_name": custom_name or "Custom Event"
                }
                # Add month and year if they were extracted
                if month_name:
                    result["month"] = month_map.get(month_name)
                if year:
                    result["year"] = year
                return result
        
        # Original patterns for standard campaign types
        add_patterns = [
            r"add\s+(?:a\s+)?(\w+)\s+(?:campaign\s+)?(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
            r"create\s+(?:a\s+)?(\w+)\s+(?:email|campaign)\s+(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
            r"schedule\s+(?:a\s+)?(\w+)\s+(?:for\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
            r"put\s+(?:a\s+)?(\w+)\s+(?:campaign\s+)?(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
        ]
        
        for pattern in add_patterns:
            match = re.search(pattern, message_lower)
            if match:
                campaign_type = match.group(1)
                day = int(match.group(2))
                
                # Normalize campaign type
                type_map = {
                    'promotional': 'promotional',
                    'promo': 'promotional',
                    'content': 'content',
                    'newsletter': 'content',
                    'engagement': 'engagement',
                    'survey': 'engagement',
                    'seasonal': 'seasonal',
                    'holiday': 'seasonal'
                }
                
                campaign_type = type_map.get(campaign_type, 'promotional')
                
                return {
                    "action": "add",
                    "type": campaign_type,
                    "day": day,
                    "time": "10:00"
                }
        
        # Check for simpler patterns
        if "add" in message_lower or "create" in message_lower or "schedule" in message_lower:
            # Try to extract day number
            day_match = re.search(r'(\d+)(?:st|nd|rd|th)?', message_lower)
            if day_match:
                day = int(day_match.group(1))
                
                # Determine type based on keywords
                campaign_type = 'promotional'  # default
                if 'content' in message_lower or 'newsletter' in message_lower:
                    campaign_type = 'content'
                elif 'engagement' in message_lower or 'survey' in message_lower:
                    campaign_type = 'engagement'
                elif 'seasonal' in message_lower or 'holiday' in message_lower:
                    campaign_type = 'seasonal'
                
                return {
                    "action": "add",
                    "type": campaign_type,
                    "day": day,
                    "time": "10:00"
                }
        
        return None
    
    @staticmethod
    def parse_move_command(message: str) -> Optional[Dict[str, Any]]:
        """Parse move campaign commands."""
        move_patterns = [
            r"move\s+(?:the\s+)?campaign\s+from\s+(?:the\s+)?(\d+)(?:st|nd|rd|th)?\s+to\s+(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
            r"reschedule\s+(?:the\s+)?(?:campaign\s+)?from\s+(?:the\s+)?(\d+)(?:st|nd|rd|th)?\s+to\s+(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
            r"change\s+(?:the\s+)?(?:campaign\s+)?(?:from\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?\s+to\s+(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
        ]
        
        message_lower = message.lower()
        
        for pattern in move_patterns:
            match = re.search(pattern, message_lower)
            if match:
                from_day = int(match.group(1))
                to_day = int(match.group(2))
                
                return {
                    "action": "move",
                    "from_day": from_day,
                    "to_day": to_day
                }
        
        return None
    
    @staticmethod
    def parse_delete_command(message: str) -> Optional[Dict[str, Any]]:
        """Parse delete campaign commands."""
        delete_patterns = [
            r"delete\s+(?:the\s+)?campaign\s+(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
            r"remove\s+(?:the\s+)?campaign\s+(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
            r"cancel\s+(?:the\s+)?(?:email|campaign)\s+(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?",
        ]
        
        message_lower = message.lower()
        
        for pattern in delete_patterns:
            match = re.search(pattern, message_lower)
            if match:
                day = int(match.group(1))
                
                return {
                    "action": "delete",
                    "day": day
                }
        
        # Check for "clear all" commands
        if "clear" in message_lower and ("all" in message_lower or "calendar" in message_lower):
            return {
                "action": "clear_all"
            }
        
        # Check for "remove all" of a specific type
        if "remove all" in message_lower or "delete all" in message_lower:
            for campaign_type in ['promotional', 'content', 'engagement', 'seasonal']:
                if campaign_type in message_lower:
                    return {
                        "action": "delete_type",
                        "type": campaign_type
                    }
        
        return None
    
    @staticmethod
    def parse_list_command(message: str) -> Optional[Dict[str, Any]]:
        """Parse list/view commands."""
        message_lower = message.lower()
        
        list_keywords = ['what', 'show', 'list', 'display', 'view']
        
        if any(keyword in message_lower for keyword in list_keywords):
            # Check for specific day
            day_match = re.search(r'(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)?', message_lower)
            if day_match:
                return {
                    "action": "list",
                    "filter": "day",
                    "day": int(day_match.group(1))
                }
            
            # Check for type filter
            for campaign_type in ['promotional', 'content', 'engagement', 'seasonal']:
                if campaign_type in message_lower:
                    return {
                        "action": "list",
                        "filter": "type",
                        "type": campaign_type
                    }
            
            # Check for analytics queries
            if 'revenue' in message_lower:
                return {"action": "analytics", "metric": "revenue"}
            if 'statistic' in message_lower or 'stats' in message_lower:
                return {"action": "analytics", "metric": "all"}
            if 'count' in message_lower or 'how many' in message_lower:
                return {"action": "analytics", "metric": "count"}
            
            # Default to list all
            return {"action": "list", "filter": "all"}
        
        return None
    
    @staticmethod
    def parse_command(message: str) -> Dict[str, Any]:
        """Parse any calendar command."""
        # Try each parser in order
        parsers = [
            CalendarCommandParser.parse_add_command,
            CalendarCommandParser.parse_move_command,
            CalendarCommandParser.parse_delete_command,
            CalendarCommandParser.parse_list_command,
        ]
        
        for parser in parsers:
            result = parser(message)
            if result:
                return result
        
        # If no command matched, return a help response
        return {
            "action": "help",
            "message": message
        }


def generate_response(action: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Generate natural language response based on action."""
    action_type = action.get("action")
    
    if action_type == "add":
        campaign_type = action.get("type", "campaign")
        day = action.get("day")
        campaign_name = action.get("campaign_name") or action.get("custom_name")
        
        # Handle custom events or named campaigns
        if campaign_name:
            return f"✅ Added '{campaign_name}' on the {day}{get_day_suffix(day)} at {action.get('time', '10:00 AM')}"
        elif campaign_type == "custom":
            custom_name = action.get("custom_name", "Custom Event")
            return f"✅ Added event '{custom_name}' on the {day}{get_day_suffix(day)}"
        else:
            return f"✅ Added {campaign_type} campaign on the {day}{get_day_suffix(day)} at {action.get('time', '10:00 AM')}"
    
    elif action_type == "move":
        from_day = action.get("from_day")
        to_day = action.get("to_day")
        return f"📅 Moved campaign from the {from_day}{get_day_suffix(from_day)} to the {to_day}{get_day_suffix(to_day)}"
    
    elif action_type == "delete":
        day = action.get("day")
        return f"❌ Deleted campaign on the {day}{get_day_suffix(day)}"
    
    elif action_type == "clear_all":
        return "🗑️ Cleared all campaigns from the calendar"
    
    elif action_type == "delete_type":
        campaign_type = action.get("type")
        return f"❌ Removed all {campaign_type} campaigns"
    
    elif action_type == "list":
        filter_type = action.get("filter")
        if filter_type == "day":
            day = action.get("day")
            return f"📋 Showing campaigns on the {day}{get_day_suffix(day)}"
        elif filter_type == "type":
            campaign_type = action.get("type")
            return f"📋 Showing all {campaign_type} campaigns"
        else:
            campaign_count = context.get("campaign_count", 0)
            return f"📊 You have {campaign_count} campaigns scheduled this month"
    
    elif action_type == "analytics":
        metric = action.get("metric")
        if metric == "revenue":
            revenue = context.get("total_revenue", 0)
            return f"💰 Expected revenue: ${revenue:,.2f}"
        elif metric == "count":
            count = context.get("campaign_count", 0)
            return f"📈 Total campaigns: {count}"
        else:
            count = context.get("campaign_count", 0)
            revenue = context.get("total_revenue", 0)
            return f"📊 Campaign Statistics:\\n• Total campaigns: {count}\\n• Expected revenue: ${revenue:,.2f}"
    
    elif action_type == "help":
        return ("💡 I can help you manage your campaign calendar! Try commands like:\\n"
                "• 'Add a promotional campaign on the 15th'\\n"
                "• 'Move the campaign from the 10th to the 20th'\\n"
                "• 'Delete the campaign on the 5th'\\n"
                "• 'Show me all campaigns'\\n"
                "• 'What's the expected revenue?'")
    
    else:
        return "🤔 I understand you want to manage your calendar. Could you be more specific?"


def get_day_suffix(day: int) -> str:
    """Get the ordinal suffix for a day number."""
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return suffix


# LLM Prompt for parsing campaign commands
CAMPAIGN_PARSER_PROMPT = """
You are a calendar assistant. Parse the following user message about creating or managing a campaign.
Extract these details from the message:
- campaign_name: The specific name mentioned (e.g., "Refer a Friend Weekend", "Summer Sale", etc.)
- campaign_type: promotional, content, engagement, seasonal, or custom
- action: add, move, delete, list, or other
- day: The day of the month (number) if mentioned
- time: Send time if mentioned (default: "10:00")
- from_day: For move operations, the source day
- to_day: For move operations, the target day

User message: {message}
Current calendar month: {current_month}

IMPORTANT RULES:
1. If the user says something like "create a campaign called X" or "add X campaign", X is the campaign_name
2. Look for quoted text as potential campaign names
3. If no explicit name is given but a descriptive phrase is used, use that as the name
4. DATE RESOLUTION: If the user mentions a day (like "the 13th") WITHOUT specifying a month:
   - Assume they mean the current calendar month shown above
   - For example: "Add Flash Sale on the 13th" with current month "October 2025" means October 13th
5. Only if a different month is explicitly mentioned should you indicate that

Return ONLY valid JSON in this format:
{{
  "action": "add|move|delete|list",
  "campaign_name": "extracted name or null",
  "campaign_type": "promotional|content|engagement|seasonal|custom",
  "day": number_or_null,
  "time": "HH:MM",
  "from_day": number_or_null,
  "to_day": number_or_null
}}
"""

@router.post("/chat", response_model=CalendarChatResponse)
async def calendar_chat(
    request: CalendarChatRequest,
    db = Depends(get_db),
    secret_manager = Depends(get_secret_manager_service)
):
    """
    Process natural language calendar commands.
    
    This endpoint uses LLMs to parse natural language messages about calendar operations
    and returns structured actions that the frontend can execute.
    """
    try:
        logger.info(f"Calendar chat request: {request.message}")
        logger.info(f"Using provider: {request.provider}")
        
        action = None
        
        # Try LLM parsing if provider is not 'regex'
        if request.provider and request.provider != 'regex':
            try:
                # Initialize AI service
                ai_service = AIModelsService(db, secret_manager)
                
                # Prepare the prompt
                prompt = CAMPAIGN_PARSER_PROMPT.format(
                    message=request.message,
                    current_month=request.context.get("current_month", "current month")
                )
                
                # Map provider names to ai_models_service format
                provider_map = {
                    "openai": "openai",
                    "anthropic": "claude",
                    "google": "gemini"
                }
                provider = provider_map.get(request.provider, request.provider)
                
                # Execute LLM request
                llm_response = await ai_service.execute_direct(
                    prompt=prompt,
                    provider=provider,
                    model=None  # Use default model for provider
                )
                
                logger.info(f"LLM response: {llm_response}")
                
                # Clean up LLM response - remove markdown code blocks if present
                cleaned_response = llm_response.strip()
                if cleaned_response.startswith("```"):
                    # Remove markdown code blocks
                    lines = cleaned_response.split('\n')
                    # Remove first line (```json or ```)
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    # Remove last line if it's ```
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    cleaned_response = '\n'.join(lines)
                
                # Parse LLM response
                parsed = json.loads(cleaned_response)
                
                # Build action from LLM response
                if parsed.get("action") == "add":
                    action = {
                        "action": "add",
                        "type": parsed.get("campaign_type", "promotional"),
                        "day": parsed.get("day", 15),
                        "time": parsed.get("time", "10:00"),
                        "campaign_name": parsed.get("campaign_name")  # Include extracted name
                    }
                elif parsed.get("action") == "move":
                    action = {
                        "action": "move",
                        "from_day": parsed.get("from_day"),
                        "to_day": parsed.get("to_day")
                    }
                elif parsed.get("action") == "delete":
                    action = {
                        "action": "delete",
                        "day": parsed.get("day")
                    }
                else:
                    action = parsed  # Use as-is for other actions
                    
                logger.info(f"LLM-parsed action: {action}")
                
            except Exception as llm_error:
                logger.warning(f"LLM parsing failed, falling back to regex: {llm_error}")
                # Fall back to regex parsing
                action = None
        
        # Use regex parsing as fallback or if provider is 'regex'
        if action is None:
            action = CalendarCommandParser.parse_command(request.message)
        
        # Generate natural language response
        response = generate_response(action, request.context)
        
        # Log the final action for debugging
        logger.info(f"Final action: {action}")
        
        return CalendarChatResponse(
            success=True,
            response=response,
            action=action,
            debug={
                "original_message": request.message,
                "parsed_action": action,
                "context": request.context,
                "provider": request.provider
            }
        )
        
    except Exception as e:
        logger.error(f"Calendar chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for calendar chat API."""
    return {"status": "healthy", "service": "calendar-chat"}