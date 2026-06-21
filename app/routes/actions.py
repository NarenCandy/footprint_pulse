"""Actions route blueprint module.

This module exposes the POST /api/actions endpoint for logging new carbon actions
with rate limiting and server-side validation, and GET /api/actions for retrieving
action logs.
"""

from datetime import datetime, timezone
import uuid
from flask import Blueprint, jsonify, request, Response

# Import shared resources
from app import action_repo
from app.models.action import Action
from app.services.carbon_calculator import CarbonCalculator
from app.services.nudge_engine import NudgeEngine
from app.services.cloud_logging import log_event
from app.utils.security import limiter
from app.utils.validators import validate_action_payload

actions_bp: Blueprint = Blueprint("actions", __name__)


@actions_bp.route("/api/actions", methods=["POST"])
@limiter.limit("30/minute")
def log_action() -> Response:
    """Logs a new carbon-producing or carbon-saving action.

    Validates input parameters, calculates CO2, generates a relatable
    comparison nudge, stores the action, and invalidates the weekly insight cache.

    Returns:
        A Flask Response containing the logged action as JSON, or an error.
    """
    # 1. Enforce payload size limit (max 10KB to prevent oversized body attacks)
    if request.content_length and request.content_length > 10 * 1024:
        return jsonify({"error": "Payload size exceeds limit of 10KB."}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON payload."}), 400

    # 2. Server-side validation
    is_valid, error_msg = validate_action_payload(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    category = data["category"]
    action_type = data["type"]
    amount = float(data["amount"])
    unit = data["unit"]

    # 3. Calculate CO2 emissions
    try:
        co2_kg = CarbonCalculator.calculate_co2(category, action_type, amount)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # 4. Generate comparison nudge
    nudge = NudgeEngine.generate_nudge(category, action_type, co2_kg)

    # 5. Create and save Action model
    action = Action(
        id=uuid.uuid4().hex,
        category=category,
        type=action_type,
        amount=amount,
        unit=unit,
        co2_kg=co2_kg,
        nudge=nudge,
        timestamp=datetime.now(timezone.utc),
    )

    action_repo.add(action)
    log_event("INFO", "action_logged", category=category, co2_kg=co2_kg)

    # 6. Invalidate weekly insight cache
    from app.routes.insights import invalidate_insight_cache
    invalidate_insight_cache()

    return jsonify(action.to_dict()), 201


@actions_bp.route("/api/actions", methods=["GET"])
def get_actions() -> Response:
    """Retrieves all logged actions in reverse chronological order.

    Returns:
        A Flask Response containing the list of logged actions as JSON.
    """
    actions = action_repo.get_all()
    return jsonify([action.to_dict() for action in actions]), 200


@actions_bp.route("/api/actions/clear", methods=["POST"])
def clear_actions() -> Response:
    """Clears all logged actions in the repository and invalidates weekly insights.

    Returns:
        A Flask Response confirming successful clearance.
    """
    action_repo.clear()
    from app.routes.insights import invalidate_insight_cache
    invalidate_insight_cache()
    return jsonify({"status": "success", "message": "Action history cleared."}), 200

