"""Configuration module for the Footprint Pulse application.

This module defines environment-specific configuration classes for Flask,
ensuring security, proper environment variable handling, and testing overrides.
"""

import os


class Config:
    """Base configuration class containing common settings."""

    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "dev_secret_key_change_me_in_production"
    )
    TESTING: bool = False
    DEBUG: bool = False
    GEMINI_API_KEY: str | None = os.environ.get("GEMINI_API_KEY")


class DevelopmentConfig(Config):
    """Configuration class for the development environment."""

    DEBUG: bool = True


class TestingConfig(Config):
    """Configuration class for the testing environment."""

    TESTING: bool = True
    SECRET_KEY: str = "test-secret-key"


class ProductionConfig(Config):
    """Configuration class for the production environment.

    Production-specific settings can go here.
    Talisman and other secure setups will rely on this environment.
    """


config_by_name: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str) -> type[Config]:
    """Retrieves the configuration class based on the environment name.

    Args:
        env_name: The name of the environment (development, testing, production).

    Returns:
        The configuration class matching the environment name.
    """
    return config_by_name.get(env_name.lower(), DevelopmentConfig)
