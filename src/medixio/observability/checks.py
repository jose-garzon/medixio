"""Health checks: each returns ok / warn / fail with a short human reason."""

import shutil
import time
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import text
from sqlmodel import Session

from medixio import knowledge
from medixio.config import get_settings
from medixio.db import engine
from medixio.modules.reminders import service as reminders
from medixio.observability.store import Store
from medixio.shared.time import utcnow


Status = Literal["ok", "warn", "fail"]
_RANK = {"ok": 0, "warn": 1, "fail": 2}


@dataclass
class Check:
    name: str
    status: Status
    detail: str


def _db() -> Check:
    try:
        with Session(engine) as s:
            s.connection().execute(text("SELECT 1"))
            result = s.connection().execute(text("PRAGMA quick_check")).scalar()
    except Exception as exc:
        return Check("database", "fail", f"{type(exc).__name__}: {exc}")
    if result != "ok":
        return Check("database", "fail", f"quick_check: {result}")
    return Check("database", "ok", "reachable, integrity ok")


def _whatsapp(channel: Any) -> Check:
    if not get_settings().whatsapp_enabled:
        return Check("whatsapp", "ok", "disabled by config")
    connected = getattr(channel, "connected", None)
    if connected is not None and connected.is_set():
        return Check("whatsapp", "ok", "connected")
    return Check("whatsapp", "fail", "not connected (pair QR or check ban/network)")


def _heartbeat(store: Store, name: str, max_age: float, enabled: bool) -> Check:
    if not enabled:
        return Check(name, "ok", "disabled by config")
    rows = store.query("SELECT ts FROM heartbeat WHERE name = ?", (name,))
    if not rows:
        return Check(name, "warn", "no heartbeat yet")
    age = time.time() - rows[0]["ts"]
    if age > max_age:
        return Check(name, "fail", f"last heartbeat {age:.0f}s ago")
    return Check(name, "ok", f"last heartbeat {age:.0f}s ago")


def _overdue_reminders() -> Check:
    from medixio.scheduler import in_quiet_hours

    now = utcnow()
    if in_quiet_hours(now):
        return Check("reminders_backlog", "ok", "quiet hours, sending paused")
    limit = now - timedelta(minutes=15)
    with Session(engine) as s:
        overdue = [occ for _, occ in reminders.due(s, now) if occ < limit]
    if not overdue:
        return Check("reminders_backlog", "ok", "no overdue reminders")
    oldest = (now - min(overdue)).total_seconds() / 60
    return Check(
        "reminders_backlog",
        "fail" if len(overdue) > 10 or oldest > 120 else "warn",
        f"{len(overdue)} overdue, oldest {oldest:.0f} min",
    )


def _errors(store: Store) -> Check:
    since = time.time() - 3600
    rows = store.query(
        "SELECT level, COUNT(*) AS n FROM event WHERE ts >= ? GROUP BY level", (since,)
    )
    counts = {r["level"]: r["n"] for r in rows}
    errors = counts.get("ERROR", 0) + counts.get("CRITICAL", 0)
    warns = counts.get("WARNING", 0)
    status: Status = (
        "fail" if errors >= 10 else "warn" if errors or warns > 20 else "ok"
    )
    return Check("errors_last_hour", status, f"{errors} errors, {warns} warnings")


def _agent(store: Store) -> Check:
    since = time.time() - 3600
    rows = store.query(
        "SELECT value, ok FROM metric WHERE name = 'agent.run' AND ts >= ? "
        "ORDER BY value",
        (since,),
    )
    if not rows:
        return Check("agent", "ok", "no runs in the last hour")
    failures = sum(1 for r in rows if not r["ok"])
    rate = failures / len(rows)
    p95 = rows[min(len(rows) - 1, int(len(rows) * 0.95))]["value"]
    status: Status = (
        "fail" if rate > 0.5 else "warn" if rate > 0.1 or p95 > 15 else "ok"
    )
    return Check(
        "agent",
        status,
        f"{len(rows)} runs, {failures} failed ({rate:.0%}), p95 {p95:.1f}s",
    )


def _disk() -> Check:
    url = get_settings().database_url
    path = (
        Path(url.removeprefix("sqlite:///")) if url.startswith("sqlite:///") else None
    )
    folder = path.parent if path else Path(".")
    free_gb = shutil.disk_usage(folder if folder.exists() else ".").free / 1e9
    size_mb = path.stat().st_size / 1e6 if path and path.exists() else 0.0
    status: Status = "fail" if free_gb < 0.5 else "warn" if free_gb < 2 else "ok"
    return Check("disk", status, f"{free_gb:.1f} GB free, db {size_mb:.1f} MB")


def _knowledge() -> Check:
    pending = knowledge.unreviewed()
    if pending:
        return Check(
            "knowledge_review", "warn", f"{len(pending)} rules/guides not reviewed"
        )
    return Check("knowledge_review", "ok", "all reviewed")


def _rate_limits() -> Check:
    from medixio import ratelimit

    budget = get_settings().daily_token_budget
    used = ratelimit.tokens_last_day()
    share = used / budget if budget else 0.0
    blocked = ratelimit.blocked_numbers(24)
    detail = f"tokens 24h {used:,} / {budget:,} ({share:.0%})"
    if blocked:
        numbers = {b["number"] for b in blocked}
        detail += f"; {len(numbers)} number(s) rate limited"
    status: Status = (
        "fail" if share >= 1 else "warn" if share >= 0.8 or blocked else "ok"
    )
    return Check("rate_limits", status, detail)


def run_checks(store: Store, channel: Any) -> dict[str, Any]:
    settings = get_settings()
    checks = [
        _db(),
        _whatsapp(channel),
        _heartbeat(
            store,
            "scheduler",
            settings.scheduler_tick_seconds * 3,
            settings.scheduler_enabled and settings.whatsapp_enabled,
        ),
        _overdue_reminders(),
        _agent(store),
        _errors(store),
        _rate_limits(),
        _disk(),
        _knowledge(),
    ]
    worst = max(checks, key=lambda c: _RANK[c.status]).status
    return {"status": worst, "checks": [asdict(c) for c in checks]}


def summary(store: Store, hours: int = 24) -> dict[str, Any]:
    """Aggregates per metric name over the window."""
    since = time.time() - hours * 3600
    rows = store.query(
        "SELECT name, COUNT(*) AS n, SUM(1 - ok) AS failed, AVG(value) AS avg, "
        "MAX(value) AS max, SUM(value) AS total "
        "FROM metric WHERE ts >= ? GROUP BY name ORDER BY name",
        (since,),
    )
    return {
        r["name"]: {
            "count": r["n"],
            "failed": r["failed"],
            "avg": round(r["avg"], 3),
            "max": round(r["max"], 3),
            "total": round(r["total"], 3),
        }
        for r in rows
    }
