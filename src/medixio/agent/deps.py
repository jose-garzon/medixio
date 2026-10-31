from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session

from medixio.modules.patients.models import Patient


@dataclass
class RunDeps:
    session: Session
    patient: Patient
    now: datetime  # UTC
    delete_requested: bool = False
