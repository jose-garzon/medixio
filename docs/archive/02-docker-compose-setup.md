# 02 — Docker Compose Setup

> **Goal:** containerise the bot, run Postgres next to it via `docker compose`, and confirm both come up cleanly. Still no real app logic — we're proving the runtime works.

---

## Why this step exists

Containerising early forces you to think about: image build, environment variables, networking between services, volumes for persistent data, and the dev/prod split. Doing it before adding code means you'll iterate on a tiny image instead of debugging a fat one later.

You'll learn:

- The difference between `docker run`, `docker compose`, and an image.
- Why a Dockerfile copies `pyproject.toml`/`uv.lock` *before* the source (build cache layer ordering).
- How services talk over Docker's internal DNS (`db` resolves from `bot`).
- Why named volumes survive `docker compose down` but bind mounts are tied to the host path.

## Prerequisites

- Step 01 done; `uv run medixio` prints `scaffold OK`.
- Docker Engine + the `docker compose` plugin installed.

## Concepts

**Image vs container.** Image = built artefact (read-only). Container = a running instance of an image with its own filesystem layer and process tree.

**Layer cache.** Each `RUN`/`COPY` line in a Dockerfile is a layer. Docker reuses a layer if its inputs haven't changed. Copying `pyproject.toml` before the rest of `src/` means edits to `src/medixio/main.py` won't bust the dependency-install layer.

**Named volume vs bind mount.** `pgdata:/var/lib/postgresql/data` (named) is managed by Docker and survives across `compose down`. `./wa_session:/app/wa_session` (bind) points at a host path; useful when you want to inspect files from the host.

**Service DNS.** `docker compose` puts every service on a shared network and registers them under their service name. From the `bot` container, `db` resolves to the Postgres container's IP.

## Steps

### 1. Add a Dockerfile

Create `Dockerfile` at the repo root:

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Cache deps separately from source
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Now copy source and install the project itself
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
CMD ["medixio"]
```

Key points:

- `--frozen` makes `uv` refuse to update the lockfile inside the build — guarantees reproducible image.
- `--no-install-project` on the first sync installs *dependencies only*; project install happens after `src/` is copied.
- The final `ENV PATH` lets you call `medixio` directly (the console script lives at `.venv/bin/medixio`).

Add `.dockerignore`:

```
.venv/
.git/
__pycache__/
*.py[cod]
.ruff_cache/
.pytest_cache/
.env
tests/
docs/
*.md
```

### 2. Add `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: medixio
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-medixio_dev}
      POSTGRES_DB: medixio
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medixio"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  bot:
    build: .
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
```

### 3. Add `.env.example` and `.env`

`.env.example` (committed):

```
DATABASE_URL=postgresql+psycopg://medixio:medixio_dev@db:5432/medixio
POSTGRES_PASSWORD=medixio_dev
LOG_LEVEL=INFO
```

Copy to `.env` locally (ignored by git):

```bash
cp .env.example .env
```

Make sure `.gitignore` has `.env`.

### 4. Bring it up

```bash
docker compose build           # build the bot image
docker compose up -d db        # start Postgres alone first
docker compose ps              # see db healthy
docker compose up bot          # foreground; should print "medixio scaffold OK" and exit
```

The bot will exit immediately because `main.py` only prints. That's fine — we'll add a long-running server next step. The point is: the image built, the container ran, it could resolve `db`.

### 5. Sanity-check the database connection

```bash
docker compose exec db psql -U medixio -d medixio -c '\dt'
```

Should print `Did not find any relations.` (empty schema, fine for now).

### 6. Tear down

```bash
docker compose down            # stops containers, keeps volume
docker compose down -v         # also wipes pgdata (use when resetting)
```

### 7. Commit

```bash
git add Dockerfile .dockerignore docker-compose.yml .env.example
git commit -m "containerize bot + add postgres service via docker compose"
```

## Files touched in this step

| Path | Purpose |
|---|---|
| `Dockerfile` | bot image build recipe |
| `.dockerignore` | excludes host clutter from build context |
| `docker-compose.yml` | services, volumes, networks |
| `.env.example` | template env vars |
| `.env` (local only) | real env vars; gitignored |

## Verification

- [ ] `docker compose build` succeeds.
- [ ] `docker compose up -d db` → `docker compose ps` shows `db` `Up (healthy)`.
- [ ] `docker compose up bot` prints `medixio scaffold OK`.
- [ ] Inside `db`: `\dt` returns no tables (DB exists, empty).
- [ ] `docker compose down -v && docker compose up -d db` from clean state still works.

## Common gotchas

- **Bot can't resolve `db`.** Make sure `DATABASE_URL` uses `db` (the service name), not `localhost`. `localhost` inside the bot container is the bot itself.
- **`pg_isready` healthcheck never green.** You forgot `-U medixio`; the default user is `postgres`.
- **`uv sync --frozen` fails in build.** You didn't commit `uv.lock` before building. Sync locally first.
- **Slow rebuilds.** You're copying `src/` before `pyproject.toml`. Order matters for cache.
