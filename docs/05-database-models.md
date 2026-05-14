# 05 — Database Models & Connecting the App

> **Goal:** wire SQLModel + Alembic to Postgres, create the four tables from the design doc (`patient`, `appointment`, `notification`, `message`), and prove end-to-end persistence via a tiny admin route.

---

## Why this step exists

This is where the system stops being a hollow scaffold. You need persistence before you can have an agent (it needs to store memory) or a scheduler (it needs notifications). Doing models + migrations now keeps the data-shape conversation separate from agent/LLM complexity later.

You'll learn:

- The difference between `SQLModel.metadata.create_all` and a real migration tool.
- How Alembic autogenerate compares model metadata to the DB and emits a diff.
- Why every new model must be imported somewhere Alembic sees, or autogenerate silently misses it.
- How `Session` works in SQLModel: a unit-of-work scoped to a request.
- TIMESTAMPTZ vs naive TIMESTAMP and why you should always store UTC.

## Prerequisites

- Step 04 done; `/health` reachable on the server.
- Postgres container healthy locally.

## Concepts

**SQLModel.** A library that defines tables as Pydantic models. One class doubles as the validation schema and the SQLAlchemy table. `table=True` flips it from a Pydantic-only DTO into a real table.

**Engine and Session.** The `Engine` is a long-lived connection pool. A `Session` is a short-lived workspace where you stage adds/updates and `commit()` to flush them. Open one per request (or per WhatsApp message).

**Migrations.** `SQLModel.metadata.create_all(engine)` creates tables that don't exist but never alters or drops. For real evolution you need Alembic: it records migrations as numbered Python scripts under `alembic/versions/`. `upgrade` applies them, `downgrade` reverses them.

**Autogenerate.** `alembic revision --autogenerate` compares your live DB to `SQLModel.metadata`. It writes a draft migration with the diff. *Read it before applying* — autogenerate is good at additions, mediocre at renames/type changes.

**UUID v7-ish IDs.** UUIDv4 fragments your index. For high-write tables you'd use v7 (time-ordered). For our scale, v4 is fine and we use `uuid.uuid4`.

## Steps

### 1. Add dependencies

```bash
uv add sqlmodel alembic 'psycopg[binary]'
```

### 2. Add settings for the database URL

Edit `src/medixio/config.py`:

```python
class Settings(BaseSettings):
    # ... existing ...
    database_url: str = "postgresql+psycopg://medixio:medixio@db:5432/medixio"
```

The `postgresql+psycopg://` scheme is **required** to select psycopg 3 over psycopg 2.

### 3. Create the engine + session helper

`src/medixio/db.py`:

```python
from collections.abc import Generator

from sqlmodel import Session, create_engine

from medixio.config import get_settings

engine = create_engine(
    get_settings().database_url,
    echo=False,
    pool_pre_ping=True,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

### 4. Define the models

`src/medixio/models/__init__.py` — must import every model so Alembic sees them:

```python
from medixio.models.appointment import Appointment, AppointmentStatus  # noqa: F401
from medixio.models.message import Message, MessageRole  # noqa: F401
from medixio.models.notification import Notification  # noqa: F401
from medixio.models.patient import Patient  # noqa: F401
```

`src/medixio/models/patient.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Patient(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    whatsapp_jid: str = Field(unique=True, index=True)
    phone_number: str
    name: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

`src/medixio/models/appointment.py`:

```python
import enum
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from medixio.models.patient import utcnow


class AppointmentStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    missed = "missed"
    done = "done"


class Appointment(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    doctor_name: str
    doctor_phone: str | None = None
    doctor_address: str | None = None
    specialty: str
    date: datetime | None = Field(default=None, index=True)
    status: AppointmentStatus = Field(default=AppointmentStatus.draft)
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

`src/medixio/models/notification.py`:

```python
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from medixio.models.patient import utcnow


class Notification(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    appointment_id: uuid.UUID | None = Field(
        default=None, foreign_key="appointment.id", ondelete="CASCADE"
    )
    date: datetime
    message: str
    rrule: str | None = None
    last_sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
```

`src/medixio/models/message.py`:

```python
import enum
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from medixio.models.patient import utcnow


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=utcnow, index=True)
```

### 5. Initialise Alembic

```bash
uv run alembic init alembic
```

Edit `alembic.ini`: empty out `sqlalchemy.url` (we'll set it from code) and add `prepend_sys_path = src`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = src
version_path_separator = os
sqlalchemy.url =
```

Edit `alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import medixio.models  # noqa: F401  ensures models register
from medixio.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = SQLModel.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

### 6. Generate and apply the first migration

```bash
docker compose up -d db
uv run alembic revision --autogenerate -m "initial schema"
# Inspect alembic/versions/<sha>_initial_schema.py — sanity-check tables/cols
uv run alembic upgrade head
```

Verify:

```bash
docker compose exec db psql -U medixio medixio -c '\dt'
# expect: patient, appointment, notification, message, alembic_version
```

### 7. Add a small admin route to prove persistence

`src/medixio/api/admin.py`:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from medixio.db import get_session
from medixio.models import Patient

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/patients")
def list_patients(session: Session = Depends(get_session)) -> list[Patient]:
    return list(session.exec(select(Patient)).all())


@router.post("/patients/seed")
def seed(session: Session = Depends(get_session)) -> Patient:
    p = Patient(whatsapp_jid="573000000000@s.whatsapp.net", phone_number="+573000000000", name="Test")
    session.add(p)
    session.commit()
    session.refresh(p)
    return p
```

Register it in `src/medixio/api/__init__.py`:

```python
from medixio.api.admin import router as admin_router

api_router.include_router(admin_router)
```

> These admin routes are **temporary** (no auth, anyone with port access can poke them). Remove or guard before the bot reaches anyone real.

### 8. Run migrations on startup (dev convenience)

You have two options:

1. **Explicit step.** Run `uv run alembic upgrade head` manually before `docker compose up bot`.
2. **Migration entrypoint container.** Add a service that runs migrations then exits:

   ```yaml
     migrate:
       image: ghcr.io/<owner>/medixio:latest
       env_file: .env
       depends_on:
         db: { condition: service_healthy }
       command: ["alembic", "upgrade", "head"]
       restart: "no"
   ```

   And have `bot` depend on `migrate: { condition: service_completed_successfully }`.

For now, pick option 1 to keep the surface small.

### 9. Verify

```bash
uv run medixio
curl -X POST http://localhost:8000/admin/patients/seed
curl http://localhost:8000/admin/patients
# list now contains one row
```

Re-run the seed — should get a `UniqueViolation` because `whatsapp_jid` is unique. That's the test that constraints actually applied.

### 10. Commit

```bash
git add pyproject.toml uv.lock src alembic alembic.ini
git commit -m "models: patient/appointment/notification/message + alembic init"
```

## Files touched in this step

| Path | Purpose |
|---|---|
| `pyproject.toml` / `uv.lock` | + sqlmodel, alembic, psycopg |
| `src/medixio/db.py` | engine + `get_session` |
| `src/medixio/models/*.py` | 4 tables |
| `src/medixio/api/admin.py` | temporary debug routes |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/<sha>_initial_schema.py` | migrations |
| `src/medixio/config.py` | `database_url` |

## Verification

- [ ] `alembic upgrade head` exits 0; `\dt` shows 5 tables.
- [ ] `POST /admin/patients/seed` returns a JSON patient with a UUID.
- [ ] `GET /admin/patients` lists it.
- [ ] Calling seed twice errors with a unique-violation (proves constraint works).
- [ ] `pytest -q` still passes.

## Common gotchas

- **Autogenerate produces an empty migration.** You forgot to import a model in `medixio/models/__init__.py`, or `env.py` doesn't import `medixio.models`. Both must be true.
- **`AttributeError: 'datetime' object has no attribute 'tzinfo'` when reading rows.** You stored naive datetimes. Always pass `datetime.now(timezone.utc)`.
- **`ondelete="CASCADE"` not respected.** It only fires for FK-driven deletes. Application-level deletes still need explicit handling.
- **Migration says "drop column id"** — autogenerate gets confused by a renamed table or an enum type change. Edit the script by hand or roll back and redo.
- **Connection refused inside container.** `DATABASE_URL` host must be `db`, not `localhost`, when running inside compose.
