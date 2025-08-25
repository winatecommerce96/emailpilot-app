import time
import threading
import os
from typing import Callable, Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse


class SimpleRateLimiter:
    def __init__(self, max_per_window: int, window_seconds: int):
        self.max = max_per_window
        self.win = window_seconds
        self.lock = threading.Lock()
        self.bucket: Dict[Tuple[str, str], Tuple[int, float]] = {}

    def allow(self, key: Tuple[str, str]) -> bool:
        now = time.time()
        with self.lock:
            count, reset = self.bucket.get(key, (0, now + self.win))
            # reset window
            if now > reset:
                count, reset = 0, now + self.win
            count += 1
            self.bucket[key] = (count, reset)
            return count <= self.max


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, default_max: int = 120, default_window: int = 60, path_limits: Dict[str, Tuple[int, int]] | None = None):
        super().__init__(app)
        self.default = SimpleRateLimiter(default_max, default_window)
        self.paths: Dict[str, SimpleRateLimiter] = {}
        path_limits = path_limits or {}
        for path, (mx, win) in path_limits.items():
            self.paths[path] = SimpleRateLimiter(mx, win)

    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.headers.get('x-forwarded-for', '').split(',')[0].strip() or request.client.host
        path = request.url.path
        key = (client_ip, path)
        limiter = self.paths.get(path) or self.default
        if not limiter.allow(key):
            return PlainTextResponse("Too Many Requests", status_code=429)
        return await call_next(request)

