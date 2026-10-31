from datetime import date, timedelta

from sqlmodel import Session, select

from medixio.modules.dispensing import service as dispensing
from medixio.modules.dispensing.models import Dispense, DispenseStatus
from medixio.modules.orders import service as orders
from medixio.modules.orders.models import OrderStatus
from medixio.modules.orders.service import ItemIn
from medixio.modules.patients.models import Patient
from medixio.modules.reminders.models import Reminder
from medixio.shared.time import to_local, utcnow


def _order(session: Session, patient: Patient) -> str:
    order = orders.create(
        session,
        patient.id,
        issued_on=utcnow().date(),
        duration_months=3,
        items=[ItemIn(medicine_name="Metformina 850 mg", dose_text="1 tableta c/12h")],
    )
    session.commit()
    return order.id


def _active(session: Session, kind: str) -> list[Reminder]:
    return list(
        session.exec(
            select(Reminder).where(Reminder.kind == kind, Reminder.cancelled_at == None)  # noqa: E711
        ).all()
    )


def test_renewal_reminder_15_days_before_expiry(
    session: Session, patient: Patient
) -> None:
    order_id = _order(session, patient)
    order = orders.get(session, patient.id, order_id)
    (renewal,) = _active(session, "order_renewal")
    assert to_local(renewal.fire_at).date() == order.expires_on - timedelta(days=15)
    assert to_local(renewal.fire_at).hour == 8


def test_three_monthly_cycles_each_asks_confirmation(
    session: Session, patient: Patient
) -> None:
    _order(session, patient)
    cycles = session.exec(select(Dispense)).all()
    assert len(cycles) == 3
    confirms = _active(session, "dispense_confirm")
    assert len(confirms) == 3
    assert all(r.rrule == "FREQ=DAILY;COUNT=3" for r in confirms)


def test_partial_dispense_stops_asking_and_follows_up(
    session: Session, patient: Patient
) -> None:
    _order(session, patient)
    first = session.exec(select(Dispense).where(Dispense.cycle == 1)).one()
    dispensing.record(
        session, patient.id, first.id, DispenseStatus.PARTIAL, pending_note="insulina"
    )
    session.commit()
    confirms = [
        r for r in _active(session, "dispense_confirm") if r.subject_id == first.id
    ]
    assert confirms == []
    (follow,) = _active(session, "pending_followup")
    assert "insulina" in follow.message
    assert "48 horas" not in follow.message  # legal rule not reviewed yet


def test_renewed_order_cancels_future_cycles(
    session: Session, patient: Patient
) -> None:
    order_id = _order(session, patient)
    orders.set_status(session, patient.id, order_id, OrderStatus.RENEWED)
    session.commit()
    assert _active(session, "order_renewal") == []
    remaining = {r.subject_id for r in _active(session, "dispense")}
    first = session.exec(select(Dispense).where(Dispense.cycle == 1)).one()
    assert remaining <= {first.id}
    assert first.due_on <= date.today() + timedelta(days=1)
