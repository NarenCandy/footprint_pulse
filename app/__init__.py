"""Flask application factory module."""

import logging
import os
from flask import Flask, render_template
from config import get_config
from app.services.firestore_repository import FirestoreRepository
from app.services.gemini_service import GeminiService
from app.utils.security import init_security

# Shared instances
action_repo: FirestoreRepository = FirestoreRepository()
gemini_service: GeminiService = GeminiService()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    if not config_name:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_cls = get_config(config_name)
    app.config.from_object(config_cls)

    logger.info("Initializing app in '%s' environment", config_name)

    init_security(app)

    # Initialize Cloud Logging (best-effort)
    from app.services.cloud_logging import init_cloud_logging
    init_cloud_logging()

    global gemini_service
    gemini_service = GeminiService()

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    from app.routes.actions import actions_bp
    from app.routes.health import health_bp
    from app.routes.insights import insights_bp
    from app.routes.translate import translate_bp

    app.register_blueprint(actions_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(translate_bp)

    return app
