"""
Enhanced Environment Manager with Secret Manager Integration
Handles both local .env file and Google Secret Manager for sensitive keys
"""
import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Define which variables should be stored in Secret Manager
SENSITIVE_VARS = {
    'SLACK_WEBHOOK_URL',
    'GEMINI_API_KEY',
    'OPENAI_API_KEY',
    'KLAVIYO_PRIVATE_KEY',
    'FIREBASE_API_KEY'
}

# Variables that should persist locally
LOCAL_VARS = {
    'ENVIRONMENT',
    'DEBUG',
    'GOOGLE_CLOUD_PROJECT',
    'GOOGLE_APPLICATION_CREDENTIALS',
    'SECRET_MANAGER_ENABLED'
}


class EnvManager:
    """Manages environment variables with Secret Manager integration"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        self.use_secret_manager = os.getenv("SECRET_MANAGER_ENABLED", "true").lower() == "true"
        self.env_file_path = Path(__file__).parent.parent.parent / ".env"
        self.secret_manager = None
        
        # Initialize Secret Manager if enabled
        if self.use_secret_manager:
            try:
                from app.services.secret_manager import SecretManagerService
                self.secret_manager = SecretManagerService(self.project_id)
                logger.info("Secret Manager initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize Secret Manager: {e}")
                self.use_secret_manager = False
    
    def load_all_vars(self) -> Dict[str, str]:
        """Load all environment variables from both sources"""
        env_vars = {}
        
        # Load local .env file
        local_vars = self._load_env_file()
        env_vars.update(local_vars)
        
        # Load sensitive vars from Secret Manager
        if self.use_secret_manager and self.secret_manager:
            for var_name in SENSITIVE_VARS:
                try:
                    secret_value = self.secret_manager.get_secret(var_name.lower().replace('_', '-'))
                    if secret_value:
                        env_vars[var_name] = secret_value
                        # Also set in current process
                        os.environ[var_name] = secret_value
                except Exception as e:
                    logger.debug(f"Secret {var_name} not found in Secret Manager: {e}")
        
        return env_vars
    
    def get_var(self, key: str) -> Optional[str]:
        """Get a single environment variable from appropriate source"""
        # Check current environment first
        value = os.getenv(key)
        if value:
            return value
        
        # Check Secret Manager for sensitive vars
        if key in SENSITIVE_VARS and self.use_secret_manager and self.secret_manager:
            try:
                secret_id = key.lower().replace('_', '-')
                value = self.secret_manager.get_secret(secret_id)
                if value:
                    # Cache in environment for this session
                    os.environ[key] = value
                    return value
            except Exception as e:
                logger.debug(f"Could not get secret {key}: {e}")
        
        # Check local .env file
        local_vars = self._load_env_file()
        return local_vars.get(key)
    
    def set_var(self, key: str, value: str) -> bool:
        """Set an environment variable in appropriate storage"""
        try:
            # Always set in current process
            os.environ[key] = value
            
            # Store sensitive vars in Secret Manager
            if key in SENSITIVE_VARS and self.use_secret_manager and self.secret_manager:
                try:
                    secret_id = key.lower().replace('_', '-')
                    self.secret_manager.create_secret(secret_id, value)
                    logger.info(f"Stored {key} in Secret Manager")
                    
                    # Also save a placeholder in .env file
                    self._update_env_file({key: "***STORED_IN_SECRET_MANAGER***"})
                    return True
                except Exception as e:
                    logger.error(f"Failed to store {key} in Secret Manager: {e}")
                    # Fall back to local storage
                    self._update_env_file({key: value})
                    return True
            else:
                # Store non-sensitive vars locally
                self._update_env_file({key: value})
                return True
                
        except Exception as e:
            logger.error(f"Failed to set environment variable {key}: {e}")
            return False
    
    def update_vars(self, vars_dict: Dict[str, str]) -> Dict[str, bool]:
        """Update multiple environment variables"""
        results = {}
        for key, value in vars_dict.items():
            results[key] = self.set_var(key, value)
        return results
    
    def _load_env_file(self) -> Dict[str, str]:
        """Load variables from local .env file"""
        env_vars = {}
        
        if self.env_file_path.exists():
            try:
                with open(self.env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            value = value.strip('"').strip("'")
                            # Don't load placeholder values
                            if value != "***STORED_IN_SECRET_MANAGER***":
                                env_vars[key.strip()] = value.strip()
            except Exception as e:
                logger.error(f"Error reading .env file: {e}")
        
        return env_vars
    
    def _update_env_file(self, updates: Dict[str, str]):
        """Update the local .env file"""
        # Load existing vars
        existing_vars = self._load_env_file()
        
        # Update with new values
        existing_vars.update(updates)
        
        # Write back to file
        try:
            with open(self.env_file_path, 'w') as f:
                f.write("# EmailPilot Environment Configuration\n")
                f.write(f"# Last updated: {datetime.now().isoformat()}\n")
                f.write("# This file is automatically managed by the Admin interface\n")
                f.write("# Sensitive variables are stored in Google Secret Manager\n\n")
                
                # Write local vars first
                for key in sorted(LOCAL_VARS):
                    if key in existing_vars:
                        value = existing_vars[key]
                        if ' ' in value or ',' in value or '#' in value:
                            value = f'"{value}"'
                        f.write(f"{key}={value}\n")
                
                f.write("\n# Sensitive variables (stored in Secret Manager)\n")
                
                # Write sensitive vars (as placeholders or values)
                for key in sorted(SENSITIVE_VARS):
                    if key in updates:
                        value = updates[key]
                        if value == "***STORED_IN_SECRET_MANAGER***":
                            f.write(f"# {key}={value}\n")
                        else:
                            # Only write actual value if Secret Manager not available
                            if not self.use_secret_manager:
                                if ' ' in value or ',' in value or '#' in value:
                                    value = f'"{value}"'
                                f.write(f"{key}={value}\n")
                            else:
                                f.write(f"# {key}=***STORED_IN_SECRET_MANAGER***\n")
                
                # Write any other vars
                f.write("\n# Other variables\n")
                for key in sorted(existing_vars.keys()):
                    if key not in LOCAL_VARS and key not in SENSITIVE_VARS:
                        value = existing_vars[key]
                        if ' ' in value or ',' in value or '#' in value:
                            value = f'"{value}"'
                        f.write(f"{key}={value}\n")
                        
        except Exception as e:
            logger.error(f"Error writing .env file: {e}")
            raise
    
    def get_all_vars_for_display(self) -> Dict[str, Dict[str, Any]]:
        """Get all environment variables formatted for admin display"""
        all_vars = self.load_all_vars()
        display_vars = {}
        
        # Add sensitive vars
        for key in SENSITIVE_VARS:
            value = self.get_var(key) or ""
            is_set = bool(value)
            
            # Mask sensitive values for display
            if is_set:
                if key == "SLACK_WEBHOOK_URL":
                    display_value = value[:30] + "..." if len(value) > 30 else value
                else:
                    display_value = value[:4] + "***" if len(value) > 4 else "***"
            else:
                display_value = ""
            
            display_vars[key] = {
                "value": display_value,
                "is_set": is_set,
                "is_sensitive": True,
                "stored_in": "Secret Manager" if self.use_secret_manager and is_set else "Local",
                "description": self._get_var_description(key)
            }
        
        # Add local vars
        for key in LOCAL_VARS:
            value = self.get_var(key) or ""
            display_vars[key] = {
                "value": value,
                "is_set": bool(value),
                "is_sensitive": False,
                "stored_in": "Local",
                "description": self._get_var_description(key)
            }
        
        return display_vars
    
    def _get_var_description(self, key: str) -> str:
        """Get description for environment variable"""
        descriptions = {
            "SLACK_WEBHOOK_URL": "Slack webhook URL for notifications",
            "GEMINI_API_KEY": "Google Gemini AI API key",
            "OPENAI_API_KEY": "OpenAI API key",
            "KLAVIYO_PRIVATE_KEY": "Klaviyo private API key",
            "FIREBASE_API_KEY": "Firebase API key",
            "ENVIRONMENT": "Deployment environment (development/production)",
            "DEBUG": "Debug mode enabled",
            "GOOGLE_CLOUD_PROJECT": "Google Cloud Project ID",
            "GOOGLE_APPLICATION_CREDENTIALS": "Path to service account key file",
            "SECRET_MANAGER_ENABLED": "Use Google Secret Manager for sensitive vars"
        }
        return descriptions.get(key, f"Configuration for {key}")


# Singleton instance
_env_manager = None

def get_env_manager() -> EnvManager:
    """Get singleton instance of EnvManager"""
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvManager()
    return _env_manager