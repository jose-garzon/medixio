from datetime import datetime, time

from sqlmodel import Session, col, select

from medixio.modules.conversations.models import Message, Role
from medixio.shared.time import local_at, today_local


def add(
    session: Session,
    patient_id: str,
    role: Role,
    content: str,
    *,
    has_image: bool = False,
) -> Message:
    msg = Message(
        patient_id=patient_id, role=role, content=content, has_image=has_image
    )
    session.add(msg)
    return msg


def session_start() -> datetime:
    """Chat sessions reset daily at local midnight."""
    return local_at(today_local(), time.min)


def last(
    session: Session,
    patient_id: str,
    limit: int,
    since: datetime | None = None,
) -> list[Message]:
    query = select(Message).where(Message.patient_id == patient_id)
    if since is not None:
        query = query.where(Message.created_at >= since)
    query = query.order_by(col(Message.created_at).desc()).limit(limit)
    return list(reversed(session.exec(query).all()))
