from datetime import date, time, timedelta

from pydantic import BaseModel
from sqlmodel import Session, col, select

from medixio.knowledge import resolve
from medixio.modules.dispensing import service as dispensing
from medixio.modules.orders.models import MedicalOrder, OrderItem, OrderStatus
from medixio.modules.patients.service import reminder_hour
from medixio.modules.reminders import service as reminders
from medixio.shared.time import add_months, local_at, today_local, utcnow


SUBJECT = "order"


class ItemIn(BaseModel):
    medicine_name: str
    presentation: str | None = None
    dose_text: str | None = None
    quantity_per_dispense: str | None = None


def create(
    session: Session,
    patient_id: str,
    *,
    issued_on: date,
    duration_months: int,
    items: list[ItemIn],
    doctor_name: str | None = None,
    expires_on: date | None = None,
    extracted_from_image: bool = False,
    plan_dispensing: bool = True,
) -> MedicalOrder:
    order = MedicalOrder(
        patient_id=patient_id,
        issued_on=issued_on,
        duration_months=duration_months,
        expires_on=expires_on or add_months(issued_on, duration_months),
        doctor_name=doctor_name,
        extracted_from_image=extracted_from_image,
    )
    session.add(order)
    for item in items:
        session.add(OrderItem(order_id=order.id, **item.model_dump()))
    session.flush()
    _schedule_renewal(session, order)
    if plan_dispensing:
        dispensing.plan_cycles(session, order)
    return order


def _schedule_renewal(session: Session, order: MedicalOrder) -> None:
    lead = int(resolve(session, order.patient_id, "order.renewal_lead_days") or 15)
    remind_on = max(order.expires_on - timedelta(days=lead), today_local())
    meds = ", ".join(i.medicine_name for i in items_of(session, order.id))
    reminders.create(
        session,
        patient_id=order.patient_id,
        kind="order_renewal",
        fire_at=local_at(remind_on, time(reminder_hour(session, order.patient_id))),
        message=(
            f"📝 Tu fórmula de {meds} vence el {order.expires_on:%d/%m/%Y}. "
            "Pide cita o la renovación con tu médico para no quedarte sin medicamento."
        ),
        subject_type=SUBJECT,
        subject_id=order.id,
    )


def items_of(session: Session, order_id: str) -> list[OrderItem]:
    return list(
        session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
    )


def get(session: Session, patient_id: str, order_id: str) -> MedicalOrder:
    order = session.get(MedicalOrder, order_id)
    if order is None or order.patient_id != patient_id:
        raise LookupError("Fórmula no encontrada")
    return order


def set_status(
    session: Session,
    patient_id: str,
    order_id: str,
    status: OrderStatus,
    renewed_by_order_id: str | None = None,
) -> MedicalOrder:
    order = get(session, patient_id, order_id)
    order.status = status
    order.renewed_by_order_id = renewed_by_order_id or order.renewed_by_order_id
    order.updated_at = utcnow()
    session.add(order)
    if status in (
        OrderStatus.RENEWED,
        OrderStatus.EXPIRED,
        OrderStatus.RENEWAL_REQUESTED,
    ):
        reminders.cancel_for_subject(session, SUBJECT, order.id)
    if status in (OrderStatus.RENEWED, OrderStatus.EXPIRED):
        dispensing.cancel_future(session, order.id)
    return order


def list_active(session: Session, patient_id: str) -> list[MedicalOrder]:
    query = select(MedicalOrder).where(
        MedicalOrder.patient_id == patient_id,
        col(MedicalOrder.status).in_(
            [OrderStatus.ACTIVE, OrderStatus.RENEWAL_REQUESTED]
        ),
    )
    return list(session.exec(query.order_by(col(MedicalOrder.expires_on))).all())
