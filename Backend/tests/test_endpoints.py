import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HEALTHY"

def test_demo_scenarios():
    resp = client.get("/demo/scenarios")
    assert resp.status_code == 200
    scens = resp.json()
    assert len(scens) >= 6
    assert any(s["id"] == "flood" for s in scens)

def test_risk_endpoint():
    resp = client.get("/v1/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert "city" in data
    assert "zones" in data
    assert len(data["zones"]) >= 16

def test_cascade_endpoint():
    resp = client.get("/v1/cascade")
    assert resp.status_code == 200
    data = resp.json()
    assert "chains" in data
    assert "rho" in data

def test_graph_and_evidence():
    resp = client.get("/v1/graph")
    assert resp.status_code == 200
    assert "nodes" in resp.json()
    assert "edges" in resp.json()

    ev_resp = client.get("/v1/graph/edge/HYD/TRF")
    assert ev_resp.status_code == 200
    card = ev_resp.json()
    assert card["from"] == "HYD"
    assert card["to"] == "TRF"
    assert card["mechanism"] == "physical"

def test_explain_endpoint():
    resp = client.get("/v1/explain?zone=z04_kurla_w&layer=HYD")
    assert resp.status_code == 200
    data = resp.json()
    assert "drivers" in data
    assert "cascade_receipt" in data

def test_decide_endpoints():
    intervene_resp = client.post("/v1/intervene", json={"interventions": ["preposition_pumps"]})
    assert intervene_resp.status_code == 200
    assert len(intervene_resp.json()["plans"]) == 1

    rec_resp = client.get("/v1/recommend")
    assert rec_resp.status_code == 200
    assert "total_risk_reduced_24h" in rec_resp.json()

    acc_resp = client.get("/v1/access")
    assert acc_resp.status_code == 200
    assert "retained_access_delta_pp" in acc_resp.json()

def test_integrity_and_ledger():
    verify_resp = client.get("/v1/ledger/verify")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["canary_passed"] is True

    canary_resp = client.get("/v1/canary")
    assert canary_resp.status_code == 200
    assert canary_resp.json()["passed"] is True

def test_scoreboard_eval():
    resp = client.get("/v1/metrics/eval")
    assert resp.status_code == 200
    data = resp.json()
    assert "lead_time_metrics" in data
    assert "calibration" in data
    assert "held_out_city" in data

def test_integration_outputs():
    cap_resp = client.get("/v1/alerts.cap")
    assert cap_resp.status_code == 200
    assert "<alert" in cap_resp.text

    geo_resp = client.get("/v1/risk.geojson")
    assert geo_resp.status_code == 200
    assert geo_resp.json()["type"] == "FeatureCollection"
