from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from medixio.shared.time import utcnow


def new_id() -> str:
    return str(uuid4())


class TableBase(SQLModel):
    id: str = Field(default_factory=new_id, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
