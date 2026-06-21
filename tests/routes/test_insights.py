"""API integration tests for the insights routes.

This module asserts correct caching behavior and automatic invalidation
of weekly insights when actions are logged or cleared.
"""

import json
from unittest.mock import MagicMock, patch
from flask.testing import FlaskClient
from app import action_repo


def test_get_insights_initial_empty(client: FlaskClient) -> None:
    """Verifies onboarding insight is returned when database is empty."""
    response = client.get("/api/insights")
    assert response.status_code == 200
    data = response.get_json()
    assert "insight" in data
    assert "source" in data
    assert "haven't logged any actions" in data["insight"]


@patch("app.services.gemini_service.GeminiService.generate_weekly_insight")
def test_get_insights_caching(
    mock_generate: MagicMock,
    client: FlaskClient
) -> None:
    """Verifies that subsequent calls serve insight from cache without re-calculating."""
    # Pre-load an action so it has context
    client.post(
        "/api/actions",
        data=json.dumps({"category": "food", "type": "veg", "amount": 1.0, "unit": "meals"}),
        content_type="application/json"
    )

    mock_generate.return_value = ("Cached advice", False)

    # First request - should call service
    resp1 = client.get("/api/insights")
    assert resp1.status_code == 200
    assert resp1.get_json()["insight"] == "Cached advice"
    assert mock_generate.call_count == 1

    # Second request - should hit cache (call_count remains 1)
    resp2 = client.get("/api/insights")
    assert resp2.status_code == 200
    assert resp2.get_json()["insight"] == "Cached advice"
    assert mock_generate.call_count == 1


@patch("app.services.gemini_service.GeminiService.generate_weekly_insight")
def test_get_insights_invalidation_on_log(
    mock_generate: MagicMock,
    client: FlaskClient
) -> None:
    """Verifies that logging a new action clears the cache, forcing regeneration."""
    # Pre-load an action
    client.post(
        "/api/actions",
        data=json.dumps({"category": "food", "type": "veg", "amount": 1.0, "unit": "meals"}),
        content_type="application/json"
    )

    mock_generate.side_effect = [("Advice 1", False), ("Advice 2", False)]

    # Fetch 1
    resp1 = client.get("/api/insights")
    assert resp1.get_json()["insight"] == "Advice 1"
    assert mock_generate.call_count == 1

    # Log new action -> invalidates cache
    client.post(
        "/api/actions",
        data=json.dumps({"category": "energy", "type": "ac", "amount": 2.0, "unit": "hours"}),
        content_type="application/json"
    )

    # Fetch 2 -> should regenerate
    resp2 = client.get("/api/insights")
    assert resp2.get_json()["insight"] == "Advice 2"
    assert mock_generate.call_count == 2


@patch("app.services.gemini_service.GeminiService.generate_weekly_insight")
def test_get_insights_invalidation_on_clear(
    mock_generate: MagicMock,
    client: FlaskClient
) -> None:
    """Verifies that clearing action history clears the cache, forcing regeneration."""
    # Pre-load action
    client.post(
        "/api/actions",
        data=json.dumps({"category": "food", "type": "veg", "amount": 1.0, "unit": "meals"}),
        content_type="application/json"
    )

    mock_generate.side_effect = [("Advice 1", False), ("Onboarding advice", False)]

    # Fetch 1
    client.get("/api/insights")
    assert mock_generate.call_count == 1

    # Clear actions -> invalidates cache
    client.post("/api/actions/clear")

    # Fetch 2 -> should regenerate onboarding
    resp2 = client.get("/api/insights")
    assert resp2.get_json()["insight"] == "Onboarding advice"
    assert mock_generate.call_count == 2
