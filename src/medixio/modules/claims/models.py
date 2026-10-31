from datetime import date
from enum import StrEnum

from sqlmodel import Field

from medixio.shared.models import TableBase


class ClaimKind(StrEnum):
    PQRS = "pqrs"
    TUTELA = "tutela"
    IMPUGNACION = "impugnacion"
    DESACATO = "desacato"


class ClaimStatus(StrEnum):
    DRAFT = "draft"
    FILED = "filed"
    ANSWERED = "answered"
    ESCALATED = "escalated"
    CLOSED = "closed"


class Claim(TableBase, table=True):
    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    kind: ClaimKind
    subject: str
    filed_on: date | None = None
    radicado: str | None = None
    response_due_on: date | None = None
    status: ClaimStatus = ClaimStatus.DRAFT
