import json
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def test_health():
    r = c.get("/api/health").json()
    assert r["status"] == "ok" and r["database"] is True


def test_overview_has_data():
    o = c.get("/api/analytics/overview").json()
    assert o["kpis"]["orders"] > 0 and o["late_by_city"] and o["refunds_by_reason"]


def test_order_endpoint():
    assert c.get("/api/orders/10245").status_code == 200
    assert c.get("/api/orders/5").status_code == 404


def test_policy_search_endpoint():
    r = c.get("/api/policy/search", params={"q": "free cancellation"}).json()
    assert r["hits"] and "60 seconds" in json.dumps(r)


def test_chat_without_key_streams_clean_error():
    with c.stream("POST", "/api/chat", json={"message": "hi", "level": "llm"}) as r:
        body = "".join(r.iter_text())
    assert '"type": "error"' in body and "GOOGLE_API_KEY" in body and '"done"' in body
    assert c.get("/api/traces").json()["stats"]["n"] >= 1


def test_approval_flow():
    from app import ops
    a = ops.create_approval("WALLET_CREDIT", 10245, 150, "test")
    r = c.post(f"/api/approvals/{a['id']}/decision", json={"decision": "approved", "note": "ok"}).json()
    assert r["status"] == "APPROVED"
    assert c.post(f"/api/approvals/{a['id']}/decision", json={"decision": "maybe"}).status_code == 400


def test_api_key_gate(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "app_api_key", "secret")
    assert c.get("/api/traces").status_code == 401
    assert c.get("/api/traces", headers={"X-API-Key": "secret"}).status_code == 200
