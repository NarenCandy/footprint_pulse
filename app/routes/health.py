"""Health route — reports operational status of all integrated services."""

from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify

from app import action_repo, gemini_service

health_bp: Blueprint = Blueprint("health", __name__)


def _service_status(active: bool, fallback_label: str = "fallback active") -> str:
    """Returns a human-readable service status string.

    Args:
        active: True if the service is connected and operational.
        fallback_label: Description appended when the service is degraded.

    Returns:
        ``"connected"`` or ``"degraded (<fallback_label>)"``.
    """
    return "connected" if active else f"degraded ({fallback_label})"


@health_bp.route("/health", methods=["GET"])
def health_check() -> Response:
    """Returns the health status of the application and all integrated services.

    Returns:
        A Flask Response containing a JSON payload with per-service statuses
        and a UTC timestamp.
    """
    from app.routes.translate import is_active as tr_active
    from app.services.cloud_logging import is_active as cl_active
    from app.utils.secret_manager import is_active as sm_active

    firestore_active: bool = (
        action_repo.is_active() if hasattr(action_repo, "is_active") else False
    )

    return jsonify(  # type: ignore[return-value]
        {
            "status": "healthy",
            "services": {
                "gemini": _service_status(
                    not gemini_service.is_degraded(), "rule-based fallback active"
                ),
                "firestore": _service_status(
                    firestore_active, "in-memory fallback active"
                ),
                "cloud_logging": _service_status(
                    cl_active(), "stdlib fallback active"
                ),
                "secret_manager": _service_status(
                    sm_active(), "env fallback active"
                ),
                "translation": _service_status(
                    tr_active(), "service unavailable"
                ),
            },
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    ), 200
