# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Medixio is a WhatsApp chatbot (Python) that helps people manage medical appointments. There is no web frontend — users interact exclusively through WhatsApp messages. An earlier version of this project was a Vite/React/IndexedDB SPA; it was scrapped and the repo was restarted as a Python service. Git history before `1c5f6d1` is the old TS app and is not relevant.

## Stack

- **Python 3.12**, managed by **uv** (`uv sync`, `uv run …`).
- **neonize** — unofficial Python WhatsApp client built on `whatsmeow` (Go, multi-device protocol). QR pairing on first run; session persisted to a SQLite file at `WA_SESSION_DB`. Using neonize may violate WhatsApp ToS — keep this in mind when suggesting features that could trip anti-abuse heuristics (bulk sends, scraping, etc.).
- **FastAPI + uvicorn** — HTTP layer for health/admin endpoints. Runs in the same process as the WA worker.
- **SQLModel** (Pydantic + SQLAlchemy) on **Postgres** via **psycopg 3**. Migrations through **Alembic**.
- **ruff** for lint + format. **pytest** + **pytest-asyncio** for tests.

Two databases coexist: a local SQLite file owned by neonize (WA session/keys) and Postgres (app data — appointments, notifications). Don't conflate them.

## Process topology

`medixio.main` is the single entrypoint. It builds the FastAPI `app` and, via the lifespan context, spawns two `asyncio` tasks alongside the HTTP server:

1. `whatsapp.client.run_client` — connects to WhatsApp, dispatches `MessageEv` to `whatsapp.handlers.handle_message`.
2. `worker.scheduler.run_scheduler` — periodic loop that will scan Postgres for due notifications and send them through the WA client.

The scheduler needs a handle to the connected WA client to actually send messages. Right now it's a stub; when wiring it up, share the client through a module-level singleton or pass it via app state rather than building a second client.

## Common commands

```bash
uv sync                                        # install deps
uv run medixio                                 # run full app (API + WA + scheduler)
uv run uvicorn medixio.main:app --reload       # API only, hot reload (no WA worker if lifespan is bypassed)
uv run alembic revision --autogenerate -m "x"  # new migration
uv run alembic upgrade head                    # apply migrations
uv run ruff check . && uv run ruff format .    # lint + format
uv run pytest                                  # all tests
uv run pytest tests/path::test_name            # one test
```

## Module map

```
src/medixio/
├── main.py        # FastAPI app + lifespan that starts WA + scheduler tasks
├── config.py      # pydantic-settings Settings, loaded from .env via get_settings()
├── db.py          # SQLModel engine + Session generator (used by FastAPI deps)
├── api/           # FastAPI routers; aggregated in api/__init__.py:api_router
├── whatsapp/
│   ├── client.py    # build_client() registers neonize event handlers; run_client() connects
│   └── handlers.py  # handle_message(client, event) — command dispatch lives here
├── worker/scheduler.py  # async tick loop for reminders
└── models/        # SQLModel tables; import every model in models/__init__.py
                  # so Alembic autogenerate sees them
alembic/           # env.py imports medixio.models and uses SQLModel.metadata
```

## Conventions specific to this project

- **Spanish-facing copy.** User-visible strings (WhatsApp replies, error messages shown to end users) are in Spanish. Code, comments, identifiers stay in English.
- **Phone number format.** International format with leading `+` and country code (e.g. `+573002346892`). Strip non-digits before passing to WhatsApp JIDs.
- **Domain reminders.** The old app scheduled three notifications per appointment: 1 day before, 30 min before, 1 hour after ("how did it go?"). Reuse this pattern when porting the notification model unless asked otherwise.
- **Settings access.** Always go through `get_settings()` (cached). Don't read env vars directly inside modules.
- **Alembic autogenerate visibility.** Any new SQLModel table must be importable from `medixio.models` (re-export in `models/__init__.py`) or autogenerate will silently miss it.
- **No frontend.** Don't add HTML templates, static assets, JS, or framework UIs. If something needs admin visibility, expose it as a FastAPI JSON endpoint.

## Environment

`.env` is loaded by `pydantic-settings`. See `.env.example` for the canonical keys. `DATABASE_URL` must use the `postgresql+psycopg://` scheme (SQLAlchemy + psycopg 3 driver), not `postgres://` or `postgresql://`.
