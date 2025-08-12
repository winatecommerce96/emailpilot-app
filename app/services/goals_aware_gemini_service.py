"""
Enhanced Goals-Aware Gemini AI Service for EmailPilot Calendar
Integrates revenue goals and historical performance for strategic campaign planning
"""

import logging
from typing import List, Dict, Any, Optional
import json
import requests
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GoalsAwareGeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"

    async def process_goal_aware_chat(
        self, 
        message: str, 
        client_name: str,
        events: List[Dict],
        goals_data: Optional[Dict] = None,
        chat_history: List[Dict] = None
    ) -> Dict:
        """
        Process calendar chat with goal awareness and strategic recommendations
        """
        
        # Build context with goals information
        goals_context = ""
        if goals_data and goals_data.get('has_goal'):
            goal_info = goals_data['goal']
            progress = goals_data['progress']
            
            goals_context = f"""
REVENUE GOAL CONTEXT:
- Client: {client_name}
- Monthly Revenue Goal: ${goal_info.get('revenue_goal', 0):,.2f} for {goal_info.get('year')}-{goal_info.get('month'):02d}
- Current Progress: {progress.get('progress_percentage', 0):.1f}% complete
- Remaining Amount: ${progress.get('remaining_amount', 0):,.2f}
- Days Remaining: {progress.get('days_remaining', 0)} days
- Goal Status: {"ON TRACK" if progress.get('is_on_track') else "NEEDS ATTENTION"}
- Scheduled Campaigns: {progress.get('campaign_count', 0)}
- Estimated Revenue from Current Calendar: ${progress.get('estimated_revenue', 0):,.2f}

CAMPAIGN PERFORMANCE BENCHMARKS:
- RRB Promotion: $850 avg revenue (High-converting promotional emails)
- Flash Sale: $920 avg revenue (Urgent, time-sensitive offers)
- Cheese Club: $450 avg revenue (Member-focused campaigns)  
- SMS Alert: $520 avg revenue (High engagement mobile campaigns)
- Seasonal: $680 avg revenue (Holiday/seasonal promotions)
- Nurturing/Education: $280 avg revenue (Educational content)
- Community/Lifestyle: $320 avg revenue (Community building)
- Re-engagement: $180 avg revenue (Win-back campaigns)
- Newsletter: $150 avg revenue (Regular updates)
"""

        # Build events context
        events_context = ""
        if events:
            events_context = f"\nCURRENT CALENDAR EVENTS ({len(events)} total):\n"
            for event in events[:10]:  # Limit to 10 most relevant
                events_context += f"- {event.get('event_date', 'TBD')}: {event.get('title', 'Untitled')} ({event.get('event_type', 'Unspecified')})\n"
        
        # Build chat history context
        history_context = ""
        if chat_history:
            history_context = "\nRECENT CONVERSATION:\n"
            for i, msg in enumerate(chat_history[-6:]):  # Last 3 exchanges
                role = "User" if i % 2 == 0 else "Assistant"
                content = msg.get('text', '')[:200]  # Limit length
                history_context += f"{role}: {content}\n"

        system_prompt = f"""You are an AI marketing strategist for EmailPilot, specializing in revenue-driven email campaign planning. You help clients achieve their revenue goals through strategic calendar planning.

{goals_context}

{events_context}

{history_context}

STRATEGIC FOCUS:
- Always consider the revenue goal when providing advice
- Prioritize high-converting campaign types when behind on goals
- Suggest specific dates and campaign types based on revenue needs
- Factor in seasonality and urgency when goal achievement is at risk
- Provide data-driven recommendations using the performance benchmarks

RESPONSE GUIDELINES:
1. Be strategic and goal-focused
2. Provide specific, actionable recommendations
3. Include revenue impact estimates when suggesting campaigns
4. Mention timeline urgency if goal is at risk
5. Be encouraging but realistic about goal achievement

If the user asks for actions (create, delete, update events), respond with structured JSON for actions.

User Question: {message}"""

        try:
            response = await self._make_gemini_request(system_prompt)
            
            # Check if response contains actionable items
            is_action = any(keyword in response.lower() for keyword in [
                'create campaign', 'add event', 'schedule', 'delete', 'remove', 'update'
            ])
            
            return {
                'message': response,
                'is_action': is_action,
                'goals_aware': goals_data is not None and goals_data.get('has_goal', False),
                'goal_status': 'on_track' if goals_data and goals_data.get('progress', {}).get('is_on_track') else 'needs_attention'
            }
            
        except Exception as e:
            logger.error(f"Error in goals-aware chat processing: {e}")
            fallback_message = self._generate_fallback_response(message, goals_data)
            return {
                'message': fallback_message,
                'is_action': False,
                'goals_aware': False,
                'goal_status': 'unknown'
            }

    def _generate_fallback_response(self, message: str, goals_data: Optional[Dict]) -> str:
        """Generate fallback response when AI service is unavailable"""
        if goals_data and goals_data.get('has_goal'):
            progress = goals_data.get('progress', {})
            remaining = progress.get('remaining_amount', 0)
            days_left = progress.get('days_remaining', 0)
            
            if days_left > 0 and remaining > 0:
                daily_needed = remaining / days_left
                return f"I'm temporarily unavailable, but I can see you need ${remaining:,.0f} more revenue in {days_left} days (${daily_needed:.0f}/day). Consider high-converting campaigns like RRB Promotions or Flash Sales to stay on track!"
            
        return "I'm temporarily unavailable. Please try your question again in a moment."

    async def generate_goal_based_campaign_suggestions(
        self,
        client_name: str,
        goals_data: Dict,
        current_events: List[Dict],
        target_date_range: Optional[tuple] = None
    ) -> List[Dict]:
        """
        Generate strategic campaign suggestions based on revenue goals
        """
        
        if not goals_data.get('has_goal'):
            return []
        
        goal_info = goals_data['goal']
        progress = goals_data['progress']
        
        prompt = f"""As a strategic email marketing consultant, generate 3-5 specific campaign suggestions for {client_name} to achieve their revenue goal.

GOAL ANALYSIS:
- Monthly Goal: ${goal_info.get('revenue_goal', 0):,.2f}
- Progress: {progress.get('progress_percentage', 0):.1f}% complete
- Remaining: ${progress.get('remaining_amount', 0):,.2f}
- Days Left: {progress.get('days_remaining', 0)}
- Current Status: {"ON TRACK" if progress.get('is_on_track') else "BEHIND GOAL"}

CURRENT CALENDAR: {len(current_events)} campaigns scheduled

CAMPAIGN PERFORMANCE BENCHMARKS:
- Flash Sale: $920 avg (urgent offers)
- RRB Promotion: $850 avg (promotional emails)
- Seasonal: $680 avg (holiday campaigns)
- SMS Alert: $520 avg (mobile engagement)
- Cheese Club: $450 avg (member campaigns)

Provide exactly this JSON structure:
{{
  "campaigns": [
    {{
      "title": "Campaign Name",
      "type": "Campaign Type",
      "suggested_date": "YYYY-MM-DD",
      "priority": "high|medium|low", 
      "estimated_revenue": 850,
      "rationale": "Why this campaign will help achieve the goal",
      "subject_line_suggestions": ["Subject 1", "Subject 2"],
      "key_tactics": ["Tactic 1", "Tactic 2"]
    }}
  ],
  "strategy_summary": "Overall strategic approach to achieve the goal"
}}"""

        try:
            response = await self._make_gemini_request(prompt)
            
            # Parse JSON response
            try:
                parsed_response = json.loads(response)
                return parsed_response.get('campaigns', [])
            except json.JSONDecodeError:
                # Fallback to manual parsing if JSON is malformed
                return self._parse_campaign_suggestions_fallback(response)
                
        except Exception as e:
            logger.error(f"Error generating goal-based suggestions: {e}")
            return []

    def _parse_campaign_suggestions_fallback(self, response: str) -> List[Dict]:
        """Fallback method to extract campaign suggestions from text response"""
        # Basic fallback suggestions based on common patterns
        suggestions = []
        
        if "flash sale" in response.lower():
            suggestions.append({
                "title": "Flash Sale Campaign",
                "type": "Flash Sale",
                "suggested_date": (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                "priority": "high",
                "estimated_revenue": 920,
                "rationale": "High-urgency campaign for immediate revenue boost"
            })
        
        if "promotion" in response.lower():
            suggestions.append({
                "title": "Strategic Promotion",
                "type": "RRB Promotion", 
                "suggested_date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                "priority": "high",
                "estimated_revenue": 850,
                "rationale": "Proven high-converting promotional campaign"
            })
        
        return suggestions

    async def _make_gemini_request(self, prompt: str) -> str:
        """Make request to Gemini API"""
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "candidates" in result and len(result["candidates"]) > 0:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise Exception("No valid response from Gemini API")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API request failed: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Gemini API response format: {e}")
            raise

# Initialize enhanced Gemini service
goals_aware_gemini = GoalsAwareGeminiService()