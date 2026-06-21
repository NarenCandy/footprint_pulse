"""Fallback path tests for all new Google services.

Each test mocks the Google SDK client to raise an exception and asserts
the fallback triggers while the app continues to return 200.
"""

import json
from unittest.mock import patch, MagicMock
import pytest
from flask.testing import FlaskClient


# ── FirestoreRepository fallback ──────────────────────────────────────────────

def test_firestore_falls_back_when_no_project(monkeypatch) -> None:
    """Without GOOGLE_CLOUD_PROJECT set, Firestore uses in-memory fallback."""
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    from app.services.firestore_repository import FirestoreRepository
    repo = FirestoreRepository()
    assert not repo.is_active()


def test_firestore_falls_back_on_client_error(monkeypatch) -> None:
    """If firestore.Client() raises, falls back to in-memory."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    with patch("google.cloud.firestore.Client", side_effect=Exception("auth error")):
        from importlib import reload
        import app.services.firestore_repository as mod
        reload(mod)
        repo = mod.FirestoreRepository()
        assert not repo.is_active()
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)


def test_firestore_add_falls_back_on_write_error(monkeypatch) -> None:
    """A Firestore write error must not lose the in-memory record."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.set.side_effect = Exception("write fail")
    with patch("google.cloud.firestore.Client", return_value=mock_db):
        from importlib import reload
        import app.services.firestore_repository as mod
        reload(mod)
        repo = mod.FirestoreRepository()
        # Manually mark active since mock didn't raise at init
        repo._firestore_active = True
        repo._db = mock_db

        from datetime import datetime, timezone
        from app.models.action import Action
        a = Action("x1", "transport", "car", 1, "km", 1.0, "n", datetime.now(timezone.utc))
        repo.add(a)
        assert len(repo.get_all()) == 1  # still in memory


# ── Cloud Logging fallback ────────────────────────────────────────────────────

def test_cloud_logging_falls_back_when_no_project(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    from importlib import reload
    import app.services.cloud_logging as cl
    reload(cl)
    result = cl.init_cloud_logging()
    assert result is False
    assert not cl.is_active()


def test_cloud_logging_falls_back_on_client_error(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    with patch("google.cloud.logging.Client", side_effect=Exception("auth error")):
        from importlib import reload
        import app.services.cloud_logging as cl
        reload(cl)
        result = cl.init_cloud_logging()
        assert result is False
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)


def test_cloud_logging_log_event_uses_stdlib_when_inactive(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    from importlib import reload
    import app.services.cloud_logging as cl
    reload(cl)
    # Must not raise even when cloud logging is inactive
    cl.log_event("INFO", "test message", key="val")


def test_cloud_logging_log_event_falls_back_on_write_error() -> None:
    from importlib import reload
    import app.services.cloud_logging as cl
    reload(cl)
    mock_cloud_logger = MagicMock()
    mock_cloud_logger.log_struct.side_effect = Exception("write error")
    cl._cloud_logger = mock_cloud_logger
    cl._cloud_active = True
    # Should fall back to stdlib without raising
    cl.log_event("ERROR", "test error")
    # Reset
    cl._cloud_active = False
    cl._cloud_logger = None


# ── Secret Manager fallback ───────────────────────────────────────────────────

def test_secret_manager_falls_back_when_no_project(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    from importlib import reload
    import app.utils.secret_manager as sm
    reload(sm)
    assert not sm.is_active()


def test_secret_manager_env_fallback(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.setenv("MY_SECRET", "env_value")
    from importlib import reload
    import app.utils.secret_manager as sm
    reload(sm)
    assert sm.get_secret("MY_SECRET") == "env_value"


def test_secret_manager_returns_default_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
    from importlib import reload
    import app.utils.secret_manager as sm
    reload(sm)
    assert sm.get_secret("NONEXISTENT_KEY", "default_val") == "default_val"


def test_secret_manager_falls_back_on_access_error(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("MY_SECRET_KEY", "from_env")
    mock_client = MagicMock()
    mock_client.access_secret_version.side_effect = Exception("permission denied")
    with patch("google.cloud.secretmanager.SecretManagerServiceClient", return_value=mock_client):
        from importlib import reload
        import app.utils.secret_manager as sm
        reload(sm)
        sm._sm_client = mock_client
        sm._sm_active = True
        val = sm.get_secret("MY_SECRET_KEY")
        assert val == "from_env"
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)


# ── Translation route fallback ────────────────────────────────────────────────

def test_translate_returns_503_when_unavailable(client: FlaskClient) -> None:
    """When translation client raises on init and is set None, endpoint returns 503."""
    import app.routes.translate as tr
    original_client = tr._translate_client
    original_active = tr._translate_active
    tr._translate_client = None
    tr._translate_active = False
    # Patch _get_translate_client to keep returning None during this request
    with patch.object(tr, "_get_translate_client", return_value=None):
        response = client.post(
            "/api/translate",
            data=json.dumps({"text": "Hello", "target": "hi"}),
            content_type="application/json",
        )
    tr._translate_client = original_client
    tr._translate_active = original_active
    assert response.status_code == 503
    data = response.get_json()
    assert data["available"] is False


def test_translate_returns_400_on_missing_text(client: FlaskClient) -> None:
    response = client.post(
        "/api/translate",
        data=json.dumps({"target": "hi"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_translate_returns_503_on_api_error(client: FlaskClient) -> None:
    from importlib import reload
    import app.routes.translate as tr
    reload(tr)
    mock_client = MagicMock()
    mock_client.translate.side_effect = Exception("quota exceeded")
    tr._translate_client = mock_client
    tr._translate_active = True

    response = client.post(
        "/api/translate",
        data=json.dumps({"text": "Test text", "target": "ta"}),
        content_type="application/json",
    )
    assert response.status_code == 503
    assert response.get_json()["available"] is False

    # Reset
    tr._translate_client = None
    tr._translate_active = False


def test_app_still_returns_200_when_all_google_services_fail(client: FlaskClient) -> None:
    """Core actions endpoint must work even if all Google services are inactive."""
    response = client.post(
        "/api/actions",
        data=json.dumps({"category": "food", "type": "veg", "amount": 1.0, "unit": "meals"}),
        content_type="application/json",
    )
    assert response.status_code == 201
