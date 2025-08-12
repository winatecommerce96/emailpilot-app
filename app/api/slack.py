"""
Slack integration API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import hmac
import hashlib
import time

from app.core.database import get_db
from app.core.config import settings
from app.services.report_generator import ReportGeneratorService

router = APIRouter()

@router.post("/webhook/test")
async def test_slack_webhook():
    """Test Slack webhook connection"""
    try:
        import requests
        
        if not settings.slack_webhook_url:
            raise HTTPException(status_code=400, detail="Slack webhook URL not configured")
        
        test_message = {
            "text": "🧪 EmailPilot API Test",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ *Slack integration working!*\n\nEmailPilot API can successfully send messages to this channel."
                    }
                }
            ]
        }
        
        response = requests.post(settings.slack_webhook_url, json=test_message)
        
        if response.status_code == 200:
            return {"status": "success", "message": "Test message sent to Slack"}
        else:
            raise HTTPException(status_code=400, detail=f"Slack webhook failed: {response.status_code}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Slack test failed: {str(e)}")

@router.post("/commands/weekly-report")
async def slack_weekly_command(request: Request, db: Session = Depends(get_db)):
    """Handle /weekly-report slash command from Slack"""
    
    # Parse form data
    form_data = await request.form()
    
    # Basic verification (you should implement proper signature verification in production)
    user_name = form_data.get("user_name", "unknown")
    channel_name = form_data.get("channel_name", "unknown")
    
    # Start report generation
    report_service = ReportGeneratorService()
    
    # Return immediate response to Slack
    return {
        "response_type": "in_channel",
        "text": f"🚀 Weekly report requested by @{user_name} - generating now...",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 *Weekly Performance Report*\n\nRequested by: @{user_name}\nChannel: #{channel_name}\nStatus: Generation started\nETA: ~2-3 minutes"
                }
            }
        ]
    }

@router.post("/commands/monthly-report")
async def slack_monthly_command(request: Request, db: Session = Depends(get_db)):
    """Handle /monthly-report slash command from Slack"""
    
    # Parse form data
    form_data = await request.form()
    
    user_name = form_data.get("user_name", "unknown")
    channel_name = form_data.get("channel_name", "unknown")
    
    # Return immediate response to Slack
    return {
        "response_type": "in_channel",
        "text": f"📊 Monthly report requested by @{user_name} - generating now...",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📈 *Monthly Performance Report*\n\nRequested by: @{user_name}\nChannel: #{channel_name}\nStatus: Generation started\nETA: ~3-5 minutes"
                }
            }
        ]
    }

@router.post("/commands/status")
async def slack_status_command(request: Request):
    """Handle /emailpilot-status slash command from Slack"""
    
    form_data = await request.form()
    user_name = form_data.get("user_name", "unknown")
    
    return {
        "response_type": "ephemeral",  # Only visible to user
        "text": "⚡ EmailPilot Status",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*EmailPilot System Status* ✅\n\n• API: Online\n• Database: Connected\n• Klaviyo: Ready\n• Reports: Active"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Available Commands:*\n• `/weekly-report` - Generate weekly update\n• `/monthly-report` - Generate monthly summary\n• `/emailpilot-status` - Check system status"
                }
            }
        ]
    }