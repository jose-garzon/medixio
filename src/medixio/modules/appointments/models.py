from datetime import datetime
from enum import StrEnum

from sqlmodel import Field

from medixio.shared.models import TableBase


class AppointmentStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    DONE = "done"
    MISSED = "missed"
    CANCELLED = "cancelled"


class Appointment(TableBase, table=True):
    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    doctor_name: str | None = None
    specialty: str
    starts_at: datetime | None = None  # UTC
    location: str | None = None
    status: AppointmentStatus = AppointmentStatus.DRAFT
    notes: str | None = None
    extracted_from_image: bool = False
