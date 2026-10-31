# Medixio — Design

> **Status:** Draft v2 · Last updated: 2026-10-31 · Companion: [intent.md](intent.md)
> Supersedes [archive/design-v1-gemini-postgres.md](archive/design-v1-gemini-postgres.md).

This document says **how** Medixio is built. Scope and motivation live in `intent.md`.

---

## 1. Architecture

Single Python asyncio process, self-hosted in one Docker container.

```
 WhatsApp ◄──multi-device──► neonize client ──┐
                                              │ MessageEv (text / image)
┌─────────────────────────────────────────────▼───────────────────────────┐
│ medixio process                                                         │
│                                                                         │
│  channel/ (Channel interface, neonize adapter)                          │
│      │                                                                  │
│      ▼                                                                  │
│  conversation handler ── loads user, profile, last N messages           │
│      │                                                                  │
│      ▼                                                                  │
│  PydanticAI agent (Anthropic Claude) ── tools ──► module services       │
│                                                      │                  │
│  scheduler loop (60 s tick) ── due reminders ────────┤                  │
│                                                      ▼                  │
│  FastAPI: /health, /admin/*            SQLite (WAL) medixio.db          │
└─────────────────────────────────────────────────────────────────────────┘
                     │
                     ▼
            Anthropic Messages API
```

**Lifespan.** FastAPI lifespan starts two tasks: the neonize client and the scheduler. Both cancelled on shutdown. The channel instance is shared so the scheduler can send.

## 2. Technology choices

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.12, `uv`, `ruff`, `mypy --strict`, `pytest` | Already set up in repo |
| LLM | Anthropic Claude via PydanticAI | Default `claude-sonnet-5-5` for conversation + vision; `claude-haiku-5-5` candidate for cheap classification. Model id via env |
| Agent framework | PydanticAI | Typed tools, `deps_type`, model-agnostic |
| WhatsApp | neonize (unofficial, whatsmeow) | Behind `Channel` interface; Cloud API adapter is future work |
| HTTP | FastAPI + uvicorn | `/health`, admin endpoints, bound to localhost / LAN |
| DB | SQLite 3, WAL mode | One file, single writer process, fits scale |
| ORM / migrations | SQLModel + Alembic | Alembic `render_as_batch=True` for SQLite ALTERs |
| Recurrence | iCal RRULE (`python-dateutil`) | LLM generates RRULE strings |
| Backups | Litestream → off-host storage, or nightly `sqlite3 .backup` | See §9 |
| Deploy | Docker compose, GHCR, Watchtower | §9 |

## 3. Code layout

Modular by domain, matching current `src/medixio/modules/`:

```
src/medixio/
  main.py                 # entrypoint: uvicorn + lifespan
  config.py               # pydantic-settings
  db.py                   # engine, session factory, PRAGMAs
  channel/
    base.py               # Channel protocol: send_text, send_image?, on_message
    neonize_adapter.py
  agent/
    agent.py              # PydanticAI Agent, system prompt
    deps.py               # RunDeps(session, user, profile, now)
    tools/                # one file per module, thin wrappers over services
  scheduler/
    loop.py, dispatch.py
  knowledge/              # shared Colombian bureaucracy rules (YAML/MD + loader)
  modules/
    patients/             # user, profile, consent, preferences
    doctors/
    appointments/
    orders/               # fórmulas médicas + order items (medicines)
    authorizations/
    dispensing/           # pickups, pendientes
    claims/               # PQRS / tutela cases
    reminders/            # generic notifications (all modules write here)
    extraction/           # in-memory image → structured data (no storage)
    conversations/        # message history
  shared/
```

Each module: `domain.py` (pydantic), `models.py` (SQLModel tables), `service.py` (business logic, no LLM), `repository.py` if needed. Agent tools call services; services never import the agent.

## 4. Data model

All tables: `id` TEXT (UUID), `created_at`, `updated_at`. Datetimes stored as UTC ISO-8601 text; rendered in `America/Bogota`. Dates without time (expiry dates) stored as `DATE`.

### 4.1 Users & profile

**patient** — `whatsapp_jid` (unique; one number = one patient, no multi-patient accounts), `phone_number`, `name`, `consent_accepted_at`, `deleted_at`.

**patient_profile** (1:1) — `eps`, `regimen` (`contributivo|subsidiado|especial`), `city`, `default_pharmacy`, `reminder_hour` (default 08:00), `delivery_mode` (`pickup|home`).

**patient_preference** — key/value overrides of shared defaults: `key` (e.g. `order.renewal_lead_days`), `value` (JSON), `note`. Unique `(patient_id, key)`.

### 4.2 Clinical-administrative records

**doctor** — `patient_id`, `name`, `specialty`, `phone`, `address`, `institution` (IPS).

**appointment** — `patient_id`, `doctor_id?`, `specialty`, `datetime?`, `location`, `status` (`draft|scheduled|done|missed|cancelled`), `notes`, `extracted_from_image` (bool).

**medical_order** (fórmula) — `patient_id`, `doctor_id?`, `issued_on`, `duration_months`, `expires_on` (computed `issued_on + duration`, editable), `status` (`active|renewal_requested|renewed|expired`), `renewed_by_order_id?`, `extracted_from_image` (bool).

**order_item** — `order_id`, `medicine_name`, `presentation`, `dose_text` (verbatim, never interpreted), `quantity_per_dispense`, `dispenses_total`.

**authorization** — `patient_id`, `order_id?`, `eps`, `number`, `service_description`, `issued_on`, `valid_until`, `provider` (pharmacy/IPS), `status` (`active|used|expired|denied`), `extracted_from_image` (bool).

**dispense** (one row per monthly pickup of a whole fórmula) — `patient_id`, `order_id`, `cycle`, `due_on`, `dispensed_on?`, `pharmacy`, `status` (`due|awaiting_confirmation|dispensed|partial|pending`), `pending_note`, `confirmation_asked_at?`. A cycle only reaches `dispensed` when the user confirms it.

**claim** — `patient_id`, `kind` (`pqrs|tutela|impugnacion|desacato`), `subject`, `filed_on?`, `response_due_on?`, `status` (`draft|filed|answered|escalated|closed`), `related_authorization_id?`.

### 4.3 Supporting

No `document` table: images are not persisted (§6.1).

**reminder** — `patient_id`, `subject_type` + `subject_id` (polymorphic link to the record that created it, nullable for free-form), `kind`, `fire_at` (one-off or DTSTART), `rrule?`, `message`, `last_sent_at?`, `cancelled_at?`. Index `(fire_at) WHERE last_sent_at IS NULL AND cancelled_at IS NULL`.

**message** — `patient_id`, `role` (`user|assistant`), `content`, `has_image` (bool; the image itself is not stored, only a placeholder like `[imagen: fórmula médica]`), `created_at`.

## 5. Shared knowledge vs per-user overrides

`knowledge/` holds versioned data files, not code. Every rule cites its source and records the admin's review. Rules with `source: product` are product decisions and always apply. **Any other entry with `reviewed_on: null` is ignored at runtime**: reminders fall back to product defaults without quoting legal deadlines, and unreviewed guides make the bot say the information isn't verified yet and point to the EPS / Supersalud / Personería.

```yaml
# knowledge/defaults.yaml
order:
  renewal_lead_days:
    value: 15                     # product decision, not legal
    source: product
    reviewed_by: admin
    reviewed_on: null
  dispense_frequency: monthly     # chronic fórmulas up to 3 months, dispensed monthly
  dispense_frequency_meta:
    source: "Guía de dispensación (cadena de droguerías, 2023) — práctica, no norma"
    reviewed_on: null
  formula_validity_days:          # 30 general / 15 control especial (Nueva EPS); no explicit legal term found
    general: 30
    control_especial: 15
    source: "Nueva EPS; concepto Minsalud 201511200169221 (2015); Decreto 780/2016"
    reviewed_on: null
dispensing:
  pending_delivery_hours:
    value: 48                     # from the moment the user claims the medicine
    source: "Decreto-ley 019/2012 art. 131; Resolución 1604/2013"
    reviewed_on: null
  pending_delivery_hours_over_62:
    value: 72                     # home delivery
    source: "Ley 1171/2007"
    reviewed_on: null
  pending_reactivates_formula_days:
    value: 30
    source: "Circular Minsalud (2026) — verify number and date"
    reviewed_on: null
claims:
  pqrs_response_business_days:
    value: 15                     # extendable by notice
    source: "Ley 1755/2015 art. 14 (Ley 1437/2011)"
    reviewed_on: null
  health_claim_response_hours:
    value: 72                     # 24 h if life at risk
    source: "Secondary source only (colombiatramita) — find primary norm"
    reviewed_on: null
  tutela_decision_business_days:
    value: 10
    source: "Decreto 2591/1991 art. 29 — not yet verified online"
    reviewed_on: null
authorization:
  expiry_lead_days: { value: 7, source: product, reviewed_on: null }
appointment:
  remind_offsets: ["-1d", "-2h", "+2h"]
```

Plus `knowledge/guides/*.md` (PQRS how-to, tutela steps, pendientes, what an autorización is), each with front-matter `sources`, `reviewed_by`, `reviewed_on`. Loaded on demand by a `get_guide(topic)` tool, keeping the system prompt small.

**Admin review workflow:** knowledge changes go through a PR; the admin (project author only) verifies each source against the official text and sets `reviewed_by` / `reviewed_on`. CI check (`just check-knowledge`) lists unreviewed entries and entries reviewed > 3 months ago (quarterly review cycle). Admin can also list them via `GET /admin/knowledge/unreviewed`.

Resolution: `settings.resolve(patient, key)` → `patient_preference` if present else reviewed `defaults.yaml` value. Every service that schedules reminders calls this.

## 6. Agent

- One PydanticAI `Agent`, model `anthropic:<ANTHROPIC_MODEL>`.
- `RunDeps`: DB session, patient, resolved profile, `now` (injected for tests).
- System prompt (Spanish, short): role, no medical/legal advice, confirm before saving, one question at a time, today's date in Bogotá, user profile summary. Cached with Anthropic prompt caching.
- History: last 20 messages from `message`.
- **Tools** (each a thin wrapper over a service):
  - profile: `get_profile`, `update_profile`, `set_preference`
  - appointments: `create_appointment`, `list_appointments`, `update_appointment`, `set_appointment_status`
  - orders: `create_order` (with items), `list_orders`, `mark_order_renewed`
  - authorizations: `create_authorization`, `list_authorizations`, `set_authorization_status`
  - dispensing: `record_dispense`, `record_pending`, `list_pendings`
  - claims: `open_claim`, `update_claim`, `get_guide`
  - reminders: `create_reminder`, `list_reminders`, `cancel_reminder`
  - privacy: `export_my_data`, `delete_my_data` (requires explicit confirmation phrase)
- Tools are the **only** way the agent mutates data.
- **Retries:** 3× exponential backoff on Anthropic 429/5xx/timeout; final failure → canned Spanish reply, log error.

### 6.1 Image flow (no retention)

1. neonize delivers `ImageMessage` → download bytes **into memory only** (never to disk).
2. Handler runs a structured-output Claude call with the image block, returning a typed pydantic model (`OrderExtraction`, `AuthorizationExtraction`, `AppointmentExtraction`, or `Unknown`).
3. Image bytes are dropped right after the call. `message` stores only a text placeholder; extraction result is kept in the pending-confirmation state of the conversation (stored as text in the assistant message).
4. Bot summarizes the extraction and asks for confirmation. On "sí", agent calls the matching `create_*` tool with `extracted_from_image=True`. On correction, agent applies edits from text; if wrong, user re-sends the photo.
5. Low-confidence or missing fields → ask the user.

Guarantees: no image in DB, filesystem, logs, or backups. neonize's media cache (if any) is disabled or purged after download. Anthropic receives the image once per extraction call.

## 7. Reminder rules

Services create `reminder` rows when records change; the scheduler only dispatches.

| Trigger | Reminder(s) |
|---|---|
| Appointment scheduled | offsets from `appointment.remind_offsets`; rescheduling cancels + recreates |
| Order created | `expires_on − renewal_lead_days` at `reminder_hour`: "Tu fórmula de X vence el …, pide la renovación" |
| Order items | monthly dispensing reminder (RRULE `FREQ=MONTHLY`) until `expires_on`; same day evening (or next morning) bot asks "¿Ya reclamaste …?" → `dispensed` / `partial` / `pending`. No answer → ask again next day, up to 3 times, then flag in the next reminder |
| Authorization created | `valid_until − expiry_lead_days` if still `active` |
| Pending recorded | follow-up after `pending_delivery_hours` asking if it arrived; if not, offer PQRS guidance; repeat until resolved |
| Claim filed | at `response_due_on`: "¿Te respondieron?" + next-step guidance |
| Free-form | as given by user (one-off or RRULE) |

Status changes (`done`, `renewed`, `used`, `closed`) cancel future linked reminders.

## 8. Scheduler

- Tick every 60 s. Query due one-offs (`fire_at <= now`, unsent, not cancelled) and recurring (`next occurrence after last_sent_at <= now`).
- Send through `Channel`; on success set `last_sent_at` in the same transaction.
- Same-patient reminders due in the same tick are merged into one message.
- After downtime: each one-off fires once; recurring sends only latest missed occurrence.
- Throttle: max 1 outbound message/sec globally (ban mitigation).
- Quiet hours: nothing sent 21:00–07:00 Bogotá; deferred to 07:00.

## 9. Deployment & operations

**Container:** one `bot` service. Volumes (bind): `./data/medixio.db`, `./data/wa_session/`. No documents volume — images aren't stored.

**SQLite settings:** `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=NORMAL`. Single process only — never run two replicas.

**Migrations:** `alembic upgrade head` on container start, before the app.

**CI/CD:** GitHub Actions on `main` → `just check` + `just test` → build image → push `ghcr.io/jose-garzon/medixio:{latest,sha}`. Watchtower on server pulls `latest`.

**Backups:** Litestream continuously replicating `medixio.db` to off-host storage (B2/S3/another machine), plus nightly encrypted tar of `wa_session/`. Restore drill documented in runbook.

**Env vars:**

| Var | Example |
|---|---|
| `ANTHROPIC_API_KEY` | secret |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` |
| `DATABASE_URL` | `sqlite:///data/medixio.db` |
| `WA_SESSION_DB` | `/app/data/wa_session/session.sqlite3` |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` |
| `TZ_DISPLAY` | `America/Bogota` |
| `LOG_LEVEL` | `INFO` |

**First run:** `docker compose up -d`, `docker compose logs -f bot`, scan QR with the bot's phone. Session persists in `wa_session/`.

## 10. Security & privacy

- Health data is sensitive (Ley 1581 *datos sensibles*): explicit consent on first message, stored with timestamp; bot refuses to process until accepted.
- `delete_my_data` hard-deletes all rows for the patient; WhatsApp history outside our control is noted to user.
- Host disk encryption; DB and API not exposed publicly (admin via Tailscale/LAN).
- Logs never contain message content or images; only ids, lengths, outcomes. Observability data lives in its own file (§10.1).
- Data sent to Anthropic: messages, last 20 turns, images (once, at extraction). Stated in consent text.
- Images never stored locally (§6.1).
- neonize ToS risk accepted; mitigations in §8.

## 10.1 Observability (local)

`src/medixio/observability/`, all local, no external service.

- **Store:** separate SQLite file `data/observability.db` (`OBSERVABILITY_DB`), so diagnostics never contend with or mix into patient data. Retention 30 days (`OBSERVABILITY_RETENTION_DAYS`), purged hourly.
- **Events:** every WARNING+ log record with exception type and traceback. Logs never carry message content or images, only ids, lengths and outcomes.
- **Metrics:** `agent.run` (latency, ok, attempt, tools called), `agent.tokens_in/out`, `extraction.run` (kind, confidence), `message.handle`, `whatsapp.inbound`, `whatsapp.send` (reply / proactive), `whatsapp.connected`, `scheduler.tick`, `reminders.sent`.
- **Heartbeats:** scheduler after every successful tick.
- **WhatsApp lifecycle:** disconnect (warning), logged out / session replaced (error), temporary ban (critical).
- **Checks** (`ok|warn|fail`): database integrity, WhatsApp connected, scheduler heartbeat < 3 ticks, overdue reminders (> 15 min, outside quiet hours), agent failure rate and p95 latency in the last hour, error count in the last hour, free disk, unreviewed knowledge.
- **Endpoints** (admin): `GET /admin/obs` HTML dashboard (auto-refresh, works offline), `/admin/obs/status`, `/admin/obs/metrics?hours=`, `/admin/obs/events?level=&limit=`. With `ADMIN_TOKEN` set, the browser uses `?token=`.
- **Logs:** stdout, plain text or JSON (`JSON_LOGS=true`).

## 10.2 Rate limits (abuse and cost protection)

`src/medixio/ratelimit.py`, checked on every inbound message **before** any LLM call. Sliding-window counters live in the observability store (`rate_event`), so they survive restarts; kept 2 days.

| Limit | Default (env) | Over the limit |
|---|---|---|
| Messages per number | 15 / 10 min, 150 / day (`RATE_MSGS_PER_10MIN`, `RATE_MSGS_PER_DAY`) | one notice per 10 min, then silence |
| Photos per number | 10 / day (`RATE_IMAGES_PER_DAY`) | notice; image dropped unread |
| New numbers (global) | 20 / hour (`RATE_SIGNUPS_PER_HOUR`) | unknown numbers ignored, warning logged |
| Message length | 2,000 chars (`MAX_MESSAGE_CHARS`) | truncated before the agent |
| Anthropic tokens (global, agent + extraction) | 2M / 24 h (`DAILY_TOKEN_BUDGET`) | canned reply to everyone; reminders keep working |
| Admin API | — | process refuses to start if `API_HOST` isn't localhost and `ADMIN_TOKEN` is missing, `change-me`, or < 16 chars |

Visibility: `rate_limits` health check (warn at 80% budget or any blocked number, fail at 100%), `ratelimit.blocked` metric, `GET /admin/obs/ratelimits` (numbers masked, e.g. `5730…33`).

## 11. Testing

- Services: unit tests with in-memory SQLite and injected `now`.
- Agent: PydanticAI `TestModel` / `FunctionModel` to assert tool calls without hitting Anthropic.
- Extraction: fixture images + recorded responses; optional live eval suite run manually. Test asserts no file is written during image handling.
- Knowledge: test that unreviewed entries are not resolved.
- Scheduler: freeze time, assert idempotency across simulated restarts.

## 12. Milestones

1. Scaffold + config + SQLite + Alembic + `/health` + Docker.
2. Patients, consent, profile; agent behind `POST /admin/chat`.
3. neonize channel, text conversations, message history.
4. Reminders + scheduler; appointments.
5. Orders + image extraction + renewal reminders.
   Knowledge base researched and reviewed by admin before milestone 6 goes live.
6. Authorizations, dispensing with confirmation, pendientes.
7. Claims + knowledge guides.
8. Privacy tools, backups, deploy hardening.

## 13. Future work

WhatsApp Cloud API adapter · voice notes (STT) · other countries' knowledge packs · adherence tracking · PDF export of a patient summary for doctor visits.

## 14. Glossary

| Term | Meaning |
|---|---|
| EPS | Entidad Promotora de Salud — health insurer |
| IPS | Institución Prestadora de Salud — clinic/hospital |
| Fórmula / orden médica | Prescription, valid for a set duration |
| Autorización | EPS approval for a medicine/procedure, with validity window |
| Pendiente | Medicine not delivered at pickup; owed by pharmacy |
| PQRS | Peticiones, Quejas, Reclamos y Sugerencias — formal complaint |
| Tutela | Constitutional action to protect the right to health |
| JID | WhatsApp user id, `<phone>@s.whatsapp.net` |
| RRULE | iCal recurrence rule (RFC 5545) |
