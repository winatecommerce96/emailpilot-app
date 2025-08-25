import os
from app.services.secrets import SecretManagerService, SecretNotFoundError

def check_secrets():
    """Checks for the required Google OAuth secrets."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ ERROR: GOOGLE_CLOUD_PROJECT environment variable is not set.")
        return

    print(f"✅ Found GOOGLE_CLOUD_PROJECT: {project_id}")
    
    required_secrets = [
        "google-oauth-client-id",
        "google-oauth-client-secret",
    ]
    
    secret_manager = SecretManagerService(project_id=project_id)
    all_secrets_found = True
    
    for secret_name in required_secrets:
        try:
            secret_value = secret_manager.get_secret(secret_name)
            if secret_value:
                print(f"✅ Successfully retrieved secret: {secret_name}")
            else:
                print(f"❌ ERROR: Secret '{secret_name}' is empty or could not be retrieved.")
                all_secrets_found = False
        except SecretNotFoundError:
            print(f"❌ ERROR: Secret '{secret_name}' not found in Secret Manager.")
            all_secrets_found = False
        except Exception as e:
            print(f"❌ ERROR: An unexpected error occurred while fetching secret '{secret_name}': {e}")
            all_secrets_found = False
            
    if all_secrets_found:
        print("\n✅ All required OAuth secrets are accessible.")
    else:
        print("\n❌ One or more required OAuth secrets are missing. Please check your Secret Manager configuration.")

if __name__ == "__main__":
    check_secrets()
