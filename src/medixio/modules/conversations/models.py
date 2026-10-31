from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from medixio.shared.models import new_id
from medixio.shared.time import utcnow


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True, ondelete="CASCADE")
    role: Role
    content: str
    has_image: bool = False
    created_at: datetime = Field(default_factory=utcnow, index=True)
