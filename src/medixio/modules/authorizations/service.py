from datetime import date, time, timedelta

from sqlmodel import Session, select

from medixio.knowledge import resolve
from medixio.modules.authorizations.models import Authorization, AuthorizationStatus
from medixio.modules.patients.service import reminder_hour
from medixio.modules.reminders import service as reminders
from medixio.shared.time import local_at, today_local, utcnow


SUBJECT = "authorization"


def create(
    session: Session,
    patient_id: str,
    *,
    service_description: str,
    valid_until: date | None = None,
    number: str | None = None,
    eps: str | None = None,
    issued_on: date | None = None,
    provider: str | None = None,
    order_id: str | None = None,
    extracted_from_image: bool = False,
) -> Authorization:
    auth = Authorization(
        patient_id=patient_id,
        service_description=service_description,
        valid_until=valid_until,
        number=number,
        eps=eps,
        issued_on=issued_on,
        provider=provider,
        order_id=order_id,
        extracted_from_image=extracted_from_image,
    )
    session.add(auth)
    if valid_until is not None:
        lead = int(resolve(session, patient_id, "authorization.expiry_lead_days") or 7)
        remind_on = max(valid_until - timedelta(days=lead), today_local())
        where = f" en {provider}" if provider else ""
        reminders.create(
            session,
            patient_id=patient_id,
            kind="authorization_expiry",
            fire_at=local_at(remind_on, time(reminder_hour(session, patient_id))),
            message=(
                f"⏳ Tu autorización para {service_description} vence el "
                f"{valid_until:%d/%m/%Y}. Úsala{where} antes de esa fecha. "
                "¿Ya la usaste?"
            ),
            subject_type=SUBJECT,
            subject_id=auth.id,
        )
    return auth


def set_status(
    session: Session, patient_id: str, auth_id: str, status: AuthorizationStatus
) -> Authorization:
    auth = session.get(Authorization, auth_id)
    if auth is None or auth.patient_id != patient_id:
        raise LookupError("Autorización no encontrada")
    auth.status = status
    auth.updated_at = utcnow()
    session.add(auth)
    if status != AuthorizationStatus.ACTIVE:
        reminders.cancel_for_subject(session, SUBJECT, auth.id)
    return auth


def list_active(session: Session, patient_id: str) -> list[Authorization]:
    query = select(Authorization).where(
        Authorization.patient_id == patient_id,
        Authorization.status == AuthorizationStatus.ACTIVE,
    )
    return list(session.exec(query).all())
