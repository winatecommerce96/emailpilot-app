#!/usr/bin/env python3
"""
Test script to verify Secret Manager LLM API key retrieval
"""
import os
import sys

def test_secret_manager_keys():
    """Test retrieving API keys from Secret Manager"""
    print("\n" + "="*70)
    print("SECRET MANAGER API KEY TEST")
    print("="*70 + "\n")
    
    # Set project ID
    os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"
    
    try:
        from app.services.secret_manager import SecretManagerService
        
        # Initialize Secret Manager
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        secret_manager = SecretManagerService(project_id)
        
        print(f"✅ Connected to Secret Manager (project: {project_id})\n")
        
        # Test retrieving each API key
        keys_to_test = [
            ("OPENAI_API_KEY", "openai-api-key"),
            ("ANTHROPIC_API_KEY", "emailpilot-claude"),
            ("GOOGLE_API_KEY", "gemini-api-key")
        ]
        
        found_keys = []
        
        for key_name, secret_name in keys_to_test:
            print(f"Testing {key_name} (secret: {secret_name})...")
            
            try:
                api_key = secret_manager.get_ai_provider_key(key_name)
                
                if api_key:
                    # Only show first and last few characters for security
                    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 10 else "***"
                    print(f"  ✅ Found: {masked}")
                    
                    # Validate format
                    validation = secret_manager.validate_ai_provider_key(key_name)
                    if validation["valid"]:
                        print(f"  ✅ Valid format: {validation['message']}")
                    else:
                        print(f"  ⚠️ Invalid format: {validation['message']}")
                        print(f"     Hint: {validation['hint']}")
                    
                    found_keys.append(key_name)
                else:
                    print(f"  ❌ Not found in Secret Manager or environment")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            print()
        
        # Summary
        print("="*70)
        print("SUMMARY")
        print("="*70)
        
        if found_keys:
            print(f"\n✅ Found {len(found_keys)} API key(s):")
            for key in found_keys:
                print(f"  • {key}")
            print("\nThe IntegratedCalendarSystem will use these keys automatically.")
        else:
            print("\n⚠️ No API keys found!")
            print("\nTo fix this, add keys to Secret Manager:")
            print("  • OpenAI: gcloud secrets create openai-api-key --data-file=-")
            print("  • Anthropic: gcloud secrets create emailpilot-claude --data-file=-")
            print("  • Google: gcloud secrets create gemini-api-key --data-file=-")
        
        # Test with IntegratedCalendarSystem
        print("\n" + "="*70)
        print("TESTING WITH INTEGRATED CALENDAR SYSTEM")
        print("="*70 + "\n")
        
        from integrated_calendar_system import IntegratedCalendarSystem
        
        system = IntegratedCalendarSystem()
        
        if system.llm_config.get("api_key"):
            print(f"✅ IntegratedCalendarSystem configured with {system.llm_config['provider']}")
            
            # Test a simple LLM call
            response = system.call_llm_locally(
                prompt="Say 'API keys working!' in exactly 3 words",
                variables={}
            )
            print(f"\nTest LLM Response: {response}")
        else:
            print("❌ IntegratedCalendarSystem could not find API keys")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nMake sure you're in the emailpilot-app directory and have installed requirements.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_secret_manager_keys()