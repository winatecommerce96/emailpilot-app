#!/usr/bin/env python3
"""
Firebase Goals-Aware Calendar Integration for EmailPilot
Enhanced calendar system that integrates with goals collection for strategic campaign planning
"""

import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin

logger = logging.getLogger(__name__)

class FirebaseGoalsCalendarService:
    """Enhanced calendar service that integrates with goals for strategic planning"""
    
    def __init__(self):
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            if not firebase_admin._apps:
                service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'emailpilot-438321')
                
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    initialize_app(cred, {'projectId': project_id})
                else:
                    initialize_app(options={'projectId': project_id})
                
                logger.info(f"Firebase initialized for project: {project_id}")
            
            self.db = firestore.client()
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    async def get_client_goals(self, client_id: str, year: Optional[int] = None, month: Optional[int] = None) -> List[Dict]:
        """Get goals for a specific client"""
        try:
            query = self.db.collection('goals').where('client_id', '==', client_id)
            
            if year:
                query = query.where('year', '==', year)
            if month:
                query = query.where('month', '==', month)
            
            docs = query.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            
            goals = []
            for doc in docs:
                goal_data = doc.to_dict()
                goal_data['id'] = doc.id
                goals.append(goal_data)
            
            return goals
            
        except Exception as e:
            logger.error(f"Error fetching goals for client {client_id}: {e}")
            return []
    
    async def get_current_month_goal(self, client_id: str) -> Optional[Dict]:
        """Get the current month's revenue goal for a client"""
        now = datetime.now()
        goals = await self.get_client_goals(client_id, year=now.year, month=now.month)
        
        if goals:
            return goals[0]  # Most recent goal for current month
        
        # If no current month goal, get the most recent goal
        all_goals = await self.get_client_goals(client_id)
        return all_goals[0] if all_goals else None
    
    async def calculate_goal_progress(self, client_id: str, goal: Dict) -> Dict:
        """Calculate progress toward goal based on calendar events"""
        try:
            # Get events for the goal period
            start_date = f"{goal['year']}-{goal['month']:02d}-01"
            
            # Get last day of month
            if goal['month'] == 12:
                next_month = datetime(goal['year'] + 1, 1, 1)
            else:
                next_month = datetime(goal['year'], goal['month'] + 1, 1)
            
            last_day = (next_month - timedelta(days=1)).day
            end_date = f"{goal['year']}-{goal['month']:02d}-{last_day:02d}"
            
            # Get calendar events for the period
            events = await self.get_client_events_for_goal_period(client_id, start_date, end_date)
            
            # Calculate estimated revenue based on events
            estimated_revenue = self._calculate_estimated_revenue_from_events(events)
            
            # Calculate progress
            goal_amount = goal.get('revenue_goal', 0)
            progress_percentage = min(100, (estimated_revenue / goal_amount) * 100) if goal_amount > 0 else 0
            
            # Calculate remaining days in month
            today = datetime.now()
            if today.year == goal['year'] and today.month == goal['month']:
                days_remaining = (next_month.date() - today.date()).days
            else:
                days_remaining = 0
            
            return {
                'goal_amount': goal_amount,
                'estimated_revenue': estimated_revenue,
                'progress_percentage': progress_percentage,
                'remaining_amount': max(0, goal_amount - estimated_revenue),
                'days_remaining': days_remaining,
                'campaign_count': len(events),
                'goal_period': f"{goal['year']}-{goal['month']:02d}",
                'is_on_track': progress_percentage >= (100 - (days_remaining / 30) * 100) if days_remaining > 0 else progress_percentage >= 100
            }
            
        except Exception as e:
            logger.error(f"Error calculating goal progress: {e}")
            return {
                'goal_amount': goal.get('revenue_goal', 0),
                'estimated_revenue': 0,
                'progress_percentage': 0,
                'remaining_amount': goal.get('revenue_goal', 0),
                'days_remaining': 0,
                'campaign_count': 0,
                'is_on_track': False
            }
    
    async def get_client_events_for_goal_period(self, client_id: str, start_date: str, end_date: str) -> List[Dict]:
        """Get calendar events for a specific goal period"""
        try:
            query = self.db.collection('calendar_events').where('client_id', '==', client_id)
            query = query.where('event_date', '>=', start_date)
            query = query.where('event_date', '<=', end_date)
            
            docs = query.order_by('event_date').stream()
            
            events = []
            for doc in docs:
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events for goal period: {e}")
            return []
    
    def _calculate_estimated_revenue_from_events(self, events: List[Dict]) -> float:
        """Calculate estimated revenue based on campaign events"""
        # Campaign type revenue multipliers based on historical performance
        campaign_multipliers = {
            'RRB Promotion': 850.0,      # High-converting promotional emails
            'Cheese Club': 450.0,        # Member-focused campaigns
            'Nurturing/Education': 280.0, # Educational content
            'Community/Lifestyle': 320.0, # Community building
            'Re-engagement': 180.0,      # Win-back campaigns
            'SMS Alert': 520.0,          # Time-sensitive alerts
            'Welcome Series': 380.0,     # New subscriber onboarding
            'Seasonal': 680.0,           # Seasonal promotions
            'Flash Sale': 920.0,         # Flash sales
            'Newsletter': 150.0          # Regular newsletters
        }
        
        total_estimated_revenue = 0
        
        for event in events:
            event_type = event.get('event_type', 'Newsletter')
            multiplier = campaign_multipliers.get(event_type, 200.0)  # Default multiplier
            
            # Adjust based on content quality indicators
            content = event.get('content', '').lower()
            title = event.get('title', '').lower()
            
            # Boost for high-value keywords
            if any(keyword in content or keyword in title for keyword in ['sale', 'discount', 'limited', 'exclusive', 'special']):
                multiplier *= 1.3
            
            # Boost for urgency indicators
            if any(keyword in content or keyword in title for keyword in ['today', 'now', 'hurry', 'ends']):
                multiplier *= 1.2
            
            total_estimated_revenue += multiplier
        
        return total_estimated_revenue
    
    async def get_goal_based_recommendations(self, client_id: str) -> Dict:
        """Get AI recommendations based on goals and current calendar"""
        try:
            current_goal = await self.get_current_month_goal(client_id)
            if not current_goal:
                return {'recommendations': [], 'message': 'No goals found for strategic recommendations'}
            
            progress = await self.calculate_goal_progress(client_id, current_goal)
            
            recommendations = []
            
            # Analyze goal achievement status
            if not progress['is_on_track']:
                gap = progress['remaining_amount']
                days_left = progress['days_remaining']
                
                # Calculate needed daily revenue
                if days_left > 0:
                    daily_needed = gap / days_left
                    
                    # Recommend high-converting campaign types
                    if daily_needed > 800:
                        recommendations.append({
                            'type': 'urgent_campaign',
                            'priority': 'high',
                            'campaign_type': 'Flash Sale',
                            'title': '⚡ Flash Sale Campaign',
                            'description': f'Launch a flash sale to generate ${daily_needed:.0f}/day. High-urgency campaigns can achieve ${920:.0f} average revenue.',
                            'suggested_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                            'estimated_impact': 920.0
                        })
                    
                    if daily_needed > 400:
                        recommendations.append({
                            'type': 'promotional_campaign',
                            'priority': 'medium',
                            'campaign_type': 'RRB Promotion',
                            'title': '🎯 Strategic Promotion',
                            'description': f'RRB promotional campaigns average ${850:.0f} revenue. Schedule 2-3 this week.',
                            'suggested_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                            'estimated_impact': 850.0
                        })
                    
                    recommendations.append({
                        'type': 'sms_campaign',
                        'priority': 'medium',
                        'campaign_type': 'SMS Alert',
                        'title': '📱 SMS Alert Campaign',
                        'description': f'SMS campaigns generate ${520:.0f} average revenue with high engagement.',
                        'suggested_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                        'estimated_impact': 520.0
                    })
            
            else:
                # On track - suggest optimization
                recommendations.append({
                    'type': 'optimization',
                    'priority': 'low',
                    'campaign_type': 'Community/Lifestyle',
                    'title': '🌟 Engagement Campaign',
                    'description': 'You\'re on track! Add community-building campaigns to strengthen relationships.',
                    'suggested_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                    'estimated_impact': 320.0
                })
            
            return {
                'goal_progress': progress,
                'recommendations': recommendations,
                'goal_info': current_goal,
                'message': f"Based on your ${progress['goal_amount']:.0f} goal, you need ${progress['remaining_amount']:.0f} more revenue in {progress['days_remaining']} days."
            }
            
        except Exception as e:
            logger.error(f"Error generating goal-based recommendations: {e}")
            return {'recommendations': [], 'message': 'Error generating recommendations'}
    
    async def create_goal_aware_event(self, event_data: Dict) -> str:
        """Create a calendar event with goal awareness"""
        try:
            # Get current goal for context
            client_id = event_data.get('client_id')
            current_goal = await self.get_current_month_goal(client_id)
            
            # Add goal context to event
            if current_goal:
                event_data['goal_context'] = {
                    'goal_id': current_goal.get('id'),
                    'goal_amount': current_goal.get('revenue_goal', 0),
                    'goal_period': f"{current_goal.get('year', 2025)}-{current_goal.get('month', 1):02d}"
                }
                
                # Suggest revenue-optimized campaign type if not specified
                if not event_data.get('event_type') and current_goal:
                    progress = await self.calculate_goal_progress(client_id, current_goal)
                    
                    if not progress['is_on_track']:
                        event_data['event_type'] = 'RRB Promotion'  # High-converting type
                        event_data['ai_suggested'] = True
                        event_data['suggestion_reason'] = 'High-converting campaign type suggested to help achieve revenue goal'
            
            # Add timestamps
            event_data['created_at'] = firestore.SERVER_TIMESTAMP
            event_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Create document
            doc_ref = self.db.collection('calendar_events').add(event_data)
            event_id = doc_ref[1].id
            
            logger.info(f"Created goal-aware event: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error creating goal-aware event: {e}")
            raise
    
    async def get_dashboard_summary(self, client_id: str) -> Dict:
        """Get comprehensive dashboard summary with goals and calendar"""
        try:
            current_goal = await self.get_current_month_goal(client_id)
            
            if not current_goal:
                return {
                    'has_goal': False,
                    'message': 'No revenue goals set for strategic planning'
                }
            
            progress = await self.calculate_goal_progress(client_id, current_goal)
            recommendations = await self.get_goal_based_recommendations(client_id)
            
            # Get upcoming events
            now = datetime.now()
            upcoming_events = await self.get_client_events_for_goal_period(
                client_id,
                now.strftime('%Y-%m-%d'),
                (now + timedelta(days=30)).strftime('%Y-%m-%d')
            )
            
            return {
                'has_goal': True,
                'goal': current_goal,
                'progress': progress,
                'recommendations': recommendations['recommendations'][:3],  # Top 3 recommendations
                'upcoming_campaigns': len(upcoming_events),
                'summary': {
                    'goal_status': 'On Track' if progress['is_on_track'] else 'Needs Attention',
                    'revenue_gap': progress['remaining_amount'],
                    'days_remaining': progress['days_remaining'],
                    'projected_success_rate': min(100, progress['progress_percentage'] + 20) if progress['campaign_count'] > 0 else 30
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard summary: {e}")
            return {
                'has_goal': False,
                'message': f'Error loading goal data: {e}'
            }

# Initialize enhanced service
firebase_goals_calendar = FirebaseGoalsCalendarService()