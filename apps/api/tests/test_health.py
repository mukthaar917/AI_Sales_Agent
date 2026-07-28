from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_system_status() -> None:
    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    assert response.json()["api"] == "connected"