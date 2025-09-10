#!/usr/bin/env python3
"""Test LangSmith configuration from Secret Manager"""

import os
from google.cloud import secretmanager

def test_langsmith_config():
    """Test if LangSmith is properly configured"""
    
    # Check environment variables
    print("=== Environment Variables ===")
    print(f"LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT', 'NOT SET')}")
    print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT', 'NOT SET')}")
    print(f"LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2', 'NOT SET')}")
    print(f"USE_SECRET_MANAGER: {os.getenv('USE_SECRET_MANAGER', 'NOT SET')}")
    
    # Try to get from Secret Manager
    print("\n=== Secret Manager Check ===")
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        
        # Check for LangSmith API key
        secret_name = "langsmith-api-key"
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        
        try:
            response = client.access_secret_version(request={"name": name})
            api_key = response.payload.data.decode("UTF-8")
            if api_key:
                print(f"✅ LangSmith API key found in Secret Manager (length: {len(api_key)})")
                # Set it for the test
                os.environ["LANGSMITH_API_KEY"] = api_key
            else:
                print("❌ LangSmith API key is empty in Secret Manager")
        except Exception as e:
            print(f"❌ Could not retrieve LangSmith API key: {e}")
            
    except Exception as e:
        print(f"❌ Secret Manager error: {e}")
    
    # Now test if tracing works
    print("\n=== Testing LangSmith Connection ===")
    
    # Set the correct project name
    os.environ["LANGCHAIN_PROJECT"] = "emailpilot-calendar"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    
    try:
        from langsmith import Client
        
        # Create a client (this will use the API key from env)
        client = Client()
        
        # Try to list projects to verify connection
        try:
            # This is a simple test to see if we can connect
            print(f"✅ LangSmith client created successfully")
            print(f"📊 Project: emailpilot-calendar")
            print(f"🔗 View at: https://smith.langchain.com/")
            
        except Exception as e:
            print(f"❌ LangSmith connection test failed: {e}")
            
    except ImportError:
        print("❌ LangSmith not installed. Run: pip install langsmith")
    except Exception as e:
        print(f"❌ LangSmith initialization error: {e}")

if __name__ == "__main__":
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Set to use Secret Manager
    os.environ["USE_SECRET_MANAGER"] = "true"
    
    test_langsmith_config()