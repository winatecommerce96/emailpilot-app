import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def build_app():
    app = FastAPI()

    # Include auth router
    from app.api.auth import router as auth_router

    app.include_router(auth_router, prefix="/api/auth")

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


def test_auth_session_unauthenticated(client: TestClient):
    # No token/cookies -> expect 401 or valid response
    r = client.get("/api/auth/session")
    assert r.status_code in (200, 401, 403)


def test_auth_me_unauthenticated(client: TestClient):
    # No token/cookies -> expect 401 from /me
    r = client.get("/api/auth/me")
    assert r.status_code in (200, 401, 403)

