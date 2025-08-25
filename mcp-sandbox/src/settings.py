import os
from functools import lru_cache


class Settings:
    app_auth_bearer: str = os.getenv("APP_AUTH_BEARER", "change-me")
    project_id: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    cors_origins: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "900"))
    use_inmemory: bool = os.getenv("SANDBOX_USE_INMEMORY", "0") == "1"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

