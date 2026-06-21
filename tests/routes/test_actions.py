"""API integration tests for the actions routes.

This module verifies correct handling of GET, POST, and CLEAR action requests,
asserting server validation, payload limits, and correct responses.
"""

import json
from flask.testing import FlaskClient
from app import action_repo


def test_get_actions_empty(client: FlaskClient) -> None:
    """Verifies that GET /api/actions returns an empty list initially."""
    response = client.get("/api/actions")
    assert response.status_code == 200
    assert response.get_json() == []


def test_post_action_success(client: FlaskClient) -> None:
    """Verifies successful action creation on valid POST payload."""
    payload = {
        "category": "transport",
        "type": "car",
        "amount": 10.0,
        "unit": "km"
    }
    response = client.post(
        "/api/actions",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 201

    data = response.get_json()
    assert "id" in data
    assert data["category"] == "transport"
    assert data["type"] == "car"
    assert data["amount"] == 10.0
    assert data["unit"] == "km"
    assert "co2_kg" in data
    assert data["co2_kg"] == 1.71  # 10 * 0.171
    assert "nudge" in data
    assert "timestamp" in data

    # Verify action added to database
    all_actions = action_repo.get_all()
    assert len(all_actions) == 1
    assert all_actions[0].id == data["id"]


def test_post_action_missing_json(client: FlaskClient) -> None:
    """Verifies that POSTing without json or header yields a 400 Bad Request."""
    response = client.post("/api/actions", data="not-json")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_post_action_missing_fields(client: FlaskClient) -> None:
    """Verifies validation failure if required fields are missing."""
    payload = {
        "category": "transport",
        "type": "car",
        # amount missing
        "unit": "km"
    }
    response = client.post(
        "/api/actions",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 400
    assert "Missing required field" in response.get_json()["error"]


def test_post_action_wrong_type(client: FlaskClient) -> None:
    """Verifies validation failure if a field has incorrect data type."""
    payload = {
        "category": "transport",
        "type": "car",
        "amount": "ten",  # should be number
        "unit": "km"
    }
    response = client.post(
        "/api/actions",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 400
    assert "must be a number" in response.get_json()["error"]


def test_post_action_negative_amount(client: FlaskClient) -> None:
    """Verifies validation failure for negative quantities."""
    payload = {
        "category": "transport",
        "type": "car",
        "amount": -5.0,
        "unit": "km"
    }
    response = client.post(
        "/api/actions",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 400
    assert "cannot be negative" in response.get_json()["error"]


def test_post_action_out_of_range(client: FlaskClient) -> None:
    """Verifies validation failure for excessively large input values."""
    payload = {
        "category": "transport",
        "type": "car",
        "amount": 9999.0,  # max is 5000
        "unit": "km"
    }
    response = client.post(
        "/api/actions",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 400
    assert "cannot exceed" in response.get_json()["error"]


def test_post_action_script_injection(client: FlaskClient) -> None:
    """Verifies script injection defense blocks malicious inputs."""
    payload = {
        "category": "transport",
        "type": "car",
        "amount": 10.0,
        "unit": "<script>console.log('attack')</script>"
    }
    response = client.post(
        "/api/actions",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert response.status_code == 400
    assert "Injection-style characters detected" in response.get_json()["error"]


def test_post_action_oversized_payload(client: FlaskClient) -> None:
    """Verifies that excessively large payloads are rejected before parsing."""
    large_payload = {
        "category": "transport",
        "type": "car",
        "amount": 10.0,
        "unit": "km" * 10000  # large payload string (>20KB)
    }
    response = client.post(
        "/api/actions",
        data=json.dumps(large_payload),
        content_type="application/json"
    )
    assert response.status_code == 400
    assert "Payload size exceeds limit" in response.get_json()["error"]



def test_get_actions_history_list(client: FlaskClient) -> None:
    """Verifies that GET /api/actions returns previously logged records."""
    # Log two actions
    client.post(
        "/api/actions",
        data=json.dumps({"category": "food", "type": "veg", "amount": 1.0, "unit": "meals"}),
        content_type="application/json"
    )
    client.post(
        "/api/actions",
        data=json.dumps({"category": "energy", "type": "ac", "amount": 2.0, "unit": "hours"}),
        content_type="application/json"
    )

    response = client.get("/api/actions")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    # Verify both categories are present (order may vary when timestamps are identical)
    categories = {d["category"] for d in data}
    assert categories == {"food", "energy"}


def test_clear_actions_endpoint(client: FlaskClient) -> None:
    """Verifies that POST /api/actions/clear wipes the database."""
    # Log an action
    client.post(
        "/api/actions",
        data=json.dumps({"category": "food", "type": "veg", "amount": 1.0, "unit": "meals"}),
        content_type="application/json"
    )
    assert len(action_repo.get_all()) == 1

    # Clear
    clear_resp = client.post("/api/actions/clear")
    assert clear_resp.status_code == 200
    assert clear_resp.get_json()["status"] == "success"

    # Verify empty
    assert len(action_repo.get_all()) == 0
    get_resp = client.get("/api/actions")
    assert get_resp.get_json() == []
