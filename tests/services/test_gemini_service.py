"""Unit tests for the GeminiService class.

This module tests Gemini API connections, mock responses, thread timeouts,
and deterministic rule-based advice generation.
"""

from unittest.mock import MagicMock, patch
import time
from typing import Generator
import pytest

from app.models.action import Action
from app.services.gemini_service import GeminiService
from datetime import datetime, timezone


@pytest.fixture
def sample_actions() -> list[Action]:
    """Provides a list of sample actions for testing recommendations.

    Returns:
        A list of Action instances.
    """
    now = datetime.now(timezone.utc)
    return [
        Action("1", "transport", "car", 15.0, "km", 2.565, "nudge 1", now),
        Action("2", "food", "meat-heavy", 1.0, "meals", 3.0, "nudge 2", now),
        Action("3", "energy", "ac", 2.0, "hours", 1.5, "nudge 3", now),
    ]


def test_gemini_init_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that the service degrades gracefully if no API key is in the env."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    service = GeminiService()
    assert service.is_degraded() is True


def test_gemini_init_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that the service attempts configuration if the API key is present."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaTestKey123")
    with patch("google.generativeai.configure") as mock_configure:
        service = GeminiService()
        mock_configure.assert_called_once_with(api_key="AIzaTestKey123")
        assert service.is_degraded() is False


def test_generate_weekly_insight_empty_actions() -> None:
    """Verifies onboarding insight message when no actions are logged."""
    service = GeminiService()
    insight, fallback = service.generate_weekly_insight([])
    assert "haven't logged any actions" in insight
    assert fallback is service.is_degraded()


@patch("google.generativeai.GenerativeModel")
def test_generate_weekly_insight_api_success(
    mock_model_class: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    sample_actions: list[Action]
) -> None:
    """Verifies that a successful API call returns the generated text."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaTestKey123")
    service = GeminiService()

    # Mock Gemini response content
    mock_response = MagicMock()
    mock_response.text = "You are doing great. Keep reducing car trips."
    
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model_instance

    insight, fallback = service.generate_weekly_insight(sample_actions)
    assert insight == "You are doing great. Keep reducing car trips."
    assert fallback is False


@patch("google.generativeai.GenerativeModel")
def test_generate_weekly_insight_api_failure(
    mock_model_class: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    sample_actions: list[Action]
) -> None:
    """Verifies fallback to rule-based insight if the API call raises an exception."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaTestKey123")
    service = GeminiService()

    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.side_effect = Exception("API quota exceeded")
    mock_model_class.return_value = mock_model_instance

    insight, fallback = service.generate_weekly_insight(sample_actions)
    
    # Assert fallback is active and rule-based advice is returned
    assert fallback is True
    # The highest emission source in sample_actions is food (meat-heavy = 3.0kg, transport = 2.565kg)
    assert "meat-heavy" in insight


@patch("google.generativeai.GenerativeModel")
def test_generate_weekly_insight_api_timeout(
    mock_model_class: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    sample_actions: list[Action]
) -> None:
    """Verifies fallback to rule-based insight if the API call takes longer than 5 seconds."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaTestKey123")
    service = GeminiService()

    # Simulate slow API call
    def slow_generate_content(*args: list[object], **kwargs: dict[str, object]) -> MagicMock:
        time.sleep(6.0)
        mock_resp = MagicMock()
        mock_resp.text = "Late response"
        return mock_resp

    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.side_effect = slow_generate_content
    mock_model_class.return_value = mock_model_instance

    # This should return in ~5 seconds due to timeout safety
    start_time = time.time()
    insight, fallback = service.generate_weekly_insight(sample_actions)
    duration = time.time() - start_time

    assert fallback is True
    assert "meat-heavy" in insight
    # Assert it timed out around 5s, not waiting full 6s
    assert duration < 5.5


def test_rule_based_insight_food_dominant() -> None:
    """Verifies food recommendation is chosen when food carbon dominates."""
    service = GeminiService()
    now = datetime.now(timezone.utc)
    actions = [
        Action("1", "food", "meat-heavy", 2.0, "meals", 6.0, "nudge 1", now), # 6.0kg
        Action("2", "transport", "car", 10.0, "km", 1.71, "nudge 2", now),   # 1.71kg
    ]
    insight, fallback = service.generate_weekly_insight(actions)
    assert fallback is True
    assert "meat-heavy" in insight
    assert "food footprint" in insight


def test_rule_based_insight_transport_flight_dominant() -> None:
    """Verifies flight recommendation is chosen when transport dominates via flight."""
    service = GeminiService()
    now = datetime.now(timezone.utc)
    actions = [
        Action("1", "transport", "flight", 1.0, "hours", 150.0, "nudge 1", now), # 150.0kg
        Action("2", "food", "mixed", 1.0, "meals", 1.5, "nudge 2", now),         # 1.5kg
    ]
    insight, fallback = service.generate_weekly_insight(actions)
    assert fallback is True
    assert "flight" in insight
    assert "aviation" in insight


def test_rule_based_insight_transport_car_dominant() -> None:
    """Verifies car recommendation is chosen when transport dominates via car."""
    service = GeminiService()
    now = datetime.now(timezone.utc)
    actions = [
        Action("1", "transport", "car", 50.0, "km", 8.55, "nudge 1", now), # 8.55kg
        Action("2", "energy", "ac", 2.0, "hours", 1.5, "nudge 2", now),    # 1.5kg
    ]
    insight, fallback = service.generate_weekly_insight(actions)
    assert fallback is True
    assert "car trips" in insight
    assert "transport" in insight


def test_rule_based_insight_energy_ac_dominant() -> None:
    """Verifies AC recommendation is chosen when energy dominates via AC."""
    service = GeminiService()
    now = datetime.now(timezone.utc)
    actions = [
        Action("1", "energy", "ac", 10.0, "hours", 7.5, "nudge 1", now), # 7.5kg
        Action("2", "food", "veg", 2.0, "meals", 1.4, "nudge 2", now),   # 1.4kg
    ]
    insight, fallback = service.generate_weekly_insight(actions)
    assert fallback is True
    assert "air conditioning" in insight
    assert "thermostat" in insight


def test_rule_based_insight_energy_appliance_dominant() -> None:
    """Verifies appliance recommendation is chosen when energy dominates via general usage."""
    service = GeminiService()
    now = datetime.now(timezone.utc)
    actions = [
        Action("1", "energy", "appliance", 20.0, "hours", 5.0, "nudge 1", now), # 5.0kg
        Action("2", "food", "veg", 1.0, "meals", 0.7, "nudge 2", now),          # 0.7kg
    ]
    insight, fallback = service.generate_weekly_insight(actions)
    assert fallback is True
    assert "energy consumption" in insight
    assert "standby electronics" in insight
