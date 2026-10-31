from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, col, select

from medixio.knowledge import resolve
from medixio.modules.appointments.models import Appointment, AppointmentStatus
from medixio.modules.reminders import service as reminders
from medixio.shared.time import fmt_local, utcnow


SUBJECT = "appointment"


def _label(appt: Appointment) -> str:
    who = f" con {appt.doctor_name}" if appt.doctor_name else ""
    return f"tu cita de {appt.specialty}{who}"


def _schedule_reminders(session: Session, appt: Appointment) -> None:
    reminders.cancel_for_subject(session, SUBJECT, appt.id)
    if appt.status != AppointmentStatus.SCHEDULED or appt.starts_at is None:
        return
    offsets = resolve(session, appt.patient_id, "appointment.remind_offsets_minutes")
    now = utcnow()
    where = f" en {appt.location}" if appt.location else ""
    for minutes in offsets or []:
        fire_at = appt.starts_at + timedelta(minutes=int(minutes))
        if fire_at <= now:
            continue
        if minutes < 0:
            message = f"📅 Recuerda {_label(appt)}: {fmt_local(appt.starts_at)}{where}."
        else:
            message = (
                f"⭐ ¿Cómo te fue en {_label(appt)}? "
                "Cuéntame si asististe y si te dieron órdenes o fórmulas nuevas."
            )
        reminders.create(
            session,
            patient_id=appt.patient_id,
            kind="appointment",
            fire_at=fire_at,
            message=message,
            subject_type=SUBJECT,
            subject_id=appt.id,
        )


def create(
    session: Session,
    patient_id: str,
    *,
    specialty: str,
    starts_at: datetime | None = None,
    doctor_name: str | None = None,
    location: str | None = None,
    notes: str | None = None,
    extracted_from_image: bool = False,
) -> Appointment:
    appt = Appointment(
        patient_id=patient_id,
        specialty=specialty,
        starts_at=starts_at,
        doctor_name=doctor_name,
        location=location,
        notes=notes,
        extracted_from_image=extracted_from_image,
        status=AppointmentStatus.SCHEDULED if starts_at else AppointmentStatus.DRAFT,
    )
    session.add(appt)
    _schedule_reminders(session, appt)
    return appt


def get(session: Session, patient_id: str, appointment_id: str) -> Appointment:
    appt = session.get(Appointment, appointment_id)
    if appt is None or appt.patient_id != patient_id:
        raise LookupError("Cita no encontrada")
    return appt


def update(
    session: Session, patient_id: str, appointment_id: str, **fields: Any
) -> Appointment:
    appt = get(session, patient_id, appointment_id)
    for key in ("specialty", "starts_at", "doctor_name", "location", "notes"):
        if fields.get(key) is not None:
            setattr(appt, key, fields[key])
    if appt.starts_at and appt.status == AppointmentStatus.DRAFT:
        appt.status = AppointmentStatus.SCHEDULED
    appt.updated_at = utcnow()
    session.add(appt)
    _schedule_reminders(session, appt)
    return appt


def set_status(
    session: Session, patient_id: str, appointment_id: str, status: AppointmentStatus
) -> Appointment:
    appt = get(session, patient_id, appointment_id)
    appt.status = status
    appt.updated_at = utcnow()
    session.add(appt)
    if status == AppointmentStatus.SCHEDULED:
        _schedule_reminders(session, appt)
    else:
        reminders.cancel_for_subject(session, SUBJECT, appt.id, future_only=True)
    return appt


def list_for(
    session: Session, patient_id: str, *, upcoming: bool = True
) -> list[Appointment]:
    query = select(Appointment).where(Appointment.patient_id == patient_id)
    if upcoming:
        query = query.where(
            col(Appointment.status).in_(
                [AppointmentStatus.DRAFT, AppointmentStatus.SCHEDULED]
            )
        )
    return list(session.exec(query.order_by(col(Appointment.starts_at))).all())
