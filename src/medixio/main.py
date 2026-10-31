import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from medixio import scheduler
from medixio.api import admin, router
from medixio.channel.base import Channel
from medixio.config import get_settings
from medixio.handler import handle
from medixio.observability import obs
from medixio.observability.logs import setup_logging


log = logging.getLogger("medixio")


def _make_channel() -> Channel | None:
    settings = get_settings()
    if not settings.whatsapp_enabled:
        return None
    from medixio.channel.neonize_adapter import NeonizeChannel

    return NeonizeChannel(settings.wa_session_db)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    channel = _make_channel()
    app.state.channel = channel
    tasks: list[asyncio.Task[None]] = []
    if channel is not None:
        tasks.append(asyncio.create_task(channel.run(handle), name="whatsapp"))
        if settings.scheduler_enabled:
            tasks.append(asyncio.create_task(scheduler.run(channel), name="scheduler"))
    tasks.append(asyncio.create_task(_housekeeping(), name="observability"))
    log.info("medixio started whatsapp=%s", channel is not None)
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
    log.info("medixio stopped")


async def _housekeeping() -> None:
    days = get_settings().observability_retention_days
    while True:
        try:
            obs().purge(days)
        except Exception:
            log.exception("observability purge failed")
        await asyncio.sleep(3600)


app = FastAPI(title="medixio", lifespan=lifespan)
app.include_router(router)
app.include_router(admin)


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
WEAK_TOKENS = {"", "change-me"}


def check_admin_exposure() -> None:
    """Refuse to serve /admin/* on a non-local interface without a real token."""
    settings = get_settings()
    token = settings.admin_token or ""
    if settings.api_host not in LOCAL_HOSTS and (
        token in WEAK_TOKENS or len(token) < 16
    ):
        raise SystemExit(
            f"API_HOST={settings.api_host} exposes /admin: set ADMIN_TOKEN "
            "(16+ random chars, e.g. `openssl rand -hex 24`)"
        )


def run() -> None:
    settings = get_settings()
    check_admin_exposure()
    setup_logging(settings.log_level, settings.json_logs, obs())
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
