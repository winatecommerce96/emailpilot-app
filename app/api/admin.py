"""
Admin API endpoints for system management with Secret Manager integration
"""
from __future__ import annotations

import os
import sys
import signal
import subprocess
import requests
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Optional, Any, List, TYPE_CHECKING
from datetime import datetime
import asyncio
import logging
import re
from collections import namedtuple

from app.core.settings import get_settings
from app.services.secret_manager import mask_sensitive, SecretNotFoundError
from app.deps import get_secret_manager_service, get_db
from google.cloud import firestore

if TYPE_CHECKING:
    from app.services.secret_manager import SecretManagerService

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

class DeleteSecretRequest(BaseModel):
    secret_id: str

class SecretListResponse(BaseModel):
    secrets: List[Dict[str, str]]
    total: int
    secret_manager_enabled: bool

# Sensitive environment variables that should be masked
SENSITIVE_VARS = {
    "SECRET_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS", "SLACK_WEBHOOK_URL"
}

# Secret Manager secret ID mappings
SECRET_MAPPINGS = {
    "SECRET_KEY": "emailpilot-secret-key",
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

# --- Utilities for Ops ---
SizeSpec = namedtuple("SizeSpec", ["bytes", "raw"])  # small helper for reporting

def _parse_size(spec: str) -> int:
    """Parse human size like '500M', '1G', '200K' to bytes; default to int bytes."""
    if not spec:
        return 0
    s = str(spec).strip().lower()
    m = re.match(r"^(\d+)([kmg])?$", s)
    if not m:
        try:
            return int(spec)
        except Exception:
            return 0
    n = int(m.group(1))
    unit = m.group(2)
    if unit == 'k':
        return n * 1024
    if unit == 'm':
        return n * 1024 * 1024
    if unit == 'g':
        return n * 1024 * 1024 * 1024
    return n

def _scan_files(threshold_bytes: int, include_logs: bool = True, include_out: bool = True, include_logs_dir: bool = True,
                exclude_logs: bool = False) -> list[dict]:
    """Return list of files over threshold with size and path.
    - If exclude_logs is True, exclude *.log, *.out, and logs/ dir.
    """
    root = Path(__file__).resolve().parents[2]
    results: list[dict] = []
    patterns = []
    if not exclude_logs:
        if include_logs:
            patterns.append('.log')
        if include_out:
            patterns.append('.out')
    for dirpath, _dirnames, filenames in os.walk(root):
        # Skip git and venv noise
        if any(skip in dirpath for skip in ("/.git", "/node_modules", "/__pycache__", "/.venv", "/venv")):
            continue
        if not exclude_logs and include_logs_dir and os.path.basename(dirpath) == 'logs':
            pass  # include
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size < threshold_bytes:
                continue
            if exclude_logs:
                if fn.endswith('.log') or fn.endswith('.out'):
                    continue
                if '/logs/' in p.replace('\\', '/') or p.endswith('/logs'):
                    continue
            else:
                # If focusing on logs, require typical patterns
                if patterns and not any(fn.endswith(ext) for ext in patterns) and '/logs/' not in p.replace('\\', '/'):
                    continue
            results.append({
                'path': os.path.relpath(p, root),
                'size_bytes': st.st_size,
            })
    results.sort(key=lambda d: d['size_bytes'], reverse=True)
    return results

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
    settings = get_settings()
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

def get_secret_value(key: str, secret_manager: "SecretManagerService") -> Optional[str]:
    """Get a secret value from Secret Manager or environment"""
    settings = get_settings()
    if settings.secret_manager_enabled and key in SECRET_MAPPINGS:
        try:
            secret_id = SECRET_MAPPINGS[key]
            return secret_manager.get_secret(secret_id)
        except SecretNotFoundError:
            logger.warning(f"Could not retrieve {key} from Secret Manager: secret not found.")
        except Exception as e:
            logger.warning(f"Could not retrieve {key} from Secret Manager: {e}")
    
    # Fall back to environment variable
    return os.getenv(key) or load_env_file().get(key)

def set_secret_value(key: str, value: str, secret_manager: "SecretManagerService") -> bool:
    """Set a secret value in Secret Manager or environment"""
    success = False
    
    # Update in Secret Manager if enabled and it's a sensitive var
    settings = get_settings()
    if settings.secret_manager_enabled and key in SECRET_MAPPINGS:
        try:
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
    if hasattr(get_settings(), key.lower()):
        setattr(get_settings(), key.lower(), value)
    elif hasattr(get_settings(), key.lower().replace('_', '')):
        setattr(get_settings(), key.lower().replace('_', ''), value)
    
    # Save to .env file if not using Secret Manager or for non-sensitive vars
    if not settings.secret_manager_enabled or key not in SENSITIVE_VARS:
        save_env_file({key: value})
        success = True
    
    return success

@router.get("/")
async def admin_root():
    """Admin API root endpoint for dashboard"""
    return {
        "status": "operational",
        "service": "EmailPilot Admin API",
        "version": "2.0.0",
        "secret_manager_enabled": get_settings().secret_manager_enabled,
        "available_endpoints": [
            "GET /api/admin/health",
            "GET /api/admin/db/status", 
            "GET /api/admin/services/status",
            "GET /api/admin/system/status",
            "POST /api/admin/slack/test",
            "GET /api/admin/environment",
            "POST /api/admin/environment",
            "DELETE /api/admin/environment/{secret_id}",
            "GET /api/admin/secrets",
            "POST /api/admin/restart",
            "POST /api/admin/secrets/migrate"
        ]
    }

@router.get("/health")
async def admin_health_check():
    """Admin health check endpoint"""
    return {
        "status": "healthy",
        "service": "EmailPilot Admin API",
        "secret_manager_enabled": get_settings().secret_manager_enabled,
        "endpoints_available": [
            "POST /admin/slack/test",
            "GET /admin/environment",
            "POST /admin/environment",
            "DELETE /admin/environment/{secret_id}",
            "GET /admin/secrets",
            "GET /admin/system/status",
            "POST /admin/restart",
            "POST /admin/secrets/migrate"
        ]
    }


# ========== Admin Ops: Logs & Files ==========

@router.get("/ops/logs/large")
async def list_large_logs(threshold: str = "500M"):
    """List large log-ish files (logs/*.log, *.out) over threshold."""
    tb = _parse_size(threshold)
    items = _scan_files(tb, exclude_logs=False)
    return {"threshold": threshold, "count": len(items), "items": items[:200]}


class LogCleanupRequest(BaseModel):
    mode: str = "list"  # list|truncate|delete
    threshold: str = "500M"


@router.post("/ops/logs/cleanup")
async def cleanup_large_logs(req: LogCleanupRequest):
    """Cleanup large log files by truncating or deleting files over threshold.
    Safe-scope: only *.log, *.out, and under logs/ directory.
    """
    tb = _parse_size(req.threshold)
    items = _scan_files(tb, exclude_logs=False)
    acted = []
    if req.mode not in ("list", "truncate", "delete"):
        raise HTTPException(status_code=400, detail="mode must be one of list|truncate|delete")
    if req.mode == "list":
        return {"threshold": req.threshold, "count": len(items), "items": items[:200]}
    for it in items:
        p = Path(__file__).resolve().parents[2] / it['path']
        try:
            if req.mode == "truncate":
                with open(p, 'w'):
                    pass
                acted.append({"path": it['path'], "action": "truncated"})
            elif req.mode == "delete":
                os.remove(p)
                acted.append({"path": it['path'], "action": "deleted"})
        except Exception as e:
            acted.append({"path": it['path'], "error": str(e)})
    return {"threshold": req.threshold, "mode": req.mode, "acted": acted}


@router.get("/ops/files/big")
async def list_large_non_logs(threshold: str = "200M"):
    """List large non-log files over threshold to aid cleanup."""
    tb = _parse_size(threshold)
    items = _scan_files(tb, exclude_logs=True)
    return {"threshold": threshold, "count": len(items), "items": items[:200]}


# ========== Admin Ops: Revenue API CORS/Health ==========

@router.get("/revenue/status")
async def revenue_status(base: Optional[str] = None, origin: Optional[str] = None):
    """Probe Revenue API health and CORS preflight without starting/stopping it."""
    import httpx
    # Back-compat: prefer KLAVIYO_API_BASE, then REVENUE_API_BASE
    base = base or os.getenv("KLAVIYO_API_BASE") or os.getenv("REVENUE_API_BASE", "http://127.0.0.1:9090")
    origin = origin or os.getenv("ORIGIN", "http://localhost:3000")
    out: dict[str, Any] = {"base": base, "origin": origin}
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{base}/healthz")
            out["healthz_status"] = r.status_code
            out["healthz_json"] = r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text[:500]
    except Exception as e:
        out["healthz_error"] = str(e)
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.request(
                "OPTIONS",
                f"{base}/clients/test/revenue/last7",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            out["preflight_status"] = r.status_code
            out["cors_headers"] = {
                k: v for k, v in r.headers.items()
                if k.lower().startswith("access-control-allow-")
            }
    except Exception as e:
        out["preflight_error"] = str(e)
    return out


class RevenueStartRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9090


@router.post("/revenue/start")
async def revenue_start(req: RevenueStartRequest):
    """Start the Revenue API via uvicorn in the background (dev convenience)."""
    pid_file = Path.cwd() / ".revenue_api.pid"
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    if pid_file.exists():
        return {"status": "already_running", "pid_file": str(pid_file)}
    cmd = [
        sys.executable, "-m", "uvicorn",
        "services.klaviyo_api.main:app",
        "--host", req.host,
        "--port", str(req.port),
    ]
    env = os.environ.copy()
    if "GOOGLE_CLOUD_PROJECT" not in env:
        env["GOOGLE_CLOUD_PROJECT"] = env.get("REVENUE_PROJECT_ID", env.get("GOOGLE_CLOUD_PROJECT", "emailpilot-438321"))
    log_path = log_dir / "klaviyo_api_uvicorn.out"
    try:
        with open(log_path, 'ab') as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, env=env)
        pid_file.write_text(str(proc.pid))
        return {"status": "started", "pid": proc.pid, "log": str(log_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Revenue API: {e}")


@router.post("/revenue/stop")
async def revenue_stop():
    """Stop the background Revenue API process started via /revenue/start."""
    pid_file = Path.cwd() / ".revenue_api.pid"
    if not pid_file.exists():
        return {"status": "not_running"}
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    try:
        pid_file.unlink()
    except Exception:
        pass
    return {"status": "stopped"}


# ========== Admin Ops: Klaviyo API Aliases ==========

@router.get("/klaviyo/status")
async def klaviyo_status_alias(base: Optional[str] = None, origin: Optional[str] = None):
    """Alias for /api/admin/revenue/status to reflect Klaviyo API naming."""
    return await revenue_status(base=base, origin=origin)


@router.post("/klaviyo/start")
async def klaviyo_start_alias(req: RevenueStartRequest):
    """Alias for /api/admin/revenue/start to reflect Klaviyo API naming."""
    return await revenue_start(req)


@router.post("/klaviyo/stop")
async def klaviyo_stop_alias():
    """Alias for /api/admin/revenue/stop to reflect Klaviyo API naming."""
    return await revenue_stop()


# ========== Reports Settings (Admin) ==========

@router.get("/reports/settings")
async def get_reports_settings(db: firestore.Client = Depends(get_db)):
    """Fetch reports-related admin settings (e.g., per-client weekly Slack posts default)."""
    try:
        ref = db.collection("app_settings").document("reports")
        doc = ref.get()
        data = doc.to_dict() if doc.exists else {}
        return {
            "weekly_send_client_posts_default": bool(data.get("weekly_send_client_posts_default", False)),
            "weekly_client_prompt_id": data.get("weekly_client_prompt_id"),
            "weekly_company_prompt_id": data.get("weekly_company_prompt_id"),
            "updated_at": data.get("updated_at")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ReportsSettingsUpdate(BaseModel):
    weekly_send_client_posts_default: Optional[bool] = None
    weekly_client_prompt_id: Optional[str] = None
    weekly_company_prompt_id: Optional[str] = None

class ReportsFlagsUpdate(BaseModel):
    weekly_insights_runner_enabled: Optional[bool] = None


@router.post("/reports/settings")
async def update_reports_settings(payload: ReportsSettingsUpdate, db: firestore.Client = Depends(get_db)):
    """Update reports-related admin settings."""
    try:
        ref = db.collection("app_settings").document("reports")
        updates: Dict[str, Any] = {"updated_at": firestore.SERVER_TIMESTAMP}
        if payload.weekly_send_client_posts_default is not None:
            updates["weekly_send_client_posts_default"] = bool(payload.weekly_send_client_posts_default)
        if payload.weekly_client_prompt_id is not None:
            updates["weekly_client_prompt_id"] = payload.weekly_client_prompt_id
        if payload.weekly_company_prompt_id is not None:
            updates["weekly_company_prompt_id"] = payload.weekly_company_prompt_id
        ref.set(updates, merge=True)
        # Return updated
        doc = ref.get(); data = doc.to_dict() or {}
        return {
            "success": True,
            "weekly_send_client_posts_default": bool(data.get("weekly_send_client_posts_default", False)),
            "weekly_client_prompt_id": data.get("weekly_client_prompt_id"),
            "weekly_company_prompt_id": data.get("weekly_company_prompt_id"),
            "updated_at": data.get("updated_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/settings/flags")
async def get_reports_flags(db: firestore.Client = Depends(get_db)):
    try:
        ref = db.collection("app_settings").document("reports")
        doc = ref.get()
        data = doc.to_dict() if doc.exists else {}
        return {
            "weekly_insights_runner_enabled": bool(data.get("weekly_insights_runner_enabled", False)),
            "updated_at": data.get("updated_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/settings/flags")
async def update_reports_flags(payload: ReportsFlagsUpdate, db: firestore.Client = Depends(get_db)):
    try:
        ref = db.collection("app_settings").document("reports")
        updates: Dict[str, Any] = {"updated_at": firestore.SERVER_TIMESTAMP}
        if payload.weekly_insights_runner_enabled is not None:
            updates["weekly_insights_runner_enabled"] = bool(payload.weekly_insights_runner_enabled)
        ref.set(updates, merge=True)
        doc = ref.get(); data = doc.to_dict() or {}
        return {
            "success": True,
            "weekly_insights_runner_enabled": bool(data.get("weekly_insights_runner_enabled", False)),
            "updated_at": data.get("updated_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ====== Klaviyo API aliases (preferred naming) ======

@router.get("/klaviyo/status")
async def klaviyo_status(base: Optional[str] = None, origin: Optional[str] = None):
    return await revenue_status(base=base, origin=origin)


class KlaviyoStartRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9090


@router.post("/klaviyo/start")
async def klaviyo_start(req: KlaviyoStartRequest):
    return await revenue_start(RevenueStartRequest(host=req.host, port=req.port))


@router.post("/klaviyo/stop")
async def klaviyo_stop():
    return await revenue_stop()

@router.post("/slack/test", response_model=SlackTestResponse)
async def test_slack_webhook(secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """Test Slack webhook functionality"""
    try:
        webhook_url = get_secret_value('SLACK_WEBHOOK_URL', secret_manager)
        
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
                            "text": f"This is a test message from EmailPilot Admin interface. Secret Manager: {'✅ Enabled' if get_settings().secret_manager_enabled else '❌ Disabled'}"
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
                webhook_url=webhook_url if not get_settings().secret_manager_enabled else "***hidden***"
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

@router.get("/environment")
async def get_environment_variables(secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """Get ALL environment variables from Secret Manager"""
    try:
        settings = get_settings()
        if not settings.secret_manager_enabled:
            raise HTTPException(
                status_code=400,
                detail="Secret Manager is disabled"
            )
        
        # Get ALL secrets from Secret Manager
        all_secrets = secret_manager.list_secrets()
        variables = {}
        
        for secret_id in all_secrets:
            try:
                value = secret_manager.get_secret(secret_id)
                # Mask sensitive values for display
                variables[secret_id] = mask_sensitive(secret_id, value)
            except SecretNotFoundError:
                # Secret may have been deleted between list and get
                variables[secret_id] = "[SECRET NOT FOUND]"
            except Exception as e:
                variables[secret_id] = f"[ERROR: {str(e)}]"
        
        return {
            "variables": variables,
            "source": {
                "type": "secret_manager",
                "provider": "gcp",
                "project": settings.google_cloud_project
            },
            "environment": settings.environment,
            "total_secrets": len(all_secrets),
            "secret_manager_enabled": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve environment variables: {str(e)}"
        )

@router.post("/environment")
async def update_environment_variables(request: UpdateEnvironmentRequest, secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """Create or update environment variables in Secret Manager"""
    try:
        settings = get_settings()
        
        if not settings.secret_manager_enabled:
            raise HTTPException(
                status_code=400,
                detail="Secret Manager is disabled"
            )
        
        updated_vars = []
        created_vars = []
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
        
        # Get existing secrets to determine if we're creating or updating
        existing_secrets = set(secret_manager.list_secrets())
        
        for key, value in variables_to_update.items():
            # Validate secret name (basic validation)
            if not key or not key.replace('-', '').replace('_', '').isalnum():
                errors.append(f"Invalid secret name '{key}'. Use only letters, numbers, hyphens, and underscores.")
                continue
            
            try:
                # Create or update the secret
                secret_manager.create_secret(
                    secret_id=key,
                    secret_value=value,
                    labels={"app": "emailpilot", "managed_by": "admin"}
                )
                
                if key in existing_secrets:
                    updated_vars.append(key)
                else:
                    created_vars.append(key)
                    
            except Exception as e:
                errors.append(f"Failed to update {key}: {str(e)}")
        
        if errors and not updated_vars and not created_vars:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Failed to update environment variables",
                    "errors": errors
                }
            )
        
        result = {
            "status": "success" if not errors else "partial_success",
            "message": f"Created {len(created_vars)} and updated {len(updated_vars)} secrets",
            "created_variables": created_vars,
            "updated_variables": updated_vars,
            "storage_location": "Google Secret Manager"
        }
        
        if errors:
            result["errors"] = errors
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update environment variables: {str(e)}"
        )

@router.delete("/environment/{secret_id}")
async def delete_environment_variable(secret_id: str, secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """Delete a secret from Secret Manager"""
    try:
        settings = get_settings()
        
        if not settings.secret_manager_enabled:
            raise HTTPException(
                status_code=400,
                detail="Secret Manager is disabled"
            )
        
        # Check if secret exists
        existing_secrets = secret_manager.list_secrets()
        if secret_id not in existing_secrets:
            raise HTTPException(
                status_code=404,
                detail=f"Secret '{secret_id}' not found"
            )
        
        # Delete the secret
        secret_manager.delete_secret(secret_id)
        
        return {
            "status": "success",
            "message": f"Secret '{secret_id}' deleted successfully",
            "deleted_secret": secret_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete secret: {str(e)}"
        )

@router.get("/secrets", response_model=SecretListResponse)
async def list_secrets(secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """List all secrets in Secret Manager"""
    settings = get_settings()
    if not settings.secret_manager_enabled:
        return SecretListResponse(
            secrets=[],
            total=0,
            secret_manager_enabled=False
        )
    
    try:
        all_secrets = secret_manager.list_secrets()
        
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
async def migrate_to_secret_manager(secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """Migrate sensitive environment variables from .env to Secret Manager"""
    settings = get_settings()
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

from app.services.klaviyo_data_service import KlaviyoDataService

@router.post("/klaviyo/sync")
async def trigger_klaviyo_sync(background_tasks: BackgroundTasks):
    """Trigger the daily Klaviyo data sync""" 
    try:
        service = KlaviyoDataService()
        background_tasks.add_task(service.run_daily_sync)
        return {
            "status": "success",
            "message": "Klaviyo data sync initiated in the background."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger Klaviyo sync: {str(e)}"
        )

@router.post("/klaviyo/backfill/{client_id}")
async def trigger_klaviyo_backfill(client_id: str, background_tasks: BackgroundTasks, sync: bool = False):
    """Backfill 2 years of daily data for a client.

    - When `sync=false` (default): run in background and return immediately.
    - When `sync=true`: run now and return summary counts.
    """
    try:
        service = KlaviyoDataService()
        if sync:
            result = await service.backfill_client_data(client_id)
            return {
                "status": "success",
                "message": f"Klaviyo backfill complete for client {client_id}",
                "result": result,
            }
        else:
            background_tasks.add_task(service.backfill_client_data, client_id)
            return {
                "status": "success",
                "message": f"Klaviyo data backfill for client {client_id} initiated in the background.",
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run Klaviyo backfill: {str(e)}"
        )

@router.post("/klaviyo/sync/{client_id}")
async def trigger_client_klaviyo_sync(client_id: str):
    """Trigger Klaviyo data sync for a specific client and return counts."""
    try:
        service = KlaviyoDataService()
        result = await service.sync_client_data(client_id)
        return {
            "status": "success",
            "message": f"Klaviyo data sync complete for client {client_id}",
            "result": result,
        }
    except Exception as e:
        # Try to surface HTTP error body if available
        detail = str(e)
        try:
            import httpx
            if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
                detail = f"{e}\nBody: {e.response.text}"
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to sync client {client_id}: {detail}")

@router.post("/clients/assign-ids")
async def assign_client_ids(db = Depends(get_db)):
    """Assign a stable, unique client_id/slug for all clients and set klaviyo_secret_name if missing.

    - client_id (field): normalized name (hyphenated), used by UI/business logic
    - client_slug (field): same as client_id for clarity
    - klaviyo_secret_name (field): klaviyo-api-<client_slug>
    """
    try:
        from app.services.client_key_resolver import ClientKeyResolver
        resolver = ClientKeyResolver()

        docs = list(db.collection('clients').stream())
        updated = 0
        for doc in docs:
            if not doc.exists:
                continue
            data = doc.to_dict() or {}
            name = data.get('name') or doc.id
            slug = resolver.normalize_client_name(name)
            update: dict = {}
            if not data.get('client_id'):
                update['client_id'] = slug
            if not data.get('client_slug'):
                update['client_slug'] = slug
            if not data.get('klaviyo_secret_name'):
                update['klaviyo_secret_name'] = f"klaviyo-api-{slug}"
            if update:
                db.collection('clients').document(doc.id).update(update)
                updated += 1

        return {"status": "success", "updated": updated, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign client ids: {e}")

@router.post("/clients/sync-5d")
async def sync_all_clients_last_5_days(background_tasks: BackgroundTasks):
    """Trigger a 5-day overwrite sync for all clients in the background."""
    try:
        service = KlaviyoDataService()
        background_tasks.add_task(service.run_daily_sync)
        return {"status": "success", "message": "5-day sync queued for all clients"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue 5-day sync: {e}")

@router.post("/clients/backfill-all")
async def backfill_all_clients(background_tasks: BackgroundTasks, sync: bool = False, db = Depends(get_db)):
    """Backfill the last 2 years for all clients.

    - sync=true: run now, return per-client results
    - sync=false: run in background
    """
    try:
        service = KlaviyoDataService()
        client_docs = list(db.collection('clients').stream())
        ids = [d.id for d in client_docs if d.exists]

        if sync:
            results = []
            for cid in ids:
                try:
                    res = await service.backfill_client_data(cid)
                    results.append(res)
                except Exception as e:
                    results.append({"client_id": cid, "error": str(e)})
            return {"status": "success", "results": results}

        def runner():
            import asyncio as _asyncio
            async def run_all():
                for cid in ids:
                    try:
                        await service.backfill_client_data(cid)
                    except Exception:
                        pass
            _asyncio.run(run_all())

        background_tasks.add_task(runner)
        return {"status": "success", "message": f"Backfill queued for {len(ids)} clients"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to backfill all clients: {e}")

@router.get("/system/status")
async def get_system_status(secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """Get comprehensive system status for admin dashboard"""
    try:
        # Get configuration from Secret Manager or environment
        slack_configured = bool(get_secret_value('SLACK_WEBHOOK_URL', secret_manager))
        gemini_configured = bool(get_secret_value('GEMINI_API_KEY', secret_manager))
        
        # Check MCP service status
        mcp_status = "not_configured"
        mcp_details = "MCP service not initialized"
        try:
            # Check if MCP server directory exists
            from pathlib import Path
            mcp_path = Path(__file__).parent.parent.parent / "email-sms-mcp-server"
            if mcp_path.exists():
                mcp_status = "operational"
                mcp_details = "MCP server available"
        except Exception:
            mcp_status = "error"
            mcp_details = "Failed to check MCP service"
        
        # Check Agent service status
        agent_status = "not_configured"
        agent_details = "Agent service not initialized"
        try:
            from app.services.agent_service import AgentService
            # Try to instantiate to check if it's available
            agent_service = AgentService()
            agent_status = "operational"
            agent_details = "Agent orchestrator ready"
        except ImportError:
            agent_status = "not_configured"
            agent_details = "Agent service not available"
        except Exception as e:
            agent_status = "error"
            agent_details = f"Agent service error: {str(e)[:50]}"
        
        return {
            "status": "healthy",
            "components": {
                "api": {
                    "status": "operational",
                    "details": "FastAPI server running"
                },
                "database": {
                    "status": "operational",
                    "details": "Using: Firestore"
                },
                "secret_manager": {
                    "status": "operational",
                    "details": f"Provider: GCP, Project: {get_settings().google_cloud_project}"
                },
                "mcp_service": {
                    "status": mcp_status,
                    "details": mcp_details
                },
                "agent_service": {
                    "status": agent_status,
                    "details": agent_details
                },
                "slack": {
                    "status": "operational" if slack_configured else "not_configured",
                    "details": "Webhook URL is set" if slack_configured else "No webhook URL configured"
                },
                "gemini": {
                    "status": "operational" if gemini_configured else "not_configured",
                    "details": "API key is set" if gemini_configured else "No API key configured"
                },
            },
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "debug": os.getenv('DEBUG', 'false').lower() == 'true',
            "secret_manager_enabled": True  # Always enabled in this architecture
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system status: {str(e)}"
        )

@router.get("/db/status")
async def get_db_status(db: firestore.Client = Depends(get_db)):
    """Database status check endpoint for admin dashboard"""
    try:
        # Test Firestore connection
        test_collection = db.collection('_health_check')
        test_doc = test_collection.document('admin_test')
        test_doc.set({'timestamp': datetime.utcnow().isoformat(), 'test': True})
        
        # Read it back
        doc = test_doc.get()
        if doc.exists:
            # Clean up
            test_doc.delete()
            
            return {
                "status": "operational",
                "database_type": "Firestore",
                "connection": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "test_write": "success",
                "test_read": "success"
            }
        else:
            raise Exception("Test document not found after write")
            
    except Exception as e:
        return {
            "status": "error",
            "database_type": "Firestore", 
            "connection": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/system/ui-status")
async def get_ui_status() -> Dict[str, Any]:
    """Quick frontend assets check to help diagnose blank UI issues."""
    try:
        base = Path("frontend/public")
        dist = base / "dist"
        utils = base / "utils"
        assets = {
            "index.html": base / "index.html",
            "router.js": base / "router.js",
            "dist/app.js": dist / "app.js",
            "dist/CalendarView.js": dist / "CalendarView.js",
            "dist/Calendar.js": dist / "Calendar.js",
            "dist/EventModal.js": dist / "EventModal.js",
            "dist/component-loader.js": dist / "component-loader.js",
            "dist/jsx-runtime-shim.js": dist / "jsx-runtime-shim.js",
            "utils/messaging-guard.js": utils / "messaging-guard.js",
            "styles/animations.css": base / "styles" / "animations.css",
        }
        results = {}
        for key, path in assets.items():
            try:
                exists = path.exists()
                size = path.stat().st_size if exists else 0
                results[key] = {"exists": exists, "size": size}
            except Exception:
                results[key] = {"exists": False, "size": 0}
        return {
            "status": "ok",
            "assets": results,
        }
    except Exception as e:
        logger.error(f"UI status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Diagnostics Summary ==========

@router.get("/diagnostics/summary")
async def diagnostics_summary(secret_manager: "SecretManagerService" = Depends(get_secret_manager_service)):
    """Aggregate a few health checks for quick diagnostics."""
    from app.utils.klaviyo_api import ensure_klaviyo_api_available, get_base_url
    import httpx
    out: Dict[str, Any] = {"success": True, "checks": {}, "timestamp": datetime.utcnow().isoformat()}
    # API
    out["checks"]["api"] = {"status": "ok"}
    # Klaviyo API
    try:
        await ensure_klaviyo_api_available()
        base = get_base_url()
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{base}/healthz")
        out["checks"]["klaviyo_api"] = {"status": "ok" if r.status_code == 200 else "error", "base": base}
    except Exception as e:
        out["checks"]["klaviyo_api"] = {"status": "error", "error": str(e)}
        out["success"] = False
    # Slack config
    try:
        webhook = None
        try:
            webhook = secret_manager.get_secret("emailpilot-slack-webhook-url")
        except Exception:
            pass
        if not webhook:
            webhook = os.getenv("SLACK_WEBHOOK_URL")
        out["checks"]["slack"] = {"configured": bool(webhook)}
    except Exception as e:
        out["checks"]["slack"] = {"configured": False, "error": str(e)}
        out["success"] = False
    # Weekly insights self-test
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get("http://127.0.0.1:8000/api/reports/mcp/v2/self-test", params={"limit_clients": 2, "metrics_only": True})
        if r.status_code == 200:
            data = r.json() or {}
            out["checks"]["weekly_self_test"] = {"status": "ok", "summary": data.get("summary")}
        else:
            out["checks"]["weekly_self_test"] = {"status": "error", "code": r.status_code}
            out["success"] = False
    except Exception as e:
        out["checks"]["weekly_self_test"] = {"status": "error", "error": str(e)}
        out["success"] = False
    return out

# REMOVED: Stub endpoint that was blocking the real Asana implementation
# The actual implementation is in app/api/admin_asana.py:433
# which is mounted at /api/admin/asana/configuration/clients-and-projects
# and properly fetches projects from Asana API

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
