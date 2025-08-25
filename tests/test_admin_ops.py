import os
import io
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _StubSecretManager:
    def get_secret(self, name: str):
        return None
    def list_secrets(self):
        return []


def build_app() -> FastAPI:
    from app.api import admin as admin_module
    app = FastAPI()
    app.include_router(admin_module.router, prefix="/api/admin")
    app.dependency_overrides[admin_module.get_secret_manager_service] = lambda: _StubSecretManager()
    return app


@pytest.fixture(scope="module")
def client():
    app = build_app()
    with TestClient(app) as c:
        yield c


def test_logs_large_and_cleanup(client: TestClient, tmp_path):
    # Create a logs dir and a >1K log file
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    bigfile = os.path.join(logs_dir, "test_smoke_big.log")
    with open(bigfile, "wb") as f:
        f.write(b"X" * 2048)

    # List with small threshold
    r = client.get("/api/admin/ops/logs/large", params={"threshold": "1K"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    # Clean by truncation
    r2 = client.post("/api/admin/ops/logs/cleanup", json={"mode": "truncate", "threshold": "1K"})
    assert r2.status_code == 200
    # Verify file truncated
    assert os.path.exists(bigfile)
    assert os.stat(bigfile).st_size == 0


def test_revenue_status_handles_unreachable(client: TestClient):
    # Point to an unreachable base; expect error fields rather than crash
    r = client.get(
        "/api/admin/revenue/status",
        params={"base": "http://127.0.0.1:0", "origin": "http://localhost:3000"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["base"].startswith("http://127.0.0.1")
    # One of the probe sections should indicate an error
    assert "preflight_error" in body or "healthz_error" in body or body.get("preflight_status") in (0, None)

