"""API tests for the /health route."""

from flask.testing import FlaskClient

_DEGRADED_SUFFIXES = ("fallback active", "service unavailable")


def _is_valid_status(s: str) -> bool:
    return s == "connected" or any(s.startswith(f"degraded ({p}") for p in _DEGRADED_SUFFIXES) or s.startswith("degraded (")


def test_health_check_endpoint_status(client: FlaskClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_endpoint_json_shape(client: FlaskClient) -> None:
    response = client.get("/health")
    data = response.get_json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["timestamp"].endswith("Z")

    services = data["services"]
    for key in ("gemini", "firestore", "cloud_logging", "secret_manager", "translation"):
        assert key in services, f"Missing service key: {key}"
        assert _is_valid_status(services[key]), f"Unexpected status for {key}: {services[key]}"
