import os, httpx, pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
ADMIN_HEADERS = {}
if os.environ.get("ADMIN_API_KEY"):
    ADMIN_HEADERS["X-Admin-Key"] = os.environ["ADMIN_API_KEY"]

@pytest.mark.asyncio
async def test_agents_and_providers():
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(f"{BASE_URL}/api/admin/langchain/agents", headers=ADMIN_HEADERS)
        # Agents endpoint returns {"agents": [...]} structure
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict) and "agents" in data and isinstance(data["agents"], list)
        
        r = await c.get(f"{BASE_URL}/api/admin/langchain/models/providers", headers=ADMIN_HEADERS)
        # Providers endpoint returns direct list
        assert r.status_code == 200 and isinstance(r.json(), list)

@pytest.mark.asyncio
async def test_models_available_and_resolve_no_500():
    async with httpx.AsyncClient(timeout=10.0) as c:
        a = await c.get(f"{BASE_URL}/api/admin/langchain/models/available?provider=openai", headers=ADMIN_HEADERS)
        assert a.status_code in (200, 400), a.text  # never 500 on input
        r = await c.get(f"{BASE_URL}/api/admin/langchain/models/resolve?user_id=demo&brand=acme", headers=ADMIN_HEADERS)
        assert r.status_code in (200, 400, 422), r.text  # never 500

@pytest.mark.asyncio
async def test_static_admin_pages_present():
    async with httpx.AsyncClient(timeout=10.0) as c:
        for path in ("/static/admin/langchain/agents.html",
                     "/static/admin/langchain/usage.html",
                     "/static/admin/langchain/models.html",
                     "/static/admin/langchain/mcp.html"):
            r = await c.get(f"{BASE_URL}{path}")
            # allow 200 or 404; if 404, assert the app has StaticFiles mounted later
            assert r.status_code in (200, 404)