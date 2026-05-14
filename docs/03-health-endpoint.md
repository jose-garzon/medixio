# 03 — Health Endpoint

> **Goal:** make the bot a long-running FastAPI server with one route, `GET /health`. This is the smallest thing you can deploy and curl from the outside.

---

## Why this step exists

A `/health` endpoint is the cheapest signal that "the process is alive and HTTP works". Adding it before any real feature gives every later step a deploy target to verify against, and gives load balancers / Docker / Watchtower something to check.

You'll learn:

- How FastAPI starts under uvicorn and where the event loop lives.
- The `lifespan` context — the right place to wire background tasks later.
- Why `0.0.0.0` (not `127.0.0.1`) is the bind inside a container.
- How `docker compose` healthchecks let one service wait on another.

## Prerequisites

- Step 02 done; `docker compose up bot` builds and runs (and currently exits).
- Postgres still not used by the app — that's step 05.

## Concepts

**ASGI vs WSGI.** WSGI (Flask) is sync, one request per worker. ASGI (FastAPI/uvicorn) is async: many concurrent requests per worker over `asyncio`. Required for our setup since neonize is async.

**Uvicorn.** ASGI server that owns the event loop and runs the FastAPI app.

**Lifespan.** A context manager passed to `FastAPI(lifespan=…)`. Code before `yield` runs at startup, after `yield` runs at shutdown. This is where step 06 will spawn the WhatsApp client and the scheduler.

**Bind address.** `127.0.0.1` only listens on loopback. Inside a container that means *the container's loopback*, unreachable from outside. Use `0.0.0.0` to listen on all interfaces; expose ports via `docker compose` to control external reach.

## Steps

### 1. Add dependencies

```bash
uv add fastapi 'uvicorn[standard]' pydantic-settings
```

This updates `pyproject.toml` and `uv.lock`.

### 2. Add settings module

`src/medixio/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`lru_cache` makes `get_settings()` a singleton across the app — env vars are read once.

### 3. Add the health router

`src/medixio/api/__init__.py`:

```python
from fastapi import APIRouter

from medixio.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
```

`src/medixio/api/health.py`:

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

### 4. Rewrite `main.py` around FastAPI

```python
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from medixio.api import api_router
from medixio.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup hooks go here in later steps
    yield
    # shutdown hooks go here


app = FastAPI(title="Medixio", lifespan=lifespan)
app.include_router(api_router)


def _setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run() -> None:
    _setup_logging()
    settings = get_settings()
    uvicorn.run(
        "medixio.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
```

### 5. Expose the port in compose

Edit `docker-compose.yml`, add to the `bot` service:

```yaml
  bot:
    build: .
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"          # host:container
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request,sys;sys.exit(0 if urllib.request.urlopen(\"http://localhost:8000/health\").status==200 else 1)'"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped
```

The Python-based healthcheck avoids needing `curl` inside the slim image.

### 6. Add a test

`tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from medixio.main import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
```

`uv add --dev httpx` (TestClient depends on it).

### 7. Run

```bash
uv run pytest -q                                # local test, no Docker
uv run medixio                                  # local server on 0.0.0.0:8000
curl http://localhost:8000/health               # {"status":"ok"}
```

Then via Docker:

```bash
docker compose up -d --build bot
curl http://localhost:8000/health
docker compose ps                               # bot should show "Up (healthy)"
docker compose logs bot --tail=20
```

### 8. Commit

```bash
git add pyproject.toml uv.lock src tests docker-compose.yml
git commit -m "add FastAPI health endpoint with lifespan scaffold"
```

## Files touched in this step

| Path | Purpose |
|---|---|
| `pyproject.toml` / `uv.lock` | new deps: fastapi, uvicorn, pydantic-settings, httpx (dev) |
| `src/medixio/config.py` | typed settings |
| `src/medixio/api/__init__.py` | aggregates routers |
| `src/medixio/api/health.py` | `/health` route |
| `src/medixio/main.py` | FastAPI app + uvicorn entry |
| `tests/test_health.py` | route smoke test |
| `docker-compose.yml` | port + healthcheck for bot |

## Verification

- [ ] `uv run pytest -q` → 2 passing tests.
- [ ] `uv run medixio` starts uvicorn; `curl :8000/health` returns `{"status":"ok"}`.
- [ ] `docker compose up -d --build bot` → `docker compose ps` shows `bot` `Up (healthy)`.
- [ ] Healthcheck visible in `docker inspect bot | grep -A3 Health`.

## Common gotchas

- **`curl` from host gets connection refused.** You bound to `127.0.0.1` inside the container. Use `0.0.0.0`.
- **`address already in use`** — port 8000 taken by an old process. `lsof -i :8000` and kill, or change `api_port`.
- **`TestClient` import error** — install `httpx` as a dev dep.
- **Lifespan never runs** — uvicorn must be told `medixio.main:app`, not just `medixio.main`. The `:app` selects the FastAPI instance.
