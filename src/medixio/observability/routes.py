from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from medixio.observability import obs
from medixio.observability.checks import run_checks, summary
from medixio.observability.dashboard import render


router = APIRouter(prefix="/obs")


def _events(limit: int, level: str | None = None) -> list[Any]:
    if level:
        return obs().query(
            "SELECT * FROM event WHERE level = ? ORDER BY ts DESC LIMIT ?",
            (level.upper(), limit),
        )
    return obs().query("SELECT * FROM event ORDER BY ts DESC LIMIT ?", (limit,))


@router.get("/status")
def status(request: Request) -> dict[str, Any]:
    return run_checks(obs(), getattr(request.app.state, "channel", None))


@router.get("/metrics")
def metrics(hours: int = Query(24, ge=1, le=24 * 30)) -> dict[str, Any]:
    return summary(obs(), hours)


@router.get("/events")
def events(
    limit: int = Query(100, ge=1, le=1000), level: str | None = None
) -> list[dict[str, Any]]:
    return [dict(r) for r in _events(limit, level)]


@router.get("/ratelimits")
def ratelimits(hours: int = Query(24, ge=1, le=48)) -> dict[str, Any]:
    from medixio import ratelimit

    return {
        "tokens_last_24h": ratelimit.tokens_last_day(),
        "blocked": ratelimit.blocked_numbers(hours),
    }


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request) -> str:
    return render(status(request), summary(obs(), 24), _events(50))
