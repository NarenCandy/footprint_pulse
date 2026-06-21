"""Unit tests for the input validation utility.

This module tests that requests are validated properly server-side, verifying
schema formats, data types, boundaries, injection prevention, and payload sizes.
"""

from app.utils.validators import validate_action_payload


def test_validator_happy_path() -> None:
    """Verifies that a valid action logging payload passes validation."""
    data = {
        "category": "transport",
        "type": "car",
        "amount": 15.0,
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is True
    assert error is None


def test_validator_not_a_dict() -> None:
    """Verifies that a non-dictionary input is rejected."""
    is_valid, error = validate_action_payload("not-a-dict")
    assert is_valid is False
    assert "JSON object" in error


def test_validator_missing_fields() -> None:
    """Verifies that missing fields in the payload are caught."""
    base_data = {
        "category": "transport",
        "type": "car",
        "amount": 15.0,
    }
    is_valid, error = validate_action_payload(base_data)
    assert is_valid is False
    assert "Missing required field" in error
    assert "unit" in error


def test_validator_wrong_types_amount() -> None:
    """Verifies that incorrect data type for amount is rejected."""
    data = {
        "category": "transport",
        "type": "car",
        "amount": "fifteen",
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "must be a number" in error


def test_validator_wrong_types_strings() -> None:
    """Verifies that incorrect data type for category is rejected."""
    data = {
        "category": 123,
        "type": "car",
        "amount": 15.0,
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "must be a string" in error


def test_validator_oversized_string() -> None:
    """Verifies that string inputs exceeding maximum length are rejected."""
    data = {
        "category": "transport",
        "type": "car" * 30, # exceeds 50 chars
        "amount": 15.0,
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "too long" in error


def test_validator_negative_amount() -> None:
    """Verifies that negative action amounts are rejected."""
    data = {
        "category": "transport",
        "type": "car",
        "amount": -5.0,
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "cannot be negative" in error


def test_validator_invalid_category() -> None:
    """Verifies that incorrect categories are rejected."""
    data = {
        "category": "space-travel",
        "type": "rocket",
        "amount": 100.0,
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "Invalid category" in error


def test_validator_invalid_type() -> None:
    """Verifies that incorrect action types under a valid category are rejected."""
    data = {
        "category": "transport",
        "type": "submarine",
        "amount": 10.0,
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "Invalid action type" in error


def test_validator_script_injection_html() -> None:
    """Verifies that HTML tags or script injection payloads are blocked."""
    data = {
        "category": "transport",
        "type": "<script>alert('xss')</script>",
        "amount": 15.0,
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "Injection-style characters detected" in error


def test_validator_script_injection_onload() -> None:
    """Verifies that event handlers are blocked in inputs."""
    data = {
        "category": "transport",
        "type": "car",
        "amount": 15.0,
        "unit": "km' onload='injected()"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "Injection-style characters detected" in error


def test_validator_out_of_range_flight() -> None:
    """Verifies that oversized flight durations are rejected."""
    data = {
        "category": "transport",
        "type": "flight",
        "amount": 25.0, # flight max is 24 hours
        "unit": "hours"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "Flight duration cannot exceed" in error


def test_validator_out_of_range_car() -> None:
    """Verifies that oversized car distances are rejected."""
    data = {
        "category": "transport",
        "type": "car",
        "amount": 6000.0, # car max is 5000 km
        "unit": "km"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "cannot exceed 5000 km" in error


def test_validator_out_of_range_food() -> None:
    """Verifies that oversized food meal quantities are rejected."""
    data = {
        "category": "food",
        "type": "veg",
        "amount": 12.0, # food max is 10 meals
        "unit": "meals"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "meal count cannot exceed 10" in error


def test_validator_out_of_range_energy() -> None:
    """Verifies that oversized AC usage duration is rejected."""
    data = {
        "category": "energy",
        "type": "ac",
        "amount": 30.0, # energy max is 24 hours
        "unit": "hours"
    }
    is_valid, error = validate_action_payload(data)
    assert is_valid is False
    assert "duration for 'ac' cannot exceed 24 hours" in error
