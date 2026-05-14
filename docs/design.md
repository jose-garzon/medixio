# Medixio — Design Document

> **Status:** Draft v1 · Last updated: 2026-05-12 · Audience: project author and future contributors.

---

## 1. Overview

Medixio is a WhatsApp-only chatbot that helps people living with chronic illnesses keep track of their medical life: scheduling and recalling appointments, taking recurring medication, and remembering one-off events (vaccines, exams, follow-ups). Patients interact with the bot through natural-language messages in Spanish; an LLM agent extracts intent, asks follow-up questions when needed, and persists data in Postgres. The bot proactively pushes reminders so the patient never has to open a separate app.

There is no web UI. WhatsApp is the only surface.

## 2. Goals & non-goals

### Goals (MVP)

- A patient can create, view, update, reschedule, and cancel medical appointments by chatting in Spanish.
- A patient receives automatic reminders for every scheduled appointment.
- A patient can ask the bot to remind them of recurring events (e.g. monthly medication intake) using natural language; the bot stores them as recurring notifications.
- The system is packaged as Docker containers and is deployable anywhere `docker compose` runs.

### Non-goals (explicit)

- **No medical advice.** The bot never diagnoses, recommends doses, or interprets symptoms.
- **No multi-language.** Spanish (es-CO) only for v1.
- **No web/mobile UI.** WhatsApp is the only interface.
- **No doctor-facing features.** Patients only.
- **No multi-tenant.** Single deployment, many patients, but no organisational hierarchy.
- **No real-time symptom tracking, no integrations with EHRs.**
- **No HIPAA / GDPR certification.** Privacy-by-default but no formal compliance posture in v1.

## 3. Functional requirements

| ID | Requirement |
|----|-------------|
| FR-1 | The bot accepts inbound WhatsApp messages over a neonize-managed session. |
| FR-2 | On a patient's first inbound message, the bot creates a `patient` row keyed by WhatsApp JID and replies with a one-question onboarding (`¿Cómo te llamas?`). The provided name is stored on the patient. |
| FR-3 | The patient can create an appointment via natural language. The bot extracts doctor name, specialty, phone, address, date, and notes; missing fields are asked one at a time. |
| FR-4 | Appointments have a status lifecycle: `draft → active → (done | missed)`. The bot can transition statuses on request or when time passes. |
| FR-5 | When an appointment becomes `active` (date assigned), the bot auto-creates three notifications: −1 day, −30 minutes, +1 hour. |
| FR-6 | The patient can list upcoming appointments (`active` and `draft`), past appointments (`done`, `missed`), or filter by date. |
| FR-7 | The patient can create recurring reminders described in natural language (e.g. "recuérdame tomar mi metformina el primero de cada mes a las 8 AM"). The bot stores them as a `notification` row with an iCal RRULE. |
| FR-8 | A scheduler dispatches due notifications via the bot's WhatsApp session. Idempotent on restart. |
| FR-9 | The bot keeps the last 20 messages per patient as conversation memory and passes them to the agent on each turn. |
| FR-10 | The agent is implemented with [PydanticAI](https://ai.pydantic.dev/) using Google Gemini as the model. Tool calls are the only way the agent mutates the database. |
| FR-11 | A FastAPI HTTP surface exposes at minimum a `/health` endpoint; future admin endpoints land here. |

## 4. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | **Locale.** All bot output is Spanish (es-CO). All datetimes are stored as UTC and rendered in `America/Bogotá` (UTC-5, no DST). |
| NFR-2 | **Latency.** P50 inbound-to-reply ≤ 3 s under normal Gemini load. Soft target. |
| NFR-3 | **Availability.** Best-effort. Matches whatever the host environment provides. No SLO. |
| NFR-4 | **Resilience.** If Gemini fails (timeout, rate limit, 5xx), retry 3× with exponential backoff (0.5s → 1s → 2s). On final failure, send a canned Spanish error reply and log. |
| NFR-5 | **Privacy.** Patient data is only sent to the two external dependencies the product requires: neonize ↔ WhatsApp and the agent ↔ Gemini API. No third-party analytics. |
| NFR-6 | **Observability.** Structured logs to stdout (JSON or key=value). Log levels driven by `LOG_LEVEL` env var. No metrics in v1. |
| NFR-7 | **Reproducibility.** `uv sync` deterministically rebuilds the environment from a committed lockfile. |

## 5. Architecture

### 5.1 High-level diagram

```
                          ┌──────────────────────┐
                          │   WhatsApp (Meta)    │
                          └──────────┬───────────┘
                                     │ multi-device protocol
                                     │
                          ┌──────────▼───────────┐
                          │  neonize (whatsmeow) │   (QR pairing on first run)
                          │  session SQLite file │
                          └──────────┬───────────┘
                                     │ MessageEv / ConnectedEv
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                       medixio (single asyncio process)                  │
│                                                                         │
│  ┌──────────────┐   ┌──────────────────────┐   ┌────────────────────┐   │
│  │ FastAPI app  │   │  Message handler     │   │  Scheduler loop    │   │
│  │  /health     │   │  (whatsapp.handlers) │   │  (worker.scheduler)│   │
│  └──────────────┘   └──────────┬───────────┘   └──────────┬─────────┘   │
│                                │                          │             │
│                                ▼                          ▼             │
│                     ┌─────────────────────┐    ┌──────────────────┐     │
│                     │  PydanticAI agent   │    │ notification     │     │
│                     │  + Gemini model     │    │ dispatcher       │     │
│                     │  + tools            │    └─────────┬────────┘     │
│                     └──────────┬──────────┘              │              │
│                                │ tool calls              │              │
│                                ▼                         ▼              │
│                     ┌──────────────────────────────────────────┐        │
│                     │  Service layer (appointments / notifs /  │        │
│                     │  patients / messages)                    │        │
│                     └────────────────────┬─────────────────────┘        │
│                                          │ SQLModel sessions            │
└──────────────────────────────────────────┼──────────────────────────────┘
                                           │
                                ┌──────────▼───────────┐
                                │   Postgres 16        │  (Docker volume)
                                │   medixio database   │
                                └──────────────────────┘
```

### 5.2 Flow notes

- **Inbound message** → neonize emits `MessageEv` → `whatsapp.handlers.handle_message` loads the patient + last 20 messages → invokes the PydanticAI agent → agent decides which tools to call → service layer mutates Postgres → handler sends the agent's reply text back through neonize.
- **Outbound reminder** → scheduler tick (every 60 s) queries `notification` rows due now (including next RRULE occurrence) → for each, sends a WhatsApp message via the shared neonize client → updates `last_sent_at`.
- **HTTP** → uvicorn serves FastAPI on a port exposed only inside the docker network (and to localhost on the host). `/health` for liveness; admin endpoints later.
- **Lifespan ownership.** The FastAPI lifespan owns two `asyncio` tasks: the neonize client and the scheduler. Both are cancelled on shutdown. The neonize client is also exposed via `app.state.wa_client` so the scheduler can reuse it.

## 6. Technology choices

| Concern | Choice | Why | Considered & rejected |
|---|---|---|---|
| Language | Python 3.12 | Best ecosystem for LLM + DB + WA libs available in Python | Node (Baileys is in JS, considered but harder for the LLM bits) |
| Package mgmt | `uv` | Fast, lockfile, replaces pip+venv+virtualenv | Poetry (slower); pip+requirements.txt (no lockfile niceties) |
| Lint/format | `ruff` | One tool replaces black+isort+flake8 | Black + isort + flake8 (3 tools, slower) |
| LLM agent SDK | **PydanticAI** | Pydantic-native, FastAPI/SQLModel synergy, model-agnostic, small surface | LangGraph (heavy, opinionated); smolagents (too minimal for tool-heavy domain); Google ADK (the user explicitly rejected); plain google-genai (more boilerplate) |
| LLM provider | Google **Gemini** (free tier) | Free quota, multimodal, generous limits for hobby use | OpenAI / Anthropic (paid); local models (too slow on home server for now) |
| WhatsApp channel | **neonize** | Python, multi-device, QR pairing, no business verification, supports proactive outbound | Cloud API (needs business verification + approved templates); Twilio (paid); Selenium (fragile DOM scraping) |
| Web framework | FastAPI | Async, Pydantic-native, easy lifespan for background tasks | Flask (no async); Starlette alone (less batteries) |
| ORM | SQLModel | Pydantic + SQLAlchemy combo, low boilerplate | SQLAlchemy raw (more boilerplate); Tortoise ORM (smaller ecosystem) |
| Migrations | Alembic | Standard SQLAlchemy migrator | Aerich (Tortoise-only); hand-rolled SQL |
| DB driver | psycopg 3 | Modern, native async support, good docs | psycopg2 (older); asyncpg (no SQLAlchemy-2 sync mode) |
| Database | Postgres 16 (Docker) | Robust, JSONB, easy RRULE storage as text, well-known on home servers | SQLite (no concurrent writer in prod); MySQL (no JSONB UX needed but Postgres preferred) |
| Container orchestration | docker compose | Single-host deploy, simple | k8s (overkill); systemd-only (less reproducible) |
| CI / image registry | GitHub Actions → GHCR | Free for public/private repos, no extra account | Docker Hub (rate limits); manual builds on the home server (slow, noisy) |
| Recurrence syntax | iCal **RRULE** (via `python-dateutil`) | Standard, expressive (monthly/weekly/custom), well-documented | Cron strings (hard for the LLM to generate reliably); homegrown DSL (NIH) |

## 7. Data model

All tables include `id` (UUID), `created_at`, `updated_at` (where mutable). All `*_at` columns are `TIMESTAMPTZ` stored UTC.

### 7.1 `patient`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `whatsapp_jid` | text | unique, indexed. e.g. `573002346892@s.whatsapp.net` |
| `phone_number` | text | derived from JID for display |
| `name` | text | nullable; filled in by onboarding question |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### 7.2 `appointment`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `patient_id` | uuid | FK → `patient.id`, ON DELETE CASCADE |
| `doctor_name` | text | required |
| `doctor_phone` | text | nullable; format `+<country><number>` |
| `doctor_address` | text | nullable |
| `specialty` | text | required (free text for v1; could become enum later) |
| `date` | timestamptz | nullable for `draft` |
| `status` | enum | `draft \| active \| missed \| done` |
| `notes` | text | nullable |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

Indexes: `(patient_id, status)`, `(patient_id, date)`.

Status lifecycle:

```
       (created without date)            (date scheduled)
created ───────────► draft ────► active ──────► done
                       │           │
                       └──► active │
                                   └─────────► missed
```

- `draft → active` happens when `date` is set.
- `active → done` happens when the patient confirms attendance, or auto on `+1h` reminder reply (future).
- `active → missed` is manual for v1.

### 7.3 `notification`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `patient_id` | uuid | FK → `patient.id`, ON DELETE CASCADE |
| `appointment_id` | uuid | FK → `appointment.id`, ON DELETE CASCADE, nullable (standalone reminders have no appointment) |
| `date` | timestamptz | for one-off: when to fire. For RRULE: the DTSTART anchor |
| `message` | text | the Spanish copy to send |
| `rrule` | text | nullable; iCal RRULE string. If present, `date` is treated as DTSTART |
| `last_sent_at` | timestamptz | nullable; null = never sent |
| `created_at` | timestamptz | |

Indexes: `(date)` where `last_sent_at IS NULL` (partial), `(patient_id, date)`.

Dispatch semantics:

- **One-off** (`rrule IS NULL`): fire when `date <= now() AND last_sent_at IS NULL`. After send, set `last_sent_at = now()`. Row remains for audit but won't fire again.
- **Recurring** (`rrule IS NOT NULL`): fire when the next RRULE occurrence ≤ now() and that occurrence is strictly after `last_sent_at`. After send, set `last_sent_at = occurrence_time`.

### 7.4 `message`

Conversation memory.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `patient_id` | uuid | FK → `patient.id`, ON DELETE CASCADE |
| `role` | enum | `user \| assistant \| system` |
| `content` | text | |
| `created_at` | timestamptz | indexed; loaded ORDER BY created_at DESC LIMIT 20 then reversed for agent context |

## 8. Conversation & agent design

### 8.1 Agent shape

- One PydanticAI `Agent` instance, configured with the Gemini model.
- `deps_type` is a `RunDeps` dataclass holding a SQLModel `Session` and the current `Patient`. Tools receive this via `RunContext` and never reach into globals.
- System prompt (sketch, Spanish):

  > "Eres Medixio, un asistente que ayuda a pacientes con enfermedades crónicas a llevar sus citas médicas y recordatorios. Responde siempre en español, sé conciso y empático. Nunca des consejo médico. Para crear, editar o eliminar datos, usa las herramientas disponibles. Si falta información, pregunta una sola cosa a la vez."

- Tools (typed Python functions wrapped with `@agent.tool`):
  - `create_appointment(doctor_name, specialty, date?, doctor_phone?, doctor_address?, notes?) -> Appointment`
  - `schedule_appointment(appointment_id, date) -> Appointment` (transitions draft → active and creates the 3 auto-notifications)
  - `update_appointment(appointment_id, fields) -> Appointment`
  - `change_appointment_status(appointment_id, status) -> Appointment`
  - `list_appointments(filter: upcoming|past|all) -> list[Appointment]`
  - `create_notification(message, date_or_rrule, appointment_id?) -> Notification`
  - `list_notifications(filter: active|all) -> list[Notification]`
  - `cancel_notification(notification_id) -> None`

### 8.2 Per-message flow

1. Handler receives `MessageEv`, extracts `chat_jid` and `text`.
2. `get_or_create_patient(jid)` — if newly created and `patient.name is None`, the handler short-circuits the agent: stores the inbound message and replies `¡Hola! Soy Medixio. ¿Cómo te llamas?`. Next inbound captures the name.
3. Else: persist inbound `message` (role=user), load last 20 messages, build agent message history, run agent with `deps=RunDeps(session, patient)`.
4. Persist outbound `message` (role=assistant). Send via neonize.

### 8.3 Gemini failure path

`agent.run(...)` is wrapped in a retry helper:

- Up to 3 attempts.
- Backoff 0.5s → 1s → 2s.
- Retry on: timeout, 429, 5xx.
- On final failure: log the exception, send the canned Spanish reply:

  > `Disculpa, no puedo responder en este momento. Intenta de nuevo en unos minutos.`

## 9. Reminder scheduling

### 9.1 Tick loop

```python
TICK_SECONDS = 60

async def run_scheduler(wa_client):
    while True:
        try:
            await dispatch_due(wa_client)
        except Exception:
            log.exception("scheduler tick failed")
        await asyncio.sleep(TICK_SECONDS)
```

### 9.2 `dispatch_due` (pseudocode)

```python
def dispatch_due(wa_client):
    now = datetime.now(timezone.utc)
    with Session(engine) as s:
        # One-off due
        oneoffs = s.exec(select(Notification).where(
            Notification.rrule.is_(None),
            Notification.last_sent_at.is_(None),
            Notification.date <= now,
        )).all()

        # Recurring due — compute next occurrence in Python
        recurring = s.exec(select(Notification).where(
            Notification.rrule.is_not(None)
        )).all()
        for n in recurring:
            next_occ = next_rrule_occurrence(n.rrule, dtstart=n.date,
                                             after=n.last_sent_at or n.date - timedelta(seconds=1))
            if next_occ and next_occ <= now:
                send_and_mark(s, wa_client, n, sent_at=next_occ)

        for n in oneoffs:
            send_and_mark(s, wa_client, n, sent_at=now)
        s.commit()
```

`next_rrule_occurrence` uses `dateutil.rrule.rrulestr(rrule_str, dtstart=dtstart).after(after)`.

### 9.3 Idempotency & drift

- `last_sent_at` is the single source of truth for "already fired".
- If the process is down across a tick, missed one-off notifications fire on the next start (no replay storm — they fire once, not once per missed tick).
- For recurring notifications, only the most recent due occurrence is sent. We do not back-fire multiple skipped occurrences (a patient who was offline for 3 days does not want 3 medication reminders at once).

## 10. Auto-notifications on appointment scheduling

When `schedule_appointment(id, date)` is called (or an appointment is created already `active`), insert these three rows in `notification`:

| Offset | Message |
|---|---|
| `date - 1 day` | `📅 Tu cita con el Dr. {doctor_name} es mañana a las {HH:MM}.` |
| `date - 30 min` | `⌛ Tu cita con el Dr. {doctor_name} es en 30 minutos.` |
| `date + 1 hour` | `⭐ ¿Cómo te fue en la cita con el Dr. {doctor_name}?` |

All three rows have `appointment_id` set so they cascade-delete if the appointment is removed.

Cancellation rules:

- Status → `done` or `missed`: delete any future-dated linked notifications (`date > now()`).
- Status → `draft` (un-schedule, edge case): delete all linked notifications.
- `update_appointment` changes the date: delete linked notifications and re-create with new offsets.

Spanish template strings live in a single `medixio.whatsapp.templates` module so they can be tweaked without touching scheduling logic.

## 11. Deployment

The MVP target is the author's home server, chosen as a pragmatic starting point (no hosting bill, full control while iterating). The architecture does not depend on that choice — the same `docker compose` stack runs on any Linux host with Docker, and the Postgres service can be swapped for a managed instance (Supabase, Neon, RDS) by changing `DATABASE_URL`.

### 11.1 `docker-compose.yml` (sketch)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: medixio
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: medixio
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "127.0.0.1:5432:5432"   # loopback only on the host
    restart: unless-stopped

  bot:
    image: ghcr.io/<owner>/medixio:latest
    env_file: .env
    depends_on: [db]
    volumes:
      - ./wa_session:/app/wa_session   # neonize session persistence
    restart: unless-stopped

  backup:
    image: postgres:16
    depends_on: [db]
    entrypoint: ["/bin/sh","-c","while true; do PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h db -U medixio medixio | gzip > /backups/medixio-$(date +%F).sql.gz; find /backups -name 'medixio-*.sql.gz' -mtime +14 -delete; sleep 86400; done"]
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./backups:/backups
    restart: unless-stopped

volumes:
  pgdata:
```

### 11.2 Environment variables

| Var | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | psycopg URL | `postgresql+psycopg://medixio:***@db:5432/medixio` |
| `POSTGRES_PASSWORD` | DB password (compose) | random secret |
| `GOOGLE_API_KEY` | Gemini API key | from AI Studio |
| `GEMINI_MODEL` | model name | `gemini-1.5-flash` |
| `WA_SESSION_DB` | neonize session file path | `/app/wa_session/medixio.sqlite3` |
| `API_HOST` / `API_PORT` | FastAPI bind | `0.0.0.0` / `8000` |
| `LOG_LEVEL` | logging level | `INFO` |
| `TZ_DISPLAY` | display timezone | `America/Bogotá` |

### 11.3 CI / CD

GitHub Actions workflow on push to `main`:

1. `uv sync` and `uv run pytest` (smoke).
2. `uv run ruff check .`
3. `docker buildx build --platform linux/amd64 -t ghcr.io/<owner>/medixio:latest -t ghcr.io/<owner>/medixio:${{ github.sha }} --push .`

Home server side (two viable patterns; pick at deploy time, doc them both):

- **Watchtower** container watches `ghcr.io/<owner>/medixio` and `docker compose up`-recreates on new digest. Zero touch.
- **Cron pull script.** Every 5 minutes: `docker compose pull bot && docker compose up -d bot`. Slightly more control, simpler to reason about.

Default recommendation: **Watchtower** for v1, swap to cron+pull if it ever misbehaves.

### 11.4 First-time bring-up

1. Clone repo on home server.
2. `cp .env.example .env`, fill secrets.
3. `docker compose up -d db` — wait for Postgres.
4. Locally: `uv run alembic upgrade head` (or run a migration job container).
5. `docker compose up -d bot`.
6. `docker compose logs -f bot` — scan QR code with the WhatsApp app. Session persists to `./wa_session/`.

## 12. Backups & disaster recovery

- Nightly `pg_dump` from the `backup` sidecar container above.
- Output: `./backups/medixio-YYYY-MM-DD.sql.gz` on the host.
- Retention: 14 days, rotated by `find … -mtime +14 -delete`.
- **Restore procedure:**
  ```bash
  docker compose down bot
  gunzip -c ./backups/medixio-YYYY-MM-DD.sql.gz | docker compose exec -T db psql -U medixio medixio
  docker compose up -d bot
  ```
- Off-site replication is a future-work item (see §15).

## 13. Security & privacy

- **Secrets.** All secrets live in `.env`, never committed. `.env.example` ships placeholder values only.
- **Database exposure.** Postgres binds to `127.0.0.1:5432` on the host so it is unreachable from outside the host's local network. Remote access (if ever needed) goes through Tailscale or an equivalent overlay, never a public port.
- **No encryption at rest** for v1. Postgres data is on the host's filesystem; protect with full-disk encryption at the OS layer if needed.
- **PHI considerations.** Medical-adjacent data is sensitive. The system is for the user's personal/family use, not for production with third-party patients. Compliance (HIPAA, GDPR Art. 9) is **out of scope** for v1 and called out in §15.
- **neonize ToS.** Using neonize means using an unofficial WhatsApp client. This may violate WhatsApp ToS and accounts can be banned, especially for high-volume proactive outbound. Mitigations: low message rate (reminders only), no broadcast, no spammy patterns. A migration path to the WhatsApp Cloud API is a §16 item.
- **LLM data flow.** Inbound messages and the last 20 turns of conversation are sent to Google as part of Gemini calls. Don't put data in this bot that you wouldn't put in a Gmail draft.

## 14. Observability

- **Logging:** Python `logging` to stdout, format `%(asctime)s %(levelname)s %(name)s: %(message)s`. JSON formatter is future-work.
- **Levels:** `LOG_LEVEL=INFO` in prod, `DEBUG` in dev. neonize emits its own logs — keep at `INFO`.
- **What we log:**
  - Inbound WA event source + length (not content, to keep logs lean).
  - Outbound dispatch (notification id, patient jid, ok/error).
  - Agent failures (full traceback).
  - DB migrations on startup.
- **Metrics / tracing:** none in v1. Future: OpenTelemetry export to a self-hosted collector.

## 15. Open questions

1. **PHI / compliance.** If this bot is ever used for third-party patients, what is the minimum compliance posture (HIPAA-equivalent, GDPR Art. 9 lawful basis)?
2. **Should `change_appointment_status` be auto-driven?** E.g. when the `+1h` reminder fires, the bot could ask "¿cómo te fue?" and infer `done`/`missed` from the reply.
3. **Multi-patient identity collision.** If two people share a phone (rare but possible), they share a record. Acceptable?
4. **Free-tier Gemini limits.** What is the daily quota of `gemini-1.5-flash` free tier in 2026 and is it enough? Plan B if exceeded?
5. **Reminder for medications: do we model dose + unit?** Currently just free-text `message`. Adding `dose`, `unit`, `taken_at` would enable adherence tracking but expands scope.
6. **Time-of-day defaults.** When the LLM extracts a date with no time, what default? "AM" → 09:00? Ask the patient? Currently: ask.

## 16. Future work

- **WhatsApp Cloud API migration.** Implement the channel as an interface (`Channel.send_message`, `Channel.on_message`); add a Cloud API adapter alongside neonize.
- **Doctor-facing companion.** Read-only summary of a patient's upcoming appointments, shared via a unique link.
- **Encryption at rest.** Postgres TDE or column-level encryption for `notes`/`message`.
- **Off-site backup replication.** `rclone` or `restic` push to Backblaze B2 / S3.
- **OpenTelemetry traces.** Especially around the agent loop and Gemini latency.
- **Multimodal inputs.** Photos of prescriptions / lab results → OCR via Gemini.
- **Adherence tracking.** "Did you take your meds?" yes/no flow + monthly summary.
- **Voice notes.** Gemini speech-to-text on WhatsApp audio messages.

## 17. Glossary

| Term | Meaning |
|---|---|
| **JID** | "Jabber ID" — WhatsApp's user identifier on the multi-device protocol. Form: `<phone>@s.whatsapp.net`. |
| **RRULE** | iCalendar recurrence rule, RFC 5545. E.g. `FREQ=MONTHLY;BYMONTHDAY=1`. |
| **DTSTART** | iCal anchor datetime for an RRULE; first eligible occurrence. |
| **neonize** | Unofficial Python binding to `whatsmeow` (Go WhatsApp client used by many Web/Desktop clones). |
| **whatsmeow** | Open-source Go library implementing WhatsApp's multi-device protocol. |
| **PydanticAI** | Agent framework from the Pydantic team; type-first, model-agnostic. |
| **SQLModel** | Pydantic + SQLAlchemy 2 hybrid by FastAPI's author. |
| **GHCR** | GitHub Container Registry (`ghcr.io`). |
| **Watchtower** | Container that auto-updates other containers when their image digest changes. |
