from sqlmodel import Field

from medixio.shared.models import TableBase


class Doctor(TableBase, table=True):
    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    name: str
    specialty: str | None = None
    phone: str | None = None
    address: str | None = None
    institution: str | None = None
