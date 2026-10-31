import logging
import time

import pytest
from fastapi.testclient import TestClient

from medixio.main import app
from medixio.observability.checks import run_checks, summary
from medixio.observability.logs import StoreHandler
from medixio.observability.store import Store


@pytest.fixture
def store() -> Store:
    return Store(":memory:")


def test_timer_records_success_and_failure(store: Store) -> None:
    with store.timer("job"):
        pass
    with pytest.raises(RuntimeError), store.timer("job"):
        raise RuntimeError("boom")
    stats = summary(store)["job"]
    assert stats["count"] == 2
    assert stats["failed"] == 1


def test_warning_logs_are_persisted_with_traceback(store: Store) -> None:
    logger = logging.getLogger("medixio.test")
    handler = StoreHandler(store)
    logger.addHandler(handler)
    try:
        logger.info("ignored")
        try:
            raise ValueError("bad")
        except ValueError:
            logger.exception("failed doing x")
    finally:
        logger.removeHandler(handler)
    (row,) = store.query("SELECT * FROM event")
    assert row["level"] == "ERROR"
    assert row["exc_type"] == "ValueError"
    assert "bad" in row["traceback"]


def test_checks_flag_agent_failures(store: Store) -> None:
    for _ in range(3):
        store.metric("agent.run", 1.0, ok=False)
    store.metric("agent.run", 1.0, ok=True)
    result = {c["name"]: c for c in run_checks(store, None)["checks"]}
    assert result["agent"]["status"] == "fail"
    assert result["database"]["status"] == "ok"
    assert result["whatsapp"]["status"] == "ok"  # disabled in tests


def test_stale_scheduler_heartbeat_fails(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    from medixio.config import get_settings

    monkeypatch.setattr(get_settings(), "whatsapp_enabled", True)
    store.heartbeat("scheduler")
    store.write("UPDATE heartbeat SET ts = ?", (time.time() - 3600,))
    result = {c["name"]: c for c in run_checks(store, None)["checks"]}
    assert result["scheduler"]["status"] == "fail"
    assert result["whatsapp"]["status"] == "fail"


def test_purge_drops_old_rows(store: Store) -> None:
    store.metric("x", 1)
    store.write("UPDATE metric SET ts = ?", (time.time() - 40 * 86400,))
    store.purge(30)
    assert store.query("SELECT * FROM metric") == []


def test_dashboard_and_status_endpoints() -> None:
    with TestClient(app) as client:
        status = client.get("/admin/obs/status").json()
        page = client.get("/admin/obs")
    assert {c["name"] for c in status["checks"]} >= {"database", "agent", "disk"}
    assert page.status_code == 200
    assert "Medixio" in page.text
