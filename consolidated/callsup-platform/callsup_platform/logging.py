import json
import logging
from datetime import datetime, timezone

from .config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": "svc-platform",
            "module": "platform",
            "event": getattr(record, "event", "application.log"),
            "request_id": getattr(record, "request_id", None),
            "business_id": getattr(record, "business_id", None),
        }
        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    logger = logging.getLogger("callsup_platform")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.info(
        "logger configured",
        extra={"event": "platform.logging.configured", "request_id": None, "business_id": None},
    )

