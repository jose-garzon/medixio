from datetime import date
from enum import StrEnum

from sqlmodel import Field

from medixio.shared.models import TableBase


class AuthorizationStatus(StrEnum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    DENIED = "denied"


class Authorization(TableBase, table=True):
    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    order_id: str | None = Field(
        default=None, foreign_key="medicalorder.id", ondelete="SET NULL"
    )
    eps: str | None = None
    number: str | None = None
    service_description: str
    issued_on: date | None = None
    valid_until: date | None = None
    provider: str | None = None
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE
    extracted_from_image: bool = False
