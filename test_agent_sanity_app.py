from fastapi import FastAPI
from app.api.agents import router as agents_router


def build_app() -> FastAPI:
    app = FastAPI(title="AgentService Sanity Test App")
    app.include_router(agents_router, prefix="/api/agents")
    return app


app = build_app()

