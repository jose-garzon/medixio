from datetime import datetime

from sqlmodel import Field

from medixio.shared.models import TableBase


class Reminder(TableBase, table=True):
    """Every proactive outbound message. `fire_at` is UTC (DTSTART if RRULE)."""

    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    subject_type: str | None = Field(default=None, index=True)
    subject_id: str | None = Field(default=None, index=True)
    kind: str
    fire_at: datetime = Field(index=True)
    rrule: str | None = None
    message: str
    last_sent_at: datetime | None = None
    cancelled_at: datetime | None = None
