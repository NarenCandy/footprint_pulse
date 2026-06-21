"""WSGI entry point for the Footprint Pulse application.

This script instantiates the Flask application using the factory function
and starts a development server if run directly.
"""

from app import create_app
from flask import Flask

app: Flask = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
