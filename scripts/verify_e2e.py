#!/usr/bin/env python3
"""
EmailPilot End-to-End Verifier

Runs a sequence of HTTP checks against a locally running EmailPilot backend
and auxiliary services to validate expected behavior end-to-end.

What it checks:
- Main backend health (/health)
- AI providers status (/api/ai-models/providers)
- Agent config presence (/api/agent-config/agents)
- Klaviyo API health (starts via admin alias, then GET :9090/healthz)
- Weekly insights generation in preview mode (/api/reports/mcp/v2/weekly/insights)
- Model list and a simple model chat call (if any provider with key)
- Basic agent invocation (/api/agents/invoke)

Usage:
  1) Ensure the backend is running locally on http://localhost:8000
  2) python scripts/verify_e2e.py

Environment:
  EP_BASE: override backend base URL (default http://localhost:8000)
  KLAVIYO_BASE: override Klaviyo API base URL (default http://127.0.0.1:9090)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


BASE = os.environ.get("EP_BASE", "http://localhost:8000").rstrip("/")
KLAVIYO = os.environ.get("KLAVIYO_BASE", "http://127.0.0.1:9090").rstrip("/")
TIMEOUT = 5.0


def _req(method: str, url: str, data: Optional[Dict[str, Any]] = None, timeout: float = TIMEOUT) -> tuple[int, dict | str]:
    headers = {"User-Agent": "emailpilot-verify/1.0"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in ctype:
                try:
                    return resp.status, json.loads(raw.decode("utf-8"))
                except Exception:
                    return resp.status, raw.decode("utf-8", errors="replace")
            return resp.status, raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = str(e)
        return e.code, raw
    except Exception as e:
        return 0, str(e)


def get(path: str) -> tuple[int, dict | str]:
    return _req("GET", f"{BASE}{path}")


def post(path: str, payload: Dict[str, Any]) -> tuple[int, dict | str]:
    return _req("POST", f"{BASE}{path}", payload)


def main() -> int:
    print(f"Backend base: {BASE}")
    print(f"Klaviyo base: {KLAVIYO}")
    print("\nStep 1: Backend health ...", flush=True)
    code, body = get("/health")
    ok_backend = code == 200 and isinstance(body, dict) and body.get("status") == "ok"
    print(f"  /health: {code} {body if not isinstance(body, dict) else body.get('status')}")

    print("\nStep 2: AI providers status ...", flush=True)
    code, body = get("/api/ai-models/providers")
    providers_with_keys = 0
    if code == 200 and isinstance(body, dict):
        providers = body.get("providers") or []
        providers_with_keys = sum(1 for p in providers if p.get("has_key"))
    print(f"  providers: HTTP {code}; with keys: {providers_with_keys}")

    print("\nStep 3: Agent config list ...", flush=True)
    code, body = get("/api/agent-config/agents")
    if code == 200:
        if isinstance(body, dict) and body.get("agents"):
            print(f"  agents: {len(body['agents'])} found")
        else:
            print(f"  agents response: {body}")
    else:
        print(f"  agents: HTTP {code} {body}")

    print("\nStep 4: Ensure Klaviyo service is running ...", flush=True)
    # Try to start via admin alias; ignore failures
    post("/api/admin/klaviyo/start", {"host": "127.0.0.1", "port": 9090})
    # Probe healthz with a few retries
    kl_ok = False
    for i in range(6):
        code_k, body_k = _req("GET", f"{KLAVIYO}/healthz")
        if code_k == 200:
            kl_ok = True
            break
        time.sleep(0.5)
    print(f"  :9090/healthz: {'OK' if kl_ok else f'HTTP {code_k}'}")

    print("\nStep 5: Weekly insights (preview) ...", flush=True)
    code, body = post("/api/reports/mcp/v2/weekly/insights", {"preview": True})
    ok_insights = code == 200 and isinstance(body, dict)
    print(f"  insights: HTTP {code}")

    print("\nStep 6: List models for a keyed provider ...", flush=True)
    chosen_provider: Optional[str] = None
    if providers_with_keys:
        # fetch providers again to pick first having has_key
        code_p, body_p = get("/api/ai-models/providers")
        if code_p == 200 and isinstance(body_p, dict):
            for p in (body_p.get("providers") or []):
                if p.get("has_key"):
                    chosen_provider = p.get("name")
                    break
    if not chosen_provider:
        print("  skip: no provider with API key configured")
    else:
        code_m, body_m = get(f"/api/ai-models/models?provider={urllib.parse.quote(chosen_provider)}")
        print(f"  models[{chosen_provider}]: HTTP {code_m}")
        # Try a tiny chat call if models returned
        model_name = None
        if code_m == 200 and isinstance(body_m, dict):
            models = body_m.get("models") or []
            if models:
                # models can be strings or objects; normalize
                first = models[0]
                model_name = first.get("id") if isinstance(first, dict) else str(first)
        if model_name:
            payload = {
                "provider": chosen_provider,
                "model": model_name,
                "messages": [{"role": "user", "content": "Ping?"}],
                "temperature": 0.0,
                "max_tokens": 8,
            }
            code_c, body_c = post("/api/ai-models/chat/complete", payload)
            print(f"  chat: HTTP {code_c}")
        else:
            print("  skip: no model discovered to chat with")

    print("\nStep 7: Basic agent invocation ...", flush=True)
    code_a, body_a = post("/api/agents/invoke", {
        "campaign_type": "promotional",
        "target_audience": "high-value customers",
        "objectives": ["increase_sales", "drive_engagement"],
    })
    print(f"  agent invoke: HTTP {code_a}")

    # Summary
    print("\nSummary:")
    print(f"  Backend health: {'PASS' if ok_backend else 'FAIL'}")
    print(f"  Providers configured: {'YES' if providers_with_keys else 'NO'}")
    print(f"  Klaviyo service: {'PASS' if kl_ok else 'FAIL'}")
    print(f"  Weekly insights: {'PASS' if ok_insights else 'FAIL'}")
    # Return non-zero if critical checks fail
    exit_code = 0
    if not ok_backend:
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

