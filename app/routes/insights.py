"""Insights route blueprint module.

This module exposes the GET /api/insights endpoint for retrieving weekly personalized
carbon-reduction advice. It implements in-memory caching of the generated insight
to optimize API calls and response speed.
"""

import threading
from typing import Dict, Tuple
from flask import Blueprint, jsonify, Response

# Import shared resources
from app import action_repo, gemini_service

insights_bp: Blueprint = Blueprint("insights", __name__)

# Thread-safe in-memory cache variables
_cache_lock: threading.Lock = threading.Lock()
_cached_insight: str | None = None
_cached_fallback_active: bool = False


def invalidate_insight_cache() -> None:
    """Invalidates the in-memory weekly insight cache.

    Should be called whenever a new carbon action is logged, ensuring that
    subsequent requests recalculate personalized advice based on the updated data.
    """
    global _cached_insight, _cached_fallback_active
    with _cache_lock:
        _cached_insight = None
        _cached_fallback_active = False


@insights_bp.route("/api/insights", methods=["GET"])
def get_weekly_insight() -> Response:
    """Retrieves the weekly personalized carbon footprint reduction insight.

    Checks the thread-safe in-memory cache first. If empty, it queries the Gemini
    service (or fallback engine) to generate recommendations, updates the cache,
    and returns the result.

    Returns:
        A Flask Response containing the carbon insight and source description.
    """
    global _cached_insight, _cached_fallback_active

    # Check cache
    with _cache_lock:
        if _cached_insight is not None:
            source = "rule-based fallback" if _cached_fallback_active else "gemini"
            return jsonify({"insight": _cached_insight, "source": source}), 200

    # Fetch actions and generate insight
    actions = action_repo.get_all()
    insight_text, fallback_active = gemini_service.generate_weekly_insight(actions)

    # Populate cache
    with _cache_lock:
        _cached_insight = insight_text
        _cached_fallback_active = fallback_active
        source = "rule-based fallback" if fallback_active else "gemini"

    return jsonify({"insight": insight_text, "source": source}), 200
