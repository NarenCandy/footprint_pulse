"""Actions route blueprint module.

This module exposes the POST /api/actions endpoint for logging new carbon
actions with rate limiting and server-side validation, and GET /api/actions
for retrieving the action log.
"""

import uuid
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request

from app import action_repo
from app.models.action import Action
from app.services.carbon_calculator import CarbonCalculator
from app.services.cloud_logging import log_event
from app.services.nudge_engine import NudgeEngine
from app.utils.security import limiter
from app.utils.validators import validate_action_payload

actions_bp: Blueprint = Blueprint("actions", __name__)


def _build_action(
    category: str, action_type: str, amount: float, unit: str
) -> Action:
    """Constructs a fully populated Action from validated request fields.

    Calculates CO2 emissions and generates a comparison nudge.

    Args:
        category: Validated action category (transport, food, energy).
        action_type: Validated action type (e.g. car, veg, ac).
        amount: Validated numeric amount.
        unit: Validated unit string.

    Returns:
        A new Action instance ready to be persisted.

    Raises:
        ValueError: If the category/type combination is not in the emission table.
    """
    co2_kg = CarbonCalculator.calculate_co2(category, action_type, amount)
    nudge = NudgeEngine.generate_nudge(category, action_type, co2_kg)
    return Action(
        id=uuid.uuid4().hex,
        category=category,
        type=action_type,
        amount=amount,
        unit=unit,
        co2_kg=co2_kg,
        nudge=nudge,
        timestamp=datetime.now(timezone.utc),
    )


@actions_bp.route("/api/actions", methods=["POST"])
@limiter.limit("30/minute")
def log_action() -> Response:
    """Logs a new carbon-producing or carbon-saving action.

    Validates the input payload, calculates CO2, generates a relatable
    comparison nudge, persists the action, and invalidates the weekly
    insight cache.

    Returns:
        A Flask Response containing the logged action as JSON (HTTP 201), or
        an error response (HTTP 400).
    """
    if request.content_length and request.content_length > 10 * 1024:
        return jsonify({"error": "Payload size exceeds limit of 10KB."}), 400  # type: ignore[return-value]

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON payload."}), 400  # type: ignore[return-value]

    is_valid, error_msg = validate_action_payload(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400  # type: ignore[return-value]

    try:
        action = _build_action(
            category=data["category"],
            action_type=data["type"],
            amount=float(data["amount"]),
            unit=data["unit"],
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400  # type: ignore[return-value]

    action_repo.add(action)
    log_event("INFO", "action_logged", category=action.category, co2_kg=action.co2_kg)

    from app.routes.insights import invalidate_insight_cache

    invalidate_insight_cache()

    return jsonify(action.to_dict()), 201  # type: ignore[return-value]


@actions_bp.route("/api/actions", methods=["GET"])
def get_actions() -> Response:
    """Retrieves all logged actions in reverse chronological order.

    Returns:
        A Flask Response containing the list of logged actions as JSON.
    """
    actions = action_repo.get_all()
    return jsonify([action.to_dict() for action in actions]), 200  # type: ignore[return-value]


@actions_bp.route("/api/actions/clear", methods=["POST"])
def clear_actions() -> Response:
    """Clears all logged actions and invalidates the weekly insight cache.

    Returns:
        A Flask Response confirming successful clearance.
    """
    action_repo.clear()
    from app.routes.insights import invalidate_insight_cache

    invalidate_insight_cache()
    return jsonify({"status": "success", "message": "Action history cleared."}), 200  # type: ignore[return-value]
