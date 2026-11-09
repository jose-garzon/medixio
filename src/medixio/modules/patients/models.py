from datetime import datetime

from sqlmodel import Field, UniqueConstraint

from medixio.shared.models import TableBase


class Patient(TableBase, table=True):
    """One WhatsApp number = one patient."""

    whatsapp_jid: str = Field(unique=True, index=True)
    phone_number: str
    name: str | None = None
    consent_accepted_at: datetime | None = None


class PatientProfile(TableBase, table=True):
    patient_id: str = Field(foreign_key="patient.id", unique=True, ondelete="CASCADE")
    eps: str | None = None
    prepaid_plan: str | None = None  # medicina prepagada, e.g. Colmédica
    regimen: str | None = None  # contributivo | subsidiado | especial
    city: str | None = None
    default_pharmacy: str | None = None
    reminder_hour: int | None = None
    delivery_mode: str | None = None  # pickup | home
    birth_year: int | None = None


class PatientPreference(TableBase, table=True):
    """Per-patient override of a shared knowledge rule; value is JSON."""

    __table_args__ = (UniqueConstraint("patient_id", "key"),)

    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    key: str
    value: str
    note: str | None = None
