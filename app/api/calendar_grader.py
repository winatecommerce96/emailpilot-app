"""
Calendar Grader API - Grades campaign calendars against revenue goals and best practices.
Uses the campaign_grader LangChain agent for AI-powered analysis.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar-grading"])


class CalendarGradeRequest(BaseModel):
    """Request model for grading a calendar."""
    campaigns: List[Dict[str, Any]]  # Current campaign calendar
    revenue_goal: float  # Monthly revenue target
    client_name: Optional[str] = None
    client_id: Optional[str] = None
    historical_performance: Optional[Dict[str, Any]] = None
    original_campaigns: Optional[List[Dict[str, Any]]] = None  # For comparison
    industry_type: Optional[str] = None
    audience_segments: Optional[List[str]] = None


class CalendarGradeResponse(BaseModel):
    """Response model for calendar grading."""
    overall_grade: str  # A+, A, B, C, D, F
    score: float  # 0-100
    revenue_score: Dict[str, Any]  # Detailed revenue analysis
    timing_score: Dict[str, Any]  # Timing and spacing analysis
    fatigue_score: Dict[str, Any]  # Audience fatigue analysis
    historical_score: Dict[str, Any]  # Historical alignment
    recommendations: List[Dict[str, Any]]  # Top recommendations
    insights: List[str]  # AI insights
    comparison: Optional[Dict[str, Any]] = None  # If original provided


class GradeCalculator:
    """Calculate grades for campaign calendars."""
    
    @staticmethod
    def calculate_revenue_score(campaigns: List[Dict], revenue_goal: float) -> Dict[str, Any]:
        """Calculate revenue alignment score (40 points max)."""
        total_revenue = sum(
            c.get('expected_metrics', {}).get('revenue', 0) or 
            c.get('metrics', {}).get('revenue', 0) 
            for c in campaigns
        )
        
        if revenue_goal > 0:
            achievement_rate = total_revenue / revenue_goal
            if achievement_rate >= 1.0:
                points = 40
            elif achievement_rate >= 0.9:
                points = 35
            elif achievement_rate >= 0.8:
                points = 30
            elif achievement_rate >= 0.7:
                points = 25
            elif achievement_rate >= 0.6:
                points = 20
            else:
                points = int(achievement_rate * 30)
        else:
            points = 20  # Default if no goal set
        
        gap = revenue_goal - total_revenue if revenue_goal > 0 else 0
        
        recommendations = []
        if gap > 0:
            campaigns_needed = int(gap / 5000)  # Assume $5k per campaign average
            recommendations.append(f"Add {campaigns_needed} more high-value campaigns to close revenue gap")
        
        return {
            "points": points,
            "max_points": 40,
            "projected_revenue": total_revenue,
            "goal": revenue_goal,
            "gap": gap,
            "achievement_rate": (total_revenue / revenue_goal * 100) if revenue_goal > 0 else 0,
            "recommendations": recommendations
        }
    
    @staticmethod
    def calculate_timing_score(campaigns: List[Dict]) -> Dict[str, Any]:
        """Calculate timing and spacing score (20 points max)."""
        if not campaigns:
            return {
                "points": 10,
                "max_points": 20,
                "issues": ["No campaigns scheduled"],
                "recommendations": ["Add campaigns to the calendar"]
            }
        
        # Sort campaigns by date
        sorted_campaigns = sorted(campaigns, key=lambda x: x.get('date', ''))
        
        # Check spacing between campaigns
        issues = []
        clustering_penalty = 0
        perfect_spacing_bonus = 0
        
        for i in range(len(sorted_campaigns) - 1):
            current_date = sorted_campaigns[i].get('date')
            next_date = sorted_campaigns[i + 1].get('date')
            
            if current_date and next_date:
                # Parse dates (handle both string and datetime)
                try:
                    if isinstance(current_date, str):
                        # Handle ISO format and remove timezone if present
                        current_str = current_date.replace('Z', '').split('+')[0].split('.')[0]
                        current = datetime.fromisoformat(current_str)
                    else:
                        current = current_date
                        
                    if isinstance(next_date, str):
                        # Handle ISO format and remove timezone if present
                        next_str = next_date.replace('Z', '').split('+')[0].split('.')[0]
                        next_dt = datetime.fromisoformat(next_str)
                    else:
                        next_dt = next_date
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Date parsing error: {e}")
                    continue
                
                days_apart = (next_dt - current).days
                
                if days_apart == 0:
                    issues.append(f"Multiple campaigns on same day")
                    clustering_penalty += 3
                elif days_apart == 1:
                    issues.append(f"Campaigns too close (1 day apart)")
                    clustering_penalty += 2
                elif days_apart >= 3 and days_apart <= 4:
                    perfect_spacing_bonus += 1
                elif days_apart > 7:
                    issues.append(f"Large gap ({days_apart} days) between campaigns")
                    clustering_penalty += 1
        
        # Calculate points
        base_points = 20
        points = max(0, base_points - clustering_penalty + min(perfect_spacing_bonus, 5))
        
        recommendations = []
        if clustering_penalty > 0:
            recommendations.append("Space campaigns at least 3-4 days apart for optimal engagement")
        if len(sorted_campaigns) < 8:
            recommendations.append("Consider adding more campaigns for consistent touchpoints")
        
        # Calculate campaign density safely
        campaign_density = len(campaigns) / 4.0 if len(campaigns) > 0 else 0
        
        return {
            "points": points,
            "max_points": 20,
            "campaign_density": campaign_density,  # Per week
            "issues": issues,
            "recommendations": recommendations
        }
    
    @staticmethod
    def calculate_fatigue_score(campaigns: List[Dict]) -> Dict[str, Any]:
        """Calculate audience fatigue prevention score (20 points max)."""
        segment_counts = {}
        channel_counts = {"email": 0, "sms": 0}
        type_counts = {}
        
        for campaign in campaigns:
            # Count segments
            segment = campaign.get('segment', 'all')
            segment_counts[segment] = segment_counts.get(segment, 0) + 1
            
            # Count channels
            channel = campaign.get('channel', 'email')
            if channel in channel_counts:
                channel_counts[channel] += 1
            
            # Count types
            camp_type = campaign.get('type', 'promotional')
            type_counts[camp_type] = type_counts.get(camp_type, 0) + 1
        
        # Calculate penalties
        penalty = 0
        issues = []
        
        # Check for segment over-use
        for segment, count in segment_counts.items():
            if count > 4:  # More than weekly
                penalty += 3
                issues.append(f"Segment '{segment}' receives {count} campaigns (too many)")
        
        # Check channel balance
        total_campaigns = len(campaigns)
        if total_campaigns > 0:
            email_ratio = channel_counts['email'] / total_campaigns
            if email_ratio == 1.0:
                penalty += 2
                issues.append("No SMS campaigns for channel diversity")
            elif email_ratio < 0.7:
                penalty += 1
                issues.append("Too many SMS campaigns relative to email")
        
        # Check type variety
        if len(type_counts) < 3 and total_campaigns > 5:
            penalty += 2
            issues.append("Limited campaign type variety")
        
        points = max(0, 20 - penalty)
        
        recommendations = []
        if 'all' in segment_counts and segment_counts['all'] > 2:
            recommendations.append("Use more targeted segments instead of 'all'")
        if channel_counts['sms'] == 0:
            recommendations.append("Add SMS campaigns for multi-channel engagement")
        
        return {
            "points": points,
            "max_points": 20,
            "segment_distribution": segment_counts,
            "channel_distribution": channel_counts,
            "type_distribution": type_counts,
            "issues": issues,
            "recommendations": recommendations
        }
    
    @staticmethod
    def calculate_historical_score(campaigns: List[Dict], historical: Optional[Dict] = None) -> Dict[str, Any]:
        """Calculate historical alignment score (20 points max)."""
        if not historical:
            # No historical data, give neutral score
            return {
                "points": 10,
                "max_points": 20,
                "comparison": "No historical data available",
                "recommendations": ["Collect more historical data for better optimization"]
            }
        
        # Compare patterns (simplified for now)
        current_count = len(campaigns)
        historical_avg = historical.get('average_campaigns_per_month', 10)
        
        count_diff = abs(current_count - historical_avg)
        
        if count_diff <= 2:
            points = 20
            comparison = "Excellent alignment with historical patterns"
        elif count_diff <= 4:
            points = 15
            comparison = "Good alignment with historical patterns"
        elif count_diff <= 6:
            points = 10
            comparison = "Moderate deviation from historical patterns"
        else:
            points = 5
            comparison = "Significant deviation from historical patterns"
        
        recommendations = []
        if current_count < historical_avg - 2:
            recommendations.append(f"Consider adding {historical_avg - current_count} more campaigns to match historical success")
        elif current_count > historical_avg + 2:
            recommendations.append(f"Consider reducing by {current_count - historical_avg} campaigns to avoid over-messaging")
        
        return {
            "points": points,
            "max_points": 20,
            "comparison": comparison,
            "current_count": current_count,
            "historical_average": historical_avg,
            "recommendations": recommendations
        }
    
    @staticmethod
    def get_letter_grade(score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 65:
            return "D+"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    @staticmethod
    def generate_insights(scores: Dict[str, Dict]) -> List[str]:
        """Generate AI insights based on scores."""
        insights = []
        
        # Revenue insights
        if scores['revenue']['achievement_rate'] > 110:
            insights.append("📈 Exceptional revenue projection! Consider testing premium offerings.")
        elif scores['revenue']['achievement_rate'] < 70:
            insights.append("⚠️ Revenue at risk. Focus on high-value segments and proven campaigns.")
        
        # Timing insights
        if 'campaign_density' in scores['timing'] and scores['timing']['campaign_density'] > 3:
            insights.append("🔥 High campaign frequency detected. Monitor unsubscribe rates closely.")
        elif 'campaign_density' in scores['timing'] and scores['timing']['campaign_density'] < 1.5:
            insights.append("💡 Opportunity for more touchpoints. Add mid-week engagement campaigns.")
        
        # Fatigue insights
        if len(scores['fatigue']['segment_distribution']) == 1:
            insights.append("🎯 Diversify your audience targeting to prevent list fatigue.")
        
        # General optimization
        total_score = sum(s['points'] for s in scores.values())
        if total_score >= 85:
            insights.append("⭐ Calendar is well-optimized. Test innovative campaign types.")
        elif total_score <= 60:
            insights.append("🔄 Major optimization needed. Consider using AI campaign suggestions.")
        
        return insights


@router.post("/grade", response_model=CalendarGradeResponse)
async def grade_calendar(request: CalendarGradeRequest):
    """
    Grade a campaign calendar against revenue goals and best practices.
    
    This endpoint analyzes the calendar and provides:
    - Overall letter grade and numeric score
    - Detailed scoring breakdown
    - Actionable recommendations
    - AI-powered insights
    """
    try:
        logger.info(f"Grading calendar for client: {request.client_name}")
        
        calculator = GradeCalculator()
        
        # Calculate individual scores
        revenue_score = calculator.calculate_revenue_score(
            request.campaigns, 
            request.revenue_goal
        )
        timing_score = calculator.calculate_timing_score(request.campaigns)
        fatigue_score = calculator.calculate_fatigue_score(request.campaigns)
        historical_score = calculator.calculate_historical_score(
            request.campaigns, 
            request.historical_performance
        )
        
        # Calculate total score
        total_score = (
            revenue_score['points'] + 
            timing_score['points'] + 
            fatigue_score['points'] + 
            historical_score['points']
        )
        
        # Get letter grade
        letter_grade = calculator.get_letter_grade(total_score)
        
        # Compile all recommendations
        all_recommendations = []
        
        # Add revenue recommendations
        for rec in revenue_score.get('recommendations', []):
            all_recommendations.append({
                "category": "Revenue",
                "priority": 1,
                "recommendation": rec,
                "impact": "high"
            })
        
        # Add timing recommendations
        for rec in timing_score.get('recommendations', []):
            all_recommendations.append({
                "category": "Timing",
                "priority": 2,
                "recommendation": rec,
                "impact": "medium"
            })
        
        # Add fatigue recommendations
        for rec in fatigue_score.get('recommendations', []):
            all_recommendations.append({
                "category": "Audience",
                "priority": 2,
                "recommendation": rec,
                "impact": "medium"
            })
        
        # Add historical recommendations
        for rec in historical_score.get('recommendations', []):
            all_recommendations.append({
                "category": "Historical",
                "priority": 3,
                "recommendation": rec,
                "impact": "low"
            })
        
        # Sort recommendations by priority
        all_recommendations.sort(key=lambda x: x['priority'])
        
        # Generate insights
        scores_dict = {
            'revenue': revenue_score,
            'timing': timing_score,
            'fatigue': fatigue_score,
            'historical': historical_score
        }
        insights = calculator.generate_insights(scores_dict)
        
        # Handle comparison if original campaigns provided
        comparison = None
        if request.original_campaigns:
            # Calculate original score
            orig_revenue = calculator.calculate_revenue_score(
                request.original_campaigns, 
                request.revenue_goal
            )
            orig_timing = calculator.calculate_timing_score(request.original_campaigns)
            orig_fatigue = calculator.calculate_fatigue_score(request.original_campaigns)
            orig_historical = calculator.calculate_historical_score(
                request.original_campaigns, 
                request.historical_performance
            )
            
            orig_total = (
                orig_revenue['points'] + 
                orig_timing['points'] + 
                orig_fatigue['points'] + 
                orig_historical['points']
            )
            
            comparison = {
                "original_score": orig_total,
                "current_score": total_score,
                "improvement": total_score - orig_total,
                "original_grade": calculator.get_letter_grade(orig_total),
                "current_grade": letter_grade,
                "changes_impact": "positive" if total_score > orig_total else "negative"
            }
        
        return CalendarGradeResponse(
            overall_grade=letter_grade,
            score=total_score,
            revenue_score=revenue_score,
            timing_score=timing_score,
            fatigue_score=fatigue_score,
            historical_score=historical_score,
            recommendations=all_recommendations[:5],  # Top 5 recommendations
            insights=insights,
            comparison=comparison
        )
        
    except Exception as e:
        logger.error(f"Calendar grading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grade/health")
async def health_check():
    """Health check endpoint for calendar grading API."""
    return {"status": "healthy", "service": "calendar-grading"}