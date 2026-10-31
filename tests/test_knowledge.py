from sqlmodel import Session

from medixio.knowledge import resolve
from medixio.modules.patients.models import Patient
from medixio.modules.patients.service import set_preference


def test_product_rule_applies(session: Session, patient: Patient) -> None:
    assert resolve(session, patient.id, "order.renewal_lead_days") == 15


def test_unreviewed_legal_rule_is_ignored(session: Session, patient: Patient) -> None:
    assert resolve(session, patient.id, "claims.pqrs_response_business_days") is None


def test_patient_override_wins(session: Session, patient: Patient) -> None:
    set_preference(session, patient.id, "order.renewal_lead_days", 20, None)
    session.commit()
    assert resolve(session, patient.id, "order.renewal_lead_days") == 20
