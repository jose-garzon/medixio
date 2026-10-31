"""Local observability store: its own SQLite file, never patient content (design §12).

Kept apart from medixio.db so diagnostics can be inspected, copied or wiped without
touching patient data, and so observability writes never contend with app writes.
"""

import json
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS event (
    ts REAL NOT NULL,
    level TEXT NOT NULL,
    logger TEXT NOT NULL,
    message TEXT NOT NULL,
    exc_type TEXT,
    traceback TEXT
);
CREATE INDEX IF NOT EXISTS ix_event_ts ON event (ts);
CREATE TABLE IF NOT EXISTS metric (
    ts REAL NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    ok INTEGER NOT NULL,
    labels TEXT
);
CREATE INDEX IF NOT EXISTS ix_metric_name_ts ON metric (name, ts);
CREATE TABLE IF NOT EXISTS heartbeat (
    name TEXT PRIMARY KEY,
    ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS rate_event (
    ts REAL NOT NULL,
    subject TEXT NOT NULL,
    kind TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_rate_event ON rate_event (subject, kind, ts);
"""


class Store:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            path, check_same_thread=False, isolation_level=None
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=2000")
        self._conn.executescript(SCHEMA)
        self._lock = threading.Lock()

    def write(self, sql: str, params: tuple[Any, ...]) -> None:
        with self._lock:
            self._conn.execute(sql, params)

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.cursor()
            cur.row_factory = sqlite3.Row
            return list(cur.execute(sql, params).fetchall())

    def event(
        self,
        level: str,
        logger: str,
        message: str,
        exc_type: str | None = None,
        traceback: str | None = None,
    ) -> None:
        self.write(
            "INSERT INTO event VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), level, logger, message[:2000], exc_type, traceback),
        )

    def metric(self, name: str, value: float, ok: bool = True, **labels: Any) -> None:
        self.write(
            "INSERT INTO metric VALUES (?, ?, ?, ?, ?)",
            (time.time(), name, value, int(ok), json.dumps(labels) if labels else None),
        )

    def heartbeat(self, name: str) -> None:
        self.write(
            "INSERT INTO heartbeat VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET ts = excluded.ts",
            (name, time.time()),
        )

    @contextmanager
    def timer(self, name: str, **labels: Any) -> Iterator[dict[str, Any]]:
        """Record duration (seconds) and success. Callers may add labels to the dict."""
        extra: dict[str, Any] = dict(labels)
        start = time.perf_counter()
        ok = True
        try:
            yield extra
        except BaseException:
            ok = False
            raise
        finally:
            self.metric(name, time.perf_counter() - start, ok, **extra)

    def purge(self, older_than_days: int) -> None:
        cutoff = time.time() - older_than_days * 86400
        self.write("DELETE FROM event WHERE ts < ?", (cutoff,))
        self.write("DELETE FROM metric WHERE ts < ?", (cutoff,))
        self.write("DELETE FROM rate_event WHERE ts < ?", (time.time() - 2 * 86400,))
