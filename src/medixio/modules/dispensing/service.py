from datetime import date, datetime, time, timedelta

from sqlmodel import Session, col, select

from medixio.knowledge import resolve
from medixio.modules.dispensing.models import Dispense, DispenseStatus
from medixio.modules.orders.models import MedicalOrder, OrderItem
from medixio.modules.patients.service import get_profile, reminder_hour
from medixio.modules.reminders import service as reminders
from medixio.shared.time import add_months, local_at, today_local, utcnow


SUBJECT = "dispense"


def _medicines(session: Session, order_id: str) -> str:
    items = session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
    return ", ".join(i.medicine_name for i in items) or "tus medicamentos"


def plan_cycles(session: Session, order: MedicalOrder) -> list[Dispense]:
    every = int(resolve(session, order.patient_id, "order.dispense_every_months") or 1)
    hour = reminder_hour(session, order.patient_id)
    confirm_hour = int(
        resolve(session, order.patient_id, "dispensing.confirm_hour") or 19
    )
    retries = int(resolve(session, order.patient_id, "dispensing.confirm_retries") or 3)
    pharmacy = get_profile(session, order.patient_id).default_pharmacy
    meds = _medicines(session, order.id)
    where = f" en {pharmacy}" if pharmacy else ""
    today = today_local()
    cycles = []
    for cycle in range(0, order.duration_months, every):
        due_on = add_months(order.issued_on, cycle)
        if due_on >= order.expires_on:
            break
        d = Dispense(
            patient_id=order.patient_id,
            order_id=order.id,
            cycle=cycle // every + 1,
            due_on=due_on,
            pharmacy=pharmacy,
        )
        session.add(d)
        cycles.append(d)
        if due_on < today:
            continue
        reminders.create(
            session,
            patient_id=order.patient_id,
            kind="dispense",
            fire_at=local_at(due_on, time(hour)),
            message=f"💊 Hoy te toca reclamar {meds}{where}.",
            subject_type=SUBJECT,
            subject_id=d.id,
        )
        reminders.create(
            session,
            patient_id=order.patient_id,
            kind="dispense_confirm",
            fire_at=local_at(due_on, time(confirm_hour)),
            rrule=f"FREQ=DAILY;COUNT={retries}",
            message=(
                f"¿Ya reclamaste {meds}? Respóndeme: completo, incompleto "
                "(queda pendiente) o todavía no."
            ),
            subject_type=SUBJECT,
            subject_id=d.id,
        )
    return cycles


def _get(session: Session, patient_id: str, dispense_id: str) -> Dispense:
    d = session.get(Dispense, dispense_id)
    if d is None or d.patient_id != patient_id:
        raise LookupError("Entrega no encontrada")
    return d


def list_open(session: Session, patient_id: str) -> list[Dispense]:
    """Cycles that are due or overdue and not confirmed by the patient."""
    today = today_local()
    query = select(Dispense).where(
        Dispense.patient_id == patient_id,
        col(Dispense.status).in_(
            [
                DispenseStatus.DUE,
                DispenseStatus.AWAITING_CONFIRMATION,
                DispenseStatus.PARTIAL,
                DispenseStatus.PENDING,
            ]
        ),
        Dispense.due_on <= today + timedelta(days=3),
    )
    return list(session.exec(query.order_by(col(Dispense.due_on))).all())


def mark_awaiting(session: Session, dispense_id: str) -> None:
    d = session.get(Dispense, dispense_id)
    if d is not None and d.status == DispenseStatus.DUE:
        d.status = DispenseStatus.AWAITING_CONFIRMATION
        session.add(d)


def record(
    session: Session,
    patient_id: str,
    dispense_id: str,
    status: DispenseStatus,
    *,
    on: date | None = None,
    pending_note: str | None = None,
    pharmacy: str | None = None,
    claimed_at: datetime | None = None,
) -> Dispense:
    """Record the patient's answer. Only called after explicit confirmation."""
    d = _get(session, patient_id, dispense_id)
    d.status = status
    d.dispensed_on = on or today_local()
    if pharmacy:
        d.pharmacy = pharmacy
    if pending_note:
        d.pending_note = pending_note
    d.updated_at = utcnow()
    session.add(d)
    reminders.cancel_for_subject(session, SUBJECT, d.id, kinds=["dispense_confirm"])
    reminders.cancel_for_subject(session, SUBJECT, d.id, kinds=["pending_followup"])
    if status in (DispenseStatus.PARTIAL, DispenseStatus.PENDING) and pending_note:
        _schedule_pending_followup(session, d, claimed_at or utcnow())
    return d


def _schedule_pending_followup(
    session: Session, d: Dispense, claimed_at: datetime
) -> None:
    profile = get_profile(session, d.patient_id)
    over_62 = (
        profile.birth_year is not None and today_local().year - profile.birth_year > 62
    )
    key = (
        "dispensing.pending_delivery_hours_over_62"
        if over_62
        else "dispensing.pending_delivery_hours"
    )
    legal_hours = resolve(session, d.patient_id, key)
    hours = legal_hours or resolve(
        session, d.patient_id, "dispensing.pending_followup_fallback_hours"
    )
    legal = (
        f" La EPS debe entregarlo en máximo {legal_hours} horas." if legal_hours else ""
    )
    reminders.create(
        session,
        patient_id=d.patient_id,
        kind="pending_followup",
        fire_at=claimed_at + timedelta(hours=int(hours or 48)),
        rrule="FREQ=DAILY;INTERVAL=2;COUNT=5",
        message=(
            f"📦 ¿Ya te entregaron el pendiente ({d.pending_note})?{legal} "
            "Si no, te puedo explicar cómo poner una PQRS."
        ),
        subject_type=SUBJECT,
        subject_id=d.id,
    )


def resolve_pending(session: Session, patient_id: str, dispense_id: str) -> Dispense:
    d = _get(session, patient_id, dispense_id)
    d.status = DispenseStatus.DISPENSED
    d.updated_at = utcnow()
    session.add(d)
    reminders.cancel_for_subject(session, SUBJECT, d.id)
    return d


def cancel_future(session: Session, order_id: str) -> None:
    today = today_local()
    for d in session.exec(select(Dispense).where(Dispense.order_id == order_id)).all():
        if d.due_on > today and d.status == DispenseStatus.DUE:
            reminders.cancel_for_subject(session, SUBJECT, d.id)
