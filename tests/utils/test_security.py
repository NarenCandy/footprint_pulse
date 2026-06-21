"""Unit tests verifying security header policies and rate limiter configuration.

This module asserts the injection of Content-Security-Policy, HSTS, X-Frame-Options,
and verification that Flask-Limiter is enabled during execution.
"""

from flask import Flask
from flask.testing import FlaskClient


def test_security_headers_present_on_get(client: FlaskClient) -> None:
    """Verifies that mandatory security headers are set on standard GET requests."""
    response = client.get("/")
    assert response.status_code == 200

    headers = response.headers
    assert "Strict-Transport-Security" in headers
    assert "X-Frame-Options" in headers
    assert headers["X-Frame-Options"] == "DENY"
    
    assert "X-Content-Type-Options" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"

    assert "Referrer-Policy" in headers
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_security_headers_present_on_post(client: FlaskClient) -> None:
    """Verifies that mandatory security headers are set on API POST requests."""
    response = client.post("/api/actions", data="invalid")
    headers = response.headers

    assert "Strict-Transport-Security" in headers
    assert "X-Frame-Options" in headers
    assert headers["X-Frame-Options"] == "DENY"
    assert "X-Content-Type-Options" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in headers


def test_rate_limiter_registered() -> None:
    """Verifies that Flask-Limiter is registered with the application.

    We create a development app instance to check the extension exists,
    as rate limiting is deactivated in testing mode.
    """
    from app import create_app
    from app.utils.security import limiter
    limiter.enabled = True
    dev_app = create_app("development")
    assert "limiter" in dev_app.extensions


