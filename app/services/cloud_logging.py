"""Structured Cloud Logging with stdlib fallback.

Attempts to initialize google-cloud-logging. Falls back to the standard
Python logging module if the SDK is missing or credentials are unavailable.
"""

import logging
import os

logger = logging.getLogger(__name__)
_cloud_logger = None
_cloud_active = False


def init_cloud_logging() -> bool:
    """Try to initialize Google Cloud Logging. Returns True if successful."""
    global _cloud_logger, _cloud_active
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        logger.info("Cloud Logging: no project env var — using stdlib fallback.")
        return False
    try:
        import google.cloud.logging as gcl  # type: ignore
        client = gcl.Client(project=project)
        client.setup_logging()
        _cloud_logger = client.logger("footprint_pulse")
        _cloud_active = True
        logger.info("Google Cloud Logging initialized.")
        return True
    except Exception as e:
        logger.warning("Cloud Logging init failed (%s) — using stdlib fallback.", e)
        return False


def is_active() -> bool:
    return _cloud_active


def log_event(severity: str, message: str, **labels) -> None:
    """Emit a structured log. Falls back to stdlib if Cloud Logging unavailable."""
    if _cloud_active and _cloud_logger:
        try:
            _cloud_logger.log_struct({"message": message, **labels}, severity=severity)
            return
        except Exception as e:
            logger.warning("Cloud Logging write failed (%s) — falling back.", e)
    # stdlib fallback
    lvl = getattr(logging, severity.upper(), logging.INFO)
    logger.log(lvl, message, extra=labels)
