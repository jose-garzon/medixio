import json
from typing import Any

from sqlmodel import Session, select

from medixio.modules.patients.models import Patient, PatientPreference, PatientProfile
from medixio.shared.time import utcnow


def phone_from_jid(jid: str) -> str:
    return jid.split("@", 1)[0].split(":", 1)[0]


def get_or_create(session: Session, jid: str) -> tuple[Patient, bool]:
    patient = session.exec(select(Patient).where(Patient.whatsapp_jid == jid)).first()
    if patient is not None:
        return patient, False
    patient = Patient(whatsapp_jid=jid, phone_number=phone_from_jid(jid))
    session.add(patient)
    session.add(PatientProfile(patient_id=patient.id))
    session.commit()
    session.refresh(patient)
    return patient, True


def accept_consent(session: Session, patient: Patient) -> None:
    patient.consent_accepted_at = utcnow()
    session.add(patient)
    session.commit()


def get_profile(session: Session, patient_id: str) -> PatientProfile:
    profile = session.exec(
        select(PatientProfile).where(PatientProfile.patient_id == patient_id)
    ).first()
    if profile is None:
        profile = PatientProfile(patient_id=patient_id)
        session.add(profile)
    return profile


PROFILE_FIELDS = {
    "eps",
    "prepaid_plan",
    "regimen",
    "city",
    "default_pharmacy",
    "reminder_hour",
    "delivery_mode",
    "birth_year",
}


def update_profile(session: Session, patient: Patient, **fields: Any) -> PatientProfile:
    profile = get_profile(session, patient.id)
    if "name" in fields and fields["name"]:
        patient.name = fields.pop("name")
        patient.updated_at = utcnow()
        session.add(patient)
    for key, value in fields.items():
        if key in PROFILE_FIELDS and value is not None:
            setattr(profile, key, value)
    profile.updated_at = utcnow()
    session.add(profile)
    return profile


def set_preference(
    session: Session, patient_id: str, key: str, value: Any, note: str | None
) -> PatientPreference:
    pref = session.exec(
        select(PatientPreference).where(
            PatientPreference.patient_id == patient_id, PatientPreference.key == key
        )
    ).first()
    if pref is None:
        pref = PatientPreference(patient_id=patient_id, key=key, value="null")
    pref.value = json.dumps(value)
    pref.note = note
    pref.updated_at = utcnow()
    session.add(pref)
    return pref


def delete_all(session: Session, patient: Patient) -> None:
    """Hard delete. Child rows go via ON DELETE CASCADE."""
    session.delete(patient)
    session.commit()


def reminder_hour(session: Session, patient_id: str) -> int:
    from medixio.knowledge import resolve

    profile = get_profile(session, patient_id)
    if profile.reminder_hour is not None:
        return profile.reminder_hour
    value = resolve(session, patient_id, "profile.reminder_hour")
    return int(value) if value is not None else 8
