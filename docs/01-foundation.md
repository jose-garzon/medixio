# 01 — Foundation: config, SQLite, Alembic, `/health`, Docker

> **Goal:** a long-running `medixio` process that reads config from env, opens a SQLite database with the right PRAGMAs, applies Alembic migrations on start, serves `GET /health`, and runs in Docker compose with its data on a bind volume. No agent, no WhatsApp yet.
>
> Implements design §1 (lifespan skeleton), §2, §3, §9. Milestone 1 of design §12.

---

## Why this step exists

Every later milestone needs the same base: settings, a DB session, migrations, and a deployable container. Doing it while there is no business logic means problems with tooling, paths, and volumes show up on their own instead of mixed with agent bugs.

You'll learn:

- How `pydantic-settings` turns env vars into a typed `Settings` object.
- Why SQLite needs WAL mode, `foreign_keys=ON`, and `busy_timeout` for a server process.
- How Alembic works with SQLite (`render_as_batch=True`) and why we run it on container start.
- How FastAPI's `lifespan` will host the WhatsApp client and scheduler later.
- How a bind volume keeps `medixio.db` alive across container rebuilds.

## Prerequisites

- Repo as it is today: `uv`, `ruff`, `mypy --strict`, `pytest`, `justfile` already set up.
- Docker Engine + `docker compose` plugin.

## Concepts

**pydantic-settings.** A `BaseSettings` subclass reads fields from env vars (and `.env`), validates types, and fails fast at startup if something is missing. One object, imported everywhere, instead of scattered `os.getenv`.

**SQLite in a server.** SQLite is a file, not a server. It allows many readers but **one writer at a time**. WAL (write-ahead log) mode lets readers continue while a write happens. `busy_timeout` makes a blocked writer wait instead of failing immediately. `foreign_keys` is **off by default** in SQLite and must be enabled per connection. Rule from design §9: only one process ever opens the DB for writing — never scale to two replicas.

**Alembic + SQLite.** SQLite can't `ALTER COLUMN` or drop constraints. Alembic's batch mode works around it by creating a new table, copying rows, and swapping. Enable it with `render_as_batch=True` in `env.py`.

**Lifespan.** Code before `yield` runs at startup, after `yield` at shutdown. In this step it only logs and checks the DB. Milestone 3 adds the neonize task, milestone 4 the scheduler.

## Steps

### 1. Clean up dependencies

Today `pyproject.toml` lists dev tools (`mypy`, `pytest`, `ruff`, `pre-commit`, `rust-just`) as runtime dependencies, so they'd ship in the Docker image. Move them to the dev group and add runtime deps:

```bash
uv remove mypy pre-commit pytest ruff rust-just
uv add --dev mypy pre-commit pytest ruff rust-just
uv add fastapi "uvicorn[standard]" pydantic-settings sqlmodel alembic
```

Also set `description = "WhatsApp assistant for Colombian patients' medical paperwork"` in `pyproject.toml`.

### 2. Settings — `src/medixio/config.py`

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///data/medixio.db"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    tz_display: str = "America/Bogota"
    log_level: str = "INFO"

    # Used from milestone 2 on; optional for now so /health runs without them.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    wa_session_db: str = "data/wa_session/session.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Add `.env.example` (committed) with the same keys and placeholder values. `.env` stays ignored — check `.gitignore` contains `.env` and `data/`.

### 3. Database — `src/medixio/db.py`

```python
from collections.abc import Iterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from medixio.config import get_settings


engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_conn: Any, _: Any) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
```

`check_same_thread=False` is needed because FastAPI may run sync dependencies in a threadpool; safety comes from one session per request.

### 4. Alembic

```bash
uv run alembic init migrations
```

In `alembic.ini`, leave `sqlalchemy.url` empty. In `migrations/env.py`:

```python
from sqlmodel import SQLModel

from medixio.config import get_settings
import medixio.models  # noqa: F401  — registers every table on SQLModel.metadata

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = SQLModel.metadata
```

and in both `run_migrations_offline` and `run_migrations_online` pass `render_as_batch=True` to `context.configure(...)`.

Create `src/medixio/models.py` as the single import point for tables (empty for now except a comment). Every module's `models.py` gets imported here from milestone 2 on — if a table isn't imported here, autogenerate silently misses it.

Add `import sqlmodel` to `migrations/script.py.mako` so generated files using `sqlmodel.sql.sqltypes.AutoString` work.

Create a baseline migration (empty):

```bash
mkdir -p data
uv run alembic revision -m "baseline"
uv run alembic upgrade head
```

### 5. App + `/health` — `src/medixio/main.py`

```python
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlmodel import Session

from medixio.config import get_settings
from medixio.db import get_session


log = logging.getLogger("medixio")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info("medixio starting")
    # milestone 3: start neonize client task
    # milestone 4: start scheduler task
    yield
    log.info("medixio stopping")


app = FastAPI(title="medixio", lifespan=lifespan)


@app.get("/health")
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    session.connection().execute(text("SELECT 1"))
    return {"status": "ok"}


def run() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
```

Add to `pyproject.toml`:

```toml
[project.scripts]
medixio = "medixio.main:run"
```

### 6. Tests — `tests/test_health.py`

Rename `tests/conftests.py` → `tests/conftest.py` (pytest only loads the exact name). Then:

```python
from fastapi.testclient import TestClient

from medixio.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

For tests, point `DATABASE_URL` at a temp file in `conftest.py` (set the env var before importing `medixio.db`, and call `get_settings.cache_clear()`).

### 7. Docker

`Dockerfile`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini README.md ./
RUN uv sync --frozen --no-dev

ENV API_HOST=0.0.0.0
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync medixio"]
```

`docker-compose.yml`:

```yaml
services:
  bot:
    build: .
    image: ghcr.io/jose-garzon/medixio:latest
    env_file: .env
    environment:
      DATABASE_URL: sqlite:////app/data/medixio.db
      WA_SESSION_DB: /app/data/wa_session/session.sqlite3
    volumes:
      - ./data:/app/data
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
```

Note the **four** slashes in the SQLite URL: `sqlite:///` + absolute path `/app/data/...`.

Add a `.dockerignore`: `.venv`, `data`, `.env`, `.git`, `.coverage`, `__pycache__`, `.ruff_cache`, `.mypy_cache`.

### 8. `justfile` additions

```just
run:
  uv run medixio

migrate:
  uv run alembic upgrade head

migration name:
  uv run alembic revision --autogenerate -m "{{name}}"

up:
  docker compose up -d --build

logs:
  docker compose logs -f bot
```

Change the existing `dev` recipe to `uv run medixio` too, or delete it in favour of `run`.

## Files touched

| Path | New / changed |
|---|---|
| `pyproject.toml`, `uv.lock` | deps moved/added, script, description |
| `.env.example`, `.dockerignore` | new |
| `src/medixio/config.py`, `db.py`, `models.py` | new |
| `src/medixio/main.py` | rewritten |
| `alembic.ini`, `migrations/` | new |
| `tests/conftest.py` | renamed from `conftests.py` |
| `tests/test_health.py` | new |
| `Dockerfile`, `docker-compose.yml` | new |
| `justfile` | recipes added |

## Verification

- [ ] `just check` passes (ruff + mypy strict).
- [ ] `just test` passes, including `test_health`.
- [ ] `just run` → `curl localhost:8000/health` returns `{"status":"ok"}`.
- [ ] `sqlite3 data/medixio.db "PRAGMA journal_mode;"` prints `wal`.
- [ ] `sqlite3 data/medixio.db "SELECT * FROM alembic_version;"` shows the baseline revision.
- [ ] `just up` → container status `healthy` in `docker compose ps`.
- [ ] `docker compose down && just up` → `data/medixio.db` still there (bind volume works).
- [ ] `docker run --rm ghcr.io/jose-garzon/medixio:latest uv pip list` shows no `pytest`/`ruff`/`mypy`.

## Common gotchas

- **`sqlite3.OperationalError: unable to open database file`** — `data/` directory doesn't exist, or wrong number of slashes in the URL.
- **`database is locked`** — two processes writing (e.g. running `just run` locally while the container uses the same `data/`). Stop one. Don't raise `busy_timeout` to hide it.
- **Autogenerate produces an empty migration** — the model isn't imported in `medixio/models.py`.
- **`NameError: sqlmodel` in a migration** — missing `import sqlmodel` in `script.py.mako`.
- **mypy strict complaining about Alembic's `env.py`** — run mypy on `src` only (the `check` recipe already does).

## Next

[02 — Patients, consent, profile, and agent behind `/admin/chat`](02-patients-and-agent.md) *(to be written)*.
