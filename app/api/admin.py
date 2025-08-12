"""
Admin API endpoints for system management with Secret Manager integration
"""

import os
import sys
import signal
import subprocess
import requests
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import logging

from app.core.database import get_db
from app.core.config import settings
from app.services.secret_manager import get_secret_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class SlackTestResponse(BaseModel):
    status: str
    message: str
    webhook_url: Optional[str] = None

class EnvironmentVariable(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class EnvironmentVariablesResponse(BaseModel):
    variables: Dict[str, Any]
    secret_manager_enabled: bool
    
class UpdateEnvironmentRequest(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None
    variables: Optional[Dict[str, str]] = None

class SecretListResponse(BaseModel):
    secrets: List[Dict[str, str]]
    total: int
    secret_manager_enabled: bool

# Sensitive environment variables that should be masked
SENSITIVE_VARS = {
    "SECRET_KEY", "KLAVIYO_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY",
    "DATABASE_URL", "GOOGLE_APPLICATION_CREDENTIALS", "SLACK_WEBHOOK_URL"
}

# Secret Manager secret ID mappings
SECRET_MAPPINGS = {
    "DATABASE_URL": "emailpilot-database-url",
    "SECRET_KEY": "emailpilot-secret-key",
    "KLAVIYO_API_KEY": "emailpilot-klaviyo-api-key",
    "SLACK_WEBHOOK_URL": "emailpilot-slack-webhook-url",
    "GEMINI_API_KEY": "emailpilot-gemini-api-key",
    "OPENAI_API_KEY": "emailpilot-openai-api-key",
    "GOOGLE_APPLICATION_CREDENTIALS": "emailpilot-google-credentials"
}

# Important environment variables for the admin interface
ADMIN_ENV_VARS = {
    "SLACK_WEBHOOK_URL": {
        "description": "Slack webhook URL for notifications",
        "example": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "required": False,
        "sensitive": True
    },
    "GEMINI_API_KEY": {
        "description": "Google Gemini API key for AI features",
        "example": "AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "required": False,
        "sensitive": True
    },
    "OPENAI_API_KEY": {
        "description": "OpenAI API key for GPT models",
        "example": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "required": False,
        "sensitive": True
    },
    "KLAVIYO_API_KEY": {
        "description": "Klaviyo API key for accessing client data",
        "example": "pk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "required": True,
        "sensitive": True
    },
    "DATABASE_URL": {
        "description": "Database connection URL",
        "example": "sqlite:///./emailpilot.db",
        "required": True,
        "sensitive": True
    },
    "SECRET_KEY": {
        "description": "JWT/Session encryption key",
        "example": "your-secret-key-here",
        "required": True,
        "sensitive": True
    },
    "GOOGLE_CLOUD_PROJECT": {
        "description": "Google Cloud Project ID",
        "example": "emailpilot-438321",
        "required": False,
        "sensitive": False
    },
    "ENVIRONMENT": {
        "description": "Deployment environment",
        "example": "production",
        "required": False,
        "sensitive": False
    },
    "DEBUG": {
        "description": "Enable debug mode",
        "example": "false",
        "required": False,
        "sensitive": False
    },
    "SECRET_MANAGER_ENABLED": {
        "description": "Enable Google Secret Manager for sensitive data",
        "example": "true",
        "required": False,
        "sensitive": False
    }
}

def mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive environment variable values"""
    if not value:
        return ""
    
    if key in SENSITIVE_VARS:
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
    
    return value

def get_env_file_path() -> Path:
    """Get the .env file path"""
    app_dir = Path(__file__).parent.parent.parent
    env_file = app_dir / ".env"
    
    if not env_file.exists():
        env_file.touch()
        logger.info(f"Created .env file at: {env_file}")
    
    return env_file

def load_env_file() -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}
    env_file = get_env_file_path()
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"').strip("'")
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

def save_env_file(env_vars: Dict[str, str]):
    """Save non-sensitive environment variables to .env file"""
    env_file = get_env_file_path()
    
    # Load existing vars from file
    existing_vars = load_env_file()
    
    # Update with new non-sensitive values only
    for key, value in env_vars.items():
        if key not in SENSITIVE_VARS:
            existing_vars[key] = value
    
    # Remove sensitive vars from .env file if Secret Manager is enabled
    if settings.secret_manager_enabled:
        for key in SENSITIVE_VARS:
            existing_vars.pop(key, None)
    else:
        # If Secret Manager is disabled, update all vars
        existing_vars.update(env_vars)
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.write("# EmailPilot Environment Configuration\n")
        f.write(f"# Last updated: {datetime.now().isoformat()}\n")
        f.write("# This file is automatically managed by the Admin interface\n")
        if settings.secret_manager_enabled:
            f.write("# Sensitive values are stored in Google Secret Manager\n")
        f.write("\n")
        
        # Write variables in a consistent order
        for key in sorted(existing_vars.keys()):
            value = existing_vars[key]
            # Add quotes for values with spaces or special characters
            if ' ' in value or ',' in value or '#' in value:
                value = f'"{value}"'
            f.write(f"{key}={value}\n")
    
    logger.info(f"Updated .env file at: {env_file}")

def get_secret_value(key: str) -> Optional[str]:
    """Get a secret value from Secret Manager or environment"""
    if settings.secret_manager_enabled and key in SECRET_MAPPINGS:
        try:
            secret_manager = get_secret_manager()
            secret_id = SECRET_MAPPINGS[key]
            return secret_manager.get_secret(secret_id)
        except Exception as e:
            logger.warning(f"Could not retrieve {key} from Secret Manager: {e}")
    
    # Fall back to environment variable
    return os.getenv(key) or load_env_file().get(key)

def set_secret_value(key: str, value: str) -> bool:
    """Set a secret value in Secret Manager or environment"""
    success = False
    
    # Update in Secret Manager if enabled and it's a sensitive var
    if settings.secret_manager_enabled and key in SECRET_MAPPINGS:
        try:
            secret_manager = get_secret_manager()
            secret_id = SECRET_MAPPINGS[key]
            secret_manager.create_secret(
                secret_id=secret_id,
                secret_value=value,
                labels={"app": "emailpilot", "type": "config", "key": key}
            )
            logger.info(f"Updated {key} in Secret Manager")
            success = True
        except Exception as e:
            logger.error(f"Failed to update {key} in Secret Manager: {e}")
            return False
    
    # Update environment variable for current session
    os.environ[key] = value
    
    # Update settings object if it has this attribute
    if hasattr(settings, key.lower()):
        setattr(settings, key.lower(), value)
    elif hasattr(settings, key.lower().replace('_', '')):
        setattr(settings, key.lower().replace('_', ''), value)
    
    # Save to .env file if not using Secret Manager or for non-sensitive vars
    if not settings.secret_manager_enabled or key not in SENSITIVE_VARS:
        save_env_file({key: value})
        success = True
    
    return success

@router.get("/health")
async def admin_health_check():
    """Admin health check endpoint"""
    return {
        "status": "healthy",
        "service": "EmailPilot Admin API",
        "secret_manager_enabled": settings.secret_manager_enabled,
        "endpoints_available": [
            "POST /admin/slack/test",
            "GET /admin/environment",
            "POST /admin/environment",
            "GET /admin/secrets",
            "GET /admin/system/status",
            "POST /admin/restart",
            "POST /admin/secrets/migrate"
        ]
    }

@router.post("/slack/test", response_model=SlackTestResponse)
async def test_slack_webhook():
    """Test Slack webhook functionality"""
    try:
        webhook_url = get_secret_value('SLACK_WEBHOOK_URL')
        
        if not webhook_url:
            raise HTTPException(
                status_code=400, 
                detail="Slack webhook URL not configured. Please set SLACK_WEBHOOK_URL."
            )
        
        # Create test message
        test_message = {
            "text": "🧪 EmailPilot Slack Test",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 EmailPilot Slack Integration Test",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Test Status:* ✅ SUCCESS\n*Source:* EmailPilot Admin Panel\n*Time:* <!date^{timestamp}^{{date_short}} at {{time}}|{timestamp}>".format(
                            timestamp=int(__import__('time').time())
                        )
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"This is a test message from EmailPilot Admin interface. Secret Manager: {'✅ Enabled' if settings.secret_manager_enabled else '❌ Disabled'}"
                        }
                    ]
                }
            ]
        }
        
        # Send test message to Slack
        response = requests.post(
            webhook_url,
            json=test_message,
            timeout=10
        )
        
        if response.status_code == 200:
            return SlackTestResponse(
                status="success",
                message="Test message sent successfully! Check your Slack channel.",
                webhook_url=webhook_url if not settings.secret_manager_enabled else "***hidden***"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Slack webhook returned status {response.status_code}: {response.text}"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test message: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Slack test failed: {str(e)}"
        )

@router.get("/environment", response_model=EnvironmentVariablesResponse)
async def get_environment_variables():
    """Get current environment variables (with sensitive values masked)"""
    try:
        env_vars = {}
        
        for key, config in ADMIN_ENV_VARS.items():
            # Get value from Secret Manager or environment
            current_value = get_secret_value(key) or ""
            
            # Check if it's actually stored in Secret Manager
            stored_in_secret_manager = False
            if settings.secret_manager_enabled and key in SECRET_MAPPINGS:
                try:
                    secret_manager = get_secret_manager()
                    secret_value = secret_manager.get_secret(SECRET_MAPPINGS[key])
                    stored_in_secret_manager = secret_value is not None
                except:
                    pass
            
            masked_value = mask_sensitive_value(key, current_value)
            
            env_vars[key] = {
                "value": masked_value,
                "description": config["description"],
                "example": config.get("example", ""),
                "required": config.get("required", False),
                "is_set": bool(current_value),
                "is_sensitive": config.get("sensitive", False),
                "stored_in_secret_manager": stored_in_secret_manager
            }
        
        return EnvironmentVariablesResponse(
            variables=env_vars,
            secret_manager_enabled=settings.secret_manager_enabled
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve environment variables: {str(e)}"
        )

@router.post("/environment")
async def update_environment_variables(request: UpdateEnvironmentRequest):
    """Update environment variables in Secret Manager or .env file"""
    try:
        updated_vars = []
        errors = []
        
        # Handle single variable update
        if request.key and request.value is not None:
            variables_to_update = {request.key: request.value}
        # Handle multiple variables update
        elif request.variables:
            variables_to_update = request.variables
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'key' and 'value' or 'variables' must be provided"
            )
        
        for key, value in variables_to_update.items():
            if key not in ADMIN_ENV_VARS:
                errors.append(f"Unknown environment variable: {key}")
                continue
            
            try:
                if set_secret_value(key, value):
                    updated_vars.append(key)
                else:
                    errors.append(f"Failed to update {key}")
            except Exception as e:
                errors.append(f"Failed to update {key}: {str(e)}")
        
        if errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Some environment variables could not be updated",
                    "errors": errors,
                    "updated": updated_vars
                }
            )
        
        storage_location = "Secret Manager" if settings.secret_manager_enabled else ".env file"
        
        return {
            "status": "success",
            "message": f"Successfully updated {len(updated_vars)} environment variables",
            "updated_variables": updated_vars,
            "storage_location": storage_location,
            "note": f"Changes have been saved to {storage_location} and will persist across restarts."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update environment variables: {str(e)}"
        )

@router.get("/secrets", response_model=SecretListResponse)
async def list_secrets():
    """List all secrets in Secret Manager"""
    if not settings.secret_manager_enabled:
        return SecretListResponse(
            secrets=[],
            total=0,
            secret_manager_enabled=False
        )
    
    try:
        secret_manager = get_secret_manager()
        all_secrets = secret_manager.list_secrets(filter_str="labels.app=emailpilot")
        
        secrets = []
        for secret_name in all_secrets:
            # Map back to environment variable name if possible
            env_key = None
            for key, secret_id in SECRET_MAPPINGS.items():
                if secret_id == secret_name:
                    env_key = key
                    break
            
            secrets.append({
                "secret_id": secret_name,
                "environment_key": env_key or "unknown",
                "type": "config" if env_key else "other"
            })
        
        return SecretListResponse(
            secrets=secrets,
            total=len(secrets),
            secret_manager_enabled=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list secrets: {str(e)}"
        )

@router.post("/secrets/migrate")
async def migrate_to_secret_manager():
    """Migrate sensitive environment variables from .env to Secret Manager"""
    if not settings.secret_manager_enabled:
        raise HTTPException(
            status_code=400,
            detail="Secret Manager is not enabled. Set SECRET_MANAGER_ENABLED=true first."
        )
    
    try:
        migrated = []
        errors = []
        
        # Load current .env file
        env_vars = load_env_file()
        
        # Also check current environment
        for key in SECRET_MAPPINGS.keys():
            if key not in env_vars and os.getenv(key):
                env_vars[key] = os.getenv(key)
        
        # Migrate each sensitive variable
        for key, secret_id in SECRET_MAPPINGS.items():
            if key in env_vars and env_vars[key]:
                try:
                    secret_manager = get_secret_manager()
                    secret_manager.create_secret(
                        secret_id=secret_id,
                        secret_value=env_vars[key],
                        labels={"app": "emailpilot", "type": "config", "key": key}
                    )
                    migrated.append(key)
                    logger.info(f"Migrated {key} to Secret Manager")
                except Exception as e:
                    errors.append(f"{key}: {str(e)}")
        
        # Clean up .env file - remove sensitive vars
        if migrated:
            cleaned_env = {k: v for k, v in env_vars.items() if k not in SENSITIVE_VARS}
            save_env_file(cleaned_env)
        
        if errors:
            return {
                "status": "partial_success",
                "message": f"Migrated {len(migrated)} secrets with {len(errors)} errors",
                "migrated": migrated,
                "errors": errors
            }
        
        return {
            "status": "success",
            "message": f"Successfully migrated {len(migrated)} secrets to Secret Manager",
            "migrated": migrated,
            "note": "Sensitive values have been removed from .env file"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )

@router.get("/system/status")
async def get_system_status():
    """Get comprehensive system status for admin dashboard"""
    try:
        # Get configuration from Secret Manager or environment
        slack_configured = bool(get_secret_value('SLACK_WEBHOOK_URL'))
        gemini_configured = bool(get_secret_value('GEMINI_API_KEY'))
        klaviyo_configured = bool(get_secret_value('KLAVIYO_API_KEY'))
        db_url = get_secret_value('DATABASE_URL') or 'sqlite:///./emailpilot.db'
        
        return {
            "status": "healthy",
            "components": {
                "api": {
                    "status": "operational",
                    "details": "FastAPI server running"
                },
                "database": {
                    "status": "operational" if db_url else "not_configured",
                    "details": f"Using: {db_url.split('://', 1)[0] if db_url else 'None'}"
                },
                "secret_manager": {
                    "status": "operational" if settings.secret_manager_enabled else "disabled",
                    "details": f"Google Cloud Project: {settings.google_cloud_project}" if settings.secret_manager_enabled else "Using .env file"
                },
                "slack": {
                    "status": "operational" if slack_configured else "not_configured",
                    "details": "Webhook URL is set" if slack_configured else "No webhook URL configured"
                },
                "gemini": {
                    "status": "operational" if gemini_configured else "not_configured",
                    "details": "API key is set" if gemini_configured else "No API key configured"
                },
                "klaviyo": {
                    "status": "operational" if klaviyo_configured else "not_configured",
                    "details": "API key is set" if klaviyo_configured else "No API key configured"
                }
            },
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "debug": os.getenv('DEBUG', 'false').lower() == 'true',
            "secret_manager_enabled": settings.secret_manager_enabled
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system status: {str(e)}"
        )

@router.post("/restart")
async def restart_server(background_tasks: BackgroundTasks):
    """Restart the FastAPI server"""
    try:
        def restart_process():
            """Restart the server process after a short delay"""
            import time
            time.sleep(2)  # Give time for response to be sent
            
            # Try to restart using uvicorn's reload mechanism
            if '--reload' in sys.argv or any('reload' in str(arg) for arg in sys.argv):
                # If running with --reload, just touch a Python file to trigger reload
                main_file = Path(__file__).parent.parent.parent / "main.py"
                if main_file.exists():
                    main_file.touch()
                    logger.info("Triggered reload by touching main.py")
            else:
                # Otherwise, restart the process
                logger.info("Restarting server process...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
        
        background_tasks.add_task(restart_process)
        
        return {
            "status": "success",
            "message": "Server restart initiated. Please wait a few seconds..."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart server: {str(e)}"
        )