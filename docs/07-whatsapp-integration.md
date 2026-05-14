# 07 — WhatsApp Integration

> **Goal:** connect the bot to a real WhatsApp account via neonize, route inbound messages to the agent, and run the notification scheduler so reminders go out. After this step the system is feature-complete for MVP.

---

## Why this step exists

This is where everything plugs together: WhatsApp transport, agent loop, scheduler dispatch, and your live deploy. Doing it last means every other piece has its own tests and admin route — when something breaks, you isolate fast.

You'll learn:

- How `whatsmeow` (via neonize) handles multi-device pairing (QR) and persists session state.
- The asyncio lifespan pattern for owning background tasks alongside FastAPI.
- How to share a single neonize client between the inbound handler and the scheduler.
- How to test message-handler logic without a real WhatsApp account.
- Why the bot's `wa_session` directory is the single most precious bind-mount.

## Prerequisites

- Step 06 done; `POST /admin/chat` works end-to-end.
- A WhatsApp account you're willing to risk (terms-of-service risk per the design doc).
- Linux (or WSL) for running neonize locally during the first QR scan — neonize ships native binaries.

## Concepts

**Multi-device protocol.** Modern WhatsApp lets your phone "pair" companion devices (Web, Desktop, neonize). Each device gets its own keys and can send/receive without the phone being online. Pairing happens by scanning a QR code displayed by the companion.

**Session persistence.** neonize keeps device keys in a SQLite file (path from `WA_SESSION_DB`). Losing this file = re-pairing required. Back it up like a credential.

**JID.** WhatsApp's identifier. For personal chats: `573001112233@s.whatsapp.net`. For groups: `<id>@g.us`. We only handle 1:1 chats for v1; ignore group messages.

**asyncio.create_task.** Spawns a coroutine on the current event loop. Inside FastAPI's lifespan this is how we start long-running background loops (WA client, scheduler) without blocking the HTTP server.

**Shared client.** The scheduler needs the same neonize client the handler uses. Stash it on `app.state.wa_client` after `client.connect()` returns. The scheduler reads it from there.

## Steps

### 1. Add the dependency and bookkeeping

```bash
uv add 'neonize>=0.3.17'
mkdir wa_session                  # local; bind-mounted in docker
```

`.gitignore` already excludes `wa_session/`.

Add to `.env.example`:

```
WA_SESSION_DB=./wa_session/medixio.sqlite3
```

### 2. WhatsApp client module

`src/medixio/whatsapp/client.py`:

```python
import logging

from neonize.aioze.client import NewAClient
from neonize.events import ConnectedEv, MessageEv, PairStatusEv

from medixio.config import get_settings
from medixio.whatsapp.handlers import handle_message

log = logging.getLogger(__name__)


def build_client() -> NewAClient:
    settings = get_settings()
    settings.wa_session_db.parent.mkdir(parents=True, exist_ok=True)
    client = NewAClient(str(settings.wa_session_db))

    @client.event(ConnectedEv)
    async def _on_connected(_c, _e):
        log.info("WhatsApp connected")

    @client.event(PairStatusEv)
    async def _on_pair(_c, e):
        log.info("paired with %s", e.ID.User)

    @client.event(MessageEv)
    async def _on_msg(c, e):
        try:
            await handle_message(c, e)
        except Exception:
            log.exception("error handling message")

    return client


async def run_client(client: NewAClient) -> None:
    """Block until disconnect. Prints a QR code on first run."""
    await client.connect()
```

Add `wa_session_db: Path` to `Settings` (with a default of `Path("./wa_session/medixio.sqlite3")`).

### 3. Inbound handler

`src/medixio/whatsapp/handlers.py`:

```python
import logging

from neonize.aioze.client import NewAClient
from neonize.events import MessageEv
from sqlmodel import Session, select

from medixio.agent import answer as agent_answer
from medixio.db import engine
from medixio.models import Message, MessageRole, Patient

log = logging.getLogger(__name__)

ONBOARDING_PROMPT = "¡Hola! Soy Medixio. ¿Cómo te llamas?"


async def handle_message(client: NewAClient, event: MessageEv) -> None:
    chat = event.Info.MessageSource.Chat
    text = (event.Message.conversation or "").strip()
    if not text:
        return

    # Ignore group messages for v1
    if chat.Server != "s.whatsapp.net":
        return

    jid = f"{chat.User}@{chat.Server}"

    with Session(engine) as session:
        patient = session.exec(select(Patient).where(Patient.whatsapp_jid == jid)).first()
        if patient is None:
            patient = Patient(whatsapp_jid=jid, phone_number=f"+{chat.User}")
            session.add(patient)
            session.commit()
            session.refresh(patient)
            await client.send_message(chat, ONBOARDING_PROMPT)
            session.add(Message(patient_id=patient.id, role=MessageRole.user, content=text))
            session.add(
                Message(patient_id=patient.id, role=MessageRole.assistant, content=ONBOARDING_PROMPT)
            )
            session.commit()
            return

        # Capture name on second message if still missing
        if patient.name is None:
            patient.name = text[:80]
            session.add(patient)
            session.commit()
            reply = f"Encantado, {patient.name}. ¿En qué te ayudo?"
            await client.send_message(chat, reply)
            session.add(Message(patient_id=patient.id, role=MessageRole.user, content=text))
            session.add(Message(patient_id=patient.id, role=MessageRole.assistant, content=reply))
            session.commit()
            return

        reply = await agent_answer(session, patient, text)

    await client.send_message(chat, reply)
```

Note: the agent runner already persists messages. The early-return branches above persist manually because they bypass the agent.

### 4. Scheduler with templates

`src/medixio/whatsapp/templates.py`:

```python
APPT_REMINDER_1D = "📅 Tu cita con el Dr. {doctor_name} es mañana a las {time}."
APPT_REMINDER_30M = "⌛ Tu cita con el Dr. {doctor_name} es en 30 minutos."
APPT_FOLLOWUP_1H = "⭐ ¿Cómo te fue en la cita con el Dr. {doctor_name}?"
```

`src/medixio/services/notifications.py` — wire auto-notif on `schedule_appointment`:

```python
from datetime import timedelta
from zoneinfo import ZoneInfo

from medixio.whatsapp.templates import APPT_REMINDER_1D, APPT_REMINDER_30M, APPT_FOLLOWUP_1H

BOGOTA = ZoneInfo("America/Bogota")


def auto_notifications_for(appointment) -> list[Notification]:
    d = appointment.date
    time_str = d.astimezone(BOGOTA).strftime("%H:%M")
    return [
        Notification(patient_id=appointment.patient_id, appointment_id=appointment.id,
                     date=d - timedelta(days=1),
                     message=APPT_REMINDER_1D.format(doctor_name=appointment.doctor_name, time=time_str)),
        Notification(patient_id=appointment.patient_id, appointment_id=appointment.id,
                     date=d - timedelta(minutes=30),
                     message=APPT_REMINDER_30M.format(doctor_name=appointment.doctor_name)),
        Notification(patient_id=appointment.patient_id, appointment_id=appointment.id,
                     date=d + timedelta(hours=1),
                     message=APPT_FOLLOWUP_1H.format(doctor_name=appointment.doctor_name)),
    ]
```

`src/medixio/worker/scheduler.py`:

```python
import asyncio
import logging
from datetime import datetime, timezone

from dateutil.rrule import rrulestr
from neonize.aioze.client import NewAClient
from sqlmodel import Session, select

from medixio.db import engine
from medixio.models import Notification, Patient

log = logging.getLogger(__name__)
TICK_SECONDS = 60


async def run_scheduler(wa_client: NewAClient) -> None:
    log.info("scheduler started (tick=%ss)", TICK_SECONDS)
    while True:
        try:
            await _tick(wa_client)
        except Exception:
            log.exception("scheduler tick failed")
        await asyncio.sleep(TICK_SECONDS)


async def _tick(wa_client: NewAClient) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine) as s:
        due_oneoff = s.exec(
            select(Notification).where(
                Notification.rrule.is_(None),
                Notification.last_sent_at.is_(None),
                Notification.date <= now,
            )
        ).all()
        recurring = s.exec(select(Notification).where(Notification.rrule.is_not(None))).all()

        for n in due_oneoff:
            await _send(wa_client, s, n, fire_time=now)

        for n in recurring:
            after = n.last_sent_at or (n.date.replace(microsecond=0))
            next_occ = rrulestr(n.rrule, dtstart=n.date).after(after, inc=False)
            if next_occ and next_occ <= now:
                await _send(wa_client, s, n, fire_time=next_occ)
        s.commit()


async def _send(client: NewAClient, s: Session, n: Notification, fire_time) -> None:
    patient = s.get(Patient, n.patient_id)
    if not patient:
        return
    try:
        await client.send_message(patient.whatsapp_jid, n.message)
        n.last_sent_at = fire_time
        s.add(n)
    except Exception:
        log.exception("failed to send notification %s", n.id)
```

### 5. Wire into the lifespan

`src/medixio/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    wa = build_client()
    app.state.wa_client = wa
    wa_task = asyncio.create_task(run_client(wa), name="whatsapp")
    sch_task = asyncio.create_task(run_scheduler(wa), name="scheduler")
    try:
        yield
    finally:
        for t in (wa_task, sch_task):
            t.cancel()
        await asyncio.gather(wa_task, sch_task, return_exceptions=True)
```

### 6. Local first-run (QR pairing)

```bash
docker compose up -d db
uv run alembic upgrade head
uv run medixio
```

Watch stdout. neonize prints an ASCII QR code. On your phone:

> WhatsApp → Settings → Linked devices → Link a device → scan.

After pairing, the same logs print `WhatsApp connected`. Send a message to *your own* number from a friend's phone (or from another account). The bot should reply.

### 7. Mount the session in Docker

`docker-compose.yml` (bot service):

```yaml
    volumes:
      - ./wa_session:/app/wa_session
```

Copy your locally-paired `wa_session/medixio.sqlite3` to the server, or re-pair from the server by running `docker compose run --rm bot medixio` interactively the first time.

### 8. Deploy

Push to `main`. CI builds. Server pulls. `docker compose ps` shows `bot` healthy. Send a message — reply comes back.

### 9. Verify the scheduler

Quick sanity-check: poke a notification due in 90 seconds:

```bash
docker compose exec db psql -U medixio medixio
# inside psql:
INSERT INTO notification (id, patient_id, date, message, created_at)
VALUES (gen_random_uuid(),
        (SELECT id FROM patient LIMIT 1),
        now() + interval '90 seconds',
        '🧪 Test reminder',
        now());
```

Wait two minutes. Your WhatsApp should ding.

### 10. Commit

```bash
git add pyproject.toml uv.lock src docker-compose.yml
git commit -m "whatsapp: neonize client + scheduler + auto-notifs"
```

## Files touched in this step

| Path | Purpose |
|---|---|
| `pyproject.toml` / `uv.lock` | + neonize, python-dateutil |
| `src/medixio/whatsapp/client.py` | builds + connects the neonize client |
| `src/medixio/whatsapp/handlers.py` | inbound routing + onboarding |
| `src/medixio/whatsapp/templates.py` | Spanish copy |
| `src/medixio/services/notifications.py` | `auto_notifications_for(...)` |
| `src/medixio/worker/scheduler.py` | tick loop, RRULE dispatch |
| `src/medixio/main.py` | lifespan spawns WA + scheduler tasks |
| `docker-compose.yml` | bind-mounts `./wa_session` |

## Verification

- [ ] First-run prints a QR; scanning produces `paired with <number>` and `WhatsApp connected`.
- [ ] Sending a real WhatsApp message triggers the agent and a reply arrives.
- [ ] Scheduling an appointment via WA creates three rows in `notification`.
- [ ] The hand-inserted "+90 s" test notification fires.
- [ ] Restarting the bot does **not** require re-pairing (session persisted in bind mount).
- [ ] Group messages are ignored (no reply, no rows).

## Common gotchas

- **QR doesn't appear in Docker logs.** Some terminals mangle ANSI. Run once *outside* Docker (`uv run medixio`), pair, then move the session file into the bind-mount.
- **`PairStatusEv` fires but no messages arrive.** WhatsApp moved the connection to the phone briefly. Watching for `ConnectedEv` after `PairStatusEv` is the real "ready" signal.
- **Bot replies to itself in groups.** You skipped the `chat.Server != "s.whatsapp.net"` guard.
- **Scheduler sends the same reminder twice.** The `_send` exception path forgot to set `last_sent_at`. Either send is idempotent on the receiver, or you guard at the DB.
- **Account banned.** You sent unsolicited bulk messages, replied to many strangers, or scraped phone numbers. neonize is invisible to anti-spam right up until you trip a heuristic. Stay low-volume.
- **`wa_session` lost.** Restore from backup, or accept re-pairing. Decide your backup strategy here as carefully as for Postgres.
