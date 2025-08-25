"""
Klaviyo API Helper
- Ensures the local Klaviyo API service (formerly Revenue API) is running
- Provides a consistent base URL from env with sensible fallbacks
"""

import os
import sys
from pathlib import Path
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)


def get_base_url() -> str:
    """Return the configured Klaviyo API base URL.

    Prefers KLAVIYO_API_BASE; falls back to REVENUE_API_BASE for backward compatibility,
    then http://localhost:9090.
    """
    return (
        os.getenv("KLAVIYO_API_BASE")
        or os.getenv("REVENUE_API_BASE")
        or "http://localhost:9090"
    )


async def ensure_klaviyo_api_available(timeout_seconds: float = 10.0) -> str:
    """Ensure the Klaviyo API is available.

    - If /healthz is healthy, returns immediately.
    - Otherwise, attempts to start uvicorn for services.revenue_api.main:app (compat path).
      The underlying service still lives under services/revenue_api; naming is being
      transitioned to "Klaviyo API".

    Returns: the base URL string.
    """
    base = get_base_url()

    # Quick health check
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"{base}/healthz")
            if r.status_code == 200:
                return base
    except Exception:
        pass

    # Try to start the service (dev convenience)
    logger.info("Klaviyo API not responding; attempting to start it...")
    try:
        import subprocess
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(exist_ok=True)
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "services.klaviyo_api.main:app",
            "--host",
            os.getenv("KLAVIYO_API_HOST", "127.0.0.1"),
            "--port",
            str(int(os.getenv("KLAVIYO_API_PORT", os.getenv("REVENUE_API_PORT", "9090")))),
        ]
        env = os.environ.copy()
        if "GOOGLE_CLOUD_PROJECT" not in env:
            env["GOOGLE_CLOUD_PROJECT"] = env.get(
                "REVENUE_PROJECT_ID",
                env.get("GOOGLE_CLOUD_PROJECT", "emailpilot-438321"),
            )
        with open(log_dir / "klaviyo_api_uvicorn.out", "ab") as lf:
            subprocess.Popen(cmd, stdout=lf, stderr=lf, env=env)
    except Exception as e:
        logger.warning(f"Could not auto-start Klaviyo API: {e}")
        return base

    # Wait for readiness
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        try:
            async with httpx.AsyncClient(timeout=1.5) as c:
                r = await c.get(f"{base}/healthz")
                if r.status_code == 200:
                    logger.info("Klaviyo API is up")
                    return base
        except Exception:
            pass
        await asyncio.sleep(0.5)
    logger.warning("Klaviyo API failed to become ready in time")
    return base
