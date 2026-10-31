import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["WHATSAPP_ENABLED"] = "false"
os.environ["OBSERVABILITY_DB"] = str(_tmp / "obs.db")
os.environ["ADMIN_TOKEN"] = ""

from sqlmodel import Session, SQLModel  # noqa: E402

import medixio.models  # noqa: E402, F401
from medixio.db import engine  # noqa: E402
from medixio.modules.patients.models import Patient  # noqa: E402
from medixio.modules.patients.service import get_or_create  # noqa: E402
from medixio.shared.time import utcnow  # noqa: E402


@pytest.fixture(autouse=True)
def _db() -> Iterator[None]:
    from medixio.observability import obs

    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)
    for table in ("rate_event", "metric", "event", "heartbeat"):
        obs().write(f"DELETE FROM {table}", ())


@pytest.fixture
def session() -> Iterator[Session]:
    with Session(engine) as s:
        yield s


@pytest.fixture
def patient(session: Session) -> Patient:
    p, _ = get_or_create(session, "573001112233@s.whatsapp.net")
    p.consent_accepted_at = utcnow()
    p.name = "Ana"
    session.add(p)
    session.commit()
    return p
