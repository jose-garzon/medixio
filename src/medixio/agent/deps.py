import threading
from dataclasses import dataclass, field
from datetime import datetime

from sqlmodel import Session

from medixio.modules.patients.models import Patient


@dataclass
class RunDeps:
    session: Session
    patient: Patient
    now: datetime  # UTC
    delete_requested: bool = False
    # The model may call tools in parallel (worker threads); they share one session.
    lock: threading.Lock = field(default_factory=threading.Lock)
