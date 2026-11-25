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
    # Records snapshot frozen at the start of the run: instructions are re-evaluated
    # on every model request, and a live snapshot made the model think its own
    # tool-driven changes contradicted what it had said earlier in the turn.
    context_snapshot: str | None = None
    # The model may call tools in parallel (worker threads); they share one session.
    lock: threading.Lock = field(default_factory=threading.Lock)
