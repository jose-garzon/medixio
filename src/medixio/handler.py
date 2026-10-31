"""Inbound message -> consent gate -> agent -> reply (design §1, §6)."""

import asyncio
import logging

from pydantic_ai.exceptions import (
    ModelConnectionError,
    ModelOverloadedError,
    ModelRateLimitError,
    ModelServerError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from sqlmodel import Session, select

from medixio import ratelimit
from medixio.agent.agent import agent
from medixio.agent.deps import RunDeps
from medixio.agent.model import get_model
from medixio.channel.base import Inbound
from medixio.config import get_settings
from medixio.db import engine
from medixio.extraction import DocumentExtraction, extract
from medixio.modules.conversations import service as conversations
from medixio.modules.conversations.models import Message, Role
from medixio.modules.patients import service as patients
from medixio.modules.patients.models import Patient
from medixio.observability import obs
from medixio.shared.time import utcnow


log = logging.getLogger(__name__)

TRANSIENT = (
    ModelConnectionError,
    ModelOverloadedError,
    ModelRateLimitError,
    ModelServerError,
    ModelTimeoutError,
    ModelUnavailableError,
)

CONSENT_TEXT = (
    "¡Hola! Soy *Medixio* 👋, te ayudo a recordar citas, fórmulas, autorizaciones, "
    "entregas de medicamentos y trámites con tu EPS.\n\n"
    "Para ayudarte necesito guardar datos de salud tuyos (datos sensibles, Ley 1581 "
    "de 2012). Se guardan en un servidor privado y se procesan con un modelo de IA "
    "(Anthropic). Las fotos que envíes se leen y se descartan, no se guardan. "
    "Puedes pedir ver o borrar tus datos cuando quieras.\n\n"
    "No doy consejo médico ni legal.\n\n"
    "Si estás de acuerdo responde *ACEPTO*."
)
CONSENT_OK = "¡Gracias! 🙌 ¿Cómo te llamas?"
ERROR_TEXT = (
    "Uy, tuve un problema para procesar tu mensaje 😕. Inténtalo de nuevo en unos "
    "minutos."
)
DELETED_TEXT = (
    "Listo, borré todos tus datos. Si vuelves a escribir empezamos de cero. 👋"
)

_locks: dict[str, asyncio.Lock] = {}


def _history(messages: list[Message]) -> list[ModelMessage]:
    result: list[ModelMessage] = []
    for m in messages:
        if m.role == Role.USER:
            result.append(ModelRequest(parts=[UserPromptPart(content=m.content)]))
        else:
            result.append(ModelResponse(parts=[TextPart(content=m.content)]))
    return result


def _describe_extraction(x: DocumentExtraction) -> str:
    data = x.model_dump(exclude_none=True, exclude_defaults=True, mode="json")
    return (
        f"[imagen recibida: {x.kind}, confianza {x.confidence}] Datos extraídos: {data}"
    )


async def _run_agent(prompt: str, deps: RunDeps, history: list[ModelMessage]) -> str:
    delays = [0.5, 1.0, 2.0]
    for attempt in range(len(delays) + 1):
        try:
            with obs().timer("agent.run", attempt=attempt + 1) as labels:
                result = await agent.run(
                    prompt, deps=deps, message_history=history, model=get_model()
                )
                usage = result.usage
                tools = [
                    p.tool_name
                    for m in result.new_messages()
                    for p in m.parts
                    if isinstance(p, ToolCallPart)
                ]
                labels["tools"] = tools
            obs().metric("agent.tokens_in", usage.input_tokens or 0)
            obs().metric("agent.tokens_out", usage.output_tokens or 0)
            return result.output
        except TRANSIENT:
            deps.session.rollback()
            if attempt == len(delays):
                raise
            log.warning("agent attempt %d failed, retrying", attempt + 1, exc_info=True)
            await asyncio.sleep(delays[attempt])
    raise AssertionError("unreachable")


async def handle(inbound: Inbound) -> str | None:
    decision = ratelimit.check_message(inbound.jid, has_image=inbound.image is not None)
    if not decision.allowed:
        inbound.image = None
        return decision.notice
    inbound.text = ratelimit.truncate(inbound.text)
    lock = _locks.setdefault(inbound.jid, asyncio.Lock())
    async with lock:
        with (
            obs().timer("message.handle", image=inbound.image is not None),
            Session(engine) as session,
        ):
            return await _handle(session, inbound)


async def _handle(session: Session, inbound: Inbound) -> str | None:
    known = session.exec(
        select(Patient).where(Patient.whatsapp_jid == inbound.jid)
    ).first()
    if known is None and not ratelimit.check_signup():
        return None
    patient, created = patients.get_or_create(session, inbound.jid)
    if patient.consent_accepted_at is None:
        if not created and inbound.text.strip().upper().startswith("ACEPTO"):
            patients.accept_consent(session, patient)
            conversations.add(session, patient.id, Role.ASSISTANT, CONSENT_OK)
            session.commit()
            return CONSENT_OK
        return CONSENT_TEXT

    prompt = inbound.text
    has_image = inbound.image is not None
    if inbound.image is not None:
        try:
            with obs().timer("extraction.run") as labels:
                extraction = await extract(
                    inbound.image,
                    inbound.image_media_type or "image/jpeg",
                    inbound.text,
                )
                labels["kind"] = extraction.kind
                labels["confidence"] = extraction.confidence
        except Exception:
            log.exception("image extraction failed")
            return "No pude leer la imagen 😕. ¿Me la envías otra vez, más nítida?"
        finally:
            inbound.image = None
        prompt = f"{_describe_extraction(extraction)}\n{inbound.text}".strip()

    history = _history(
        conversations.last(session, patient.id, get_settings().history_size)
    )
    deps = RunDeps(session=session, patient=patient, now=utcnow())
    try:
        reply = await _run_agent(prompt, deps, history)
    except Exception:
        log.exception("agent failed patient=%s", patient.id)
        return ERROR_TEXT

    if deps.delete_requested:
        patients.delete_all(session, patient)
        log.info("patient data deleted id=%s", patient.id)
        return DELETED_TEXT

    conversations.add(session, patient.id, Role.USER, prompt, has_image=has_image)
    conversations.add(session, patient.id, Role.ASSISTANT, reply)
    session.commit()
    return reply
