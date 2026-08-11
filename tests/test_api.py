from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_shell_and_security_headers() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Data Platform Control Tower" in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok", "mode": "demo"},
        "error": None,
    }


def test_dashboard_endpoint_uses_response_envelope() -> None:
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["data"]["overview"]["total_pipelines"] == 8
    assert len(payload["data"]["pipelines"]) == 8


def test_pipeline_endpoint_validates_status() -> None:
    response = client.get("/api/pipelines?status=unknown")

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "status" in response.json()["error"].lower()


def test_approval_requires_valid_actor() -> None:
    response = client.post(
        "/api/incidents/inc-1042/approve",
        json={"actor": ""},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_approval_updates_incident() -> None:
    response = client.post(
        "/api/incidents/inc-1042/approve",
        json={"actor": "demo-operator"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "remediation_queued"
