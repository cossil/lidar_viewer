"""Standard API error envelope (PRD section 25.

All errors are returned as::

    {"error": {"code": str, "message": str, "field": str | None, "details": {}}}

Recommended error codes:
INVALID_PARAMETER, MISSING_PARAMETER, INVALID_UNIT, UNKNOWN_SENSOR,
UNKNOWN_SCENARIO, UNKNOWN_SIMULATION, INVALID_GEOMETRY,
INVALID_DETECTION_MODEL, INSUFFICIENT_DATA, SIMULATION_NOT_COMPLETE,
SIMULATION_FAILED, INTERNAL_ERROR.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Raise inside route handlers to surface a standard error envelope."""

    def __init__(
        self,
        status_code: int = 400,
        code: str = "INVALID_PARAMETER",
        message: str = "An error occurred.",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        self.details = details or {}


def api_error(
    request: Request, exc: Exception, status_code: int | None = None
) -> JSONResponse:
    """Build the standard error envelope response for an exception."""
    code = "INTERNAL_ERROR"
    message = str(exc) or "Internal server error."
    field: Optional[str] = None
    details: Dict[str, Any] = {}
    effective_status = status_code or 500

    if isinstance(exc, ApiError):
        code = exc.code
        message = exc.message or message
        field = exc.field
        details = exc.details or {}
        effective_status = status_code or exc.status_code

    return JSONResponse(
        status_code=effective_status,
        content={
            "error": {
                "code": code,
                "message": message,
                "field": field,
                "details": details,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Wire the standard error handler(s) onto the app."""

    @app.exception_handler(ApiError)
    async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return api_error(request, exc)