from datetime import date
from enum import StrEnum

from sqlmodel import Field

from medixio.shared.models import TableBase


class OrderStatus(StrEnum):
    ACTIVE = "active"
    RENEWAL_REQUESTED = "renewal_requested"
    RENEWED = "renewed"
    EXPIRED = "expired"


class MedicalOrder(TableBase, table=True):
    """Fórmula / orden médica."""

    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    doctor_name: str | None = None
    issued_on: date
    duration_months: int
    expires_on: date
    status: OrderStatus = OrderStatus.ACTIVE
    renewed_by_order_id: str | None = None
    extracted_from_image: bool = False


class OrderItem(TableBase, table=True):
    order_id: str = Field(foreign_key="medicalorder.id", index=True, ondelete="CASCADE")
    medicine_name: str
    presentation: str | None = None
    dose_text: str | None = None  # verbatim from the order, never interpreted
    quantity_per_dispense: str | None = None
