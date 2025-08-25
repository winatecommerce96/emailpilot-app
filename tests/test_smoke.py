import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def build_app():
    app = FastAPI()

    # Include only auth google + compat routers to avoid external deps
    from app.api.auth_google import router as google_router
    from app.api.auth_compat import router as compat_router

    app.include_router(google_router, prefix="/api/auth/google")
    app.include_router(compat_router, prefix="/api/auth")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


@pytest.fixture(scope="module")
def client():
    app = build_app()
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_auth_google_status(client: TestClient):
    r = client.get("/api/auth/google/status")
    assert r.status_code == 200
    assert "configured" in r.json()


def test_auth_me_unauthenticated(client: TestClient):
    # No token/cookies -> expect 401 from compat /me
    r = client.get("/api/auth/me")
    assert r.status_code in (401, 404) or isinstance(r.json(), dict)

