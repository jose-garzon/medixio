from fastapi.testclient import TestClient

from medixio.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unreviewed_knowledge_listed() -> None:
    with TestClient(app) as client:
        items = client.get("/admin/knowledge/unreviewed").json()
    keys = {i["key"] for i in items}
    assert "dispensing.pending_delivery_hours" in keys
    assert "order.renewal_lead_days" not in keys  # product rules need no review
