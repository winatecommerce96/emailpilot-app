import json
import logging
import sys
import time
import uuid
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        for k in ("request_id", "session_id", "client_key", "route", "tool_name", "status", "latency_ms"):
            v = getattr(record, k, None)
            if v is not None:
                payload[k] = v
        return json.dumps(payload, separators=(",", ":"))


def setup_json_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def new_request_id() -> str:
    return uuid.uuid4().hex

