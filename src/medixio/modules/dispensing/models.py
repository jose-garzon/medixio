from datetime import date
from enum import StrEnum

from sqlmodel import Field

from medixio.shared.models import TableBase


class DispenseStatus(StrEnum):
    DUE = "due"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    DISPENSED = "dispensed"
    PARTIAL = "partial"
    PENDING = "pending"


class Dispense(TableBase, table=True):
    """One monthly pickup cycle of a fórmula. Only the user can mark it dispensed."""

    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    order_id: str = Field(foreign_key="medicalorder.id", index=True, ondelete="CASCADE")
    cycle: int
    due_on: date
    dispensed_on: date | None = None
    pharmacy: str | None = None
    status: DispenseStatus = DispenseStatus.DUE
    pending_note: str | None = None
