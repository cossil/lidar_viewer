"""REST API layer.

PRD section 58: FastAPI application with CRUD endpoints.
"""

from .app import app, create_app

__all__ = ["app", "create_app"]