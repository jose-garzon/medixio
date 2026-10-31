"""Dispatch due reminders through the channel (design §8)."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime

from sqlmodel import Session

from medixio.channel.base import Channel
from medixio.config import get_settings
from medixio.db import engine
from medixio.modules.dispensing import service as dispensing
from medixio.modules.patients.models import Patient
from medixio.modules.reminders import service as reminders
from medixio.modules.reminders.models import Reminder
from medixio.observability import obs
from medixio.shared.time import to_local, utcnow


log = logging.getLogger(__name__)


def in_quiet_hours(now: datetime) -> bool:
    s = get_settings()
    hour = to_local(now).hour
    return hour >= s.quiet_hours_start or hour < s.quiet_hours_end


async def dispatch_due(session: Session, channel: Channel, now: datetime) -> int:
    if in_quiet_hours(now):
        return 0
    by_patient: dict[str, list[tuple[Reminder, datetime]]] = defaultdict(list)
    for reminder, occurrence in reminders.due(session, now):
        by_patient[reminder.patient_id].append((reminder, occurrence))
    sent = 0
    for patient_id, items in by_patient.items():
        patient = session.get(Patient, patient_id)
        if patient is None or patient.consent_accepted_at is None:
            continue
        items.sort(key=lambda pair: pair[0].fire_at)
        text = "\n\n".join(r.message for r, _ in items)
        try:
            await channel.send_text(patient.whatsapp_jid, text)
        except Exception:
            log.exception("dispatch failed patient=%s", patient_id)
            continue
        for reminder, occurrence in items:
            reminder.last_sent_at = occurrence
            session.add(reminder)
            if reminder.kind == "dispense_confirm" and reminder.subject_id:
                dispensing.mark_awaiting(session, reminder.subject_id)
        session.commit()
        sent += 1
        obs().metric("reminders.sent", len(items))
        log.info("dispatched patient=%s reminders=%d", patient_id, len(items))
        await asyncio.sleep(1)  # throttle: ban mitigation
    return sent


async def run(channel: Channel) -> None:
    tick = get_settings().scheduler_tick_seconds
    while True:
        try:
            with obs().timer("scheduler.tick"), Session(engine) as session:
                await dispatch_due(session, channel, utcnow())
            obs().heartbeat("scheduler")
        except Exception:
            log.exception("scheduler tick failed")
        await asyncio.sleep(tick)
