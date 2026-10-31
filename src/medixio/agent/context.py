"""Compact snapshot of the patient's records, injected into the agent instructions."""

from sqlmodel import Session

from medixio.modules.appointments import service as appointments
from medixio.modules.authorizations import service as authorizations
from medixio.modules.claims import service as claims
from medixio.modules.dispensing import service as dispensing
from medixio.modules.orders import service as orders
from medixio.modules.patients.models import Patient
from medixio.modules.patients.service import get_profile
from medixio.modules.reminders import service as reminders
from medixio.shared.time import fmt_local


def snapshot(session: Session, patient: Patient) -> str:
    p = get_profile(session, patient.id)
    lines = [
        "## Perfil",
        f"nombre={patient.name or '?'} eps={p.eps or '?'} regimen={p.regimen or '?'} "
        f"ciudad={p.city or '?'} farmacia={p.default_pharmacy or '?'} "
        f"entrega={p.delivery_mode or '?'} hora_recordatorios={p.reminder_hour or 8} "
        f"año_nacimiento={p.birth_year or '?'}",
    ]
    appts = appointments.list_for(session, patient.id)
    if appts:
        lines.append("## Citas próximas")
        for a in appts:
            when = fmt_local(a.starts_at) if a.starts_at else "sin fecha"
            lines.append(
                f"- id={a.id} {a.specialty} {a.doctor_name or ''} {when} [{a.status}]"
            )
    active = orders.list_active(session, patient.id)
    if active:
        lines.append("## Fórmulas vigentes")
        for o in active:
            meds = "; ".join(
                f"{i.medicine_name} {i.dose_text or ''}".strip()
                for i in orders.items_of(session, o.id)
            )
            lines.append(f"- id={o.id} vence={o.expires_on} [{o.status}] {meds}")
    cycles = dispensing.list_open(session, patient.id)
    if cycles:
        lines.append("## Entregas de farmacia sin confirmar / pendientes")
        for d in cycles:
            note = f" pendiente: {d.pending_note}" if d.pending_note else ""
            lines.append(
                f"- id={d.id} fórmula={d.order_id} entrega#{d.cycle} "
                f"fecha={d.due_on} [{d.status}]{note}"
            )
    auths = authorizations.list_active(session, patient.id)
    if auths:
        lines.append("## Autorizaciones activas")
        for au in auths:
            lines.append(
                f"- id={au.id} {au.service_description} n°{au.number or '?'} "
                f"vence={au.valid_until or '?'}"
            )
    open_claims = claims.list_open(session, patient.id)
    if open_claims:
        lines.append("## Casos PQRS/tutela")
        for c in open_claims:
            lines.append(
                f"- id={c.id} {c.kind} {c.subject} [{c.status}] "
                f"radicado={c.radicado or '?'} "
                f"respuesta_hasta={c.response_due_on or '?'}"
            )
    free = [r for r in reminders.list_active(session, patient.id) if r.kind == "custom"]
    if free:
        lines.append("## Recordatorios personales")
        for r in free:
            rule = f" rrule={r.rrule}" if r.rrule else ""
            lines.append(f"- id={r.id} {fmt_local(r.fire_at)}{rule}: {r.message}")
    return "\n".join(lines)
