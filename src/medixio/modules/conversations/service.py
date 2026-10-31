from sqlmodel import Session, col, select

from medixio.modules.conversations.models import Message, Role


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


def last(session: Session, patient_id: str, limit: int) -> list[Message]:
    query = (
        select(Message)
        .where(Message.patient_id == patient_id)
        .order_by(col(Message.created_at).desc())
        .limit(limit)
    )
    return list(reversed(session.exec(query).all()))
