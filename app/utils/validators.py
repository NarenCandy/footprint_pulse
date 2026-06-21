"""Input validation and sanitisation module for the Footprint Pulse application.

This module provides functions to validate action logging payloads, checking
for missing fields, data types, value ranges, script injections, and payload
sizing.
"""

import re
from typing import Any

from app.services.carbon_calculator import CarbonCalculator

# Regex to detect common injection patterns (HTML tags, JS event handlers).
INJECTION_PATTERN = re.compile(
    r"(<[^>]+>|javascript:|onload\s*=|onerror\s*=|script\b)", re.IGNORECASE
)


def validate_action_payload(data: Any) -> tuple[bool, str | None]:
    """Validates the action logging payload against all business rules.

    Args:
        data: The deserialised JSON payload from the request.

    Returns:
        A tuple of ``(is_valid, error_message)``. ``error_message`` is None
        when ``is_valid`` is True.
    """
    if not isinstance(data, dict):
        return False, "Request payload must be a JSON object."

    error = _check_required_fields(data)
    if error:
        return False, error

    category: str = data["category"]
    action_type: str = data["type"]
    amount: Any = data["amount"]
    unit: str = data["unit"]

    error = _check_field_types(category, action_type, amount, unit)
    if error:
        return False, error

    error = _check_string_lengths(category, action_type, unit)
    if error:
        return False, error

    error = _check_injection(category, action_type, unit)
    if error:
        return False, error

    error = _check_valid_category_and_type(category, action_type)
    if error:
        return False, error

    error = _check_amount_range(category, action_type, float(amount))
    if error:
        return False, error

    return True, None


# ── Private helpers ────────────────────────────────────────────────────────────

def _check_required_fields(data: dict[str, Any]) -> str | None:
    """Returns an error message if any required field is absent.

    Args:
        data: The payload dictionary.

    Returns:
        An error string, or None if all fields are present.
    """
    for field in ("category", "type", "amount", "unit"):
        if field not in data:
            return f"Missing required field: '{field}'."
    return None


def _check_field_types(
    category: Any, action_type: Any, amount: Any, unit: Any
) -> str | None:
    """Returns an error message if any field has the wrong type.

    Args:
        category: Raw category value.
        action_type: Raw type value.
        amount: Raw amount value.
        unit: Raw unit value.

    Returns:
        An error string, or None if all types are correct.
    """
    if not isinstance(category, str):
        return "Field 'category' must be a string."
    if not isinstance(action_type, str):
        return "Field 'type' must be a string."
    if not isinstance(amount, int | float):
        return "Field 'amount' must be a number."
    if not isinstance(unit, str):
        return "Field 'unit' must be a string."
    return None


def _check_string_lengths(
    category: str, action_type: str, unit: str
) -> str | None:
    """Returns an error message if any string field exceeds its length limit.

    Args:
        category: Category string value.
        action_type: Type string value.
        unit: Unit string value.

    Returns:
        An error string, or None if all lengths are acceptable.
    """
    if len(category) > 50:
        return "Field 'category' is too long (max 50 chars)."
    if len(action_type) > 50:
        return "Field 'type' is too long (max 50 chars)."
    if len(unit) > 50:
        return "Field 'unit' is too long (max 50 chars)."
    return None


def _check_injection(
    category: str, action_type: str, unit: str
) -> str | None:
    """Returns an error message if any string field contains injection patterns.

    Args:
        category: Category string value.
        action_type: Type string value.
        unit: Unit string value.

    Returns:
        An error string, or None if no injection patterns are detected.
    """
    if (
        INJECTION_PATTERN.search(category)
        or INJECTION_PATTERN.search(action_type)
        or INJECTION_PATTERN.search(unit)
    ):
        return "Injection-style characters detected in input fields."
    return None


def _check_valid_category_and_type(
    category: str, action_type: str
) -> str | None:
    """Returns an error message if category or type is not in the emission table.

    Args:
        category: Category string value.
        action_type: Type string value.

    Returns:
        An error string, or None if both are valid.
    """
    cat_lower = category.lower()
    if cat_lower not in CarbonCalculator.EMISSION_FACTORS:
        valid = list(CarbonCalculator.EMISSION_FACTORS.keys())
        return f"Invalid category: '{category}'. Must be one of: {valid}."
    valid_types = CarbonCalculator.EMISSION_FACTORS[cat_lower]
    if action_type.lower() not in valid_types:
        return f"Invalid action type: '{action_type}' for category '{category}'."
    return None


def _check_amount_range(
    category: str, action_type: str, amount: float
) -> str | None:
    """Returns an error message if the amount is outside permitted boundaries.

    Args:
        category: Lowercased category string value.
        action_type: Lowercased action type string value.
        amount: Numeric amount to validate.

    Returns:
        An error string, or None if the amount is within bounds.
    """
    if amount < 0.0:
        return "Field 'amount' cannot be negative."

    cat_lower = category.lower()
    type_lower = action_type.lower()

    if cat_lower == "transport":
        if type_lower == "flight" and amount > 24.0:
            return "Flight duration cannot exceed 24 hours in a single log."
        if type_lower != "flight" and amount > 5000.0:
            return (
                f"Transport distance for '{action_type}' cannot exceed "
                "5000 km in a single log."
            )
    elif cat_lower == "food":
        if amount > 10.0:
            return "Food meal count cannot exceed 10 in a single log."
    elif cat_lower == "energy":
        if amount > 24.0:
            return (
                f"Energy duration for '{action_type}' cannot exceed "
                "24 hours in a single log."
            )
    return None
