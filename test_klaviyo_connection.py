"""
API endpoint to test Klaviyo connection for unified client form
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
import requests
import logging

logger = logging.getLogger(__name__)

async def test_klaviyo_connection(api_key: str) -> Dict[str, Any]:
    """
    Test Klaviyo API connection with provided key
    """
    try:
        # Test with Klaviyo API v3 (latest)
        headers = {
            'Authorization': f'Klaviyo-API-Key {api_key}',
            'Accept': 'application/json',
            'revision': '2024-10-15'
        }
        
        # Try to get account info
        response = requests.get(
            'https://a.klaviyo.com/api/accounts/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            account_info = data.get('data', [])
            if account_info:
                account = account_info[0]
                return {
                    'success': True,
                    'message': f"Connected to: {account.get('attributes', {}).get('test_account', {}).get('company_name', 'Unknown')}",
                    'account_id': account.get('id'),
                    'details': account.get('attributes', {})
                }
            return {
                'success': True,
                'message': 'Connection successful - API key is valid'
            }
        elif response.status_code == 401:
            return {
                'success': False,
                'message': 'Invalid API key - please check your Klaviyo private key'
            }
        elif response.status_code == 403:
            return {
                'success': False,
                'message': 'API key lacks required permissions'
            }
        else:
            return {
                'success': False,
                'message': f'Connection failed with status {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'message': 'Connection timeout - Klaviyo API is not responding'
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'message': 'Connection error - unable to reach Klaviyo API'
        }
    except Exception as e:
        logger.error(f"Error testing Klaviyo connection: {e}")
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }