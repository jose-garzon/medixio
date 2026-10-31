from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from medixio.modules.patients.models import Patient
from medixio.modules.reminders import service as reminders


def test_one_off_fires_once(session: Session, patient: Patient) -> None:
    now = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)
    r = reminders.create(
        session, patient_id=patient.id, kind="custom", fire_at=now, message="x"
    )
    assert [x for x, _ in reminders.due(session, now)] == [r]
    r.last_sent_at = now
    assert reminders.due(session, now + timedelta(hours=1)) == []


def test_recurring_sends_only_latest_missed(session: Session, patient: Patient) -> None:
    start = datetime(2026, 11, 1, 13, 0, tzinfo=UTC)
    r = reminders.create(
        session,
        patient_id=patient.id,
        kind="custom",
        fire_at=start,
        message="x",
        rrule="FREQ=DAILY",
    )
    now = start + timedelta(days=3, hours=1)
    due = reminders.due(session, now)
    assert due == [(r, start + timedelta(days=3))]
    r.last_sent_at = due[0][1]
    assert reminders.due(session, now) == []


def test_cancelled_never_due(session: Session, patient: Patient) -> None:
    now = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)
    r = reminders.create(
        session, patient_id=patient.id, kind="custom", fire_at=now, message="x"
    )
    reminders.cancel(session, patient.id, r.id)
    assert reminders.due(session, now) == []
