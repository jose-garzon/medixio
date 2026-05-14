# Medixio

WhatsApp chatbot that helps people with complex illnesses manage medical appointments. Users interact with the bot over WhatsApp to create, list, and get reminders for their appointments.

## Stack

- **Python 3.12** managed by [uv](https://github.com/astral-sh/uv)
- **neonize** — WhatsApp client (multi-device, QR pairing) built on top of `whatsmeow`
- **FastAPI** — HTTP API for admin endpoints and health checks
- **SQLModel** + **Alembic** — Postgres ORM and migrations
- **psycopg 3** — Postgres driver
- **ruff** — lint and format

The app runs the FastAPI server and the WhatsApp event loop together in a single process via `asyncio`. The WhatsApp client persists its session to a local SQLite file (managed by neonize); application data (appointments, notifications) lives in Postgres.

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Install Python and dependencies:

   ```bash
   uv sync
   ```

3. Copy env template and adjust:

   ```bash
   cp .env.example .env
   ```

4. Start Postgres (use your own instance or docker), then run migrations:

   ```bash
   uv run alembic upgrade head
   ```

5. Run the app:

   ```bash
   uv run medixio
   ```

   On first start neonize prints a QR code in the terminal. Scan it from WhatsApp (Settings → Linked Devices → Link a Device).

## Common commands

| Command | What it does |
|---------|--------------|
| `uv sync` | Install/update deps from `pyproject.toml` |
| `uv run medixio` | Run the chatbot (FastAPI + WhatsApp worker) |
| `uv run uvicorn medixio.main:app --reload` | API-only with hot reload |
| `uv run alembic revision --autogenerate -m "msg"` | Create new migration |
| `uv run alembic upgrade head` | Apply migrations |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv run pytest` | Run tests |

## Layout

```
src/medixio/
├── main.py          # Entrypoint: starts FastAPI + WA worker
├── config.py        # Settings (pydantic-settings, reads .env)
├── db.py            # SQLModel engine and session helpers
├── api/             # FastAPI routes
├── whatsapp/        # neonize client + message handlers
├── worker/          # Background scheduler (reminders)
└── models/          # SQLModel tables
alembic/             # Migrations
```

## Disclaimer

neonize is an **unofficial** WhatsApp client. Using it may violate WhatsApp's Terms of Service and can lead to account bans. For production use prefer the [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api).
