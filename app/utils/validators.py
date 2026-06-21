"""Input validation and sanitization module for the Footprint Pulse application.

This module provides functions to validate action logging payloads, checking for
missing fields, data types, value ranges, script injections, and payload sizing.
"""

import re
from typing import Dict, Any, Tuple
from app.services.carbon_calculator import CarbonCalculator

# Regex to detect common injection patterns (like <script>, HTML tags, or onload handlers)
INJECTION_PATTERN = re.compile(
    r"(<[^>]+>|javascript:|onload\s*=|onerror\s*=|script\b)", re.IGNORECASE
)


def validate_action_payload(data: Any) -> Tuple[bool, str | None]:
    """Validates the action logging payload.

    Args:
        data: The deserialized JSON payload from the request.

    Returns:
        A tuple of (is_valid, error_message). If is_valid is True, error_message is None.
    """
    if not isinstance(data, dict):
        return False, "Request payload must be a JSON object."

    # 1. Check for missing fields
    required_fields = ["category", "type", "amount", "unit"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: '{field}'."

    category = data["category"]
    action_type = data["type"]
    amount = data["amount"]
    unit = data["unit"]

    # 2. Check for correct data types
    if not isinstance(category, str):
        return False, "Field 'category' must be a string."
    if not isinstance(action_type, str):
        return False, "Field 'type' must be a string."
    if not isinstance(amount, (int, float)):
        return False, "Field 'amount' must be a number."
    if not isinstance(unit, str):
        return False, "Field 'unit' must be a string."

    # 3. Check for oversized string values (prevent buffer overflow/denial of service)
    if len(category) > 50:
        return False, "Field 'category' is too long (max 50 chars)."
    if len(action_type) > 50:
        return False, "Field 'type' is too long (max 50 chars)."
    if len(unit) > 50:
        return False, "Field 'unit' is too long (max 50 chars)."

    # 4. Check for injection-style strings
    if INJECTION_PATTERN.search(category) or INJECTION_PATTERN.search(action_type) or INJECTION_PATTERN.search(unit):
        return False, "Injection-style characters detected in input fields."

    # 5. Check valid category and action type boundaries
    cat_lower = category.lower()
    type_lower = action_type.lower()

    if cat_lower not in CarbonCalculator.EMISSION_FACTORS:
        return False, f"Invalid category: '{category}'. Must be one of: {list(CarbonCalculator.EMISSION_FACTORS.keys())}."

    valid_types = CarbonCalculator.EMISSION_FACTORS[cat_lower]
    if type_lower not in valid_types:
        return False, f"Invalid action type: '{action_type}' for category '{category}'."

    # 6. Check out-of-range values
    if amount < 0.0:
        return False, "Field 'amount' cannot be negative."

    # Limit maximum quantities to reasonable boundaries to prevent overflow/abuse
    if cat_lower == "transport":
        if type_lower == "flight" and amount > 24.0:
            return False, "Flight duration cannot exceed 24 hours in a single log."
        if type_lower != "flight" and amount > 5000.0:
            return False, f"Transport distance for '{action_type}' cannot exceed 5000 km in a single log."
    elif cat_lower == "food":
        if amount > 10.0:
            return False, "Food meal count cannot exceed 10 in a single log."
    elif cat_lower == "energy":
        if amount > 24.0:
            return False, f"Energy duration for '{action_type}' cannot exceed 24 hours in a single log."

    return True, None
