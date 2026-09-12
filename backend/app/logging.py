import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    _fields = (
        "request_id",
        "operation",
        "outcome",
        "ticket_id",
        "investigation_id",
        "tool_name",
        "step_key",
        "source_count",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "component",
    )
    _field_limits = {"request_id": 128, "operation": 256, "path": 256}

    @staticmethod
    def _safe_string(value: object, limit: int = 256) -> str:
        text = str(value)
        return "".join(character for character in text if character.isprintable())[:limit]

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": self._safe_string(record.name, 128),
            "message": self._safe_string(record.getMessage(), 512),
        }
        for key in self._fields:
            if hasattr(record, key):
                value = getattr(record, key)
                payload[key] = (
                    value
                    if isinstance(value, (int, float, bool))
                    else self._safe_string(value, self._field_limits.get(key, 128))
                )
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
