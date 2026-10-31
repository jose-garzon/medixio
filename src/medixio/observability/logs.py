import json
import logging
import traceback
from datetime import UTC, datetime

from medixio.observability.store import Store


class StoreHandler(logging.Handler):
    """Persist WARNING+ log records so problems survive restarts and log rotation."""

    def __init__(self, store: Store) -> None:
        super().__init__(level=logging.WARNING)
        self.store = store

    def emit(self, record: logging.LogRecord) -> None:
        try:
            exc_type = tb = None
            if record.exc_info and record.exc_info[0] is not None:
                exc_type = record.exc_info[0].__name__
                tb = "".join(traceback.format_exception(*record.exc_info))[-8000:]
            self.store.event(
                record.levelname, record.name, record.getMessage(), exc_type, tb
            )
        except Exception:
            self.handleError(record)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str, json_logs: bool, store: Store) -> None:
    stream = logging.StreamHandler()
    stream.setFormatter(
        JsonFormatter()
        if json_logs
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [stream, StoreHandler(store)]
