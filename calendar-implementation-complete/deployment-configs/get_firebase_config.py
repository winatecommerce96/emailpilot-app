#!/usr/bin/env python3
"""
Get Firebase configuration for web client
"""

import json
import os
from google.oauth2 import service_account
import google.auth.transport.requests
import requests

def get_firebase_web_config():
    """Get Firebase web configuration"""
    
    # Path to your service account key
    service_account_path = "/Users/Damon/Downloads/emailpilot-438321-6335761b472e.json"
    project_id = "emailpilot-438321"
    
    if not os.path.exists(service_account_path):
        print("Service account file not found")
        return None
    
    try:
        # Load service account
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Get access token
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        # Call Firebase API to get web config
        url = f"https://firebase.googleapis.com/v1beta1/projects/{project_id}/webApps"
        headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        print(f"Web apps response: {response.status_code}")
        
        if response.status_code == 200:
            apps_data = response.json()
            print("Web apps found:", json.dumps(apps_data, indent=2))
            
            if 'apps' in apps_data and len(apps_data['apps']) > 0:
                app_id = apps_data['apps'][0]['appId']
                
                # Get config for the first web app
                config_url = f"https://firebase.googleapis.com/v1beta1/projects/{project_id}/webApps/{app_id}/config"
                config_response = requests.get(config_url, headers=headers)
                
                if config_response.status_code == 200:
                    config_data = config_response.json()
                    print("Firebase config:", json.dumps(config_data, indent=2))
                    return config_data
        
        # If no web app exists, try to get project info
        project_url = f"https://firebase.googleapis.com/v1beta1/projects/{project_id}"
        project_response = requests.get(project_url, headers=headers)
        
        if project_response.status_code == 200:
            project_data = project_response.json()
            print("Project info:", json.dumps(project_data, indent=2))
            
            # Create a basic config
            return {
                "apiKey": "AIzaSyB0RrH7hbER2R-SzXfNmFe0O32HhH7HBEM",  # You may need to get this from console
                "authDomain": f"{project_id}.firebaseapp.com",
                "projectId": project_id,
                "storageBucket": f"{project_id}.appspot.com",
                "messagingSenderId": "104067375141",
                "appId": "1:104067375141:web:2b65c86eec8e8c8b4c9f3a"
            }
        
    except Exception as e:
        print(f"Error getting Firebase config: {e}")
        return None
    
    return None

if __name__ == "__main__":
    config = get_firebase_web_config()
    if config:
        print("\nUse this Firebase config:")
        print(json.dumps(config, indent=2))
    else:
        print("Could not retrieve Firebase config")
        
        # Provide fallback info
        print("\nYou may need to:")
        print("1. Go to Firebase Console: https://console.firebase.google.com/")
        print("2. Select your project: emailpilot-438321")
        print("3. Go to Project Settings > General")
        print("4. Scroll down to 'Your apps' section")
        print("5. Create a web app if none exists")
        print("6. Copy the Firebase configuration from there")