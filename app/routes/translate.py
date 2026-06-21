"""Translate route exposing POST /api/translate.

Uses google-cloud-translate to translate insight text. If the SDK is
unavailable or the API call fails, returns a 503 so the frontend can
hide/disable the Translate button gracefully.
"""

import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

logger = logging.getLogger(__name__)
translate_bp: Blueprint = Blueprint("translate", __name__)

_translate_client: Any | None = None
_translate_active: bool = False


def _get_translate_client() -> Any | None:
    """Lazily initialises and returns the Cloud Translation client.

    Returns:
        The translate_v2.Client instance, or None if unavailable.
    """
    global _translate_client, _translate_active
    if _translate_client is not None:
        return _translate_client
    try:
        from google.cloud import (  # type: ignore[import-untyped,attr-defined]
            translate_v2 as translate,
        )

        _translate_client = translate.Client()
        _translate_active = True
        logger.info("Cloud Translation client initialised.")
    except Exception as exc:
        logger.warning("Cloud Translation init failed (%s).", exc)
    return _translate_client


def is_active() -> bool:
    """Returns True if Cloud Translation is connected and active.

    Returns:
        True when translation calls are possible, False otherwise.
    """
    _get_translate_client()
    return _translate_active


@translate_bp.route("/api/translate", methods=["POST"])
def translate_insight() -> Response:
    """Translates insight text via the Cloud Translation API.

    Expects a JSON body with keys:
        - ``text``   (str): The text to translate.
        - ``target`` (str, optional): BCP-47 language code (default ``"hi"``).

    Returns:
        A Flask Response with ``{"translated": "..."}`` on success,
        ``{"error": "...", "available": false}`` with status 503 when the
        service is unavailable, or ``{"error": "..."}`` with status 400 for
        invalid input.
    """
    data = request.get_json(silent=True) or {}
    text: str = data.get("text", "").strip()
    target: str = data.get("target", "hi")

    if not text:
        return jsonify({"error": "No text provided."}), 400  # type: ignore[return-value]

    client = _get_translate_client()
    if not client:
        return jsonify({"error": "Translation service unavailable.", "available": False}), 503  # type: ignore[return-value]

    try:
        result = client.translate(text, target_language=target)
        return jsonify({"translated": result["translatedText"]}), 200  # type: ignore[return-value]
    except Exception as exc:
        logger.error("Translation API error: %s", exc)
        return jsonify({"error": "Translation failed.", "available": False}), 503  # type: ignore[return-value]
