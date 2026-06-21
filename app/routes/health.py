"""Health route — reports status of all integrated services."""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, Response
from app import gemini_service, action_repo

health_bp: Blueprint = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check() -> Response:
    from app.services.cloud_logging import is_active as cl_active
    from app.utils.secret_manager import is_active as sm_active
    from app.routes.translate import is_active as tr_active

    def status(active: bool, fallback_label: str = "fallback active") -> str:
        return "connected" if active else f"degraded ({fallback_label})"

    firestore_active = action_repo.is_active() if hasattr(action_repo, "is_active") else False

    return jsonify({
        "status": "healthy",
        "services": {
            "gemini": status(not gemini_service.is_degraded(), "rule-based fallback active"),
            "firestore": status(firestore_active, "in-memory fallback active"),
            "cloud_logging": status(cl_active(), "stdlib fallback active"),
            "secret_manager": status(sm_active(), "env fallback active"),
            "translation": status(tr_active(), "service unavailable"),
        },
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }), 200
