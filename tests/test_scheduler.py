from datetime import datetime

import pytest
from sqlmodel import Session

from medixio.channel.base import RecordingChannel
from medixio.modules.patients.models import Patient
from medixio.modules.reminders import service as reminders
from medixio.scheduler import dispatch_due
from medixio.shared.time import from_local


@pytest.mark.asyncio
async def test_merges_per_patient_and_is_idempotent(
    session: Session, patient: Patient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("medixio.scheduler.asyncio.sleep", _no_sleep)
    now = from_local(datetime(2026, 11, 2, 10, 0))
    for text in ("uno", "dos"):
        reminders.create(
            session, patient_id=patient.id, kind="custom", fire_at=now, message=text
        )
    session.commit()
    channel = RecordingChannel()
    assert await dispatch_due(session, channel, now) == 1
    assert await dispatch_due(session, channel, now) == 0
    assert len(channel.sent) == 1
    assert "uno" in channel.sent[0][1]
    assert "dos" in channel.sent[0][1]


@pytest.mark.asyncio
async def test_quiet_hours_defer(session: Session, patient: Patient) -> None:
    night = from_local(datetime(2026, 11, 2, 23, 0))
    reminders.create(
        session, patient_id=patient.id, kind="custom", fire_at=night, message="x"
    )
    session.commit()
    channel = RecordingChannel()
    assert await dispatch_due(session, channel, night) == 0
    assert channel.sent == []


async def _no_sleep(_: float) -> None:
    return None
