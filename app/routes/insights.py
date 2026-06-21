"""Insights route blueprint module.

This module exposes the GET /api/insights endpoint for retrieving weekly
personalised carbon-reduction advice. It implements thread-safe in-memory
caching of the generated insight to optimise API calls and response speed.
"""

import threading

from flask import Blueprint, Response, jsonify

from app import action_repo, gemini_service

insights_bp: Blueprint = Blueprint("insights", __name__)

# Thread-safe in-memory cache variables
_cache_lock: threading.Lock = threading.Lock()
_cached_insight: str | None = None
_cached_fallback_active: bool = False


def invalidate_insight_cache() -> None:
    """Invalidates the in-memory weekly insight cache.

    Should be called whenever a new carbon action is logged so that
    subsequent requests regenerate advice from the updated action data.
    """
    global _cached_insight, _cached_fallback_active
    with _cache_lock:
        _cached_insight = None
        _cached_fallback_active = False


@insights_bp.route("/api/insights", methods=["GET"])
def get_weekly_insight() -> Response:
    """Retrieves the weekly personalised carbon footprint reduction insight.

    Checks the thread-safe in-memory cache first. If the cache is empty it
    queries the Gemini service (or the rule-based fallback), populates the
    cache, and returns the result.

    Returns:
        A Flask Response containing the carbon insight text and its source.
    """
    global _cached_insight, _cached_fallback_active

    with _cache_lock:
        if _cached_insight is not None:
            source = "rule-based fallback" if _cached_fallback_active else "gemini"
            return jsonify({"insight": _cached_insight, "source": source}), 200  # type: ignore[return-value]

    actions = action_repo.get_all()
    insight_text, fallback_active = gemini_service.generate_weekly_insight(actions)

    with _cache_lock:
        _cached_insight = insight_text
        _cached_fallback_active = fallback_active
        source = "rule-based fallback" if fallback_active else "gemini"

    return jsonify({"insight": insight_text, "source": source}), 200  # type: ignore[return-value]
