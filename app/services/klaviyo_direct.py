"""
Direct Klaviyo API integration service
Replaces MCP service for direct API calls
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class KlaviyoDirectService:
    """Direct Klaviyo API client"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://a.klaviyo.com/api"
        self.headers = {
            'Authorization': f'Klaviyo-API-Key {api_key}',
            'Accept': 'application/json',
            'revision': '2024-10-15'
        }
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            response = requests.get(
                f"{self.base_url}/accounts/",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                accounts = data.get('data', [])
                if accounts:
                    return accounts[0].get('attributes', {})
            return {}
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def get_campaigns(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get campaigns for date range"""
        try:
            # No pagination params for campaigns endpoint
            params = {}
            
            response = requests.get(
                f"{self.base_url}/campaigns/",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                campaigns = data.get('data', [])
                
                # Filter by date in Python since Klaviyo filter syntax is complex
                filtered_campaigns = []
                for campaign in campaigns:
                    created = campaign.get('attributes', {}).get('created_at')
                    if created:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        if start_date <= created_dt <= end_date:
                            filtered_campaigns.append(campaign)
                
                return {
                    'campaigns': filtered_campaigns,
                    'total': len(filtered_campaigns)
                }
            else:
                logger.error(f"Error getting campaigns: {response.status_code} - {response.text}")
                return {'campaigns': [], 'total': 0}
                
        except Exception as e:
            logger.error(f"Error fetching campaigns: {e}")
            return {'campaigns': [], 'total': 0}
    
    def get_flows(self) -> Dict[str, Any]:
        """Get active flows"""
        try:
            params = {}
            
            response = requests.get(
                f"{self.base_url}/flows/",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                flows = data.get('data', [])
                
                # Filter for active flows
                active_flows = [f for f in flows if f.get('attributes', {}).get('status') == 'live']
                
                return {
                    'flows': active_flows,
                    'total': len(active_flows)
                }
            else:
                logger.error(f"Error getting flows: {response.status_code}")
                return {'flows': [], 'total': 0}
                
        except Exception as e:
            logger.error(f"Error fetching flows: {e}")
            return {'flows': [], 'total': 0}
    
    def get_metrics(self, metric_ids: List[str], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get metrics for specific metric IDs"""
        try:
            # For now, return mock data since metrics API is complex
            # In production, implement proper metrics aggregation
            return {
                'total_revenue': 0,
                'total_orders': 0,
                'emails_sent': 0,
                'emails_opened': 0,
                'emails_clicked': 0
            }
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return {
                'total_revenue': 0,
                'total_orders': 0,
                'emails_sent': 0,
                'emails_opened': 0,
                'emails_clicked': 0
            }