"""Security module for the Footprint Pulse application.

This module configures secure HTTP response headers (CSP, HSTS, X-Frame-Options, etc.)
and sets up rate limiting on mutable endpoints.
"""

from flask import Flask, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize the rate limiter. We'll use local in-memory storage.
limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day"],
    storage_uri="memory://",
)


def init_security(app: Flask) -> None:
    """Registers security headers and rate limiter with the Flask application.

    Args:
        app: The Flask application instance.
    """
    # Disable rate limiting if testing config is active
    if app.config.get("TESTING"):
        app.config["RATELIMIT_ENABLED"] = False

    # Initialize rate limiter on the app
    limiter.init_app(app)

    @app.after_request
    def apply_security_headers(response: Response) -> Response:
        """Appends security headers to every outgoing HTTP response.

        Args:
            response: The outgoing response object.

        Returns:
            The modified response object containing security headers.
        """
        # Strict-Transport-Security (HSTS)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        # X-Frame-Options (prevent clickjacking)
        response.headers["X-Frame-Options"] = "DENY"
        # X-Content-Type-Options (prevent MIME sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content-Security-Policy (CSP)
        # Allows self, Google Fonts, and Cloudflare CDNs for scripts/styles
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com fonts.googleapis.com; "
            "font-src 'self' cdnjs.cloudflare.com fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        return response
