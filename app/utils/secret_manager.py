"""Secret Manager utility with os.environ fallback.

Attempts to read secrets from Google Cloud Secret Manager. Falls back to
os.environ if Secret Manager is unavailable or the secret doesn't exist.
"""

import logging
import os

logger = logging.getLogger(__name__)
_sm_client = None
_sm_active = False


def _get_client():
    global _sm_client, _sm_active
    if _sm_client is not None:
        return _sm_client
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        return None
    try:
        from google.cloud import secretmanager  # type: ignore
        _sm_client = secretmanager.SecretManagerServiceClient()
        _sm_active = True
        logger.info("Secret Manager client initialized.")
    except Exception as e:
        logger.warning("Secret Manager init failed (%s) — using env fallback.", e)
    return _sm_client


def is_active() -> bool:
    _get_client()
    return _sm_active


def get_secret(name: str, default: str | None = None) -> str | None:
    """Fetch secret from Secret Manager, falling back to os.environ then default."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    client = _get_client()
    if client and project:
        try:
            secret_path = f"projects/{project}/secrets/{name}/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("utf-8")
        except Exception as e:
            logger.debug("Secret Manager read failed for '%s' (%s) — env fallback.", name, e)
    # os.environ fallback
    return os.environ.get(name, default)
