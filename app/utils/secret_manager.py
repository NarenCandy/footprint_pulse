"""Secret Manager utility with os.environ fallback.

Attempts to read secrets from Google Cloud Secret Manager. Falls back to
os.environ if Secret Manager is unavailable or the secret does not exist.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)
_sm_client: Any | None = None
_sm_active: bool = False


def _get_client() -> Any | None:
    """Lazily initialises and returns the Secret Manager client.

    Returns:
        The SecretManagerServiceClient instance, or None if unavailable.
    """
    global _sm_client, _sm_active
    if _sm_client is not None:
        return _sm_client
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        return None
    try:
        from google.cloud import secretmanager  # type: ignore[import-untyped]

        _sm_client = secretmanager.SecretManagerServiceClient()
        _sm_active = True
        logger.info("Secret Manager client initialised.")
    except Exception as exc:
        logger.warning("Secret Manager init failed (%s) — using env fallback.", exc)
    return _sm_client


def is_active() -> bool:
    """Returns True if Secret Manager is connected and active.

    Returns:
        True when Secret Manager is reachable, False when env fallback only.
    """
    _get_client()
    return _sm_active


def get_secret(name: str, default: str | None = None) -> str | None:
    """Fetches a secret value from Secret Manager with os.environ fallback.

    Tries Secret Manager first (latest version), then falls back to
    ``os.environ.get(name, default)`` if the client is unavailable or the
    secret access fails.

    Args:
        name: Secret name (also used as the environment variable key).
        default: Value to return when neither Secret Manager nor env has the key.

    Returns:
        The secret value string, or ``default`` if not found.
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    client = _get_client()
    if client is not None and project:
        try:
            secret_path = f"projects/{project}/secrets/{name}/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            value: str = response.payload.data.decode("utf-8")
            return value
        except Exception as exc:
            logger.debug(
                "Secret Manager read failed for '%s' (%s) — env fallback.", name, exc
            )
    return os.environ.get(name, default)
