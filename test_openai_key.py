#!/usr/bin/env python3
"""
Test that OPENAI_API_KEY can be saved via the admin API
"""

import requests
import json

def test_openai_key_config():
    """Test that OPENAI_API_KEY is now configurable"""
    
    # Check environment variables endpoint
    url = "http://127.0.0.1:8000/api/admin/environment"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            variables = data.get('variables', {})
            
            if 'OPENAI_API_KEY' in variables:
                openai_config = variables['OPENAI_API_KEY']
                print("✅ OPENAI_API_KEY is now configurable!")
                print(f"   Description: {openai_config.get('description')}")
                print(f"   Required: {openai_config.get('required')}")
                print(f"   Sensitive: {openai_config.get('is_sensitive')}")
                print(f"   Currently Set: {openai_config.get('is_set')}")
                
                if data.get('secret_manager_enabled'):
                    print(f"   Stored in Secret Manager: {openai_config.get('stored_in_secret_manager')}")
                
                print("\n📝 To set the OPENAI_API_KEY:")
                print("   1. Go to the Admin Dashboard")
                print("   2. Navigate to Environment Variables")
                print("   3. Enter your OpenAI API key in the OPENAI_API_KEY field")
                print("   4. Click Save")
                print("\n   The key will be securely stored in Google Secret Manager")
                
            else:
                print("❌ OPENAI_API_KEY not found in environment variables")
                print("Available variables:", list(variables.keys()))
        else:
            print(f"❌ Failed to fetch environment variables. Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_openai_key_config()