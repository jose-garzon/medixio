from datetime import date, time

from sqlmodel import Session, col, select

from medixio.knowledge import resolve
from medixio.modules.claims.models import Claim, ClaimKind, ClaimStatus
from medixio.modules.patients.service import reminder_hour
from medixio.modules.reminders import service as reminders
from medixio.shared.time import add_business_days, local_at, today_local, utcnow


SUBJECT = "claim"

_RESPONSE_DAYS_KEY = {
    ClaimKind.PQRS: "claims.pqrs_response_business_days",
    ClaimKind.TUTELA: "claims.tutela_decision_business_days",
}


def _schedule(session: Session, claim: Claim) -> None:
    reminders.cancel_for_subject(session, SUBJECT, claim.id)
    if claim.status != ClaimStatus.FILED or claim.response_due_on is None:
        return
    reminders.create(
        session,
        patient_id=claim.patient_id,
        kind="claim_due",
        fire_at=local_at(
            max(claim.response_due_on, today_local()),
            time(reminder_hour(session, claim.patient_id)),
        ),
        message=(
            f"⚖️ Hoy vence el plazo de respuesta de tu {claim.kind.upper()} "
            f"({claim.subject}). ¿Ya te respondieron? "
            "Si no, te explico el siguiente paso."
        ),
        subject_type=SUBJECT,
        subject_id=claim.id,
    )


def open_claim(
    session: Session,
    patient_id: str,
    *,
    kind: ClaimKind,
    subject: str,
    filed_on: date | None = None,
    radicado: str | None = None,
    response_due_on: date | None = None,
) -> Claim:
    claim = Claim(
        patient_id=patient_id,
        kind=kind,
        subject=subject,
        filed_on=filed_on,
        radicado=radicado,
        status=ClaimStatus.FILED if filed_on else ClaimStatus.DRAFT,
    )
    claim.response_due_on = response_due_on or _computed_due(session, claim)
    session.add(claim)
    _schedule(session, claim)
    return claim


def _computed_due(session: Session, claim: Claim) -> date | None:
    key = _RESPONSE_DAYS_KEY.get(claim.kind)
    if claim.filed_on is None or key is None:
        return None
    days = resolve(session, claim.patient_id, key)
    return add_business_days(claim.filed_on, int(days)) if days else None


def update(
    session: Session,
    patient_id: str,
    claim_id: str,
    *,
    status: ClaimStatus | None = None,
    filed_on: date | None = None,
    radicado: str | None = None,
    response_due_on: date | None = None,
) -> Claim:
    claim = session.get(Claim, claim_id)
    if claim is None or claim.patient_id != patient_id:
        raise LookupError("Caso no encontrado")
    if filed_on:
        claim.filed_on = filed_on
        if claim.status == ClaimStatus.DRAFT:
            claim.status = ClaimStatus.FILED
    if radicado:
        claim.radicado = radicado
    if status:
        claim.status = status
    claim.response_due_on = (
        response_due_on or claim.response_due_on or _computed_due(session, claim)
    )
    claim.updated_at = utcnow()
    session.add(claim)
    _schedule(session, claim)
    return claim


def list_open(session: Session, patient_id: str) -> list[Claim]:
    query = select(Claim).where(
        Claim.patient_id == patient_id, col(Claim.status) != ClaimStatus.CLOSED
    )
    return list(session.exec(query).all())
