"""Translate route exposing POST /api/translate.

Uses google-cloud-translate to translate insight text. If the SDK is
unavailable or the API call fails, returns a 503 with a clear message
so the frontend can hide/disable the button gracefully.
"""

import logging
import os
from flask import Blueprint, jsonify, request, Response

logger = logging.getLogger(__name__)
translate_bp: Blueprint = Blueprint("translate", __name__)

_translate_client = None
_translate_active = False


def _get_translate_client():
    global _translate_client, _translate_active
    if _translate_client is not None:
        return _translate_client
    try:
        from google.cloud import translate_v2 as translate  # type: ignore
        _translate_client = translate.Client()
        _translate_active = True
        logger.info("Cloud Translation client initialized.")
    except Exception as e:
        logger.warning("Cloud Translation init failed (%s).", e)
    return _translate_client


def is_active() -> bool:
    _get_translate_client()
    return _translate_active


@translate_bp.route("/api/translate", methods=["POST"])
def translate_insight() -> Response:
    """Translate insight text via Cloud Translation API.

    Body JSON: {"text": "...", "target": "hi"}   (target defaults to "hi")
    Returns: {"translated": "..."} or {"error": "...", "available": false}
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    target = data.get("target", "hi")

    if not text:
        return jsonify({"error": "No text provided."}), 400

    client = _get_translate_client()
    if not client:
        return jsonify({"error": "Translation service unavailable.", "available": False}), 503

    try:
        result = client.translate(text, target_language=target)
        return jsonify({"translated": result["translatedText"]}), 200
    except Exception as e:
        logger.error("Translation API error: %s", e)
        return jsonify({"error": "Translation failed.", "available": False}), 503
