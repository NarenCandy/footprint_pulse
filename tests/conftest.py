"""Configuration and fixtures for pytest.

This module provides common fixtures such as the Flask test client,
a clean repository context, and mock environments.
"""

from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, action_repo


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Provides a Flask application instance configured for testing.

    Yields:
        A Flask app instance with TESTING = True.
    """
    # Create the app in testing mode
    app_instance = create_app("testing")
    yield app_instance


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Provides a test client for the Flask application.

    Args:
        app: The Flask app fixture.

    Returns:
        A Flask test client.
    """
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_repo() -> Generator[None, None, None]:
    """Ensures the ActionRepository is cleared before and after each test.

    Yields:
        None.
    """
    action_repo.clear()
    yield
    action_repo.clear()
