import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _StubSecretManager:
    def get_secret(self, name: str) -> str | None:
        return None

    def list_secrets(self):
        return []


def build_app() -> FastAPI:
    from app.api import admin as admin_module
    app = FastAPI()
    # Mount admin router under /api/admin
    app.include_router(admin_module.router, prefix="/api/admin")
    # Dependency override for Secret Manager service
    app.dependency_overrides[admin_module.get_secret_manager_service] = lambda: _StubSecretManager()
    return app


@pytest.fixture(scope="module")
def client():
    app = build_app()
    with TestClient(app) as c:
        yield c


def test_admin_system_status(client: TestClient):
    r = client.get("/api/admin/system/status")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status")
    assert "components" in data

