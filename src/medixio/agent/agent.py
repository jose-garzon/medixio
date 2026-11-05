from datetime import date, datetime
from typing import Any, Literal

from pydantic_ai import Agent, ModelRetry, RunContext

from medixio import knowledge
from medixio.agent.context import snapshot
from medixio.agent.deps import RunDeps
from medixio.modules.appointments import service as appointments
from medixio.modules.appointments.models import AppointmentStatus
from medixio.modules.authorizations import service as authorizations
from medixio.modules.authorizations.models import AuthorizationStatus
from medixio.modules.claims import service as claims
from medixio.modules.claims.models import ClaimKind, ClaimStatus
from medixio.modules.dispensing import service as dispensing
from medixio.modules.dispensing.models import DispenseStatus
from medixio.modules.orders import service as orders
from medixio.modules.orders.models import OrderStatus
from medixio.modules.orders.service import ItemIn
from medixio.modules.patients import service as patients
from medixio.modules.reminders import service as reminders
from medixio.shared.time import fmt_local, from_local, to_local


DELETE_PHRASE = "BORRAR MIS DATOS"

INSTRUCTIONS = f"""\
Eres Medixio, un asistente por WhatsApp que ayuda a pacientes en Colombia con
enfermedades crónicas a no perderse en los trámites de salud: citas, fórmulas
médicas, autorizaciones de la EPS, entregas en farmacia, pendientes, PQRS y tutelas.

Reglas:
- Responde siempre en español colombiano, corto, cálido y claro. Formato WhatsApp
  (usa *negrilla* con asteriscos, sin Markdown de títulos).
- Nunca des consejo médico: no diagnostiques, no recomiendes ni cambies dosis, no
  interpretes síntomas ni exámenes. Remite al médico.
- La ayuda con PQRS/tutela es informativa, no asesoría legal. Usa la herramienta
  get_guide; si la guía no está revisada, dilo y sugiere confirmar con la EPS o la
  Personería/Defensoría.
- Pregunta UNA sola cosa a la vez cuando falte información.
- ANTES de guardar cualquier dato extraído de una imagen o deducido por ti, léeselo
  al usuario y pide confirmación ("¿Está bien así?"). Solo llama la herramienta
  después de un "sí" explícito.
- Nunca marques una entrega de farmacia como reclamada sin que el usuario lo
  confirme explícitamente (completo, incompleto/pendiente, o todavía no).
- Las fechas y horas que recibes y envías a las herramientas son hora local de
  Colombia (America/Bogota), formato ISO.
- Si el perfil está incompleto (nombre o EPS en '?'), pídelo de forma natural, una
  cosa a la vez, sin interrumpir lo que el usuario necesita.
- Para borrar todos sus datos, el usuario debe escribir exactamente "{DELETE_PHRASE}".
- Usa los id del contexto al llamar herramientas; nunca muestres ids al usuario.
"""

agent = Agent(deps_type=RunDeps, instructions=INSTRUCTIONS, retries=2)


@agent.instructions
def _context(ctx: RunContext[RunDeps]) -> str:
    now = to_local(ctx.deps.now)
    return f"Ahora: {now:%A %Y-%m-%d %H:%M} (hora Colombia).\n\n" + snapshot(
        ctx.deps.session, ctx.deps.patient
    )


def _done(ctx: RunContext[RunDeps], text: str) -> str:
    ctx.deps.session.commit()
    return text


def _guard(fn: Any) -> Any:
    """Serialize parallel tool calls on the shared session; errors become retries."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with args[0].deps.lock:
            try:
                return fn(*args, **kwargs)
            except (LookupError, ValueError) as exc:
                args[0].deps.session.rollback()
                raise ModelRetry(str(exc)) from exc

    return wrapper


# --- profile --------------------------------------------------------------


@agent.tool
@_guard
def update_profile(
    ctx: RunContext[RunDeps],
    name: str | None = None,
    eps: str | None = None,
    regimen: Literal["contributivo", "subsidiado", "especial"] | None = None,
    city: str | None = None,
    default_pharmacy: str | None = None,
    reminder_hour: int | None = None,
    delivery_mode: Literal["pickup", "home"] | None = None,
    birth_year: int | None = None,
) -> str:
    """Guarda datos del perfil del paciente. Solo los campos dados cambian."""
    patients.update_profile(
        ctx.deps.session,
        ctx.deps.patient,
        name=name,
        eps=eps,
        regimen=regimen,
        city=city,
        default_pharmacy=default_pharmacy,
        reminder_hour=reminder_hour,
        delivery_mode=delivery_mode,
        birth_year=birth_year,
    )
    return _done(ctx, "Perfil actualizado.")


@agent.tool
@_guard
def set_preference(
    ctx: RunContext[RunDeps], key: str, value: Any, note: str | None = None
) -> str:
    """Guarda una excepción del paciente a una regla compartida.

    Claves conocidas: order.renewal_lead_days (días antes del vencimiento de la
    fórmula para avisar), order.dispense_every_months, authorization.expiry_lead_days,
    dispensing.confirm_hour, appointment.remind_offsets_minutes (lista de minutos).
    """
    if key not in knowledge.rules():
        raise ValueError(f"Clave desconocida: {key}")
    patients.set_preference(ctx.deps.session, ctx.deps.patient.id, key, value, note)
    return _done(ctx, f"Preferencia {key} guardada.")


# --- appointments ---------------------------------------------------------


@agent.tool
@_guard
def create_appointment(
    ctx: RunContext[RunDeps],
    specialty: str,
    starts_at_local: datetime | None = None,
    doctor_name: str | None = None,
    location: str | None = None,
    notes: str | None = None,
    extracted_from_image: bool = False,
) -> str:
    """Crea una cita médica. Sin fecha queda como borrador."""
    appt = appointments.create(
        ctx.deps.session,
        ctx.deps.patient.id,
        specialty=specialty,
        starts_at=from_local(starts_at_local) if starts_at_local else None,
        doctor_name=doctor_name,
        location=location,
        notes=notes,
        extracted_from_image=extracted_from_image,
    )
    return _done(ctx, f"Cita creada id={appt.id} estado={appt.status}.")


@agent.tool
@_guard
def update_appointment(
    ctx: RunContext[RunDeps],
    appointment_id: str,
    starts_at_local: datetime | None = None,
    specialty: str | None = None,
    doctor_name: str | None = None,
    location: str | None = None,
    notes: str | None = None,
) -> str:
    """Cambia datos de una cita (p. ej. reprogramar). Recalcula recordatorios."""
    appointments.update(
        ctx.deps.session,
        ctx.deps.patient.id,
        appointment_id,
        starts_at=from_local(starts_at_local) if starts_at_local else None,
        specialty=specialty,
        doctor_name=doctor_name,
        location=location,
        notes=notes,
    )
    return _done(ctx, "Cita actualizada.")


@agent.tool
@_guard
def set_appointment_status(
    ctx: RunContext[RunDeps], appointment_id: str, status: AppointmentStatus
) -> str:
    """Marca una cita como done (asistió), missed (no asistió) o cancelled."""
    appointments.set_status(
        ctx.deps.session, ctx.deps.patient.id, appointment_id, status
    )
    return _done(ctx, f"Cita marcada {status}.")


@agent.tool
@_guard
def list_past_appointments(ctx: RunContext[RunDeps]) -> str:
    """Historial de citas, incluidas las pasadas."""
    items = appointments.list_for(ctx.deps.session, ctx.deps.patient.id, upcoming=False)
    return (
        "\n".join(
            f"{a.specialty} {a.doctor_name or ''} "
            f"{fmt_local(a.starts_at) if a.starts_at else 'sin fecha'} [{a.status}]"
            for a in items
        )
        or "Sin citas."
    )


# --- orders & dispensing --------------------------------------------------


@agent.tool
@_guard
def create_order(
    ctx: RunContext[RunDeps],
    issued_on: date,
    duration_months: int,
    items: list[ItemIn],
    doctor_name: str | None = None,
    expires_on: date | None = None,
    extracted_from_image: bool = False,
    renews_order_id: str | None = None,
) -> str:
    """Registra una fórmula/orden médica confirmada por el usuario.

    Programa el aviso de renovación antes del vencimiento y las entregas mensuales.
    Si reemplaza una fórmula anterior, pasa renews_order_id.
    """
    if duration_months < 1:
        raise ValueError("duration_months debe ser >= 1")
    order = orders.create(
        ctx.deps.session,
        ctx.deps.patient.id,
        issued_on=issued_on,
        duration_months=duration_months,
        items=items,
        doctor_name=doctor_name,
        expires_on=expires_on,
        extracted_from_image=extracted_from_image,
    )
    if renews_order_id:
        orders.set_status(
            ctx.deps.session,
            ctx.deps.patient.id,
            renews_order_id,
            OrderStatus.RENEWED,
            renewed_by_order_id=order.id,
        )
    return _done(ctx, f"Fórmula creada id={order.id}, vence {order.expires_on}.")


@agent.tool
@_guard
def set_order_status(
    ctx: RunContext[RunDeps], order_id: str, status: OrderStatus
) -> str:
    """renewal_requested (ya pidió renovación), renewed, expired."""
    orders.set_status(ctx.deps.session, ctx.deps.patient.id, order_id, status)
    return _done(ctx, f"Fórmula marcada {status}.")


@agent.tool
@_guard
def record_dispense(
    ctx: RunContext[RunDeps],
    dispense_id: str,
    outcome: Literal["dispensed", "partial", "not_yet"],
    pending_medicines: str | None = None,
    pharmacy: str | None = None,
) -> str:
    """Registra la respuesta EXPLÍCITA del usuario sobre una entrega de farmacia.

    dispensed = recibió todo; partial = quedó pendiente (indica pending_medicines);
    not_yet = aún no ha ido.
    """
    if outcome == "not_yet":
        return "Sin cambios; se le volverá a preguntar."
    if outcome == "partial" and not pending_medicines:
        raise ValueError("Indica qué medicamentos quedaron pendientes")
    status = (
        DispenseStatus.DISPENSED if outcome == "dispensed" else DispenseStatus.PARTIAL
    )
    dispensing.record(
        ctx.deps.session,
        ctx.deps.patient.id,
        dispense_id,
        status,
        pending_note=pending_medicines,
        pharmacy=pharmacy,
        claimed_at=ctx.deps.now,
    )
    return _done(ctx, f"Entrega registrada: {status}.")


@agent.tool
@_guard
def resolve_pending(ctx: RunContext[RunDeps], dispense_id: str) -> str:
    """El usuario confirma que ya le entregaron el pendiente."""
    dispensing.resolve_pending(ctx.deps.session, ctx.deps.patient.id, dispense_id)
    return _done(ctx, "Pendiente resuelto.")


# --- authorizations -------------------------------------------------------


@agent.tool
@_guard
def create_authorization(
    ctx: RunContext[RunDeps],
    service_description: str,
    valid_until: date | None = None,
    number: str | None = None,
    eps: str | None = None,
    issued_on: date | None = None,
    provider: str | None = None,
    order_id: str | None = None,
    extracted_from_image: bool = False,
) -> str:
    """Registra una autorización de la EPS confirmada por el usuario."""
    auth = authorizations.create(
        ctx.deps.session,
        ctx.deps.patient.id,
        service_description=service_description,
        valid_until=valid_until,
        number=number,
        eps=eps,
        issued_on=issued_on,
        provider=provider,
        order_id=order_id,
        extracted_from_image=extracted_from_image,
    )
    return _done(ctx, f"Autorización creada id={auth.id}.")


@agent.tool
@_guard
def set_authorization_status(
    ctx: RunContext[RunDeps], authorization_id: str, status: AuthorizationStatus
) -> str:
    """used (ya la usó), expired, denied (la EPS la negó)."""
    authorizations.set_status(
        ctx.deps.session, ctx.deps.patient.id, authorization_id, status
    )
    return _done(ctx, f"Autorización marcada {status}.")


# --- claims ---------------------------------------------------------------


@agent.tool_plain
def get_guide(topic: Literal["pqrs", "tutela", "pendientes", "autorizaciones"]) -> str:
    """Guía revisada sobre un trámite. Úsala antes de explicar PQRS, tutela, etc."""
    guide = knowledge.guides().get(topic)
    if guide is None or guide.reviewed_on is None:
        return (
            "GUÍA NO REVISADA por el administrador. No des plazos ni pasos concretos; "
            "di que la información aún no está verificada y sugiere confirmar con la "
            "EPS, la Supersalud (línea 01 8000 513 700) o la Personería."
        )
    return guide.body


@agent.tool
@_guard
def open_claim(
    ctx: RunContext[RunDeps],
    kind: ClaimKind,
    subject: str,
    filed_on: date | None = None,
    radicado: str | None = None,
    response_due_on: date | None = None,
) -> str:
    """Registra un caso PQRS/tutela. Si ya se radicó, pasa filed_on."""
    claim = claims.open_claim(
        ctx.deps.session,
        ctx.deps.patient.id,
        kind=kind,
        subject=subject,
        filed_on=filed_on,
        radicado=radicado,
        response_due_on=response_due_on,
    )
    due = claim.response_due_on or "sin plazo verificado (pregúntale al usuario)"
    return _done(ctx, f"Caso creado id={claim.id}, respuesta hasta: {due}.")


@agent.tool
@_guard
def update_claim(
    ctx: RunContext[RunDeps],
    claim_id: str,
    status: ClaimStatus | None = None,
    filed_on: date | None = None,
    radicado: str | None = None,
    response_due_on: date | None = None,
) -> str:
    """Actualiza un caso PQRS/tutela."""
    claims.update(
        ctx.deps.session,
        ctx.deps.patient.id,
        claim_id,
        status=status,
        filed_on=filed_on,
        radicado=radicado,
        response_due_on=response_due_on,
    )
    return _done(ctx, "Caso actualizado.")


# --- free-form reminders --------------------------------------------------


@agent.tool
@_guard
def create_reminder(
    ctx: RunContext[RunDeps],
    message: str,
    fire_at_local: datetime,
    rrule: str | None = None,
) -> str:
    """Recordatorio libre. Para repetir usa un RRULE iCal, p. ej. FREQ=DAILY o
    FREQ=MONTHLY;BYMONTHDAY=1. fire_at_local es la primera vez (hora Colombia)."""
    reminder = reminders.create(
        ctx.deps.session,
        patient_id=ctx.deps.patient.id,
        kind="custom",
        fire_at=from_local(fire_at_local),
        message=f"⏰ {message}",
        rrule=rrule,
    )
    return _done(ctx, f"Recordatorio creado id={reminder.id}.")


@agent.tool
@_guard
def cancel_reminder(ctx: RunContext[RunDeps], reminder_id: str) -> str:
    """Cancela un recordatorio personal."""
    if not reminders.cancel(ctx.deps.session, ctx.deps.patient.id, reminder_id):
        raise LookupError("Recordatorio no encontrado")
    return _done(ctx, "Recordatorio cancelado.")


@agent.tool
@_guard
def list_upcoming_reminders(ctx: RunContext[RunDeps]) -> str:
    """Todos los avisos programados (citas, fórmulas, entregas, personales)."""
    rows = []
    for r in reminders.list_active(ctx.deps.session, ctx.deps.patient.id):
        nxt = reminders.next_fire(r)
        if nxt is not None:
            rows.append((nxt, r.message))
    rows.sort()
    return "\n".join(f"{fmt_local(t)}: {m}" for t, m in rows[:30]) or "Nada programado."


# --- privacy --------------------------------------------------------------


@agent.tool
@_guard
def request_data_deletion(ctx: RunContext[RunDeps], confirmation_phrase: str) -> str:
    """Borra TODOS los datos del paciente. Solo si escribió la frase exacta."""
    if confirmation_phrase.strip().upper() != DELETE_PHRASE:
        return f'No borrado. El usuario debe escribir exactamente "{DELETE_PHRASE}".'
    ctx.deps.delete_requested = True
    return "Borrado programado al terminar este mensaje. Despídete brevemente."
