default:
  @just --list

run:
  PYTHONUNBUFFERED=1 uv run medixio

# Run without WhatsApp; talk to the bot with `just chat "hola"`
dev:
  WHATSAPP_ENABLED=false uv run medixio

chat text jid="573000000000@s.whatsapp.net":
  curl -s -X POST localhost:8000/admin/chat -H 'content-type: application/json' -H "x-admin-token: ${ADMIN_TOKEN:-}" -d '{"jid": "{{jid}}", "text": "{{text}}"}'

check:
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy src

format:
  uv run ruff check --fix .
  uv run ruff format .

test *args:
  uv run pytest {{args}}

migrate:
  uv run alembic upgrade head

migration name:
  uv run alembic revision --autogenerate -m "{{name}}"

unreviewed:
  curl -s localhost:8000/admin/knowledge/unreviewed -H "x-admin-token: ${ADMIN_TOKEN:-}"

status:
  curl -s localhost:8000/admin/obs/status -H "x-admin-token: ${ADMIN_TOKEN:-}"

up:
  docker compose up -d --build

logs:
  docker compose logs -f bot

update:
  uv lock --upgrade
  uv sync
