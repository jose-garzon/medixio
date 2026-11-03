FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# neonize imports python-magic, which needs the libmagic system library
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini README.md ./
RUN uv sync --frozen --no-dev

ENV API_HOST=0.0.0.0 \
    DATABASE_URL=sqlite:////app/data/medixio.db \
    WA_SESSION_DB=/app/data/wa_session/session.sqlite3 \
    OBSERVABILITY_DB=/app/data/observability.db
CMD ["sh", "-c", "mkdir -p /app/data && uv run --no-sync alembic upgrade head && exec uv run --no-sync medixio"]
