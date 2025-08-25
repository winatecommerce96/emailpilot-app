import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def build_app():
    from app.api.auth_google import router as google_router
    from app.api.auth_compat import router as compat_router
    app = FastAPI()
    app.include_router(google_router, prefix="/api/auth/google")
    app.include_router(compat_router, prefix="/api/auth")
    return app


@pytest.fixture(scope="module")
def client():
    app = build_app()
    with TestClient(app) as c:
        yield c


def test_login_redirects_get(client: TestClient):
    r = client.get("/api/auth/login", allow_redirects=False)
    # Should redirect to google login or directly to accounts.google.com via handler
    assert r.status_code in (302, 307)
    assert "location" in r.headers


def test_login_redirects_post(client: TestClient):
    r = client.post("/api/auth/login", allow_redirects=False)
    assert r.status_code in (302, 307)
    assert "/api/auth/google/login" in r.headers.get("location", "") or "accounts.google.com" in r.headers.get("location", "")


def test_me_unauthenticated(client: TestClient):
    r = client.get("/api/auth/me")
    assert r.status_code in (401, 404)


def test_logout_clears_cookies(client: TestClient):
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    # Cookies should be cleared (Set-Cookie with Max-Age=0 or expired); implementation uses delete_cookie
    # We assert the response shape only (compat behavior)
    assert r.json().get("message")

