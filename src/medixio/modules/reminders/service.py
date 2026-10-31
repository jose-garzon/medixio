from datetime import datetime, timedelta

from dateutil.rrule import rrulestr
from sqlmodel import Session, col, select

from medixio.modules.reminders.models import Reminder
from medixio.shared.time import utcnow


def create(
    session: Session,
    *,
    patient_id: str,
    kind: str,
    fire_at: datetime,
    message: str,
    rrule: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
) -> Reminder:
    if rrule is not None:
        rrulestr(rrule, dtstart=fire_at)  # validate early
    reminder = Reminder(
        patient_id=patient_id,
        kind=kind,
        fire_at=fire_at,
        message=message,
        rrule=rrule,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    session.add(reminder)
    return reminder


def cancel_for_subject(
    session: Session,
    subject_type: str,
    subject_id: str,
    *,
    kinds: list[str] | None = None,
    future_only: bool = False,
) -> int:
    query = select(Reminder).where(
        Reminder.subject_type == subject_type,
        Reminder.subject_id == subject_id,
        col(Reminder.cancelled_at).is_(None),
    )
    if kinds:
        query = query.where(col(Reminder.kind).in_(kinds))
    now = utcnow()
    count = 0
    for reminder in session.exec(query).all():
        if future_only and reminder.rrule is None and reminder.fire_at <= now:
            continue
        reminder.cancelled_at = now
        session.add(reminder)
        count += 1
    return count


def cancel(session: Session, patient_id: str, reminder_id: str) -> bool:
    reminder = session.get(Reminder, reminder_id)
    if reminder is None or reminder.patient_id != patient_id:
        return False
    reminder.cancelled_at = utcnow()
    session.add(reminder)
    return True


def list_active(session: Session, patient_id: str) -> list[Reminder]:
    query = (
        select(Reminder)
        .where(Reminder.patient_id == patient_id, col(Reminder.cancelled_at).is_(None))
        .order_by(col(Reminder.fire_at))
    )
    return [r for r in session.exec(query).all() if next_fire(r) is not None]


def next_fire(reminder: Reminder) -> datetime | None:
    """Next occurrence not yet sent (may be in the past = overdue)."""
    if reminder.cancelled_at is not None:
        return None
    if reminder.rrule is None:
        return reminder.fire_at if reminder.last_sent_at is None else None
    rule = rrulestr(reminder.rrule, dtstart=reminder.fire_at)
    after = reminder.last_sent_at or reminder.fire_at - timedelta(seconds=1)
    result: datetime | None = rule.after(after)
    return result


def due(session: Session, now: datetime) -> list[tuple[Reminder, datetime]]:
    """Due reminders with the occurrence to mark as sent.

    For recurring reminders only the latest missed occurrence is returned,
    so downtime never causes a burst of repeated messages.
    """
    query = select(Reminder).where(
        col(Reminder.cancelled_at).is_(None), Reminder.fire_at <= now
    )
    result = []
    for reminder in session.exec(query).all():
        if reminder.rrule is None:
            if reminder.last_sent_at is None:
                result.append((reminder, now))
            continue
        rule = rrulestr(reminder.rrule, dtstart=reminder.fire_at)
        latest: datetime | None = rule.before(now, inc=True)
        if latest is not None and (
            reminder.last_sent_at is None or latest > reminder.last_sent_at
        ):
            result.append((reminder, latest))
    return result
