# 06 — Agent: PydanticAI + Gemini

> **Goal:** stand up a PydanticAI agent backed by Gemini, expose a `POST /admin/chat` route that takes a patient JID + text and returns the agent's reply. WhatsApp transport is the *next* step — here we prove the agent can think and write to the DB.

---

## Why this step exists

The agent is the brain of the system; debugging it through WhatsApp is painful (round trips through a flaky channel). Building it behind an HTTP endpoint first lets you iterate fast with `curl`, write deterministic tests, and watch the tool-call trace without scanning a phone.

You'll learn:

- The PydanticAI `Agent` contract: model + system prompt + typed tools + `deps_type` + message history.
- How tool calls work: the LLM decides *which* function to call and *what* args; PydanticAI invokes the Python function and feeds the result back.
- Why dependencies (DB session, current patient) flow through `RunContext` and not module globals.
- How to keep system prompts short — every token is paid for.
- How retry / fallback wraps the agent call without leaking into the agent itself.

## Prerequisites

- Step 05 done; the four tables exist and `/admin/patients` works.
- A Google AI Studio API key (free tier): <https://aistudio.google.com/app/apikey>.

## Concepts

**PydanticAI agent.** A typed wrapper around an LLM. You declare the model, the dependency type (`deps_type`), the structured output type (`output_type`, optional), and one or more tools. Calling `agent.run(prompt, deps=…, message_history=…)` returns a `RunResult` with the model's text and a trace of tool calls.

**Tool.** A regular Python function decorated with `@agent.tool` (gets `RunContext[Deps]`) or `@agent.tool_plain` (no context). The function's type hints become the JSON schema the LLM sees. Return values are serialised back to the model as the tool's "observation".

**Message history.** A list of `ModelMessage` objects. The agent appends to it each turn. For our case we *load* the last N from the `message` table at the start of a turn and *append* the new user/assistant messages at the end.

**Spanish system prompt.** Stays short. Heavy instructions belong in tool descriptions (which the model reads as the schema), not in the system block.

**Retry envelope.** Don't put retry logic inside the agent. Wrap the whole `agent.run(...)` call in an exponential-backoff retry so transient Gemini 429/5xx don't fail the conversation turn.

## Steps

### 1. Add dependencies

```bash
uv add 'pydantic-ai[gemini]'
```

PydanticAI's Gemini provider uses Google's GenAI SDK under the hood.

### 2. Settings for the LLM

Append to `src/medixio/config.py`:

```python
class Settings(BaseSettings):
    # ... existing ...
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
```

Add to `.env.example`:

```
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
```

### 3. Service layer for tool calls

Tools should be thin — they receive params, hand off to a service function, return the result. Build a minimal services layer first.

`src/medixio/services/appointments.py`:

```python
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from medixio.models import Appointment, AppointmentStatus


def create_appointment(
    session: Session,
    *,
    patient_id: UUID,
    doctor_name: str,
    specialty: str,
    date: datetime | None = None,
    doctor_phone: str | None = None,
    doctor_address: str | None = None,
    notes: str | None = None,
) -> Appointment:
    appt = Appointment(
        patient_id=patient_id,
        doctor_name=doctor_name,
        specialty=specialty,
        date=date,
        doctor_phone=doctor_phone,
        doctor_address=doctor_address,
        notes=notes,
        status=AppointmentStatus.active if date else AppointmentStatus.draft,
    )
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt


def list_appointments(
    session: Session,
    *,
    patient_id: UUID,
    only_upcoming: bool = False,
) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.patient_id == patient_id)
    if only_upcoming:
        stmt = stmt.where(Appointment.status == AppointmentStatus.active)
    return list(session.exec(stmt).all())
```

Repeat the same shape for `update_appointment`, `schedule_appointment`, `change_appointment_status` (split appointment lifecycle moves), `create_notification`, `list_notifications`, `cancel_notification`. Keep each function ≤ 30 lines.

### 4. Build the agent

`src/medixio/agent/__init__.py`:

```python
from medixio.agent.runner import answer
__all__ = ["answer"]
```

`src/medixio/agent/agent.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic_ai import Agent, RunContext
from sqlmodel import Session

from medixio.config import get_settings
from medixio.models import Appointment, Notification, Patient
from medixio.services import appointments as appt_svc
from medixio.services import notifications as notif_svc


@dataclass
class RunDeps:
    session: Session
    patient: Patient


SYSTEM_PROMPT = """\
Eres Medixio, un asistente que ayuda a pacientes con enfermedades crónicas a llevar
sus citas médicas y recordatorios.

Reglas:
- Responde siempre en español, sé conciso y empático.
- Nunca des consejo médico.
- Para crear, editar o eliminar datos, usa las herramientas disponibles.
- Si falta información (doctor, especialidad, fecha…), pregunta una sola cosa a la vez.
- Las fechas que el usuario diga ("mañana", "el lunes") deben convertirse a fecha
  absoluta antes de llamar a una herramienta. Zona horaria: America/Bogotá.
"""

agent = Agent(
    model=f"google-gla:{get_settings().gemini_model}",
    deps_type=RunDeps,
    system_prompt=SYSTEM_PROMPT,
)


@agent.tool
def create_appointment(
    ctx: RunContext[RunDeps],
    doctor_name: str,
    specialty: str,
    date: datetime | None = None,
    doctor_phone: str | None = None,
    doctor_address: str | None = None,
    notes: str | None = None,
) -> Appointment:
    """Crea una cita médica. Si `date` es None, queda en estado 'draft'."""
    return appt_svc.create_appointment(
        ctx.deps.session,
        patient_id=ctx.deps.patient.id,
        doctor_name=doctor_name,
        specialty=specialty,
        date=date,
        doctor_phone=doctor_phone,
        doctor_address=doctor_address,
        notes=notes,
    )


@agent.tool
def list_appointments(ctx: RunContext[RunDeps], only_upcoming: bool = False) -> list[Appointment]:
    """Lista las citas del paciente. `only_upcoming=True` filtra a las activas."""
    return appt_svc.list_appointments(
        ctx.deps.session, patient_id=ctx.deps.patient.id, only_upcoming=only_upcoming
    )


@agent.tool
def create_notification(
    ctx: RunContext[RunDeps],
    date: datetime,
    message: str,
    rrule: str | None = None,
) -> Notification:
    """Crea un recordatorio. `rrule` opcional para recurrencia (iCal RRULE)."""
    return notif_svc.create_notification(
        ctx.deps.session, patient_id=ctx.deps.patient.id, date=date, message=message, rrule=rrule
    )

# Add: update_appointment, schedule_appointment, change_status, list_notifications, cancel_notification
```

Notes:

- Tool docstrings are the schema description the LLM sees. Keep them short, in Spanish if you want the LLM to bias Spanish.
- Returning the model directly lets PydanticAI serialise it for the tool observation, and the agent can mention fields in its reply.
- `model="google-gla:..."` is PydanticAI's URI for Google AI Studio (the free-tier endpoint). For Vertex use `google-vertex:`.

### 5. The runner: history + retry

`src/medixio/agent/runner.py`:

```python
import asyncio
import logging
from datetime import datetime
from uuid import UUID

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from sqlmodel import Session, select

from medixio.agent.agent import RunDeps, agent
from medixio.models import Message, MessageRole, Patient

log = logging.getLogger(__name__)

HISTORY_LIMIT = 20
CANNED_FAIL = "Disculpa, no puedo responder en este momento. Intenta de nuevo en unos minutos."


def _load_history(session: Session, patient_id: UUID) -> list[ModelMessage]:
    rows = session.exec(
        select(Message)
        .where(Message.patient_id == patient_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
    ).all()
    rows = list(reversed(rows))
    history: list[ModelMessage] = []
    for r in rows:
        if r.role == MessageRole.user:
            history.append(ModelRequest(parts=[UserPromptPart(content=r.content)]))
        elif r.role == MessageRole.assistant:
            history.append(ModelResponse(parts=[TextPart(content=r.content)]))
    return history


async def _run_with_retry(prompt: str, deps: RunDeps, history: list[ModelMessage]) -> str:
    delays = [0.5, 1.0, 2.0]
    last_exc: Exception | None = None
    for attempt, delay in enumerate(delays + [None], start=1):
        try:
            result = await agent.run(prompt, deps=deps, message_history=history)
            return result.output
        except Exception as e:
            last_exc = e
            log.warning("agent attempt %d failed: %s", attempt, e)
            if delay is not None:
                await asyncio.sleep(delay)
    log.exception("agent gave up after retries", exc_info=last_exc)
    return CANNED_FAIL


async def answer(session: Session, patient: Patient, user_text: str) -> str:
    session.add(Message(patient_id=patient.id, role=MessageRole.user, content=user_text))
    session.commit()

    history = _load_history(session, patient.id)
    deps = RunDeps(session=session, patient=patient)
    reply = await _run_with_retry(user_text, deps, history)

    session.add(Message(patient_id=patient.id, role=MessageRole.assistant, content=reply))
    session.commit()
    return reply
```

### 6. Admin chat route

`src/medixio/api/admin.py` (extend):

```python
from pydantic import BaseModel

from medixio.agent import answer as agent_answer


class ChatIn(BaseModel):
    jid: str
    text: str


class ChatOut(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn, session: Session = Depends(get_session)) -> ChatOut:
    patient = session.exec(select(Patient).where(Patient.whatsapp_jid == body.jid)).first()
    if patient is None:
        patient = Patient(whatsapp_jid=body.jid, phone_number=body.jid.split("@")[0])
        session.add(patient)
        session.commit()
        session.refresh(patient)
    reply = await agent_answer(session, patient, body.text)
    return ChatOut(reply=reply)
```

### 7. Try it

```bash
export GOOGLE_API_KEY=...
uv run medixio
curl -sS -X POST http://localhost:8000/admin/chat \
  -H 'content-type: application/json' \
  -d '{"jid":"573001112233@s.whatsapp.net","text":"Hola, ¿quién eres?"}'
# {"reply":"¡Hola! Soy Medixio…"}

curl -sS -X POST http://localhost:8000/admin/chat \
  -H 'content-type: application/json' \
  -d '{"jid":"573001112233@s.whatsapp.net","text":"Agrega una cita con la Dra. Ramírez de cardiología el viernes 17 de mayo a las 10 AM"}'
# Watch logs — should see a create_appointment tool call.
docker compose exec db psql -U medixio medixio -c 'select doctor_name, date from appointment;'
```

### 8. Add a test (mocked Gemini)

`tests/test_agent.py`:

```python
from pydantic_ai.models.test import TestModel

from medixio.agent.agent import agent


def test_agent_runs_with_test_model():
    with agent.override(model=TestModel()):
        # TestModel auto-calls the first tool it sees with placeholder args
        ...
```

`TestModel` is PydanticAI's built-in deterministic stub — perfect for unit tests so CI doesn't burn quota.

### 9. Commit

```bash
git add pyproject.toml uv.lock src tests
git commit -m "agent: pydantic-ai + gemini with tool-driven appointment/notification ops"
```

## Files touched in this step

| Path | Purpose |
|---|---|
| `pyproject.toml` / `uv.lock` | + pydantic-ai[gemini] |
| `src/medixio/config.py` | + `google_api_key`, `gemini_model` |
| `src/medixio/services/*.py` | thin service-layer functions |
| `src/medixio/agent/agent.py` | Agent, system prompt, tools |
| `src/medixio/agent/runner.py` | history load + retry envelope |
| `src/medixio/api/admin.py` | `POST /admin/chat` |
| `tests/test_agent.py` | TestModel-driven test |

## Verification

- [ ] `POST /admin/chat` with a greeting returns Spanish text.
- [ ] A "schedule X with Dr Y" message produces an `appointment` row.
- [ ] Subsequent turns recall the previous context (the bot says "as I mentioned…").
- [ ] Killing your network mid-call → eventually returns the canned reply, doesn't 500.
- [ ] `pytest -q` passes; CI doesn't hit Gemini.

## Common gotchas

- **`google-gla` returns 401.** `GOOGLE_API_KEY` not set or wrong. PydanticAI reads the env var unless you pass a provider explicitly.
- **Tool not invoked.** The LLM thinks the question is conversational. Sharpen the tool docstring or the system prompt ("para crear/editar/eliminar usa siempre las herramientas").
- **Datetime arrives without timezone.** Your tool got a naive `datetime`. Coerce to UTC in the tool: `date = date if date.tzinfo else date.replace(tzinfo=timezone.utc)`.
- **History order is wrong.** You forgot to reverse after `ORDER BY created_at DESC LIMIT 20`.
- **Token blowup.** History accumulates across turns. The N=20 limit + concise system prompt keeps each call under 1 K input tokens.
- **Free-tier rate limit.** Gemini Flash free tier rate-limits per minute. Spreading test calls across seconds avoids 429s.
