from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def test_root_serves_a_non_blank_dashboard():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "FleetAvail" in response.text
    assert 'id="total"' in response.text or 'id="root"' in response.text


def test_testing_report_route():
    response = TestClient(app).get("/fleetavail/testing")
    assert response.status_code == 200
    assert "Testing & Verification Report" in response.text
    assert "58 passed" in response.text
