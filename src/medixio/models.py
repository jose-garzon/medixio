"""Single import point for every table, so Alembic autogenerate sees them all."""

from medixio.modules.appointments.models import Appointment
from medixio.modules.authorizations.models import Authorization
from medixio.modules.claims.models import Claim
from medixio.modules.conversations.models import Message
from medixio.modules.dispensing.models import Dispense
from medixio.modules.doctors.models import Doctor
from medixio.modules.orders.models import MedicalOrder, OrderItem
from medixio.modules.patients.models import Patient, PatientPreference, PatientProfile
from medixio.modules.reminders.models import Reminder


__all__ = [
    "Appointment",
    "Authorization",
    "Claim",
    "Dispense",
    "Doctor",
    "MedicalOrder",
    "Message",
    "OrderItem",
    "Patient",
    "PatientPreference",
    "PatientProfile",
    "Reminder",
]
