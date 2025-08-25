import logging
import os
import json
from logging.handlers import RotatingFileHandler


def setup_rotating_file_logging(
    logger_name: str,
    logfile: str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    level: int = logging.INFO,
):
    """Attach a RotatingFileHandler to the named logger.

    - Creates the parent directory for `logfile` if needed.
    - Skips if a RotatingFileHandler is already attached.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Determine logfile path
    if logfile is None:
        log_dir = os.environ.get("LOG_DIR", os.path.join("logs"))
        os.makedirs(log_dir, exist_ok=True)
        logfile = os.path.join(log_dir, f"{logger_name}.log")
    else:
        os.makedirs(os.path.dirname(logfile) or ".", exist_ok=True)

    # Skip if already added
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler):
            return logger

    handler = RotatingFileHandler(logfile, maxBytes=max_bytes, backupCount=backup_count)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def setup_json_console_logging(level: int = logging.INFO):
    """Configure root logger for JSON console logging (Cloud Run friendly)."""
    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicating handlers
    if any(isinstance(h, logging.StreamHandler) and getattr(h, "_json", False) for h in root.handlers):
        return root

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
            # Common extras
            for key in ("request_id", "path", "method", "status_code", "duration_ms"):
                if hasattr(record, key):
                    payload[key] = getattr(record, key)
            return json.dumps(payload)

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(JsonFormatter())
    sh._json = True  # mark to avoid duplication
    root.addHandler(sh)
    return root
