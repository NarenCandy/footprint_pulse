"""Structured Cloud Logging with stdlib fallback.

Attempts to initialise google-cloud-logging. Falls back to the standard
Python logging module if the SDK is missing or credentials are unavailable.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)
_cloud_logger: Any = None
_cloud_active: bool = False


def init_cloud_logging() -> bool:
    """Attempts to initialise Google Cloud Logging.

    Attaches the Cloud Logging handler to the root logger on success.
    Sets the module-level ``_cloud_active`` flag accordingly.

    Returns:
        True if Cloud Logging was initialised successfully, False otherwise.
    """
    global _cloud_logger, _cloud_active
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        logger.info("Cloud Logging: no project env var — using stdlib fallback.")
        return False
    try:
        import google.cloud.logging as gcl  # type: ignore[import-untyped]

        client = gcl.Client(project=project)
        client.setup_logging()
        _cloud_logger = client.logger("footprint_pulse")
        _cloud_active = True
        logger.info("Google Cloud Logging initialised.")
        return True
    except Exception as exc:
        logger.warning("Cloud Logging init failed (%s) — using stdlib fallback.", exc)
        return False


def is_active() -> bool:
    """Returns True if Cloud Logging is connected and active.

    Returns:
        True when Cloud Logging writes are active, False when stdlib only.
    """
    return _cloud_active


def log_event(severity: str, message: str, **labels: Any) -> None:
    """Emits a structured log event.

    Uses Cloud Logging when available; falls back to the stdlib logger
    transparently if the cloud client is inactive or a write fails.

    Args:
        severity: Log severity string (e.g. 'INFO', 'ERROR').
        message: Human-readable log message.
        **labels: Additional key-value pairs to include in the structured payload.
    """
    if _cloud_active and _cloud_logger is not None:
        try:
            _cloud_logger.log_struct(
                {"message": message, **labels}, severity=severity
            )
            return
        except Exception as exc:
            logger.warning("Cloud Logging write failed (%s) — falling back.", exc)
    lvl = getattr(logging, severity.upper(), logging.INFO)
    logger.log(lvl, message, extra=labels)
